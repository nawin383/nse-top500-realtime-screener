"""Intraday scoring 0-100 configurable."""
from __future__ import annotations
from typing import Dict
from .models import StockState

DEFAULT_WEIGHTS = {
    "momentum": 25,
    "volume": 25,
    "rel_volume": 20,
    "breakout": 15,
    "vwap": 10,
    "volatility": 5,
}

def score_stock(state: StockState, weights: Dict[str,int]=None) -> tuple[float, Dict[str,float], str, float]:
    if weights is None:
        from .config import settings
        weights = {
            "momentum": settings.score_w_momentum,
            "volume": settings.score_w_volume,
            "rel_volume": settings.score_w_rel_volume,
            "breakout": settings.score_w_breakout,
            "vwap": settings.score_w_vwap,
            "volatility": settings.score_w_volatility,
        }
    breakdown={}
    total=0

    # Momentum 0-25
    mom_score=0
    m = state.momentum
    rets = [m.ret_1m, m.ret_3m, m.ret_5m]
    valid_rets = [abs(r) for r in rets if r is not None]
    if valid_rets:
        avg_abs = sum(valid_rets)/len(valid_rets)
        # scale: 0.5% => 8, 1%=>15, 2%=>25
        if avg_abs >= 2: mom_score = weights["momentum"]
        elif avg_abs >= 1: mom_score = weights["momentum"]*0.6
        elif avg_abs >= 0.5: mom_score = weights["momentum"]*0.3
        else: mom_score = avg_abs/0.5 * weights["momentum"]*0.3
    # breakout bonus
    if m.day_high_breakout or m.opening_range_breakout:
        mom_score = min(weights["momentum"], mom_score + 5)
    breakdown["momentum"]=round(mom_score,2)
    total+=mom_score

    # Volume 0-25: based on change vs avg or raw volume percentile
    vol_score=0
    if state.volume:
        # normalize: assume avg vol ~ 1M; log scale
        import math
        # 500k => 10, 1M=>15, 5M=>25
        v = state.volume
        if v >= 5_000_000: vol_score=weights["volume"]
        elif v >= 1_000_000: vol_score=weights["volume"]*0.6
        elif v >= 500_000: vol_score=weights["volume"]*0.4
        else: vol_score = min(weights["volume"]*0.4, math.log10(max(v,1))/6*weights["volume"])
        if state.volume_spike:
            vol_score = min(weights["volume"], vol_score+5)
    breakdown["volume"]=round(vol_score,2)
    total+=vol_score

    # Rel volume 0-20
    rv = state.rel_volume or 0
    rv_score=0
    if rv >= 3: rv_score=weights["rel_volume"]
    elif rv >=2: rv_score=weights["rel_volume"]*0.75
    elif rv >=1.5: rv_score=weights["rel_volume"]*0.5
    elif rv >=1: rv_score=weights["rel_volume"]*0.25
    breakdown["rel_volume"]=round(rv_score,2)
    total+=rv_score

    # Breakout/breakdown 0-15
    br_score=0
    if state.momentum.day_high_breakout or state.momentum.opening_range_breakout or state.momentum.vwap_breakout:
        br_score=weights["breakout"]
    elif state.momentum.day_low_breakdown:
        br_score=weights["breakout"]*0.7
    elif state.change_pct and abs(state.change_pct) > 2:
        br_score=weights["breakout"]*0.5
    breakdown["breakout"]=round(br_score,2)
    total+=br_score

    # VWAP structure 0-10
    vwap_score=0
    vwap = state.indicators.vwap
    if vwap and state.ltp:
        dist = abs(state.ltp - vwap)/vwap*100
        if state.ltp > vwap:
            # above vwap bullish
            vwap_score = min(weights["vwap"], 5 + min(dist*2,5))
        else:
            vwap_score = min(weights["vwap"]*0.6, dist*1.5)
        # cross detection: if close to vwap
        if dist < 0.2:
            vwap_score+=2
    breakdown["vwap"]=round(vwap_score,2)
    total+=vwap_score

    # Volatility 0-5 (ATR based or range_pct)
    vola_score=0
    if state.range_pct:
        rp = state.range_pct
        if rp > 4: vola_score=weights["volatility"]
        elif rp >2: vola_score=weights["volatility"]*0.6
        elif rp >1: vola_score=weights["volatility"]*0.3
    elif state.indicators.atr and state.ltp:
        atr_pct = state.indicators.atr / state.ltp *100
        if atr_pct > 1: vola_score=weights["volatility"]
        elif atr_pct >0.5: vola_score=weights["volatility"]*0.6
    breakdown["volatility"]=round(vola_score,2)
    total+=vola_score

    total = min(100, round(total,2))

    # signal
    if total >= 80:
        signal="STRONG_BUY" if (state.change_pct or 0) >=0 else "STRONG_SELL"
    elif total >=65:
        signal="BUY" if (state.change_pct or 0) >=0 else "SELL"
    elif br_score==weights["breakout"]:
        signal="BREAKOUT"
    elif state.momentum.day_low_breakdown:
        signal="BREAKDOWN"
    elif rv_score >= weights["rel_volume"]*0.5:
        signal="VOLUME_SPIKE"
    else:
        signal="NEUTRAL"

    strength = total/100
    return total, breakdown, signal, strength
