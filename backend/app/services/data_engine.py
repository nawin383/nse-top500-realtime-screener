"""High-performance market data engine: WebSocketFeed -> Parser -> Mapper -> InMemoryMarketState -> Indicator -> Signal -> Broadcast

Handles reconnect, heartbeat, subscription management, stale detection, malformed messages, rate-limit.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

from ..models import MarketTick
from ..market_state import MarketState
from ..alerts import AlertEngine
from ..providers.base import BaseProvider
from ..providers.mock_provider import MockProvider
from ..providers.kite_provider import KiteProvider
from ..providers.replay_provider import ReplayProvider
from .broadcaster import broadcaster
from ..config import settings

logger = logging.getLogger(__name__)

class DataEngine:
    def __init__(self, universe: List[Dict[str, Any]], market_state: MarketState, alert_engine: AlertEngine):
        self.universe = universe
        self.market_state = market_state
        self.alert_engine = alert_engine
        self.provider: Optional[BaseProvider] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._broadcast_task: Optional[asyncio.Task] = None
        self._tick_count = 0
        self._last_broadcast = datetime.now(tz=IST)
        self._pending_ticks: List[MarketTick] = []
        self._lock = asyncio.Lock()
        self._stats = {"ticks_processed":0, "batches":0, "errors":0, "last_tick_time": None}

    def _create_provider(self) -> BaseProvider:
        mode = settings.data_mode.lower()
        if mode == "live":
            if not settings.kite_api_key or not settings.kite_access_token:
                logger.warning("Live mode requested but KITE credentials missing, falling back to mock")
                return MockProvider(self.universe)
            return KiteProvider(self.universe, settings.kite_api_key, settings.kite_access_token, settings.websocket_url)
        elif mode == "replay":
            return ReplayProvider(self.universe, settings.replay_file, settings.replay_speed)
        else:
            return MockProvider(self.universe)

    async def start(self):
        if self._running:
            return
        self._running = True
        self.provider = self._create_provider()
        logger.info(f"DataEngine start mode={settings.data_mode} provider={self.provider.name} ticks={len(self.universe)}")
        # start provider in background
        self._task = asyncio.create_task(self.provider.start(self.on_ticks))
        # start batched broadcaster
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("DataEngine started")

    async def stop(self):
        self._running = False
        if self.provider:
            try:
                await self.provider.stop()
            except Exception as e:
                logger.error(f"provider stop error {e}")
        if self._task:
            self._task.cancel()
        if self._broadcast_task:
            self._broadcast_task.cancel()
        logger.info("DataEngine stopped")

    async def on_ticks(self, ticks: List[MarketTick]):
        # This is called by provider (could be from thread). Ensure thread-safe
        if not ticks:
            return
        # process ticks async but quickly
        for tick in ticks:
            try:
                # validate
                if not tick.symbol or tick.ltp is None or tick.ltp <=0:
                    self._stats["errors"]+=1
                    continue
                # stale check? we process even stale but mark
                prev_state = self.market_state.states.get(tick.symbol)
                # deep copy for alert comparison inside market_state.on_tick returns prev
                result = self.market_state.on_tick(tick)
                if result is None:
                    continue
                prev, curr = result
                # alerts
                now = datetime.now(tz=IST)
                alerts = self.alert_engine.check(prev, curr, now)
                # queue for broadcast: collect minimal changed rows
                async with self._lock:
                    self._pending_ticks.append(curr)
                self._stats["ticks_processed"]+=1
                self._stats["last_tick_time"]=now.isoformat()
            except Exception as e:
                logger.error(f"tick processing error {e}", exc_info=True)
                self._stats["errors"]+=1
        self._stats["batches"]+=1

    async def _broadcast_loop(self):
        interval = settings.ws_broadcast_interval_ms / 1000.0
        while self._running:
            await asyncio.sleep(interval)
            async with self._lock:
                if not self._pending_ticks:
                    continue
                # deduplicate: keep last state per symbol
                dedup: Dict[str, Any] = {}
                for st in self._pending_ticks:
                    dedup[st.symbol] = st
                batch = list(dedup.values())
                self._pending_ticks.clear()
            # build minimal payload
            payload = {
                "type": "ticks",
                "data": [self._minimal_state(s) for s in batch],
                "meta": {
                    "count": len(batch),
                    "total_ticks": self._stats["ticks_processed"],
                    "timestamp": datetime.now(tz=IST).isoformat()
                }
            }
            try:
                await broadcaster.broadcast(payload)
            except Exception as e:
                logger.error(f"broadcast error {e}")
            # also broadcast alerts if any new
            # we embed alerts in next heartbeat? Alternatively broadcast separately when generated
            # For simplicity, broadcast alerts as separate message when generated inside on_ticks would be immediate.
            # Here we just periodically broadcast stats

    def _minimal_state(self, s):
        # minimal JSON for frontend update: only needed fields (include both snake and camelCase for compatibility)
        is_above = None
        if s.indicators.vwap and s.ltp:
            is_above = s.ltp > s.indicators.vwap
        # compute camel aliases
        chg_pct = round(s.change_pct,2) if s.change_pct is not None else None
        rel_vol = round(s.rel_volume,2) if s.rel_volume else None
        vwap = round(s.indicators.vwap,2) if s.indicators.vwap else None
        rsi = round(s.indicators.rsi,1) if s.indicators.rsi else None
        ema9 = round(s.indicators.ema9,2) if s.indicators.ema9 else None
        ema20 = round(s.indicators.ema20,2) if s.indicators.ema20 else None
        atr = round(s.indicators.atr,2) if s.indicators.atr else None
        macd = round(s.indicators.macd,2) if s.indicators.macd else None
        # base dict
        base = {
            "symbol": s.symbol,
            "token": s.token,
            "ltp": s.ltp,
            "change": s.change,
            "change_pct": chg_pct,
            "changePercent": chg_pct,
            "volume": s.volume,
            "rel_volume": rel_vol,
            "relVolume": rel_vol,
            "high": s.high,
            "low": s.low,
            "open": s.open,
            "previous_close": s.previous_close,
            "previousClose": s.previous_close,
            "vwap": vwap,
            "rsi": rsi,
            "ema9": ema9,
            "ema20": ema20,
            "atr": atr,
            "macd": macd,
            "score": s.score,
            "signal": s.signal,
            "signal_strength": round(s.signal_strength,2) if s.signal_strength else 0,
            "signalStrength": round(s.signal_strength,2) if s.signal_strength else 0,
            "rank": s.rank,
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
            "momentum": {
                "ret_1m": s.momentum.ret_1m,
                "ret_3m": s.momentum.ret_3m,
                "ret_5m": s.momentum.ret_5m,
                "ret_15m": s.momentum.ret_15m,
                "ret_30m": s.momentum.ret_30m,
                "breakout": s.momentum.day_high_breakout,
                "breakdown": s.momentum.day_low_breakdown,
            },
            "range_pct": round(s.range_pct,2) if s.range_pct else None,
            "gap_pct": round(s.gap_pct,2) if s.gap_pct else None,
            "gapPercent": round(s.gap_pct,2) if s.gap_pct else None,
            "distanceFromHigh": s.distance_from_high_pct,
            "distanceFromLow": s.distance_from_low_pct,
        }
        return base

    def get_stats(self):
        return self._stats.copy()
