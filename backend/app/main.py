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
    logger.info("=== NSE Top500 Realtime Screener starting ===")
    logger.info(f"DATA_MODE={settings.data_mode} UNIVERSE={UNIVERSE_PATH}")
    universe = load_universe()
    if len(universe)==0:
        logger.error("No universe loaded! App will run with empty universe - check config/nse_top500.json")
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
    logger.info(f"MarketState: {len(market_state.states)} symbols, intervals {settings.candle_intervals_list}")
    logger.info(f"AlertEngine max_alerts={settings.max_alerts}")

    # start data engine
    await data_engine.start()

    logger.info(f"API ready at http://{settings.host}:{settings.port}")
    yield
    # shutdown
    logger.info("Shutting down...")
    try:
        await data_engine.stop()
    except Exception as e:
        logger.error(f"Shutdown error {e}")
    logger.info("Shutdown complete")

app = FastAPI(
    title="NSE Top 500 Realtime Screener",
    version="1.0.0",
    description="Production-quality NSE Top500 intraday screener with Kite WebSocket + mock/replay modes",
    lifespan=lifespan,
)

# CORS - safe config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(market_router, prefix="/api", tags=["market"])
app.include_router(stocks_router, prefix="/api", tags=["stocks"])
app.include_router(screener_router, prefix="/api", tags=["screener"])
app.include_router(alerts_router, prefix="/api", tags=["alerts"])

@app.get("/api/info")
async def api_info():
    return {
        "name": "NSE Top 500 Realtime Screener",
        "version": "1.0.0",
        "data_mode": settings.data_mode,
        "universe": len(app_state.get("universe",[])),
        "docs": "/docs",
        "health": "/api/health",
        "websocket": "/ws",
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
        return {"ticks_processed":0}
    return de.get_stats()

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
                data.append({
                    "symbol": s.symbol,
                    "token": s.token,
                    "ltp": s.ltp,
                    "change_pct": chg,
                    "changePercent": chg,
                    "change": s.change,
                    "volume": s.volume,
                    "rel_volume": round(s.rel_volume,2) if s.rel_volume else None,
                    "relVolume": round(s.rel_volume,2) if s.rel_volume else None,
                    "high": s.high,
                    "low": s.low,
                    "open": s.open,
                    "previous_close": s.previous_close,
                    "previousClose": s.previous_close,
                    "vwap": round(s.indicators.vwap,2) if s.indicators.vwap else None,
                    "rsi": round(s.indicators.rsi,1) if s.indicators.rsi else None,
                    "ema9": round(s.indicators.ema9,2) if s.indicators.ema9 else None,
                    "ema20": round(s.indicators.ema20,2) if s.indicators.ema20 else None,
                    "score": s.score,
                    "signal": s.signal,
                    "signal_strength": s.signal_strength,
                    "signalStrength": s.signal_strength,
                    "freshness": s.freshness,
                    "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                    "sector": s.sector,
                    "company": s.company,
                    "companyName": s.company,
                    "industry": s.industry,
                    "isAboveVwap": is_above,
                    "is_above_vwap": is_above,
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

