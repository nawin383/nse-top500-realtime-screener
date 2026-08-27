"""Mock data provider - generates realistic market ticks for all 500 instruments for testing without API credentials."""
from __future__ import annotations
import asyncio
import random
import logging
from datetime import datetime, timedelta
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

class MockProvider(BaseProvider):
    def __init__(self, universe: List[Dict[str, Any]], tick_interval_ms: int = 200, volatility: float = 0.008):
        super().__init__(universe)
        self.tick_interval_ms = tick_interval_ms
        self.volatility = volatility
        self._running = False
        # state per symbol: ltp, open, high, low, prev_close, volume
        self._state: Dict[str, Dict] = {}
        for u in universe:
            prev = u.get("prev_close") or random.uniform(100, 3000)
            # ensure realistic base
            base = prev
            self._state[u["symbol"]] = {
                "ltp": base,
                "open": base * random.uniform(0.995, 1.005),
                "high": base * random.uniform(1.005, 1.02),
                "low": base * random.uniform(0.98, 0.995),
                "prev_close": base,
                "volume": random.randint(100000, 800000),
                "token": u["instrument_token"],
            }
            # fix high/low sanity
            s = self._state[u["symbol"]]
            s["high"] = max(s["high"], s["ltp"], s["open"])
            s["low"] = min(s["low"], s["ltp"], s["open"])

    @property
    def name(self) -> str:
        return "mock"

    async def start(self, on_ticks):
        self._running = True
        logger.info(f"MockProvider starting for {len(self.universe)} symbols, interval {self.tick_interval_ms}ms")
        ticks_total = 0
        while self._running:
            ticks: List[MarketTick] = []
            now = datetime.now(tz=IST)
            # generate a batch: randomly pick subset to update each interval to simulate real market (~30-60 ticks per batch)
            batch_size = random.randint(30, 120)
            symbols = random.sample(list(self._state.keys()), k=min(batch_size, len(self._state)))
            for sym in symbols:
                st = self._state[sym]
                # random walk
                change_pct = random.gauss(0, self.volatility/2)
                # occasionally spike
                if random.random() < 0.01:
                    change_pct = random.choice([-1,1]) * random.uniform(1.0, 3.0)
                new_ltp = st["ltp"] * (1 + change_pct/100)
                new_ltp = round(max(new_ltp, 1.0), 2)
                st["ltp"] = new_ltp
                # update high/low
                st["high"] = max(st["high"], new_ltp)
                st["low"] = min(st["low"], new_ltp)
                # volume increment
                vol_inc = random.randint(100, 5000)
                st["volume"] += vol_inc
                # randomly pick bid/ask spread
                spread = new_ltp * 0.0005
                bid = round(new_ltp - spread/2, 2)
                ask = round(new_ltp + spread/2, 2)
                tick = MarketTick(
                    symbol=sym,
                    token=st["token"],
                    timestamp=now,
                    ltp=new_ltp,
                    last_quantity=random.randint(1, 1000),
                    open=st["open"],
                    high=st["high"],
                    low=st["low"],
                    previousClose=st["prev_close"],
                    volume=st["volume"],
                    bid=bid,
                    ask=ask,
                    bid_qty=random.randint(100, 5000),
                    ask_qty=random.randint(100, 5000),
                )
                ticks.append(tick)
            if ticks:
                ticks_total += len(ticks)
                try:
                    res = on_ticks(ticks)
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as e:
                    logger.error(f"mock on_ticks error {e}", exc_info=True)
            await asyncio.sleep(self.tick_interval_ms/1000)

    async def stop(self):
        self._running = False
        logger.info("MockProvider stopped")
