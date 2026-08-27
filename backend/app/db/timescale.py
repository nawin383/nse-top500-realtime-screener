"""TimescaleDB interface with file fallback for candles."""
from __future__ import annotations
import json, os, asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

try:
    import asyncpg  # type: ignore
    _has_pg=True
except: _has_pg=False

FALLBACK = Path(__file__).resolve().parents[3] / "backend" / "data" / "candles.jsonl"
FALLBACK2 = Path("backend/data/candles.jsonl")

class TimescaleStore:
    def __init__(self, dsn: str = ""):
        self.dsn = dsn or os.getenv("TIMESCALE_DSN","")
        self.pool=None
        self._fallback = FALLBACK if FALLBACK.parent.exists() else FALLBACK2

    async def connect(self):
        if _has_pg and self.dsn:
            try:
                self.pool=await asyncpg.create_pool(self.dsn, min_size=1, max_size=3)
            except: self.pool=None

    async def save_candles(self, candles: List[dict]):
        if self.pool:
            try:
                async with self.pool.acquire() as c:
                    for ch in candles:
                        await c.execute("INSERT INTO candles(symbol,interval,ts,open,high,low,close,volume) VALUES($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT DO NOTHING",
                            ch["symbol"], ch["interval"], ch["timestamp"], ch["open"], ch["high"], ch["low"], ch["close"], ch["volume"])
                return
            except: pass
        # fallback file
        try:
            self._fallback.parent.mkdir(parents=True, exist_ok=True)
            with open(self._fallback,"a") as f:
                for ch in candles:
                    f.write(json.dumps(ch,default=str)+"\n")
        except: pass

    async def query(self, symbol: str, interval: int=1, limit: int=100) -> List[dict]:
        if self.pool:
            try:
                async with self.pool.acquire() as c:
                    rows=await c.fetch("SELECT * FROM candles WHERE symbol=$1 AND interval=$2 ORDER BY ts DESC LIMIT $3", symbol, interval, limit)
                    return [dict(r) for r in rows]
            except: pass
        # fallback
        if not self._fallback.exists(): return []
        out=[]
        try:
            with open(self._fallback) as f:
                for line in f:
                    try:
                        j=json.loads(line)
                        if j.get("symbol")==symbol and j.get("interval")==interval:
                            out.append(j)
                    except: continue
            out.sort(key=lambda x: x.get("timestamp",""), reverse=True)
            return out[:limit]
        except: return []

    async def backtest_query(self, symbol: str, start: datetime, end: datetime, interval:int=1) -> List[dict]:
        rows=await self.query(symbol, interval, limit=10000)
        def _in(r):
            try: ts=datetime.fromisoformat(str(r["timestamp"]).replace("Z",""))
            except: return False
            return start <= ts <= end
        return [r for r in rows if _in(r)]

store = TimescaleStore()
