"""v1 webhooks with pagination."""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from typing import Optional

router=APIRouter()

# reuse storage from api.webhooks
try:
    from ..webhooks import webhooks_storage, Webhook, CreateWebhookRequest, trigger_webhook
except: webhooks_storage={}; Webhook=None

@router.get("/webhooks")
async def v1_list(limit: int=Query(20, le=100), offset: int=0, fields: Optional[str]=None):
    vals=list(webhooks_storage.values()); total=len(vals); page=vals[offset:offset+limit]
    data=[v.model_dump(mode="json") for v in page]
    if fields:
        keep=set(fields.split(",")); data=[{k:v for k,v in d.items() if k in keep} for d in data]
    return {"total":total,"count":len(data),"offset":offset,"limit":limit,"data":data}

@router.post("/webhooks")
async def v1_create(req: CreateWebhookRequest):
    from ..webhooks import create_webhook
    return await create_webhook(req)

@router.get("/webhooks/{wid}")
async def v1_get(wid: str): 
    if wid not in webhooks_storage: raise HTTPException(404,"not found")
    return webhooks_storage[wid]

@router.post("/webhooks/{wid}/test")
async def v1_test(wid: str, background_tasks: BackgroundTasks):
    if wid not in webhooks_storage: raise HTTPException(404,"not found")
    wh=webhooks_storage[wid]
    from datetime import datetime
    payload={"test":True,"ts":datetime.now().isoformat()}
    background_tasks.add_task(trigger_webhook, wh, "test", payload)
    return {"status":"test_queued","webhook_id":wid}

@router.delete("/webhooks/{wid}")
async def v1_del(wid: str):
    if wid not in webhooks_storage: raise HTTPException(404,"not found")
    del webhooks_storage[wid]
    return {"status":"deleted","webhook_id":wid}
