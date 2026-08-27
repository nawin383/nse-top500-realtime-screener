"""Replay provider - replays recorded ticks from file at configurable speed."""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

from .base import BaseProvider
from ..models import MarketTick

logger = logging.getLogger(__name__)

class ReplayProvider(BaseProvider):
    def __init__(self, universe: List[Dict[str, Any]], replay_file: str = "", speed: float = 10.0):
        super().__init__(universe)
        self.replay_file = Path(replay_file) if replay_file else None
        self.speed = speed
        self._running = False
        self.token_to_symbol = {u["instrument_token"]: u["symbol"] for u in universe}

    @property
    def name(self) -> str:
        return "replay"

    async def start(self, on_ticks):
        self._running = True
        # if no file exists, generate synthetic replay data on fly
        if not self.replay_file or not self.replay_file.exists():
            logger.warning(f"Replay file {self.replay_file} not found, using synthetic generation")
            # fallback to mock-like but deterministic replay
            from .mock_provider import MockProvider
            mock = MockProvider(self.universe, tick_interval_ms=int(1000/self.speed*200))
            await mock.start(on_ticks)
            return

        logger.info(f"Replay start file={self.replay_file} speed={self.speed}x")
        with open(self.replay_file, "r") as f:
            records = [json.loads(line) for line in f if line.strip()]

        # sort by timestamp
        records.sort(key=lambda x: x.get("timestamp",""))

        prev_ts = None
        ticks_buf: List[MarketTick] = []
        for rec in records:
            if not self._running:
                break
            # parse record: expected {token, ltp, volume, timestamp, ...}
            try:
                ts_str = rec.get("timestamp")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=IST)
                else:
                    ts = datetime.now(tz=IST)
                # speed handling: sleep delta / speed
                if prev_ts:
                    delta = (ts - prev_ts).total_seconds()
                    sleep_s = max(0, delta / self.speed)
                    if sleep_s > 0 and sleep_s < 5:
                        await asyncio.sleep(sleep_s)
                prev_ts = ts
                token = rec.get("instrument_token") or rec.get("token")
                sym = self.token_to_symbol.get(token) or rec.get("symbol")
                if not sym:
                    continue
                tick = MarketTick(
                    symbol=sym, token=token, timestamp=ts,
                    ltp=rec.get("last_price") or rec.get("ltp") or 0,
                    last_quantity=rec.get("last_quantity",0),
                    open=rec.get("ohlc",{}).get("open") if isinstance(rec.get("ohlc"),dict) else rec.get("open"),
                    high=rec.get("ohlc",{}).get("high") if isinstance(rec.get("ohlc"),dict) else rec.get("high"),
                    low=rec.get("ohlc",{}).get("low") if isinstance(rec.get("ohlc"),dict) else rec.get("low"),
                    previousClose=rec.get("ohlc",{}).get("close") if isinstance(rec.get("ohlc"),dict) else rec.get("previous_close"),
                    volume=rec.get("volume",0),
                    bid=rec.get("bid"), ask=rec.get("ask"),
                )
                ticks_buf.append(tick)
                # batch dispatch every 10 ticks or 100ms
                if len(ticks_buf) >= 20:
                    res = on_ticks(ticks_buf)
                    if asyncio.iscoroutine(res):
                        await res
                    ticks_buf=[]
            except Exception as e:
                logger.error(f"replay parse error {e}")
        # flush
        if ticks_buf:
            res = on_ticks(ticks_buf)
            if asyncio.iscoroutine(res):
                await res
        logger.info("Replay finished")

    async def stop(self):
        self._running=False
