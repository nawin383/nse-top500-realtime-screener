from fastapi import APIRouter, Query, Request
from typing import Optional
try: from ...cache import get_cache
except: get_cache=lambda: None
router=APIRouter()
@router.get("/screener")
async def v1_list(): from ...screeners import SCREENERS; return {"available": list(SCREENERS.keys())}
@router.get("/screener/{name}")
async def v1_screener(name: str, limit: int=20, offset:int=0, sort_by: Optional[str]=None, order: str="desc", fields: Optional[str]=None, filter: Optional[str]=None):
    from ...main import app_state; from ...screeners import SCREENERS
    ms=app_state.get("market_state")
    if not ms: return {"error":"not ready"}
    fn=SCREENERS.get(name)
    if not fn: return {"error":"unknown","available": list(SCREENERS.keys())}
    cache=get_cache(); key={"v1_screener":name,"limit":limit,"offset":offset,"sort":sort_by,"filter":filter}
    if cache:
        hit=cache.get("v1_screener", key)
        if hit: return hit
    states=ms.all_states()
    results=fn(states, limit=limit+offset)
    # offset paginate
    results=results[offset:offset+limit]
    if sort_by and results:
        rev=order=="desc"
        try: results=sorted(results, key=lambda x: getattr(x, sort_by, 0) or 0, reverse=rev)
        except: pass
    data=[r.model_dump() for r in results]
    if fields:
        keep=set(fields.split(","))
        data=[{k:v for k,v in d.items() if k in keep or k=="symbol"} for d in data]
    if filter:
        try:
            k,v=filter.split("=",1)
            data=[d for d in data if str(d.get(k,""))==v]
        except: pass
    payload={"screener":name,"count":len(data),"offset":offset,"limit":limit,"data":data}
    if cache:
        try: cache.set("v1_screener", key, payload, ttl=5)
        except: pass
    return payload
