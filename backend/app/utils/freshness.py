from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

def compute_freshness(last_ts, stale_sec: int, now=None) -> str:
    if last_ts is None:
        return "NO_DATA"
    if now is None:
        now = datetime.now(tz=IST)
    # ensure tz aware
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=IST)
    delta = (now - last_ts).total_seconds()
    if delta <= stale_sec:
        return "LIVE"
    if delta <= stale_sec * 3:
        return "DELAYED"
    return "STALE"
