"""OHLC 'Breaker' breakout module.

Tracks a prior-day-OHLC / opening-range breakout level per symbol, gates a
break through it on relative volume + trend strength (ADX), and applies a
retest-and-hold filter -- the last two *closed* 1-minute candles must have
held beyond the level, not just the live tick -- before calling it a
confirmed breakout. A single tick poking through a level and immediately
snapping back is exactly the false-breakout case this filter exists to
reject.

Scoring is a 0-100 composite of RVOL / ADX / VWAP-distance / OI-trend,
weighted 40/30/20/10. OI trend is only meaningful for symbols with a live
F&O chain (a minority of the Top 500) and pulling it here would mean an
expensive per-tick options-chain fetch for every symbol, duplicating the
options-analytics module that already owns OI analysis (Part 5). Rather
than fabricate a placeholder OI contribution when it isn't available, the
score renormalizes across whichever components are actually available.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, List, Any

from .indicators import atr_stop_target

RVOL_GATE = 1.5
ADX_GATE = 20.0
RETEST_HOLD_CANDLES = 2

_WEIGHTS = {"rvol": 40.0, "adx": 30.0, "vwap": 20.0, "oi": 10.0}


@dataclass
class BreakerSignal:
    symbol: str
    direction: Optional[str]  # long | short | None
    level: Optional[float]
    status: str  # WATCHING | WEAK_BREAK | PENDING_RETEST | CONFIRMED | FAILED
    score: float
    rvol: Optional[float]
    adx: Optional[float]
    vwap_distance_pct: Optional[float]
    oi_trend_score: Optional[float]
    entry: Optional[float] = None
    stop: Optional[float] = None
    target1: Optional[float] = None
    target2: Optional[float] = None
    reward_risk_1: Optional[float] = None
    updated_at: Optional[str] = None


def _score(rvol: Optional[float], adx: Optional[float], vwap_dist: Optional[float],
           oi_trend_score: Optional[float], direction: Optional[str]) -> float:
    if direction is None:
        return 0.0
    raw = 0.0
    used_weight = 0.0
    if rvol is not None:
        raw += min(_WEIGHTS["rvol"], (rvol / RVOL_GATE) * (_WEIGHTS["rvol"] * 0.6))
        used_weight += _WEIGHTS["rvol"]
    if adx is not None:
        raw += min(_WEIGHTS["adx"], (adx / ADX_GATE) * (_WEIGHTS["adx"] * 0.6))
        used_weight += _WEIGHTS["adx"]
    if vwap_dist is not None:
        aligned = (vwap_dist > 0) if direction == "long" else (vwap_dist < 0)
        if aligned:
            raw += min(_WEIGHTS["vwap"], abs(vwap_dist) * 4)
        used_weight += _WEIGHTS["vwap"]
    if oi_trend_score is not None:
        raw += min(_WEIGHTS["oi"], oi_trend_score / 100.0 * _WEIGHTS["oi"])
        used_weight += _WEIGHTS["oi"]
    if used_weight == 0:
        return 0.0
    return round(min(100.0, raw / used_weight * 100.0), 1)


class BreakerEngine:
    """Per-symbol breakout state machine. Stateful across ticks, mirroring
    the pattern MarketState already uses for indicator accumulation."""

    def __init__(self):
        self._state: Dict[str, Dict[str, Any]] = {}

    def reset_day(self):
        self._state.clear()

    def evaluate(self, state, candles_1m: List) -> Optional[BreakerSignal]:
        level_long = state.previous_day_high if state.previous_day_high is not None else state.momentum.or15_high
        level_short = state.previous_day_low if state.previous_day_low is not None else state.momentum.or15_low
        if level_long is None and level_short is None:
            return None

        ltp = state.ltp
        rvol = state.rel_volume
        adx = state.indicators.adx
        vwap = state.indicators.vwap
        vwap_dist = round((ltp - vwap) / vwap * 100, 3) if vwap else None
        oi_trend_score = None  # see module docstring: not fetched per-tick here

        direction = None
        level = None
        if level_long is not None and ltp > level_long:
            direction, level = "long", level_long
        elif level_short is not None and ltp < level_short:
            direction, level = "short", level_short

        st = self._state.setdefault(state.symbol, {"status": "WATCHING", "direction": None, "level": None})
        gated = bool(rvol and rvol >= RVOL_GATE and adx and adx >= ADX_GATE)

        if direction is None:
            # Price is back inside the range. A breakout attempt in progress
            # (or one that was already CONFIRMED and has now reversed, e.g.
            # stopped out) becomes FAILED -- keeping direction/level for that
            # one transition so callers can see *what* failed, then decaying
            # to a clean WATCHING/no-direction state on the next check.
            if st["status"] in ("PENDING_RETEST", "WEAK_BREAK", "CONFIRMED"):
                st["status"] = "FAILED"
            elif st["status"] == "FAILED":
                st["status"] = "WATCHING"
                st["direction"] = None
                st["level"] = None
            else:
                st["status"] = "WATCHING"
        elif not gated:
            st["status"] = "WEAK_BREAK"
            st["direction"] = direction
            st["level"] = level
        else:
            if st["direction"] != direction:
                st["direction"] = direction
                st["level"] = level
                st["status"] = "PENDING_RETEST"
            if st["status"] in ("WATCHING", "WEAK_BREAK", "PENDING_RETEST"):
                recent = candles_1m[-RETEST_HOLD_CANDLES:] if len(candles_1m) >= RETEST_HOLD_CANDLES else []
                holds = len(recent) == RETEST_HOLD_CANDLES and all(
                    (c.close > level if direction == "long" else c.close < level) for c in recent
                )
                st["status"] = "CONFIRMED" if holds else "PENDING_RETEST"

        score = _score(rvol, adx, vwap_dist, oi_trend_score, st["direction"])

        entry = stop = target1 = target2 = rr1 = None
        if st["status"] == "CONFIRMED":
            entry = ltp
            sized = atr_stop_target(entry, state.indicators.atr, "long" if st["direction"] == "long" else "short")
            if sized:
                stop, target1, target2, rr1 = sized["stop"], sized["target1"], sized["target2"], sized["reward_risk_1"]

        return BreakerSignal(
            symbol=state.symbol,
            direction=st["direction"],
            level=st.get("level"),
            status=st["status"],
            score=score,
            rvol=rvol, adx=adx, vwap_distance_pct=vwap_dist,
            oi_trend_score=oi_trend_score,
            entry=entry, stop=stop, target1=target1, target2=target2, reward_risk_1=rr1,
            updated_at=state.timestamp.isoformat() if state.timestamp else None,
        )
