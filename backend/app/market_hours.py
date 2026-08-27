"""NSE market hours in Asia/Kolkata timezone."""
from __future__ import annotations
from datetime import datetime, time, timedelta
from typing import Tuple, Optional

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

# NSE trading hours
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
PRE_OPEN_START = time(9, 0)
PRE_OPEN_END = time(9, 15)
POST_CLOSE_END = time(16, 0)

# 2026 NSE holidays (subset + weekly weekends). In production, load from config or API.
NSE_HOLIDAYS_2026 = {
    "2026-01-26", "2026-03-14", "2026-03-31", "2026-04-14", "2026-04-18",
    "2026-05-01", "2026-08-15", "2026-10-02", "2026-10-21", "2026-10-22",
    "2026-11-05", "2026-12-25",
}

def now_ist() -> datetime:
    return datetime.now(tz=IST)

def is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5

def is_holiday(dt: datetime) -> bool:
    dstr = dt.strftime("%Y-%m-%d")
    return dstr in NSE_HOLIDAYS_2026 or is_weekend(dt)

def get_market_status(dt: Optional[datetime] = None) -> Tuple[str, bool]:
    """Returns (status, is_live). status in pre_open|open|closed|post_close|holiday"""
    if dt is None:
        dt = now_ist()
    if is_holiday(dt):
        return "holiday", False
    t = dt.time()
    if PRE_OPEN_START <= t < PRE_OPEN_END:
        return "pre_open", False
    if MARKET_OPEN <= t <= MARKET_CLOSE:
        return "open", True
    if MARKET_CLOSE < t <= POST_CLOSE_END:
        return "post_close", False
    return "closed", False

def next_open_close(dt: Optional[datetime] = None):
    if dt is None:
        dt = now_ist()
    # find next open (skip holidays)
    d = dt
    for _ in range(10):
        if not is_holiday(d):
            open_dt = datetime.combine(d.date(), MARKET_OPEN, tzinfo=IST)
            close_dt = datetime.combine(d.date(), MARKET_CLOSE, tzinfo=IST)
            if d < open_dt:
                return open_dt, close_dt
            if d <= close_dt and not is_holiday(dt):
                # today is open day and we are within or before close
                if dt <= close_dt:
                    return (open_dt if dt < open_dt else None), close_dt
        d = d + timedelta(days=1)
        d = datetime.combine(d.date(), time(9, 0), tzinfo=IST)
    return None, None

def label_for_status(status: str, is_live: bool) -> str:
    if status == "open" and is_live:
        return "LIVE"
    if status == "holiday":
        return "HOLIDAY"
    return "MARKET CLOSED"
