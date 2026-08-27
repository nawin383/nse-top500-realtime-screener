from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

@router.get("/screener/{name}")
async def screener(name: str, limit: int = 20):
    from ..main import app_state
    ms = app_state.get("market_state")
    if not ms:
        return {"error":"market state not ready"}
    from ..screeners import SCREENERS
    fn = SCREENERS.get(name)
    if not fn:
        return {"error": f"Unknown screener {name}", "available": list(SCREENERS.keys())}
    states = ms.all_states()
    results = fn(states, limit=limit)
    return {"screener": name, "count": len(results), "data": [r.model_dump() for r in results]}

@router.get("/screener")
async def list_screeners():
    from ..screeners import SCREENERS
    return {"available": list(SCREENERS.keys())}
