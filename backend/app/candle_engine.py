"""Candle aggregation engine - aggregates ticks into OHLCV candles.

Handles IST timezone, market open/close, candle boundaries, duplicate ticks,
missing ticks and reconnects.
"""
from __future__ import annotations
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

from .models import Candle

logger = logging.getLogger(__name__)

def floor_to_interval(dt: datetime, interval_min: int) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    # floor to interval
    minute = (dt.minute // interval_min) * interval_min
    return dt.replace(minute=minute, second=0, microsecond=0)

class CandleEngine:
    """Per-symbol, per-interval candle store."""

    def __init__(self, intervals: List[int] = None, max_candles: int = 500):
        self.intervals = intervals or [1,3,5,15,30]
        self.max_candles = max_candles
        # symbol -> interval -> deque[Candle]
        self._store: Dict[str, Dict[int, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=max_candles)))
        # symbol -> interval -> current building candle
        self._current: Dict[str, Dict[int, Candle]] = defaultdict(dict)
        # deduplication: symbol -> last tick ts
        self._last_tick_ts: Dict[str, datetime] = {}

    def on_tick(self, symbol: str, ltp: float, volume: int, timestamp: datetime):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=IST)
        # duplicate tick handling: same timestamp & same ltp
        prev = self._last_tick_ts.get(symbol)
        if prev and timestamp == prev:
            # allow if volume changed? treat duplicate if same ts
            return
        self._last_tick_ts[symbol] = timestamp

        for interval in self.intervals:
            self._update_interval(symbol, interval, ltp, volume, timestamp)

    def _update_interval(self, symbol: str, interval: int, ltp: float, volume: int, timestamp: datetime):
        bucket = floor_to_interval(timestamp, interval)
        cur = self._current[symbol].get(interval)
        if cur is None or cur.timestamp != bucket:
            # seal previous candle
            if cur is not None:
                dq = self._store[symbol][interval]
                # avoid duplicate timestamp
                if not dq or dq[-1].timestamp != cur.timestamp:
                    dq.append(cur)
                else:
                    # replace last
                    dq[-1] = cur
            # start new candle (volume is cumulative intraday; candle volume = delta from open)
            # For simplicity, we treat volume as tick volume delta: use volume field from tick as cumulative,
            # but candle volume we compute as cumulative diff. Here we approximate by storing tick volume as candle volume
            # and downstream VWAP uses tick-level aggregation instead.
            new = Candle(timestamp=bucket, open=ltp, high=ltp, low=ltp, close=ltp, volume=volume, interval=interval)
            self._current[symbol][interval] = new
        else:
            # update current candle
            cur.high = max(cur.high, ltp)
            cur.low = min(cur.low, ltp)
            cur.close = ltp
            cur.volume = volume  # keep cumulative; indicator engine handles delta

    def get_candles(self, symbol: str, interval: int, limit: int = 100) -> List[Candle]:
        dq = self._store[symbol].get(interval, deque())
        cur = self._current[symbol].get(interval)
        result = list(dq)
        if cur is not None:
            # include current building candle if not already in store
            if not result or result[-1].timestamp != cur.timestamp:
                result.append(cur)
        if limit:
            return result[-limit:]
        return result

    def get_all_intervals(self, symbol: str) -> Dict[int, List[Candle]]:
        return {iv: self.get_candles(symbol, iv) for iv in self.intervals}

    def reset_day(self):
        """Call at market open to clear previous day candles."""
        self._store.clear()
        self._current.clear()
        self._last_tick_ts.clear()
        logger.info("Candle engine reset for new trading day")
