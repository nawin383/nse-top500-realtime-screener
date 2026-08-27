from fastapi import APIRouter, Query, Request
from typing import Optional
try:
    from ..cache import get_cache
except: get_cache=lambda: None

router = APIRouter()

@router.get("/screener/{name}")
async def screener(name: str, limit: int = 20, request: Request = None):
    from ..main import app_state
    ms = app_state.get("market_state")
    if not ms:
        return {"error":"market state not ready"}
    from ..screeners import SCREENERS
    fn = SCREENERS.get(name)
    if not fn:
        return {"error": f"Unknown screener {name}", "available": list(SCREENERS.keys())}
    cache = get_cache()
    key = {"screener":name,"limit":limit}
    if cache:
        hit = cache.get("screener", key)
        if hit is not None: return hit
    states = ms.all_states()
    results = fn(states, limit=limit)
    payload = {"screener": name, "count": len(results), "data": [r.model_dump() for r in results]}
    if cache:
        try: cache.set("screener", key, payload, ttl=5)
        except: pass
    return payload

@router.get("/screener")
async def list_screeners():
    from ..screeners import SCREENERS
    return {"available": list(SCREENERS.keys())}
