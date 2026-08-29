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


@router.get("/analytics/elite-quant")
async def elite_quant_scan(market: str = Query("IN", pattern="^(IN|US)$"), limit: int = Query(50, ge=1, le=100)):
    """Serves the once-a-day cached elite-quant scan -- never runs the scan
    itself (that's the background scheduler's job), so this always responds
    instantly regardless of whether yfinance is even installed."""
    from ..analytics import elite_quant
    cached = elite_quant.read_cache(market)
    if not cached:
        return {"available": False, "reason": "No scan has completed yet for this market — check back after the next daily run", "market": market, "rows": []}
    rows = cached.get("rows", [])[:limit]
    return {**cached, "rows": rows}


@router.get("/analytics/elite-quant/status")
async def elite_quant_status():
    from ..analytics import elite_quant
    out = {}
    for market, cfg in elite_quant.MARKETS.items():
        cached = elite_quant.read_cache(market)
        out[market] = {
            "label": cfg.label, "universeSize": len(cfg.symbols),
            "generatedAt": cached.get("generatedAt") if cached else None,
            "analyzed": cached.get("analyzed") if cached else None,
            "stale": elite_quant.is_stale(market),
        }
    return out
