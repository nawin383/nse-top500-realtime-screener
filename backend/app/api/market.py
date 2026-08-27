from fastapi import APIRouter, Depends
from datetime import datetime
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

@router.get("/market/status", response_model=MarketStatusResponse)
async def market_status():
    now = now_ist()
    status, is_live = get_market_status(now)
    label = label_for_status(status, is_live)
    # last_data_received injected via app.state
    from ..main import app_state
    last = None
    if app_state.get("market_state"):
        last = app_state["market_state"]._last_data_received
    # next open/close
    from ..market_hours import next_open_close
    nxt_open, nxt_close = next_open_close(now)
    return MarketStatusResponse(
        status=status, is_live=is_live, label=label,
        last_data_received=last,
        server_time_ist=now,
        next_open=nxt_open,
        next_close=nxt_close
    )

@router.get("/market/overview")
async def market_overview():
    from ..main import app_state
    ms = app_state.get("market_state")
    if not ms:
        return {"error":"market state not initialized"}
    ov = ms.market_overview()
    # need to serialize ScreenerResult correctly
    return ov.model_dump()
