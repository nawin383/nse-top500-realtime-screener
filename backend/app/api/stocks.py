from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter()

@router.get("/stocks")
async def list_stocks(
    search: Optional[str] = None,
    sector: Optional[str] = None,
    sort_by: str = "rank",
    order: str = "asc",
    limit: int = Query(500, le=500),
    offset: int = 0,
    freshness: Optional[str] = None,
):
    from ..main import app_state
    ms = app_state.get("market_state")
    if not ms:
        raise HTTPException(500, "market state not ready")
    states = ms.ranking()  # already ranked and freshness refreshed
    # filters
    filtered = states
    if search:
        s_lower = search.lower()
        filtered = [x for x in filtered if s_lower in x.symbol.lower() or s_lower in (x.company or "").lower()]
    if sector and sector != "All":
        filtered = [x for x in filtered if x.sector == sector]
    if freshness:
        filtered = [x for x in filtered if x.freshness == freshness]
    # sorting
    sort_key_map = {
        "rank": lambda x: x.rank or 9999,
        "symbol": lambda x: x.symbol,
        "ltp": lambda x: x.ltp or 0,
        "change_pct": lambda x: x.change_pct or -999,
        "volume": lambda x: x.volume or 0,
        "rel_volume": lambda x: x.rel_volume or 0,
        "vwap": lambda x: x.indicators.vwap or 0,
        "rsi": lambda x: x.indicators.rsi or 0,
        "score": lambda x: x.score or 0,
        "momentum": lambda x: x.momentum.ret_5m or 0,
    }
    key_fn = sort_key_map.get(sort_by, sort_key_map["rank"])
    reverse = order == "desc"
    # rank is asc, others usually desc
    filtered = sorted(filtered, key=key_fn, reverse=reverse)
    total = len(filtered)
    paged = filtered[offset: offset+limit]
    # minimal representation
    def minimal(s):
        return {
            "symbol": s.symbol,
            "token": s.token,
            "company": s.company,
            "sector": s.sector,
            "industry": s.industry,
            "ltp": s.ltp,
            "change": s.change,
            "change_pct": round(s.change_pct,2) if s.change_pct is not None else None,
            "volume": s.volume,
            "rel_volume": round(s.rel_volume,2) if s.rel_volume else None,
            "high": s.high, "low": s.low, "open": s.open, "previous_close": s.previous_close,
            "vwap": round(s.indicators.vwap,2) if s.indicators.vwap else None,
            "rsi": round(s.indicators.rsi,1) if s.indicators.rsi else None,
            "ema9": round(s.indicators.ema9,2) if s.indicators.ema9 else None,
            "ema20": round(s.indicators.ema20,2) if s.indicators.ema20 else None,
            "score": s.score,
            "signal": s.signal,
            "rank": s.rank,
            "freshness": s.freshness,
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "momentum": s.momentum.model_dump(),
            "indicators": s.indicators.model_dump(),
        }
    payload={"total": total, "count": len(paged), "offset": offset, "limit": limit, "data": [minimal(s) for s in paged]}
    # compat for tests expecting "stocks" key
    payload["stocks"]=payload["data"]
    return payload

@router.get("/stocks/{symbol}")
async def get_stock(symbol: str):
    from ..main import app_state
    ms = app_state.get("market_state")
    if not ms:
        raise HTTPException(500, "market state not ready")
    sym = symbol.upper()
    state = ms.get_state(sym)
    if not state:
        raise HTTPException(404, f"Symbol {sym} not found")
    # get candles
    candles = {}
    for iv in [1,3,5,15,30]:
        lst = ms.candle_engine.get_candles(sym, iv, limit=100)
        candles[str(iv)] = [c.model_dump() for c in lst]
    return {
        "symbol": state.symbol,
        "token": state.token,
        "company": state.company,
        "sector": state.sector,
        "industry": state.industry,
        "ltp": state.ltp,
        "change": state.change,
        "change_pct": state.change_pct,
        "open": state.open, "high": state.high, "low": state.low, "previous_close": state.previous_close,
        "volume": state.volume,
        "avg_price": state.avg_price,
        "bid": state.bid, "ask": state.ask,
        "freshness": state.freshness,
        "distance_from_high_pct": state.distance_from_high_pct,
        "distance_from_low_pct": state.distance_from_low_pct,
        "range_pct": state.range_pct,
        "gap_pct": state.gap_pct,
        "rel_volume": state.rel_volume,
        "volume_spike": state.volume_spike,
        "indicators": state.indicators.model_dump(),
        "momentum": state.momentum.model_dump(),
        "score": state.score,
        "score_breakdown": state.score_breakdown,
        "signal": state.signal,
        "signal_strength": state.signal_strength,
        "rank": state.rank,
        "timestamp": state.timestamp.isoformat() if state.timestamp else None,
        "candles": candles,
    }

@router.get("/universe")
async def get_universe():
    from ..main import app_state
    from ..config import UNIVERSE_PATH
    from fastapi import HTTPException
    if not UNIVERSE_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Universe file missing at {UNIVERSE_PATH}")
    uni = app_state.get("universe")
    if not uni or len(uni)==0:
        raise HTTPException(status_code=500, detail="Universe not loaded — check config/nse_top500.json")
    return {"count": len(uni) if uni else 0, "data": uni}
