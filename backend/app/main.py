"""FastAPI application entry - connects market data engine, WebSocket broadcast, REST APIs."""
from __future__ import annotations
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings, UNIVERSE_PATH
from .utils.logging_config import setup_logging
from .market_state import MarketState
from .alerts import AlertEngine
from .services.data_engine import DataEngine
from .services.broadcaster import broadcaster

# routers
from .api.health import router as health_router
from .api.market import router as market_router
from .api.stocks import router as stocks_router
from .api.screener import router as screener_router
from .api.alerts_api import router as alerts_router
from .api.options import router as options_router
from .api.institutional import router as institutional_router
from .api.watchlists import router as watchlists_router
from .api.webhooks import router as webhooks_router

# Monitoring and metrics
from .utils.metrics import setup_metrics
from .utils.redis_manager import redis_manager
from .utils.rate_limiter import limiter, get_rate_limit_handler
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# global app state dict for simple DI (also stored in app.state)
app_state: Dict[str, Any] = {}

def load_universe() -> list:
    path = UNIVERSE_PATH
    if not path.exists():
        logger.warning(f"Universe file not found at {path}, creating empty")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # validate each entry has required fields
    validated=[]
    for e in data:
        if "symbol" not in e or "instrument_token" not in e:
            logger.warning(f"Skipping invalid entry {e}")
            continue
        validated.append(e)
    logger.info(f"Loaded universe {len(validated)} instruments from {path}")
    return validated

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    setup_logging(settings.log_level)
    logger.info("=== NSE Top500 Realtime Screener v2.0 starting ===")
    logger.info(f"DATA_MODE={settings.data_mode} UNIVERSE={UNIVERSE_PATH}")

    # Initialize Redis if enabled
    if settings.redis_enabled:
        await redis_manager.connect()

    universe = load_universe()
    # startup validation: warn if <500 and log count
    logger.info(f"Universe load count: {len(universe)}/500 from {UNIVERSE_PATH}")
    if not UNIVERSE_PATH.exists():
        logger.error(f"UNIVERSE_PATH missing: {UNIVERSE_PATH} — /api/universe will return 500")
    if len(universe)==0:
        logger.error("No universe loaded! App will run with empty universe - check config/nse_top500.json")
    elif len(universe) < 500:
        logger.warning(f"Universe incomplete: {len(universe)}/500 instruments — check config/nse_top500.json")
    # sector validation
    sectors = set(x.get("sector") for x in universe if x.get("sector"))
    if sectors and len(sectors) < 12:
        logger.warning(f"Sector count low: {len(sectors)} sectors, expected 12 — {sectors}")
    # WS credentials validation
    if settings.data_mode.lower() == "live" and (not settings.kite_api_key or not settings.kite_access_token):
        logger.error("KiteAuthenticationError: live mode requires KITE_API_KEY + KITE_ACCESS_TOKEN — falling back to mock (WS will use mock provider)")
    # init engines
    market_state = MarketState(universe, stale_threshold_sec=settings.stale_threshold_sec, intervals=settings.candle_intervals_list)
    alert_engine = AlertEngine(max_alerts=settings.max_alerts)
    data_engine = DataEngine(universe, market_state, alert_engine)

    app_state["universe"]=universe
    app_state["market_state"]=market_state
    app_state["alert_engine"]=alert_engine
    app_state["data_engine"]=data_engine
    app.state.app_state = app_state

    # log startup details
    logger.info(f"Subscribed {len(universe)}/500 instruments (pending WS subscription in batches of 200)")
    logger.info(f"MarketState: {len(market_state.states)} symbols, intervals {settings.candle_intervals_list}")
    logger.info(f"AlertEngine max_alerts={settings.max_alerts}")

    # start data engine
    await data_engine.start()

    # start daily token refresher if creds present (auto live)
    refresher_task = None
    try:
        from pathlib import Path as _P
        from .services.token_refresher import token_refresher_loop
        _cache = _P(__file__).resolve().parents[2] / "data" / "access_token.json"
        # also try project root
        if not _cache.parent.exists():
            _cache.parent.mkdir(parents=True, exist_ok=True)
        refresher_task = asyncio.create_task(token_refresher_loop(settings, data_engine, _cache))
        logger.info("Token refresher task scheduled")
    except Exception as e:
        logger.warning(f"Token refresher not started: {e}")

    logger.info(f"API ready at http://{settings.host}:{settings.port}")
    logger.info(f"Redis: {'enabled' if settings.redis_enabled else 'disabled'}")
    logger.info(f"ML Anomaly Detection: {'enabled' if settings.ml_anomaly_detection else 'disabled'}")
    logger.info(f"Metrics: {'enabled' if settings.enable_metrics else 'disabled'}")
    yield
    # shutdown
    logger.info("Shutting down...")

    # Disconnect Redis
    if settings.redis_enabled:
        await redis_manager.disconnect()

    if refresher_task:
        refresher_task.cancel()
        try:
            await refresher_task
        except asyncio.CancelledError:
            pass
    try:
        await data_engine.stop()
    except Exception as e:
        logger.error(f"Shutdown error {e}")
    logger.info("Shutdown complete")

app = FastAPI(
    title="NSE Top 500 Realtime Screener",
    version="2.0.0",
    description="World-class NSE Top500 intraday screener with ML anomaly detection, advanced indicators, and real-time analytics",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Liveness / readiness probes"},
        {"name": "market", "description": "Market status & overview"},
        {"name": "stocks", "description": "Universe & per-symbol detail"},
        {"name": "screener", "description": "Ranked screeners"},
        {"name": "alerts", "description": "Real-time alerts"},
        {"name": "options", "description": "Options chain & Greeks"},
        {"name": "institutional", "description": "FII/DII & sector flows"},
        {"name": "watchlists", "description": "User watchlists"},
        {"name": "webhooks", "description": "Webhook subscriptions"},
    ],
)
try:
    from .docs.openapi_extra import enhance_openapi
    enhance_openapi(app)
except Exception:
    pass

# Add rate limiting state
if settings.rate_limit_enabled:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, get_rate_limit_handler())

# CORS - safe config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup monitoring metrics
if settings.enable_metrics:
    setup_metrics(app)

# include routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(market_router, prefix="/api", tags=["market"])
app.include_router(stocks_router, prefix="/api", tags=["stocks"])
# verify router for troubleshooting diagnostics
try:
    from .api.verify import router as verify_router
    app.include_router(verify_router, prefix="/api/verify", tags=["verify"])
except Exception as e:
    logger.warning(f"verify router not loaded {e}")
app.include_router(screener_router, prefix="/api", tags=["screener"])
app.include_router(alerts_router, prefix="/api", tags=["alerts"])
app.include_router(options_router, prefix="/api", tags=["options"])
app.include_router(institutional_router, prefix="/api", tags=["institutional"])
app.include_router(watchlists_router, prefix="/api", tags=["watchlists"])
app.include_router(webhooks_router, prefix="/api", tags=["webhooks"])
try:
    from .api.v1 import router as v1_router
    app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
except Exception as e:
    logger.warning(f"v1 router not loaded {e}")

# in-memory rate limit middleware (fallback) + monitoring metrics extra endpoint
try:
    from .middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
except: pass
try:
    from .monitoring.metrics import get_metrics
    @app.get("/api/monitoring/metrics")
    async def monitoring_metrics(): return get_metrics()
except: pass
try:
    from fastapi import Depends as _Dep
    from .auth.jwt_auth import jwt_or_api_key
    @app.get("/api/v1/premium/overview")
    async def premium_overview(user=_Dep(jwt_or_api_key)):
        ms=app_state.get("market_state")
        return ms.market_overview().model_dump() if ms else {"error":"not ready"}
except Exception as _e:
    logger.debug(f"premium route failed {_e}")

@app.get("/api/info")
async def api_info():
    return {
        "name": "NSE Top 500 Realtime Screener",
        "version": "2.0.0",
        "data_mode": settings.data_mode,
        "universe": len(app_state.get("universe",[])),
        "features": {
            "redis": settings.redis_enabled,
            "ml_anomaly_detection": settings.ml_anomaly_detection,
            "rate_limiting": settings.rate_limit_enabled,
            "metrics": settings.enable_metrics,
            "watchlists": True,
            "webhooks": True,
            "advanced_indicators": True,
        },
        "docs": "/docs",
        "health": "/api/health",
        "websocket": "/ws",
        "metrics": "/metrics" if settings.enable_metrics else None,
    }

@app.get("/api/root")
async def root_alias():
    return await api_info()

@app.get("/api/config")
async def get_config():
    # never expose secrets
    return {
        "data_mode": settings.data_mode,
        "universe_file": str(UNIVERSE_PATH),
        "stale_threshold_sec": settings.stale_threshold_sec,
        "candle_intervals": settings.candle_intervals_list,
        "ws_broadcast_interval_ms": settings.ws_broadcast_interval_ms,
    }

@app.get("/api/stats")
async def get_stats():
    de = app_state.get("data_engine")
    if not de:
        return {"ticks_processed":0, "batches":0, "errors":0}
    stats = de.get_stats()
    # ensure required keys
    stats.setdefault("ticks_processed", 0)
    stats.setdefault("batches", 0)
    return stats

@app.get("/api/monitoring/memory")
async def monitoring_memory():
    from .api.verify import verify_memory as _vm
    return await _vm()

@app.get("/api/verify/ws-health")
async def ws_health_alias():
    from .api.verify import verify_ws as _vw
    return await _vw()

# WebSocket for frontend: Backend maintains single market connection, fans out to many clients
@app.websocket("/ws")
@app.websocket("/ws/stream")
@app.websocket("/ws/ticks")
async def websocket_endpoint(ws: WebSocket):
    await broadcaster.register(ws)
    # send initial snapshot (full universe for table)
    try:
        ms = app_state.get("market_state")
        if ms:
            states = ms.ranking()  # all 500 ranked
            data = []
            for s in states:
                is_above = s.indicators.vwap and s.ltp and s.ltp > s.indicators.vwap
                chg = round(s.change_pct,2) if s.change_pct is not None else None
                is_synth = s.freshness=="CLOSED"
                data.append({
                    "symbol": s.symbol,
                    "token": s.token,
                    "ltp": s.ltp,
                    "changePercent": chg,
                    "change": s.change,
                    "volume": s.volume,
                    "relVolume": round(s.rel_volume,2) if s.rel_volume else None,
                    "high": s.high,
                    "low": s.low,
                    "open": s.open,
                    "previousClose": s.previous_close,
                    "vwap": round(s.indicators.vwap,2) if s.indicators.vwap else None,
                    "rsi": round(s.indicators.rsi,1) if s.indicators.rsi else None,
                    "ema9": round(s.indicators.ema9,2) if s.indicators.ema9 else None,
                    "ema20": round(s.indicators.ema20,2) if s.indicators.ema20 else None,
                    "score": s.score,
                    "signal": s.signal,
                    "signalStrength": round(s.signal_strength,2) if s.signal_strength else 0,
                    "freshness": s.freshness,
                    "synthetic": bool(is_synth),
                    "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                    "sector": s.sector,
                    "companyName": s.company,
                    "industry": s.industry,
                    "isAboveVwap": is_above,
                    "volumeSpike": bool(s.volume_spike),
                    "isBreakout": bool(s.momentum.day_high_breakout),
                    "isBreakdown": bool(s.momentum.day_low_breakdown),
                    "momentum5m": s.momentum.ret_5m,
                    "gapPercent": round(s.gap_pct,2) if s.gap_pct else None,
                    "rank": s.rank,
                })
            payload = {
                "type": "snapshot",
                "data": data,
                "count": len(data),
                "meta": {"total": len(ms.states), "mode": settings.data_mode},
                "marketStatus": {"status": "OPEN", "is_open": True},
                "dataMode": settings.data_mode,
            }
            await broadcaster.send_to(ws, payload)
        # keep connection alive and handle client messages (e.g., subscribe filters)
        while True:
            try:
                msg = await ws.receive_text()
                # optionally handle client control messages (filter subscriptions etc)
                # For now just echo / log
                try:
                    data = json.loads(msg)
                    # client can send ping
                    if data.get("a") == "ping":
                        await ws.send_text(json.dumps({"type":"pong"}))
                except:
                    pass
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.debug(f"ws receive error {e}")
                break
    finally:
        await broadcaster.unregister(ws)

# Mount frontend static (if built)
try:
    _dist_candidates = [
        Path(__file__).resolve().parents[2] / "frontend" / "dist",
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
        Path.cwd() / "frontend" / "dist",
        Path.cwd().parent / "frontend" / "dist",
    ]
    _frontend_dist = next((p for p in _dist_candidates if p.exists() and (p / "index.html").exists()), None)
    if _frontend_dist:
        # Use a separate mount that doesn't override API/WS/docs
        app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets") if (_frontend_dist / "assets").exists() else None
        app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
        logger.info(f"Frontend static mounted from {_frontend_dist}")
    else:
        logger.info(f"Frontend dist not found, candidates checked: {_dist_candidates} — run 'npm run build' in frontend for production serving")
except Exception as e:
    logger.warning(f"Failed to mount frontend static: {e}")

# Global exception handler - production-safe
@app.exception_handler(Exception)
async def global_exc_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

