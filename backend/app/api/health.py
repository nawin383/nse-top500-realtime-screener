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
    # compatible with both "ok" and "healthy" checks
    return {"status":"ok", "healthy": True, "timestamp": datetime.now(tz=IST).isoformat(), "service":"nse-top500-screener"}

@router.get("/healthz")
async def healthz():
    return {"status":"healthy", "timestamp": datetime.now(tz=IST).isoformat()}

@router.get("/ready")
async def ready():
    return {"ready": True}
