from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

@router.get("/alerts")
async def list_alerts(limit: int = 100, symbol: Optional[str] = None, type: Optional[str] = None):
    from ..main import app_state
    ae = app_state.get("alert_engine")
    if not ae:
        return {"count":0, "data":[]}
    alerts = ae.get_recent(limit=limit, symbol=symbol.upper() if symbol else None, atype=type)
    return {"count": len(alerts), "data": [a.model_dump() for a in alerts]}

@router.delete("/alerts")
async def clear_alerts():
    from ..main import app_state
    ae = app_state.get("alert_engine")
    if ae:
        ae.clear()
    return {"cleared": True}
