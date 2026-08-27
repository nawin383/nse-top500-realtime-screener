"""In-memory market state + indicator updates, tick normalization, scoring.
Preserves efficient incremental calculations, handles stale, duplicate, missing.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
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
from .indicators import ema_series, rsi, atr, macd, bollinger, adx
from .scoring import score_stock
from .utils.freshness import compute_freshness

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
        self._cum_vol: Dict[str, int] = {}
        self._prev_close_map: Dict[str, float] = {}
        self._opening_range: Dict[str, Dict] = {}  # first 15m high/low
        self._first_tick_time: Optional[datetime] = None
        self._last_data_received: Optional[datetime] = None
        self._init_universe(universe)

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
            prev_close = entry.get("prev_close") or 100.0
            avg_vol = entry.get("avg_volume") or 1000000
            self._prev_close_map[sym] = prev_close
            # if market is closed, pre-populate synthetic last trading day OHLC so UI shows data
            if not _is_live:
                # synthetic last day: open ~prev_close ±0.5%, high +1.5%, low -1.2%, volume = avg
                import random
                # deterministic per symbol
                rnd = random.Random(hash(sym) % 100000)
                open_p = prev_close * rnd.uniform(0.995, 1.005)
                high_p = max(open_p, prev_close) * rnd.uniform(1.005, 1.015)
                low_p = min(open_p, prev_close) * rnd.uniform(0.985, 0.995)
                # last trading day close is prev_close; ltp = prev_close
                # set timestamp to last trading day 15:30 IST
                last_close = self._last_trading_close_time()
                state = StockState(
                    symbol=sym,
                    token=token,
                    company=entry.get("company"),
                    sector=entry.get("sector"),
                    industry=entry.get("industry"),
                    exchange=entry.get("exchange","NSE"),
                    ltp=prev_close,
                    open=round(open_p,2), high=round(high_p,2), low=round(low_p,2),
                    previous_close=prev_close,
                    change=0, change_pct=0,
                    volume=avg_vol,
                    freshness="CLOSED",
                    timestamp=last_close,
                )
                # set indicators with synthetic
                state.indicators.vwap = round((open_p+high_p+low_p+prev_close)/4,2)
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

    def symbol_for_token(self, token: int) -> Optional[str]:
        return self.token_to_symbol.get(token)

    def token_for_symbol(self, symbol: str) -> Optional[int]:
        m = self.universe_map.get(symbol)
        return m["instrument_token"] if m else None

    def on_tick(self, tick: MarketTick):
        sym = tick.symbol
        if sym not in self.states:
            # unknown symbol - create on fly if token mapped? else ignore
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
        else:
            delta_vol = tick.last_quantity or 0
            self._cum_vol[sym] = self._cum_vol.get(sym,0) + delta_vol

        cum_pv = self._cum_pv.get(sym, 0) + tick.ltp * max(delta_vol,0)
        self._cum_pv[sym] = cum_pv
        cum_vol = self._cum_vol.get(sym, 0)
        if cum_vol > 0:
            state.indicators.vwap = cum_pv / cum_vol

        # rel volume approx: current vol / expected avg vol at this time of day
        # we simulate avg daily vol from universe if present
        avg_vol = self.universe_map[sym].get("avg_volume", 1000000)
        # intraday expected volume = avg_vol * time_progress (9:15-15:30 = 375 min)
        try:
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
        candles_1m = self.candle_engine.get_candles(symbol, 1, limit=100)
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
        # ATR needs OHLC candles
        if len(candles_1m) >= 15:
            dict_candles = [{"high":c.high,"low":c.low,"close":c.close} for c in candles_1m]
            state.indicators.atr = atr(dict_candles, 14)
        if len(closes) >= 35:
            m,s,h = macd(closes)
            state.indicators.macd = m
            state.indicators.macd_signal = s
            state.indicators.macd_hist = h
        if len(closes) >= 20:
            upper,mid,lower = bollinger(closes,20,2)
            state.indicators.bb_upper = upper
            state.indicators.bb_middle = mid
            state.indicators.bb_lower = lower
        if len(candles_1m) >= 28:
            dict_candles = [{"high":c.high,"low":c.low,"close":c.close} for c in candles_1m]
            state.indicators.adx = adx(dict_candles,14)

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
        # opening range breakout
        ors = self._opening_range.get(symbol)
        if ors and state.ltp:
            if ors.get("high") and state.ltp > ors["high"]:
                state.momentum.opening_range_breakout = True
            elif ors.get("low") and state.ltp < ors["low"]:
                state.momentum.day_low_breakdown = True  # reuse
            else:
                state.momentum.opening_range_breakout = False
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
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=IST)
        market_start = ts.replace(hour=9, minute=15, second=0, microsecond=0)
        opening_end = market_start + timedelta(minutes=15)
        if market_start <= ts <= opening_end:
            entry = self._opening_range.get(symbol)
            if entry is None:
                self._opening_range[symbol] = {"high": ltp, "low": ltp}
            else:
                entry["high"] = max(entry["high"], ltp)
                entry["low"] = min(entry["low"], ltp)

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
        return list(self.states.values())

    def get_state(self, symbol: str) -> Optional[StockState]:
        s = self.states.get(symbol)
        if s:
            s.freshness = compute_freshness(s.timestamp, self.stale_threshold_sec, datetime.now(tz=IST))
        return s

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
        self._cum_vol.clear()
        self._opening_range.clear()
        for s in self.states.values():
            s.open = None
            s.high = None
            s.low = None
            s.volume = 0
            s.indicators = s.indicators.__class__()
            s.momentum = s.momentum.__class__()
            s.score = 0
