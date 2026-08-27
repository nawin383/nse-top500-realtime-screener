"""Screener logic."""
from __future__ import annotations
from typing import List, Dict, Callable
from .models import StockState, ScreenerResult

def to_result(s: StockState, reason: str=None) -> ScreenerResult:
    return ScreenerResult(
        symbol=s.symbol, token=s.token, ltp=s.ltp, change_pct=s.change_pct,
        volume=s.volume, rel_volume=s.rel_volume, score=s.score, signal=s.signal, reason=reason
    )

def top_gainers(states: List[StockState], limit=10) -> List[ScreenerResult]:
    filtered = [s for s in states if s.change_pct is not None]
    sorted_s = sorted(filtered, key=lambda x: x.change_pct, reverse=True)
    return [to_result(s, f"Change {s.change_pct:.2f}%") for s in sorted_s[:limit]]

def top_losers(states: List[StockState], limit=10) -> List[ScreenerResult]:
    filtered = [s for s in states if s.change_pct is not None]
    sorted_s = sorted(filtered, key=lambda x: x.change_pct)
    return [to_result(s, f"Change {s.change_pct:.2f}%") for s in sorted_s[:limit]]

def volume_spike(states: List[StockState], threshold: float=1.5, limit=20) -> List[ScreenerResult]:
    cand = [s for s in states if (s.rel_volume or 0) >= threshold]
    cand = sorted(cand, key=lambda x: x.rel_volume or 0, reverse=True)
    return [to_result(s, f"RelVol {s.rel_volume:.2f}x") for s in cand[:limit]]

def momentum_stocks(states: List[StockState], limit=20) -> List[ScreenerResult]:
    def mom_val(s: StockState):
        # 5m return weighted
        return abs(s.momentum.ret_5m or 0) + abs(s.momentum.ret_3m or 0)*0.7 + abs(s.momentum.ret_1m or 0)*0.3
    cand = sorted(states, key=mom_val, reverse=True)
    return [to_result(s, f"5m {s.momentum.ret_5m:.2f}%" if s.momentum.ret_5m else "mom") for s in cand[:limit]]

def breakout_stocks(states: List[StockState], limit=20) -> List[ScreenerResult]:
    cand = [s for s in states if s.momentum.day_high_breakout or s.momentum.opening_range_breakout or s.momentum.vwap_breakout]
    # rank by change_pct
    cand = sorted(cand, key=lambda x: x.change_pct or 0, reverse=True)
    return [to_result(s, "Breakout") for s in cand[:limit]]

def breakdown_stocks(states: List[StockState], limit=20) -> List[ScreenerResult]:
    cand = [s for s in states if s.momentum.day_low_breakdown]
    cand = sorted(cand, key=lambda x: x.change_pct or 0)
    return [to_result(s, "Breakdown") for s in cand[:limit]]

def vwap_above(states: List[StockState], limit=50) -> List[ScreenerResult]:
    cand = [s for s in states if s.indicators.vwap and s.ltp > s.indicators.vwap]
    cand = sorted(cand, key=lambda x: (x.ltp - x.indicators.vwap)/x.indicators.vwap, reverse=True)
    return [to_result(s, "Above VWAP") for s in cand[:limit]]

def vwap_below(states: List[StockState], limit=50) -> List[ScreenerResult]:
    cand = [s for s in states if s.indicators.vwap and s.ltp < s.indicators.vwap]
    cand = sorted(cand, key=lambda x: (x.indicators.vwap - x.ltp)/x.indicators.vwap, reverse=True)
    return [to_result(s, "Below VWAP") for s in cand[:limit]]

def unusual_activity(states: List[StockState], limit=20) -> List[ScreenerResult]:
    # use score
    cand = sorted(states, key=lambda x: x.score, reverse=True)
    return [to_result(s, f"Score {s.score}") for s in cand[:limit]]

SCREENERS: Dict[str, Callable] = {
    "gainers": top_gainers,
    "losers": top_losers,
    "volume": volume_spike,
    "momentum": momentum_stocks,
    "breakout": breakout_stocks,
    "breakdown": breakdown_stocks,
    "vwap_above": vwap_above,
    "vwap_below": vwap_below,
    "unusual": unusual_activity,
}
