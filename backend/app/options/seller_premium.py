"""Part 6: Seller's Premium Dashboard. Extends the existing VIX/IV analytics
(institutional.vix_analysis, historical.store.iv_percentile, hv_cone,
institutional.term_structure) rather than duplicating them, adding:

  - VIX mean-reversion z-score: current VIX vs its own historical mean/std.
  - real IV-RV spread: today's live IV minus the ACTUAL trailing realized
    vol computed from real historical closes (both genuine numbers). This
    module does not fabricate a historical *IV* series -- there is no
    stored IV-history data source, so "IV-RV spread over time" would mean
    inventing past IV values. Only the current spread point is claimed as
    real; the realized-vol series is real and can be charted on its own.
  - a composite 0-100 "Premium Selling Favorability Score" from whichever
    of IV rank / IV-RV spread / ADX / VIX z-score / term-structure shape
    are actually available, renormalized across present components (same
    pattern as breaker.py's _score) rather than fabricating a value for a
    missing one.
  - expiry-day pin-risk: spot's distance to max pain and OI concentration
    near the money, most meaningful on the expiry date itself.

Every field is real-data-or-null: this sandbox has no network access to
backfill NSE/Kite VIX or underlying candle history, so most series will be
null here -- exactly the same honest-null rule used throughout this project.
"""
from __future__ import annotations
import math
import statistics
from datetime import datetime
from typing import List, Dict, Any, Optional

VIX_ZSCORE_LOOKBACK_DAYS = 252
IV_RV_SPREAD_HISTORY_DAYS = 252


def vix_mean_reversion_zscore(vix_history_closes: List[float], current_vix: Optional[float]) -> Dict[str, Any]:
    if not vix_history_closes or len(vix_history_closes) < 30 or current_vix is None:
        return {"z_score": None, "mean": None, "std": None, "sample_size": len(vix_history_closes or []),
                "reason": "insufficient VIX history (need >=30 days)"}
    mean = statistics.mean(vix_history_closes)
    std = statistics.pstdev(vix_history_closes)
    if std == 0:
        return {"z_score": None, "mean": round(mean, 2), "std": 0.0, "sample_size": len(vix_history_closes),
                "reason": "zero variance in VIX history"}
    z = (current_vix - mean) / std
    return {
        "z_score": round(z, 2), "mean": round(mean, 2), "std": round(std, 2),
        "current": current_vix, "sample_size": len(vix_history_closes),
        "interpretation": "elevated (favors selling)" if z > 1 else "depressed (favors buying)" if z < -1 else "near mean",
    }


def real_iv_rv_spread(underlying_closes: List[float], current_iv_pct: Optional[float],
                       rv_window: int = 20) -> Dict[str, Any]:
    """Real trailing realized vol (annualized, from actual historical closes)
    vs today's real live ATM IV. Returns the realized-vol series too (for a
    frontend chart) but never a fabricated historical IV series."""
    if not underlying_closes or len(underlying_closes) < rv_window + 1:
        return {"current_iv": current_iv_pct, "realized_vol": None, "spread": None,
                "realized_vol_series": [], "reason": "insufficient price history for realized vol"}
    rv_series = []
    for i in range(rv_window, len(underlying_closes)):
        window = underlying_closes[i - rv_window:i]
        rets = [math.log(window[j] / window[j - 1]) for j in range(1, len(window)) if window[j - 1] > 0]
        if len(rets) > 1:
            rv_series.append(round(statistics.stdev(rets) * math.sqrt(252) * 100, 2))
    if not rv_series:
        return {"current_iv": current_iv_pct, "realized_vol": None, "spread": None,
                "realized_vol_series": [], "reason": "could not compute realized vol"}
    current_rv = rv_series[-1]
    spread = round(current_iv_pct - current_rv, 2) if current_iv_pct is not None else None
    return {
        "current_iv": current_iv_pct, "realized_vol": current_rv, "spread": spread,
        "realized_vol_series": rv_series[-90:],
        "interpretation": (
            "IV rich vs realized (favors selling)" if spread is not None and spread > 2 else
            "IV cheap vs realized (favors buying)" if spread is not None and spread < -2 else
            "roughly fair" if spread is not None else None
        ),
    }


def _sub_score(value: Optional[float], favorable_high: bool, lo: float, hi: float) -> Optional[float]:
    """Linearly map value in [lo,hi] to a 0-100 sub-score; None passes through."""
    if value is None:
        return None
    v = max(lo, min(hi, value))
    frac = (v - lo) / (hi - lo) if hi != lo else 0.5
    return round((frac if favorable_high else 1 - frac) * 100, 1)


def premium_selling_favorability_score(iv_rank: Optional[float], iv_rv_spread: Optional[float],
                                        adx: Optional[float], vix_zscore: Optional[float],
                                        term_structure_backwardation: Optional[bool]) -> Dict[str, Any]:
    weights = {"iv_rank": 30.0, "iv_rv_spread": 25.0, "adx": 20.0, "vix_z": 15.0, "term_structure": 10.0}
    subs = {
        "iv_rank": _sub_score(iv_rank, favorable_high=True, lo=0, hi=100),
        "iv_rv_spread": _sub_score(iv_rv_spread, favorable_high=True, lo=-10, hi=10),
        "adx": _sub_score(adx, favorable_high=False, lo=10, hi=40),
        "vix_z": _sub_score(vix_zscore, favorable_high=True, lo=-2, hi=2),
        "term_structure": 100.0 if term_structure_backwardation is True else 0.0 if term_structure_backwardation is False else None,
    }
    used_weight = sum(weights[k] for k, v in subs.items() if v is not None)
    if used_weight == 0:
        return {"score": None, "components": subs, "reason": "no regime inputs available"}
    raw = sum(weights[k] * v for k, v in subs.items() if v is not None)
    score = round(raw / used_weight, 1)
    return {
        "score": score, "components": subs,
        "coverage_pct": round(used_weight / sum(weights.values()) * 100, 0),
        "label": "favorable for premium selling" if score >= 65 else "favorable for premium buying" if score <= 35 else "neutral",
    }


def expiry_day_pin_risk(chain: List[Dict], spot: float, expiry: str, max_pain: Optional[float]) -> Dict[str, Any]:
    try:
        is_expiry_day = datetime.strptime(expiry, "%Y-%m-%d").date() == datetime.now().date()
    except (ValueError, TypeError):
        is_expiry_day = False
    if not chain or not spot or max_pain is None:
        return {"is_expiry_day": is_expiry_day, "pin_risk_score": None, "reason": "missing chain/spot/max-pain"}

    distance_to_max_pain_pct = round(abs(spot - max_pain) / spot * 100, 3)
    band = spot * 0.01
    near_oi = sum(c["CE"]["oi"] + c["PE"]["oi"] for c in chain if abs(c["strike"] - spot) <= band)
    total_oi = sum(c["CE"]["oi"] + c["PE"]["oi"] for c in chain) or 1
    concentration_pct = round(near_oi / total_oi * 100, 2)

    proximity_score = max(0.0, 100.0 - distance_to_max_pain_pct * 20)  # 0% away=100, >=5% away=>0
    pin_risk_score = round((proximity_score * 0.6 + concentration_pct * 0.4), 1)
    return {
        "is_expiry_day": is_expiry_day,
        "distance_to_max_pain_pct": distance_to_max_pain_pct,
        "oi_concentration_near_money_pct": concentration_pct,
        "pin_risk_score": pin_risk_score,
        "label": ("high pin risk" if pin_risk_score >= 65 else "low pin risk" if pin_risk_score < 35 else "moderate pin risk"),
    }
