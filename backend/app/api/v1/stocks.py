from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router=APIRouter()

@router.get("/stocks")
async def v1_list(search: Optional[str]=None, sector: Optional[str]=None, sort_by: str="rank", order: str="asc",
    limit: int=Query(50,le=500), offset: int=0, freshness: Optional[str]=None, fields: Optional[str]=None):
    from ...main import app_state
    ms=app_state.get("market_state")
    if not ms: raise HTTPException(500,"not ready")
    states=ms.ranking()
    filt=states
    if search:
        s=search.lower(); filt=[x for x in filt if s in x.symbol.lower() or s in (x.company or "").lower()]
    if sector and sector!="All": filt=[x for x in filt if x.sector==sector]
    if freshness: filt=[x for x in filt if x.freshness==freshness]
    keys={"rank":lambda x:x.rank or 9999,"symbol":lambda x:x.symbol,"ltp":lambda x:x.ltp or 0,"change_pct":lambda x:x.change_pct or -999,"volume":lambda x:x.volume or 0,"score":lambda x:x.score or 0}
    filt=sorted(filt, key=keys.get(sort_by, keys["rank"]), reverse=(order=="desc"))
    total=len(filt); page=filt[offset:offset+limit]
    def proj(s):
        d={"symbol":s.symbol,"token":s.token,"ltp":s.ltp,"change_pct":s.change_pct,"volume":s.volume,"score":s.score,"sector":s.sector,"freshness":s.freshness,"rank":s.rank}
        if fields: 
            keep=set(fields.split(",")); d={k:v for k,v in d.items() if k in keep or k=="symbol"}
        return d
    return {"total":total,"count":len(page),"offset":offset,"limit":limit,"data": [proj(s) for s in page], "stocks":[proj(s) for s in page]}

@router.get("/stocks/{symbol}")
async def v1_get(symbol: str, fields: Optional[str]=None):
    from ...main import app_state
    ms=app_state.get("market_state")
    s=ms.get_state(symbol.upper()) if ms else None
    if not s: raise HTTPException(404,"not found")
    d=s.model_dump()
    if fields:
        keep=set(fields.split(",")); d={k:v for k,v in d.items() if k in keep}
    return d
