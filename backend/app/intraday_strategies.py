"""Five intraday strategies, each a pure function of a symbol's current
StockState producing an entry/stop/target/status, plus a lightweight
tracker that follows every fired signal tick-to-tick to record whether its
target or stop was hit first -- a genuine forward, same-session hit rate.

This is NOT a historical backtest: computing one honestly needs multiple
days of real historical candles from Kite/NSE, and this sandbox has no
network access to either. Fabricating a "backtested win rate" number would
violate the no-dummy-data rule this whole project is built on. Instead,
every signal this module fires is followed forward against real live ticks
for the rest of the session, so the hit rate reported is real -- it's just
building up sample size from today only, and callers should treat it as
provisional until enough trades have completed (see StrategyTracker.MIN_SAMPLE).

Strategies:
 1. orb15            -- opening-range-15 breakout
 2. vwap_reversion    -- mean-reversion fade to VWAP, gated to range regime (ADX<20)
 3. supertrend_flip   -- momentum entry on a fresh Supertrend BUY/SELL flip
 4. gap_classifier    -- Gap-and-Go (continuation) vs Gap Fade (reversal) at the open
 5. vwap_pullback     -- first pullback to VWAP after a strong directional open
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from collections import deque, defaultdict

from .indicators import atr_stop_target

ORB_RVOL_GATE = 1.2
GAP_RVOL_GATE = 1.3
GAP_MIN_PCT = 0.3
RANGE_ADX_CEILING = 20.0
VWAP_TOUCH_PCT = 0.15
STRONG_MOVE_15M_PCT = 0.5


@dataclass
class StrategySignal:
    strategy: str
    symbol: str
    direction: Optional[str]  # long | short | None
    status: str  # WATCHING | WEAK | TRIGGERED | NOT_APPLICABLE
    reason: str
    entry: Optional[float] = None
    stop: Optional[float] = None
    target1: Optional[float] = None
    target2: Optional[float] = None
    updated_at: Optional[str] = None


def _ts(state) -> Optional[str]:
    return state.timestamp.isoformat() if state.timestamp else None


def orb15(state) -> Optional[StrategySignal]:
    or_high, or_low = state.momentum.or15_high, state.momentum.or15_low
    if or_high is None or or_low is None:
        return None
    ltp = state.ltp
    rvol = state.rel_volume
    if ltp > or_high:
        direction, level = "long", or_high
    elif ltp < or_low:
        direction, level = "short", or_low
    else:
        return StrategySignal("orb15", state.symbol, None, "WATCHING",
                               "inside 15-min opening range", updated_at=_ts(state))
    gated = bool(rvol and rvol >= ORB_RVOL_GATE)
    entry = ltp
    sized = atr_stop_target(entry, state.indicators.atr, direction, stop_mult=1.0, target_mults=(1.0, 1.5)) if gated else None
    status = "TRIGGERED" if gated else "WEAK"
    reason = f"broke 15m OR {'high' if direction=='long' else 'low'} {level:.2f}" + ("" if gated else f" (RVOL {rvol or 0:.2f}x < {ORB_RVOL_GATE}x gate)")
    return StrategySignal("orb15", state.symbol, direction, status, reason,
                           entry=entry if gated else None,
                           stop=sized["stop"] if sized else None,
                           target1=sized["target1"] if sized else None,
                           target2=sized["target2"] if sized else None,
                           updated_at=_ts(state))


def vwap_reversion(state) -> Optional[StrategySignal]:
    adx = state.indicators.adx
    vwap = state.indicators.vwap
    upper2, lower2 = state.indicators.vwap_upper2, state.indicators.vwap_lower2
    if adx is None or vwap is None or upper2 is None or lower2 is None:
        return None
    if adx >= RANGE_ADX_CEILING:
        return StrategySignal("vwap_reversion", state.symbol, None, "NOT_APPLICABLE",
                               f"trending regime (ADX {adx:.1f} >= {RANGE_ADX_CEILING}), mean-reversion disabled",
                               updated_at=_ts(state))
    ltp = state.ltp
    if ltp >= upper2:
        direction = "short"
    elif ltp <= lower2:
        direction = "long"
    else:
        return StrategySignal("vwap_reversion", state.symbol, None, "WATCHING",
                               "range regime, price inside VWAP bands", updated_at=_ts(state))
    entry = ltp
    stop_ref = upper2 if direction == "short" else lower2
    band_width = abs(stop_ref - vwap)
    stop = round(stop_ref + (band_width * 0.3 if direction == "short" else -band_width * 0.3), 2)
    target1 = round(vwap, 2)
    target2 = round(lower2 if direction == "short" else upper2, 2)
    return StrategySignal("vwap_reversion", state.symbol, direction, "TRIGGERED",
                           f"range regime (ADX {adx:.1f}), price outside VWAP 2sigma band, fading to VWAP",
                           entry=entry, stop=stop, target1=target1, target2=target2, updated_at=_ts(state))


def supertrend_flip(state) -> Optional[StrategySignal]:
    sig = state.indicators.supertrend_signal
    if sig not in ("BUY", "SELL"):
        return None
    direction = "long" if sig == "BUY" else "short"
    entry = state.ltp
    sized = atr_stop_target(entry, state.indicators.atr, direction, stop_mult=1.5, target_mults=(1.5, 3.0))
    return StrategySignal("supertrend_flip", state.symbol, direction, "TRIGGERED",
                           f"fresh Supertrend {sig} flip",
                           entry=entry,
                           stop=sized["stop"] if sized else None,
                           target1=sized["target1"] if sized else None,
                           target2=sized["target2"] if sized else None,
                           updated_at=_ts(state))


def gap_classifier(state) -> Optional[StrategySignal]:
    gap = state.gap_pct
    open_, ltp, prev_close, rvol = state.open, state.ltp, state.previous_close, state.rel_volume
    if gap is None or open_ is None or prev_close is None or abs(gap) < GAP_MIN_PCT:
        return None
    gap_up = gap > 0
    if gap_up:
        if ltp >= open_:
            classification, direction = "GAP_AND_GO", "long"
        elif ltp < prev_close:
            classification, direction = "GAP_FADE", "short"
        else:
            classification, direction = "UNRESOLVED", None
    else:
        if ltp <= open_:
            classification, direction = "GAP_AND_GO", "short"
        elif ltp > prev_close:
            classification, direction = "GAP_FADE", "long"
        else:
            classification, direction = "UNRESOLVED", None

    if direction is None:
        return StrategySignal("gap_classifier", state.symbol, None, "WATCHING",
                               f"{gap:+.2f}% gap {'up' if gap_up else 'down'}, unresolved between open and prior close",
                               updated_at=_ts(state))
    gated = bool(rvol and rvol >= GAP_RVOL_GATE)
    entry = ltp
    sized = atr_stop_target(entry, state.indicators.atr, direction, stop_mult=1.2, target_mults=(1.5, 2.5)) if gated else None
    status = "TRIGGERED" if gated else "WEAK"
    reason = f"{classification.replace('_',' ').title()} on {gap:+.2f}% gap" + ("" if gated else f" (RVOL {rvol or 0:.2f}x < {GAP_RVOL_GATE}x gate)")
    return StrategySignal("gap_classifier", state.symbol, direction, status, reason,
                           entry=entry if gated else None,
                           stop=sized["stop"] if sized else None,
                           target1=sized["target1"] if sized else None,
                           target2=sized["target2"] if sized else None,
                           updated_at=_ts(state))


class StrategyTracker:
    """Forward-tracks every TRIGGERED signal against real subsequent ticks to
    compute a same-session hit rate, and owns the 'first pullback today'
    state for the vwap_pullback strategy (the only one of the five needing
    cross-tick memory beyond what StockState already carries)."""

    MIN_SAMPLE = 5

    def __init__(self):
        self._pullback_seen: Dict[str, bool] = {}
        self._open: Dict[tuple, dict] = {}
        self._outcomes: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))

    def reset_day(self):
        self._pullback_seen.clear()
        self._open.clear()
        self._outcomes.clear()

    def vwap_pullback(self, state) -> Optional[StrategySignal]:
        vwap = state.indicators.vwap
        ret15 = state.momentum.ret_15m
        if vwap is None or ret15 is None or abs(ret15) < STRONG_MOVE_15M_PCT:
            return None
        direction = "long" if ret15 > 0 else "short"
        if self._pullback_seen.get(state.symbol):
            return None
        ltp = state.ltp
        near_vwap = abs(ltp - vwap) / vwap * 100 < VWAP_TOUCH_PCT
        if not near_vwap:
            return StrategySignal("vwap_pullback", state.symbol, direction, "WATCHING",
                                   f"strong {ret15:+.2f}% 15m move, awaiting first VWAP pullback", updated_at=_ts(state))
        self._pullback_seen[state.symbol] = True
        entry = ltp
        sized = atr_stop_target(entry, state.indicators.atr, direction, stop_mult=1.0, target_mults=(1.5, 2.5))
        return StrategySignal("vwap_pullback", state.symbol, direction, "TRIGGERED",
                               f"first pullback to VWAP after {ret15:+.2f}% 15m move",
                               entry=entry,
                               stop=sized["stop"] if sized else None,
                               target1=sized["target1"] if sized else None,
                               target2=sized["target2"] if sized else None,
                               updated_at=_ts(state))

    def register_and_update(self, signals: List[StrategySignal], states: Dict[str, Any]):
        # register newly-triggered, sized signals for forward tracking
        for sig in signals:
            if sig.status != "TRIGGERED" or sig.entry is None or sig.stop is None or sig.target1 is None:
                continue
            key = (sig.strategy, sig.symbol)
            if key not in self._open:
                self._open[key] = {"direction": sig.direction, "entry": sig.entry, "stop": sig.stop, "target1": sig.target1}
        # check open positions against current ltp for a resolution
        for key in list(self._open.keys()):
            strategy, symbol = key
            state = states.get(symbol)
            if not state:
                continue
            pos = self._open[key]
            ltp = state.ltp
            hit_target = (ltp >= pos["target1"]) if pos["direction"] == "long" else (ltp <= pos["target1"])
            hit_stop = (ltp <= pos["stop"]) if pos["direction"] == "long" else (ltp >= pos["stop"])
            if hit_target:
                self._outcomes[strategy].append(1)
                del self._open[key]
            elif hit_stop:
                self._outcomes[strategy].append(0)
                del self._open[key]

    def hit_rate(self, strategy: str) -> Optional[Dict[str, Any]]:
        outcomes = self._outcomes.get(strategy)
        if not outcomes:
            return {"sample_size": 0, "win_rate_pct": None, "provisional": True}
        n = len(outcomes)
        wins = sum(outcomes)
        return {
            "sample_size": n,
            "win_rate_pct": round(wins / n * 100, 1),
            "provisional": n < self.MIN_SAMPLE,
        }


STRATEGIES = {
    "orb15": orb15,
    "vwap_reversion": vwap_reversion,
    "supertrend_flip": supertrend_flip,
    "gap_classifier": gap_classifier,
}
