from fastapi import APIRouter
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

router = APIRouter()

@router.get("/health")
async def health():
    return {"status":"ok", "timestamp": datetime.now(tz=IST).isoformat(), "service":"nse-top500-screener"}

@router.get("/ready")
async def ready():
    return {"ready": True}
