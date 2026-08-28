from fastapi import APIRouter, Query, HTTPException

router = APIRouter()


@router.get("/analytics/vix-open-volatility")
async def vix_open_volatility(days: int = Query(60, ge=10, le=200)):
    from ..analytics.vix_open_volatility import analyze
    try:
        return await analyze(days=days)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"VIX volatility analysis unavailable: {e}")


@router.get("/etf/screener")
async def etf_screener():
    from ..analytics.etf_screener import screener
    try:
        return await screener()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ETF screener unavailable: {e}")
