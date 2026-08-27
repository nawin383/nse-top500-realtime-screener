from fastapi import APIRouter, Depends, Request
from datetime import datetime
try:
    from ..cache import get_cache
except: get_cache=lambda: None
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")
from ..market_hours import get_market_status, label_for_status, now_ist
from ..models import MarketStatusResponse

router = APIRouter()

def get_market_state():
    # will be overridden via dependency injection in main.py
    pass

@router.get("/market/status")
async def market_status():
    now = now_ist()
    status, is_live = get_market_status(now)
    label = label_for_status(status, is_live)
    from ..main import app_state
    last = None
    if app_state.get("market_state"):
        last = app_state["market_state"]._last_data_received
    from ..market_hours import next_open_close
    nxt_open, nxt_close = next_open_close(now)
    resp = MarketStatusResponse(status=status, is_live=is_live, label=label, last_data_received=last, server_time_ist=now, next_open=nxt_open, next_close=nxt_close)
    data = resp.model_dump()
    # compat: add is_open alias expected by some tests
    data["is_open"] = is_live
    return data

@router.get("/market/overview")
async def market_overview(request: Request = None):
    from ..main import app_state
    ms = app_state.get("market_state")
    if not ms:
        return {"error":"market state not initialized"}
    cache = get_cache()
    key = {"path":"overview"}
    if cache:
        hit = cache.get("market", key)
        if hit is not None: return hit
    ov = ms.market_overview()
    data = ov.model_dump()
    if cache:
        try: cache.set("market", key, data, ttl=10)
        except: pass
    return data
