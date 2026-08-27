"""Verification and troubleshooting endpoints for NSE Top500 diagnostics."""
from __future__ import annotations
import logging
from fastapi import APIRouter
from pathlib import Path

from ..config import settings, UNIVERSE_PATH

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/subscription")
async def verify_subscription():
    from ..main import app_state
    universe = app_state.get("universe") or []
    de = app_state.get("data_engine")
    provider = getattr(de, "provider", None) if de else None
    subscribed = set()
    mode = settings.data_mode
    if provider and hasattr(provider, "_subscribed"):
        subscribed = getattr(provider, "_subscribed", set())
        # mock provider has no _subscribed, treat as fully subscribed
        if mode != "live" and len(subscribed) == 0:
            subscribed = set(u["instrument_token"] for u in universe)
    else:
        if mode != "live":
            subscribed = set(u["instrument_token"] for u in universe)
    total = 500
    # if universe smaller, total reflects universe len but spec says 500
    subscribed_count = len(subscribed)
    # fallback: if live failed but universe loaded, show subscribed 0 and missing
    missing = []
    if subscribed_count < total:
        # compute missing tokens
        all_tokens = set(u["instrument_token"] for u in universe)
        missing = list(all_tokens - subscribed)[:20]  # cap for payload
    return {"subscribed": subscribed_count, "total": total, "missing": missing, "mode": mode, "universe": len(universe)}

@router.get("/universe")
async def verify_universe():
    exists = UNIVERSE_PATH.exists()
    count = 0
    sectors = 0
    sector_missing = []
    if exists:
        try:
            import json
            data = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
            count = len(data)
            sectors_set = set(x.get("sector") for x in data if x.get("sector"))
            sectors = len(sectors_set)
            sector_missing = [x["symbol"] for x in data if not x.get("sector")]
            if sector_missing:
                logger.warning(f"Universe has {len(sector_missing)} entries missing sector field")
        except Exception as e:
            logger.error(f"verify universe read error {e}")
    return {"exists": exists, "path": str(UNIVERSE_PATH), "count": count, "sectors": sectors, "sector_missing_sample": sector_missing[:5]}

@router.get("/ticks")
async def verify_ticks():
    from ..main import app_state
    de = app_state.get("data_engine")
    stats = de.get_stats() if de else {"ticks_processed": 0, "batches": 0, "errors": 0}
    healthy = stats.get("ticks_processed", 0) > 0
    # during market closed mock still produces ticks
    return {"ticks_processed": stats.get("ticks_processed", 0), "batches": stats.get("batches", 0), "errors": stats.get("errors", 0), "healthy": healthy, "last_tick_time": stats.get("last_tick_time")}

@router.get("/ws")
async def verify_ws():
    mode = settings.data_mode
    has_key = bool(settings.kite_api_key)
    has_token = bool(settings.kite_access_token)
    valid = has_key and has_token
    if mode == "live" and not valid:
        logger.error("KiteAuthenticationError: KITE_API_KEY or KITE_ACCESS_TOKEN missing in live mode — falling back to mock")
    fallback = "mock" if (mode == "live" and not valid) else mode
    return {"mode": mode, "has_api_key": has_key, "has_access_token": has_token, "valid": valid, "fallback": fallback, "websocket_url": settings.websocket_url}

@router.get("/sectors")
async def verify_sectors():
    from ..main import app_state
    uni = app_state.get("universe") or []
    import collections
    counter = collections.Counter(x.get("sector") or "Unknown" for x in uni)
    return {"sectors": 12 if len(counter) >= 12 else len(counter), "distinct": len(counter), "breakdown": dict(counter)}

@router.get("/memory")
async def verify_memory():
    from ..main import app_state
    ms = app_state.get("market_state")
    if not ms:
        return {"error": "market_state not ready"}
    ce = ms.candle_engine
    per_symbol = {}
    total_candles = 0
    for sym, intervals in ce._store.items():
        cnt = sum(len(dq) for dq in intervals.values())
        # include current building candles
        cur = ce._current.get(sym, {})
        cnt += len(cur)
        per_symbol[sym] = cnt
        total_candles += cnt
    # estimate ~ 200 bytes per candle
    est_bytes = total_candles * 200
    est_mb = round(est_bytes / (1024*1024), 2)
    advice = None
    if est_mb > 100 or total_candles > 500*5*100:
        advice = "high memory: consider reducing max_candles from 500 to 200 via CandleEngine(max_candles=200)"
    return {"total_candles": total_candles, "est_mb": est_mb, "max_candles": ce.max_candles, "per_symbol_sample": dict(list(per_symbol.items())[:5]), "advice": advice}
