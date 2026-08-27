from fastapi import APIRouter, Query, Request
from typing import Optional
try: from ...cache import get_cache
except: get_cache=lambda: None

router=APIRouter()

@router.get("/market/status")
async def v1_status():
    from ...main import app_state
    from ...market_hours import get_market_status, label_for_status, now_ist, next_open_close
    from ...models import MarketStatusResponse
    now=now_ist(); s,live=get_market_status(now); label=label_for_status(s,live)
    last=app_state.get("market_state")._last_data_received if app_state.get("market_state") else None
    nxt_o,nxt_c=next_open_close(now)
    r=MarketStatusResponse(status=s,is_live=live,label=label,last_data_received=last,server_time_ist=now,next_open=nxt_o,next_close=nxt_c)
    d=r.model_dump(); d["is_open"]=live; return d

@router.get("/market/overview")
async def v1_overview(fields: Optional[str]=None):
    from ...main import app_state
    ms=app_state.get("market_state")
    if not ms: return {"error":"not ready"}
    cache=get_cache(); key={"v1_overview": fields}
    if cache:
        hit=cache.get("v1_market", key)
        if hit: return hit
    ov=ms.market_overview().model_dump()
    if fields:
        keep=set(fields.split(","))
        ov={k:v for k,v in ov.items() if k in keep}
    if cache:
        try: cache.set("v1_market", key, ov, ttl=10)
        except: pass
    return ov
