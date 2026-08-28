"""In-memory market state + indicator updates, tick normalization, scoring.
Preserves efficient incremental calculations, handles stale, duplicate, missing.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict
import logging
import copy

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

from .models import MarketTick, StockState, Candle
from .candle_engine import CandleEngine
from .indicators import ema_series, rsi, atr, macd, bollinger, adx, vwap_bands, macd_cross_signal, rsi_divergence
from .indicators_advanced import calculate_supertrend
from .breaker import BreakerEngine
from .scoring import score_stock
from .utils.freshness import compute_freshness
try:
    from .cache import get_cache
except: get_cache=lambda: None

logger = logging.getLogger(__name__)

class MarketState:
    def __init__(self, universe: List[Dict[str, Any]], stale_threshold_sec: int=30, intervals: List[int]=None):
        self.stale_threshold_sec = stale_threshold_sec
        self.candle_engine = CandleEngine(intervals=intervals or [1,3,5,15,30])
        # symbol -> StockState
        self.states: Dict[str, StockState] = {}
        # token -> symbol
        self.token_to_symbol: Dict[int,str] = {}
        # symbol -> meta
        self.universe_map: Dict[str, Dict] = {}
        # per-symbol tick history for candle-based indicators (closing prices per 1m)
        # also store VWAP cumulative
        self._cum_pv: Dict[str, float] = {}
        self._cum_pv2: Dict[str, float] = {}  # cumulative volume*price^2, for VWAP bands
        self._cum_vol: Dict[str, int] = {}
        self._prev_close_map: Dict[str, float] = {}
        self._opening_range: Dict[str, Dict] = {}  # first 15m/30m high/low
        self._first_tick_time: Optional[datetime] = None
        self._last_data_received: Optional[datetime] = None
        self._last_candle_count: Dict[str, int] = {}
        self._tick_counter: Dict[str, int] = {}
        self._rsi_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.breaker_engine = BreakerEngine()
        self._init_universe(universe)

    def get_breaker_signals(self, min_score: float = 0.0, statuses: Optional[List[str]] = None):
        """Evaluate the OHLC Breaker breakout module against every symbol's
        current live state. Computed on demand (not cached) since it's cheap
        relative to a full ranking pass and the retest-hold state machine
        lives inside self.breaker_engine, persisting across calls."""
        statuses = statuses or ["WEAK_BREAK", "PENDING_RETEST", "CONFIRMED", "FAILED"]
        out = []
        for sym, state in self.states.items():
            candles = self.candle_engine.get_candles(sym, 1, limit=10)
            sig = self.breaker_engine.evaluate(state, candles)
            if sig and sig.direction and sig.status in statuses and sig.score >= min_score:
                out.append(sig)
        out.sort(key=lambda s: s.score, reverse=True)
        return out

    def _init_universe(self, universe: List[Dict[str, Any]]):
        # check if market is currently closed to pre-populate last trading day
        try:
            from .market_hours import get_market_status
            _is_live = get_market_status(datetime.now(tz=IST))[1]
        except:
            _is_live = False
        for entry in universe:
            sym = entry["symbol"]
            token = entry["instrument_token"]
            self.token_to_symbol[token] = sym
            self.universe_map[sym] = entry
            prev_close = entry.get("prev_close") or None
            avg_vol = entry.get("avg_volume") or None
            self._prev_close_map[sym] = prev_close
            # If market is closed, show the last known close as a flat placeholder (no
            # open/high/low guessing) until a real REST snapshot (services/quote_fallback)
            # or the next live tick replaces it with actual last-trading-day OHLC.
            if not _is_live:
                last_close = self._last_trading_close_time()
                state = StockState(
                    symbol=sym,
                    token=token,
                    company=entry.get("company"),
                    sector=entry.get("sector"),
                    industry=entry.get("industry"),
                    exchange=entry.get("exchange","NSE"),
                    ltp=prev_close or 0,
                    open=prev_close, high=prev_close, low=prev_close,
                    previous_close=prev_close,
                    change=0, change_pct=0,
                    volume=0,
                    freshness="CLOSED" if prev_close else "NO_DATA",
                    timestamp=last_close if prev_close else None,
                )
            else:
                state = StockState(
                    symbol=sym,
                    token=token,
                    company=entry.get("company"),
                    sector=entry.get("sector"),
                    industry=entry.get("industry"),
                    exchange=entry.get("exchange","NSE"),
                    ltp=prev_close,
                    open=None, high=None, low=None,
                    previous_close=prev_close,
                    volume=0,
                    freshness="NO_DATA",
                )
            # Real previous-day high/low, if this symbol has ingested bhavcopy history
            # (see historical/store.py, populated via GET /api/historical/bhavcopy) --
            # left None rather than guessed when no history has been ingested yet.
            try:
                from .historical.store import get_history
                hist = get_history(sym, days=2)
                if hist:
                    state.previous_day_high = hist[-1].get("high")
                    state.previous_day_low = hist[-1].get("low")
            except Exception:
                pass
            self.states[sym] = state
        logger.info(f"MarketState initialized with {len(self.states)} symbols (is_live={_is_live})")

    def _last_trading_close_time(self) -> datetime:
        # last trading day 15:30 IST, skip weekends/holidays
        try:
            from .market_hours import IST as _IST2
        except:
            _IST2 = IST
        now = datetime.now(tz=_IST2)
        # go back up to 7 days to find last trading day
        for i in range(7):
            cand = now - timedelta(days=i)
            # check if weekday and not holiday (simplified)
            if cand.weekday() < 5:
                # check get_market_status for that day at 12:00
                try:
                    from .market_hours import get_market_status as _gms
                    check = cand.replace(hour=12, minute=0, second=0, microsecond=0)
                    status, is_live = _gms(check)
                    if status not in ("holiday",):
                        # return that day 15:30
                        return cand.replace(hour=15, minute=30, second=0, microsecond=0)
                except:
                    return cand.replace(hour=15, minute=30, second=0, microsecond=0)
        return now.replace(hour=15, minute=30, second=0, microsecond=0)

    def apply_last_close_snapshot(self, symbol: str, ohlc: Dict[str, Any], prev_close: Optional[float] = None, timestamp: Optional[datetime] = None):
        """Patch a symbol with a REAL last-trading-day OHLC snapshot fetched over REST
        (services/quote_fallback), replacing the flat placeholder set at startup.
        Never overwrites a symbol that already has a live tick flowing."""
        state = self.states.get(symbol)
        if not state or state.freshness == "LIVE":
            return
        pc = prev_close if prev_close is not None else state.previous_close
        o = ohlc.get("open"); h = ohlc.get("high"); l = ohlc.get("low")
        close = ohlc.get("close") or ohlc.get("last_price")
        if close is None:
            return
        state.previous_close = pc
        state.open = o if o is not None else state.open
        state.high = h if h is not None else state.high
        state.low = l if l is not None else state.low
        state.ltp = close
        if pc:
            state.change = state.ltp - pc
            state.change_pct = (state.change / pc) * 100 if pc else None
        state.freshness = "CLOSED"
        state.timestamp = timestamp or self._last_trading_close_time()
        if state.open and state.high and state.low:
            state.indicators.vwap = round((state.open + state.high + state.low + state.ltp) / 4, 2)
        self._prev_close_map[symbol] = pc

    def set_avg_volume(self, symbol: str, avg_volume: float):
        """Update a symbol's average daily volume with a real value computed from
        Kite historical daily candles (services/history_warmer), replacing any placeholder."""
        if symbol in self.universe_map and avg_volume:
            self.universe_map[symbol]["avg_volume"] = avg_volume

    def symbol_for_token(self, token: int) -> Optional[str]:
        return self.token_to_symbol.get(token)

    def token_for_symbol(self, symbol: str) -> Optional[int]:
        m = self.universe_map.get(symbol)
        return m["instrument_token"] if m else None

    def on_tick(self, tick: MarketTick):
        sym = tick.symbol
        if sym not in self.states:
            # auto-create for options (NIFTY/SENSEX) - dynamic subscription
            if tick.token and tick.symbol:
                from .models import StockState
                # infer sector from symbol prefix
                sector = "Options" if any(x in sym for x in ["NIFTY","BANKNIFTY","SENSEX"]) else "Unknown"
                state = StockState(symbol=sym, token=tick.token, company=sym, sector=sector, exchange="NSE", ltp=tick.ltp, previous_close=tick.previousClose or tick.ltp, volume=tick.volume or 0, freshness="LIVE", timestamp=tick.timestamp)
                self.states[sym]=state
                self.token_to_symbol[tick.token]=sym
                self.universe_map[sym]={"symbol":sym,"instrument_token":tick.token,"sector":sector,"avg_volume":1000000,"prev_close":tick.previousClose or tick.ltp}
                logger.info(f"Dynamic options state created {sym} token {tick.token}")
            else:
                logger.warning(f"Unknown symbol {sym} token {tick.token}")
                return
        state = self.states[sym]
        # duplicate detection via timestamp+ltp
        now = datetime.now(tz=IST)
        self._last_data_received = now
        if state.timestamp and tick.timestamp == state.timestamp and tick.ltp == state.ltp:
            return  # duplicate

        # store previous for alert engine
        prev_state = copy.deepcopy(state)

        # update OHLCV
        if state.open is None:
            state.open = tick.open if tick.open is not None else tick.ltp
        state.ltp = tick.ltp
        state.last_quantity = tick.last_quantity
        state.volume = tick.volume or state.volume
        # store OTC fields
        state.bid = tick.bid
        state.ask = tick.ask
        state.bid_qty = tick.bid_qty
        state.ask_qty = tick.ask_qty
        state.timestamp = tick.timestamp
        # update high/low intraday
        if tick.high is not None:
            state.high = tick.high
        else:
            if state.high is None or tick.ltp > state.high:
                state.high = tick.ltp
        if tick.low is not None:
            state.low = tick.low
        else:
            if state.low is None or tick.ltp < state.low:
                state.low = tick.ltp
        # previous close
        if tick.previous_close is not None:
            state.previous_close = tick.previous_close
        elif state.previous_close is None:
            state.previous_close = self._prev_close_map.get(sym)

        # change
        if state.previous_close and state.previous_close != 0:
            state.change = state.ltp - state.previous_close
            state.change_pct = (state.change / state.previous_close)*100
            # gap %
            if state.open and state.previous_close:
                state.gap_pct = (state.open - state.previous_close)/state.previous_close*100
        # distances
        if state.high and state.high !=0:
            state.distance_from_high_pct = (state.ltp - state.high)/state.high*100
        if state.low and state.low !=0:
            state.distance_from_low_pct = (state.ltp - state.low)/state.low*100
        if state.high and state.low and state.high!=state.low:
            state.range_pct = (state.high - state.low)/state.low*100

        # VWAP incremental (use cumulative PV)
        # volume delta approximation: use tick.volume as cumulative
        # we keep cum_vol as total volume, cum_pv as sum(price*delta_vol)
        prev_cum = self._cum_vol.get(sym, 0)
        delta_vol = 0
        if tick.volume is not None:
            if tick.volume >= prev_cum:
                delta_vol = tick.volume - prev_cum
                self._cum_vol[sym] = tick.volume
            else:
                # reset at day start? volume went down => new day or correction
                delta_vol = tick.volume
                self._cum_vol[sym] = tick.volume
                self._cum_pv[sym] = 0  # reset
                self._cum_pv2[sym] = 0  # reset (VWAP band variance tracker)
        else:
            delta_vol = tick.last_quantity or 0
            self._cum_vol[sym] = self._cum_vol.get(sym,0) + delta_vol

        cum_pv = self._cum_pv.get(sym, 0) + tick.ltp * max(delta_vol,0)
        self._cum_pv[sym] = cum_pv
        cum_pv2 = self._cum_pv2.get(sym, 0) + (tick.ltp**2) * max(delta_vol,0)
        self._cum_pv2[sym] = cum_pv2
        cum_vol = self._cum_vol.get(sym, 0)
        if cum_vol > 0:
            state.indicators.vwap = cum_pv / cum_vol
            bands = vwap_bands(state.indicators.vwap, cum_vol, cum_pv, cum_pv2)
            state.indicators.vwap_upper1 = bands["upper1"]
            state.indicators.vwap_lower1 = bands["lower1"]
            state.indicators.vwap_upper2 = bands["upper2"]
            state.indicators.vwap_lower2 = bands["lower2"]

        # rel volume: current vol / expected avg vol at this time of day, using a REAL
        # average daily volume (from history_warmer's Kite historical candles, or the
        # universe file if pre-populated). Without one, leave rel_volume unset rather
        # than dividing against a guessed baseline that would misrepresent every stock.
        avg_vol = self.universe_map[sym].get("avg_volume")
        try:
            if not avg_vol:
                raise ValueError("no real avg_volume available yet")
            ist_now = tick.timestamp if tick.timestamp.tzinfo else tick.timestamp.replace(tzinfo=IST)
            market_start = ist_now.replace(hour=9, minute=15, second=0, microsecond=0)
            elapsed_min = max(1, (ist_now - market_start).total_seconds()/60)
            progress = min(1.0, elapsed_min/375)
            expected_vol = avg_vol * progress
            if expected_vol > 0:
                state.rel_volume = state.volume / expected_vol if state.volume else 0
                state.volume_spike = (state.rel_volume or 0) > 1.5
        except Exception as e:
            logger.debug(f"rel vol calc failed {e}")

        # candle engine
        self.candle_engine.on_tick(sym, tick.ltp, tick.volume or 0, tick.timestamp)

        # compute EMA/RSI etc from 1m candles
        self._update_indicators(sym)

        # momentum returns
        self._update_momentum(sym, tick.timestamp)

        # scoring
        score, br, sig, strength = score_stock(state)
        state.score = score
        state.score_breakdown = br
        state.signal = sig
        state.signal_strength = strength

        # freshness will be updated lazily or immediately
        state.freshness = compute_freshness(state.timestamp, self.stale_threshold_sec, now)

        # opening range (first 15 min)
        self._update_opening_range(sym, tick.timestamp, tick.ltp)

        return prev_state, state

    def _update_indicators(self, symbol: str):
        state = self.states[symbol]
        # perf: skip heavy calc if no new 1m candle and not every 3rd tick
        candles_1m = self.candle_engine.get_candles(symbol, 1, limit=100)
        cnt = len(candles_1m)
        last = self._last_candle_count.get(symbol, -1)
        tc = self._tick_counter.get(symbol, 0) + 1
        self._tick_counter[symbol]=tc
        is_new_candle = cnt != last
        # only compute heavy indicators on new candle or every 3 ticks
        if not is_new_candle and tc % 3 != 0 and cnt>10:
            closes = [c.close for c in candles_1m]
            # still quick EMA9 update from last close
            if len(closes) >= 9:
                try: state.indicators.ema9 = ema_series(closes, 9)[-1]
                except: pass
            self._last_candle_count[symbol]=cnt
            return
        self._last_candle_count[symbol]=cnt
        closes = [c.close for c in candles_1m]
        if len(closes) >= 9:
            ema9 = ema_series(closes, 9)
            state.indicators.ema9 = ema9[-1]
        if len(closes) >= 20:
            ema20 = ema_series(closes, 20)
            state.indicators.ema20 = ema20[-1]
        if len(closes) >= 50:
            ema50 = ema_series(closes, 50)
            state.indicators.ema50 = ema50[-1]
        if len(closes) >= 15:
            state.indicators.rsi = rsi(closes, 14)
            self._rsi_history[symbol].append(state.indicators.rsi)
            state.indicators.rsi_divergence = rsi_divergence(closes, list(self._rsi_history[symbol]))
        if len(candles_1m) >= 15:
            dict_candles = [{"high":c.high,"low":c.low,"close":c.close} for c in candles_1m]
            state.indicators.atr = atr(dict_candles, 14)
        if len(closes) >= 35:
            m,s,h = macd(closes)
            prev_hist = state.indicators.macd_hist
            state.indicators.macd = m
            state.indicators.macd_signal = s
            state.indicators.macd_hist = h
            state.indicators.macd_cross = macd_cross_signal(prev_hist, h)
        if len(closes) >= 20:
            upper,mid,lower = bollinger(closes,20,2)
            state.indicators.bb_upper = upper
            state.indicators.bb_middle = mid
            state.indicators.bb_lower = lower
            state.indicators.bb_width_pct = round((upper-lower)/mid*100, 3) if mid else None
        if len(candles_1m) >= 15:
            dict_candles = [{"high":c.high,"low":c.low,"close":c.close} for c in candles_1m]
            adx_val, plus_di, minus_di = adx(dict_candles, 14)
            state.indicators.adx = adx_val
            state.indicators.di_plus = plus_di
            state.indicators.di_minus = minus_di
        if len(candles_1m) >= 10:
            highs = [c.high for c in candles_1m]
            lows = [c.low for c in candles_1m]
            st = calculate_supertrend(highs, lows, closes, period=10, multiplier=3.0)
            if st:
                state.indicators.supertrend = round(st.value, 2)
                state.indicators.supertrend_direction = st.direction
                state.indicators.supertrend_signal = st.signal

    def _update_momentum(self, symbol: str, now: datetime):
        state = self.states[symbol]
        # use candle closes to compute returns over intervals
        for interval, attr in [(1,"ret_1m"),(3,"ret_3m"),(5,"ret_5m"),(15,"ret_15m"),(30,"ret_30m")]:
            candles = self.candle_engine.get_candles(symbol, 1, limit= interval+5)
            if len(candles) < 2:
                continue
            # need price now vs price interval ago
            # Approximate: current ltp vs close interval ago
            # Use candle closes: find candle at time now-interval
            if len(candles) >= interval+1:
                prev_close = candles[-(interval+1)].close
                if prev_close and prev_close !=0:
                    ret = (state.ltp - prev_close)/prev_close*100
                    setattr(state.momentum, attr, round(ret,3))
        # opening range breakout (15-min range; 30-min exposed alongside for
        # strategies/UI that want the wider window)
        ors = self._opening_range.get(symbol)
        if ors and state.ltp:
            if ors.get("high") and state.ltp > ors["high"]:
                state.momentum.opening_range_breakout = True
            elif ors.get("low") and state.ltp < ors["low"]:
                state.momentum.day_low_breakdown = True  # reuse
            else:
                state.momentum.opening_range_breakout = False
            state.momentum.or15_high = ors.get("high15")
            state.momentum.or15_low = ors.get("low15")
            state.momentum.or30_high = ors.get("high30")
            state.momentum.or30_low = ors.get("low30")
        # day high breakout
        if state.high and state.ltp >= state.high and state.high != state.previous_close:
            # breakout if ltp == high and vol spike maybe
            state.momentum.day_high_breakout = (abs(state.ltp - state.high)/state.high < 0.001)
        else:
            # alternative: if ltp made new intraday high
            candles_1m = self.candle_engine.get_candles(symbol,1,limit=50)
            if candles_1m and state.ltp == max(c.high for c in candles_1m):
                state.momentum.day_high_breakout = True
            else:
                # keep false unless breakout
                if state.momentum.day_high_breakout is None:
                    state.momentum.day_high_breakout = False
        # day low breakdown
        if state.low and state.ltp <= state.low:
            state.momentum.day_low_breakdown = True
        # VWAP breakout
        if state.indicators.vwap:
            if state.previous_close and state.indicators.vwap:
                # did we cross VWAP? check previous state handled in alert engine
                # here we just set flag if price above VWAP significantly
                state.momentum.vwap_breakout = state.ltp > state.indicators.vwap

    def _update_opening_range(self, symbol: str, ts: datetime, ltp: float):
        """Tracks both the 15-min and 30-min opening range in one pass (30-min
        window is a superset of the 15-min one, both closed off at market_start
        + N minutes; configurable windows beyond these two would need a list
        instead of two hardcoded keys, not needed by anything using this yet)."""
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=IST)
        market_start = ts.replace(hour=9, minute=15, second=0, microsecond=0)
        end15 = market_start + timedelta(minutes=15)
        end30 = market_start + timedelta(minutes=30)
        if not (market_start <= ts <= end30):
            return
        entry = self._opening_range.setdefault(symbol, {})
        if ts <= end15:
            entry["high15"] = max(entry.get("high15", ltp), ltp)
            entry["low15"] = min(entry.get("low15", ltp), ltp)
        entry["high30"] = max(entry.get("high30", ltp), ltp)
        entry["low30"] = min(entry.get("low30", ltp), ltp)
        # keep legacy keys ("high"/"low" == the 15-min range) for the existing
        # opening_range_breakout flag logic in _update_momentum below
        entry["high"] = entry.get("high15", entry.get("high30"))
        entry["low"] = entry.get("low15", entry.get("low30"))

    def refresh_freshness(self):
        now = datetime.now(tz=IST)
        try:
            from .market_hours import get_market_status as _gms2
            _status, _is_live = _gms2(now)
            _is_open = _is_live
        except:
            _is_open = False
        for s in self.states.values():
            # if market closed and state is CLOSED with last trading close timestamp, keep CLOSED
            if not _is_open and s.freshness == "CLOSED" and s.timestamp:
                # keep as CLOSED, don't mark stale even though timestamp is old
                continue
            # if never received tick and market closed, keep CLOSED
            if s.timestamp is None and not _is_open:
                s.freshness = "CLOSED"
                continue
            s.freshness = compute_freshness(s.timestamp, self.stale_threshold_sec, now)
            # if market closed and freshness would be NO_DATA but we have synthetic, keep CLOSED
            if not _is_open and s.freshness == "NO_DATA" and s.volume and s.volume > 0:
                s.freshness = "CLOSED"

    def all_states(self) -> List[StockState]:
        self.refresh_freshness()
        # optional cache for ranking/overview keys
        return list(self.states.values())

    def cached_overview(self, ttl: int = 10):
        cache=get_cache()
        if cache:
            hit=cache.get("ms_overview", {"k":"overview"})
            if hit is not None: return hit
        ov=self.market_overview()
        data=ov.model_dump()
        if cache:
            try: cache.set("ms_overview", {"k":"overview"}, data, ttl)
            except: pass
        return data

    def cached_ranking(self, ttl: int = 5):
        cache=get_cache()
        if cache:
            hit=cache.get("ms_ranking", {"k":"ranking"})
            if hit is not None: return hit
        r=self.ranking()
        if cache:
            try: cache.set("ms_ranking", {"k":"ranking"}, r, ttl)
            except: pass
        return r

    def get_state(self, symbol: str) -> Optional[StockState]:
        # allow token int lookup for compatibility
        if isinstance(symbol, int) or (isinstance(symbol, str) and symbol.isdigit()):
            tok=int(symbol)
            sym=self.token_to_symbol.get(tok)
            if sym: symbol=sym
        s = self.states.get(symbol)
        if s:
            s.freshness = compute_freshness(s.timestamp, self.stale_threshold_sec, datetime.now(tz=IST))
            return s
        # fallback token direct
        if isinstance(symbol, int):
            sym=self.token_to_symbol.get(symbol)
            if sym: return self.states.get(sym)
        return s

    def update_tick(self, tick_dict: dict):
        """Compat for tests: tick_dict with token, ltp, volume etc."""
        try:
            from .models import MarketTick
            tok=tick_dict.get("token") or tick_dict.get("instrument_token")
            sym=self.token_to_symbol.get(tok) or tick_dict.get("symbol")
            if not sym and tok: sym=str(tok)
            # build MarketTick
            ts=tick_dict.get("timestamp") or datetime.now(tz=IST)
            if isinstance(ts, str):
                try: ts=datetime.fromisoformat(ts)
                except: ts=datetime.now(tz=IST)
            mt=MarketTick(symbol=sym, token=tok or 0, timestamp=ts, ltp=float(tick_dict.get("ltp", tick_dict.get("price",100))), volume=tick_dict.get("volume"), open=tick_dict.get("open"), high=tick_dict.get("high"), low=tick_dict.get("low"))
            return self.on_tick(mt)
        except Exception as e:
            logger.debug(f"update_tick failed {e}")

    def ranking(self) -> List[StockState]:
        lst = self.all_states()
        sorted_lst = sorted(lst, key=lambda x: x.score, reverse=True)
        for i, s in enumerate(sorted_lst, start=1):
            s.rank = i
        return sorted_lst

    def market_overview(self):
        states = self.all_states()
        adv = sum(1 for s in states if (s.change_pct or 0) > 0)
        dec = sum(1 for s in states if (s.change_pct or 0) < 0)
        unc = len(states)-adv-dec
        from .screeners import top_gainers, top_losers, momentum_stocks, volume_spike
        above = sum(1 for s in states if s.indicators.vwap and s.ltp > s.indicators.vwap)
        below = sum(1 for s in states if s.indicators.vwap and s.ltp < s.indicators.vwap)
        br = sum(1 for s in states if s.momentum.day_high_breakout)
        bd = sum(1 for s in states if s.momentum.day_low_breakdown)
        # sector performance
        sector_map={}
        for s in states:
            sec = s.sector or "Unknown"
            if sec not in sector_map:
                sector_map[sec] = {"count":0,"adv":0,"avg_change":0,"total_change":0}
            sector_map[sec]["count"]+=1
            if (s.change_pct or 0) >0:
                sector_map[sec]["adv"]+=1
            sector_map[sec]["total_change"]+= (s.change_pct or 0)
        for sec, v in sector_map.items():
            v["avg_change"] = round(v["total_change"]/v["count"],2) if v["count"] else 0
            v["breadth"] = round(v["adv"]/v["count"]*100,1) if v["count"] else 0
        from .models import MarketOverview
        from .screeners import to_result
        return MarketOverview(
            total=len(states),
            advancing=adv,
            declining=dec,
            unchanged=unc,
            top_gainers=top_gainers(states,5),
            top_losers=top_losers(states,5),
            highest_volume=[to_result(s, f"Vol {s.volume:,}") for s in sorted([s for s in states], key=lambda x: x.volume, reverse=True)[:5]],
            highest_rel_volume=[to_result(s, f"RelVol {s.rel_volume:.2f}x") for s in sorted([s for s in states if s.rel_volume], key=lambda x: x.rel_volume, reverse=True)[:5]],
            strongest_momentum=momentum_stocks(states,5),
            weakest_momentum=[to_result(s, f"5m {s.momentum.ret_5m}") for s in sorted(states, key=lambda x: x.momentum.ret_5m if x.momentum.ret_5m is not None else 999)[:5]],
            above_vwap=above,
            below_vwap=below,
            breakouts=br,
            breakdowns=bd,
            sector_performance=sector_map
        )

    def reset_day(self):
        self.candle_engine.reset_day()
        self._cum_pv.clear()
        self._cum_pv2.clear()
        self._cum_vol.clear()
        self._opening_range.clear()
        self._rsi_history.clear()
        self.breaker_engine.reset_day()
        for s in self.states.values():
            s.open = None
            s.high = None
            s.low = None
            s.volume = 0
            s.indicators = s.indicators.__class__()
            s.momentum = s.momentum.__class__()
            s.score = 0
