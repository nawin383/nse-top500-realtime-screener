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
from .kite_rest import get_kite_client, fetch_quote
from ..config import settings

logger = logging.getLogger(__name__)

REST_FALLBACK_INTERVAL_SEC = 5
REST_FALLBACK_STALE_SEC = 8  # only poll symbols the WS hasn't updated recently

class DataEngine:
    def __init__(self, universe: List[Dict[str, Any]], market_state: MarketState, alert_engine: AlertEngine):
        self.universe = universe
        self.market_state = market_state
        self.alert_engine = alert_engine
        self.provider: Optional[BaseProvider] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._broadcast_task: Optional[asyncio.Task] = None
        self._rest_fallback_task: Optional[asyncio.Task] = None
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
        # REST quote/ltp fallback: supplements the WebSocket when it's down/stale
        # (Kite Connect docs recommend this for reconnect gaps + market-closed polling)
        if settings.data_mode.lower() == "live" and settings.kite_api_key and settings.kite_access_token:
            self._rest_fallback_task = asyncio.create_task(self._rest_fallback_loop())
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
        if self._rest_fallback_task:
            self._rest_fallback_task.cancel()
        logger.info("DataEngine stopped")

    async def _rest_fallback_loop(self):
        """Poll GET /quote (full: OHLC + volume, not just last price) for symbols the
        WebSocket hasn't updated recently. Only fires for stale/no-data symbols, so on
        a healthy connection this is a near-empty no-op batch every interval, not a
        duplicate full-universe poll.

        Deliberately NOT /quote/ltp: that endpoint returns last_price only, no OHLC.
        A tick with no ohlc.close leaves previous_close pinned to whatever placeholder
        was already in state, so change%/day-high-breakout come out nonsensical the
        moment a real price differs from it -- this is exactly what /quote/ltp did
        here before, and with the market closed (the WebSocket sending nothing) this
        loop was the *only* tick source, corrupting every single symbol immediately.
        """
        kite = get_kite_client(settings.kite_api_key, settings.kite_access_token)
        if not kite:
            return
        instrument_key = {f"{e.get('exchange','NSE')}:{e['symbol']}": e["symbol"] for e in self.universe}
        while self._running:
            await asyncio.sleep(REST_FALLBACK_INTERVAL_SEC)
            try:
                now = datetime.now(tz=IST)
                stale_instruments = []
                for key, sym in instrument_key.items():
                    state = self.market_state.states.get(sym)
                    if not state:
                        continue
                    if state.freshness == "LIVE":
                        continue
                    if state.timestamp and (now - state.timestamp).total_seconds() < REST_FALLBACK_STALE_SEC:
                        continue
                    stale_instruments.append(key)
                if not stale_instruments:
                    continue
                result = await fetch_quote(kite, stale_instruments)
                ticks = []
                for key, data in result.items():
                    sym = instrument_key.get(key)
                    ltp = data.get("last_price")
                    if not sym or not ltp:
                        continue
                    ohlc = data.get("ohlc") or {}
                    ticks.append(MarketTick(
                        symbol=sym, token=data.get("instrument_token", 0), timestamp=now, ltp=ltp,
                        volume=data.get("volume") or self.market_state.states[sym].volume or 0,
                        open=ohlc.get("open"), high=ohlc.get("high"), low=ohlc.get("low"),
                        previousClose=ohlc.get("close"),
                    ))
                if ticks:
                    await self.on_ticks(ticks)
            except Exception as e:
                logger.debug(f"REST fallback poll error {e}")

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
                # queue for broadcast: collect minimal changed rows. Option contracts
                # (sector=='Options', dynamically created for NIFTY/SENSEX WS ticks)
                # are processed and counted here but never broadcast on the equity
                # screener's "ticks" channel -- they get their own dedicated
                # option-instruments endpoint instead (see market_state.option_states()).
                if curr.sector != "Options":
                    async with self._lock:
                        self._pending_ticks.append(curr)
                self._stats["ticks_processed"]+=1
                self._stats["last_tick_time"]=now.isoformat()
            except Exception as e:
                logger.error(f"tick processing error {e}", exc_info=True)
                self._stats["errors"]+=1
        self._stats["batches"]+=1
        if self._stats["batches"] % 50 == 0:
            logger.info(f"ticks_processed={self._stats['ticks_processed']} batches={self._stats['batches']}")
        elif self._stats["ticks_processed"] and self._stats["ticks_processed"] % 500 == 0:
            logger.info(f"ticks_processed={self._stats['ticks_processed']} batches={self._stats['batches']}")

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
        ind = s.indicators
        # optimized payload: single camelCase keys only (~22% smaller WS)
        is_synthetic = s.freshness == "CLOSED" and s.volume and s.volume>0
        base = {
            "symbol": s.symbol,
            "token": s.token,
            "ltp": s.ltp,
            "change": s.change,
            "changePercent": chg_pct,
            "volume": s.volume,
            "relVolume": rel_vol,
            "high": s.high,
            "low": s.low,
            "open": s.open,
            "previousClose": s.previous_close,
            "vwap": vwap,
            "rsi": rsi,
            "ema9": ema9,
            "ema20": ema20,
            "atr": atr,
            "macd": macd,
            "score": s.score,
            "signal": s.signal,
            "signalStrength": round(s.signal_strength,2) if s.signal_strength else 0,
            "rank": s.rank,
            "freshness": s.freshness,
            "synthetic": bool(is_synthetic),
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "sector": s.sector,
            "companyName": s.company,
            "industry": s.industry,
            "isAboveVwap": is_above,
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
            "gapPercent": round(s.gap_pct,2) if s.gap_pct else None,
            "distanceFromHigh": s.distance_from_high_pct,
            "distanceFromLow": s.distance_from_low_pct,
            "vwapUpper1": ind.vwap_upper1, "vwapLower1": ind.vwap_lower1,
            "vwapUpper2": ind.vwap_upper2, "vwapLower2": ind.vwap_lower2,
            "adx": ind.adx, "diPlus": ind.di_plus, "diMinus": ind.di_minus,
            "macdSignal": ind.macd_signal, "macdHist": ind.macd_hist, "macdCross": ind.macd_cross,
            "bbUpper": ind.bb_upper, "bbLower": ind.bb_lower, "bbMiddle": ind.bb_middle, "bbWidthPct": ind.bb_width_pct,
            "supertrend": ind.supertrend, "supertrendDirection": ind.supertrend_direction, "supertrendSignal": ind.supertrend_signal,
            "rsiDivergence": ind.rsi_divergence,
            "previousDayHigh": s.previous_day_high, "previousDayLow": s.previous_day_low,
            "or15High": s.momentum.or15_high, "or15Low": s.momentum.or15_low,
            "or30High": s.momentum.or30_high, "or30Low": s.momentum.or30_low,
            "oi": s.oi, "oiChangePct": s.oi_change_pct, "oiBuildup": s.oi_buildup,
        }
        return base

    def get_stats(self):
        return self._stats.copy()
