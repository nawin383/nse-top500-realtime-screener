"""Signal modules: OHLC Breaker breakout (Part 3), intraday strategies (Part 4)."""
from dataclasses import asdict
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/signals/breaker")
async def breaker_signals(min_score: float = Query(0.0, ge=0, le=100), limit: int = Query(50, ge=1, le=500)):
    from ..main import app_state
    ms = app_state.get("market_state")
    if not ms:
        return {"error": "market state not ready"}
    signals = ms.get_breaker_signals(min_score=min_score)[:limit]
    return {
        "count": len(signals),
        "gates": {"rvol_gate": 1.5, "adx_gate": 20.0, "retest_hold_candles": 2},
        "data": [asdict(s) for s in signals],
    }


@router.get("/signals/intraday")
async def intraday_signals():
    from ..main import app_state
    ms = app_state.get("market_state")
    if not ms:
        return {"error": "market state not ready"}
    return {
        "note": "hit_rate is a same-session forward-tracked outcome rate (real signals followed against live ticks), not a historical backtest -- no multi-day historical data source is reachable from this environment.",
        "strategies": ms.get_intraday_signals(),
    }
