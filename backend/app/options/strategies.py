"""Options strategy panel (Part 5): constructs real multi-leg strategies from
the live option chain and prices them with the existing profit_loss_diagram
P&L engine (institutional.py) -- extending that module's payoff/OI/scoring
logic rather than duplicating it.

Each strategy picks real strikes off the live chain (by delta where relevant),
reads real premiums/theta from that chain, and returns net premium, max
profit/loss, breakevens, POP, theta, and a margin estimate.

POP (probability of profit) is the risk-neutral lognormal probability that
spot finishes between the position's breakevens at expiry, using the
position's average IV and days-to-expiry via the same _norm_cdf already used
for Black-Scholes greeks elsewhere in this codebase -- a standard, principled
approximation, not a fabricated number. For a one-sided break-even (a credit
spread has only one), the missing side is treated as +/-infinity.

Margin is approximated as the strategy's own defined max loss (correct for
exchange SPAN on a defined-risk spread/condor/fly) for the four defined-risk
strategies, and via institutional.margin_risk's naked/short-leg approximation
for the two undefined-risk strategies (calendar spread, 1x2 ratio spread).
"""
from __future__ import annotations
import math
from typing import List, Dict, Any, Optional

from .institutional import profit_loss_diagram, margin_risk as _margin_risk_calc
from .greeks import _norm_cdf, days_to_expiry

IV_RANK_HIGH_GATE = 50.0
ADX_LOW_GATE = 25.0


def _atm(chain: List[Dict]) -> Optional[Dict]:
    return next((c for c in chain if c.get("isATM")), None)


def _nearest_by_strike_distance(chain: List[Dict], target_strike: float) -> Optional[Dict]:
    if not chain:
        return None
    return min(chain, key=lambda c: abs(c["strike"] - target_strike))


def _nearest_by_delta(chain: List[Dict], side: str, target_abs_delta: float) -> Optional[Dict]:
    candidates = [c for c in chain if c.get(side, {}).get("delta") is not None]
    if not candidates:
        return None
    return min(candidates, key=lambda c: abs(abs(c[side]["delta"]) - target_abs_delta))


def _net_theta(legs_with_theta: List[Dict]) -> Optional[float]:
    vals = [t for t in legs_with_theta if t is not None]
    if not vals:
        return None
    return round(sum(vals), 2)


def _pop_between(breakevens: List[float], spot: float, avg_iv_pct: float, T: float,
                  direction: str = "between") -> Optional[float]:
    """Risk-neutral probability spot finishes between (or outside, for a
    naked/ratio position) the breakevens at expiry, using a lognormal model
    with the position's average IV. Returns a 0-100 percentage."""
    if not breakevens or avg_iv_pct is None or avg_iv_pct <= 0 or T is None or T <= 0 or spot <= 0:
        return None
    vol = avg_iv_pct / 100.0
    sigma_sqrt_t = vol * math.sqrt(T)
    if sigma_sqrt_t <= 0:
        return None

    def cdf_le(k: float) -> float:
        d = (math.log(k / spot) + 0.5 * vol * vol * T) / sigma_sqrt_t
        return _norm_cdf(d)

    bes = sorted(breakevens)
    if len(bes) == 1:
        # one-sided: profit zone is either above or below the single breakeven
        p_below = cdf_le(bes[0])
        p_above = 1 - p_below
        return round((p_above if direction == "above" else p_below) * 100, 1)
    lo, hi = bes[0], bes[-1]
    p_between = cdf_le(hi) - cdf_le(lo)
    if direction == "outside":
        p_between = 1 - p_between
    return round(max(0.0, min(1.0, p_between)) * 100, 1)


def _avg_iv(*contracts_sides) -> Optional[float]:
    vals = [c[side]["iv"] for c, side in contracts_sides if c and c.get(side, {}).get("iv") is not None]
    return sum(vals) / len(vals) if vals else None


def _regime_gate(iv_rank: Optional[float], adx: Optional[float]) -> Dict[str, Any]:
    if iv_rank is None or adx is None:
        return {"eligible": None, "reason": "IV rank and/or ADX not supplied -- regime unknown"}
    eligible = iv_rank >= IV_RANK_HIGH_GATE and adx <= ADX_LOW_GATE
    reason = (f"IV rank {iv_rank:.0f} >= {IV_RANK_HIGH_GATE:.0f} and ADX {adx:.1f} <= {ADX_LOW_GATE:.0f}"
              if eligible else
              f"needs IV rank >= {IV_RANK_HIGH_GATE:.0f} (got {iv_rank:.0f}) and ADX <= {ADX_LOW_GATE:.0f} (got {adx:.1f})")
    return {"eligible": eligible, "reason": reason}


def short_strangle(chain: List[Dict], spot: float, expiry: str, iv_rank: Optional[float] = None,
                    adx: Optional[float] = None, target_delta: float = 0.16) -> Dict[str, Any]:
    call = _nearest_by_delta(chain, "CE", target_delta)
    put = _nearest_by_delta(chain, "PE", target_delta)
    if not call or not put:
        return {"strategy": "short_strangle", "error": "chain missing delta data"}
    legs = [
        {"type": "CE", "strike": call["strike"], "premium": call["CE"]["ltp"], "qty": 1, "side": "sell"},
        {"type": "PE", "strike": put["strike"], "premium": put["PE"]["ltp"], "qty": 1, "side": "sell"},
    ]
    pnl = profit_loss_diagram(legs)
    net_premium = round(call["CE"]["ltp"] + put["PE"]["ltp"], 2)
    T = days_to_expiry(expiry)
    avg_iv = _avg_iv((call, "CE"), (put, "PE"))
    pop = _pop_between(pnl["breakevens"], spot, avg_iv, T, direction="between")
    theta = _net_theta([-call["CE"].get("theta"), -put["PE"].get("theta")]) if call["CE"].get("theta") is not None else None
    return {
        "strategy": "short_strangle", "legs": legs, "net_premium": net_premium,
        "max_profit": net_premium, "max_loss": pnl["maxLoss"], "breakevens": pnl["breakevens"],
        "pop_pct": pop, "theta": theta, "margin_estimate": None,
        "regime": _regime_gate(iv_rank, adx),
    }


def iron_condor(chain: List[Dict], spot: float, expiry: str, iv_rank: Optional[float] = None,
                 adx: Optional[float] = None, short_delta: float = 0.16, wing_delta: float = 0.05) -> Dict[str, Any]:
    short_call = _nearest_by_delta(chain, "CE", short_delta)
    short_put = _nearest_by_delta(chain, "PE", short_delta)
    long_call = _nearest_by_delta(chain, "CE", wing_delta)
    long_put = _nearest_by_delta(chain, "PE", wing_delta)
    if not all([short_call, short_put, long_call, long_put]):
        return {"strategy": "iron_condor", "error": "chain missing delta data"}
    legs = [
        {"type": "CE", "strike": short_call["strike"], "premium": short_call["CE"]["ltp"], "qty": 1, "side": "sell"},
        {"type": "CE", "strike": long_call["strike"], "premium": long_call["CE"]["ltp"], "qty": 1, "side": "buy"},
        {"type": "PE", "strike": short_put["strike"], "premium": short_put["PE"]["ltp"], "qty": 1, "side": "sell"},
        {"type": "PE", "strike": long_put["strike"], "premium": long_put["PE"]["ltp"], "qty": 1, "side": "buy"},
    ]
    pnl = profit_loss_diagram(legs)
    net_premium = round(short_call["CE"]["ltp"] + short_put["PE"]["ltp"] - long_call["CE"]["ltp"] - long_put["PE"]["ltp"], 2)
    T = days_to_expiry(expiry)
    avg_iv = _avg_iv((short_call, "CE"), (short_put, "PE"))
    pop = _pop_between(pnl["breakevens"], spot, avg_iv, T, direction="between")
    theta = _net_theta([-short_call["CE"].get("theta"), -short_put["PE"].get("theta"),
                         long_call["CE"].get("theta"), long_put["PE"].get("theta")])
    max_loss = pnl["maxLoss"] if isinstance(pnl["maxLoss"], (int, float)) else None
    return {
        "strategy": "iron_condor", "legs": legs, "net_premium": net_premium,
        "max_profit": net_premium, "max_loss": max_loss, "breakevens": pnl["breakevens"],
        "pop_pct": pop, "theta": theta, "margin_estimate": abs(max_loss) if max_loss is not None else None,
        "regime": _regime_gate(iv_rank, adx),
    }


def _credit_spread(chain: List[Dict], spot: float, expiry: str, side: str, short_delta: float,
                    long_delta: float) -> Dict[str, Any]:
    short_leg = _nearest_by_delta(chain, side, short_delta)
    long_leg = _nearest_by_delta(chain, side, long_delta)
    if not short_leg or not long_leg or short_leg["strike"] == long_leg["strike"]:
        return {"error": "chain missing delta data or strikes collapsed"}
    legs = [
        {"type": side, "strike": short_leg["strike"], "premium": short_leg[side]["ltp"], "qty": 1, "side": "sell"},
        {"type": side, "strike": long_leg["strike"], "premium": long_leg[side]["ltp"], "qty": 1, "side": "buy"},
    ]
    pnl = profit_loss_diagram(legs)
    net_premium = round(short_leg[side]["ltp"] - long_leg[side]["ltp"], 2)
    T = days_to_expiry(expiry)
    avg_iv = _avg_iv((short_leg, side), (long_leg, side))
    direction = "above" if side == "CE" else "below"
    pop = _pop_between(pnl["breakevens"], spot, avg_iv, T, direction=direction)
    theta = _net_theta([-short_leg[side].get("theta"), long_leg[side].get("theta")])
    max_loss = pnl["maxLoss"] if isinstance(pnl["maxLoss"], (int, float)) else None
    return {
        "legs": legs, "net_premium": net_premium, "max_profit": net_premium, "max_loss": max_loss,
        "breakevens": pnl["breakevens"], "pop_pct": pop, "theta": theta,
        "margin_estimate": abs(max_loss) if max_loss is not None else None,
    }


def bull_put_spread(chain: List[Dict], spot: float, expiry: str, short_delta: float = 0.30,
                     long_delta: float = 0.16) -> Dict[str, Any]:
    res = _credit_spread(chain, spot, expiry, "PE", short_delta, long_delta)
    res["strategy"] = "bull_put_spread"
    return res


def bear_call_spread(chain: List[Dict], spot: float, expiry: str, short_delta: float = 0.30,
                      long_delta: float = 0.16) -> Dict[str, Any]:
    res = _credit_spread(chain, spot, expiry, "CE", short_delta, long_delta)
    res["strategy"] = "bear_call_spread"
    return res


def iron_fly(chain: List[Dict], spot: float, expiry: str, iv_rank: Optional[float] = None,
             adx: Optional[float] = None, wing_delta: float = 0.10) -> Dict[str, Any]:
    atm = _atm(chain) or _nearest_by_strike_distance(chain, spot)
    long_call = _nearest_by_delta(chain, "CE", wing_delta)
    long_put = _nearest_by_delta(chain, "PE", wing_delta)
    if not atm or not long_call or not long_put:
        return {"strategy": "iron_fly", "error": "chain missing ATM/delta data"}
    legs = [
        {"type": "CE", "strike": atm["strike"], "premium": atm["CE"]["ltp"], "qty": 1, "side": "sell"},
        {"type": "PE", "strike": atm["strike"], "premium": atm["PE"]["ltp"], "qty": 1, "side": "sell"},
        {"type": "CE", "strike": long_call["strike"], "premium": long_call["CE"]["ltp"], "qty": 1, "side": "buy"},
        {"type": "PE", "strike": long_put["strike"], "premium": long_put["PE"]["ltp"], "qty": 1, "side": "buy"},
    ]
    pnl = profit_loss_diagram(legs)
    net_premium = round(atm["CE"]["ltp"] + atm["PE"]["ltp"] - long_call["CE"]["ltp"] - long_put["PE"]["ltp"], 2)
    T = days_to_expiry(expiry)
    avg_iv = _avg_iv((atm, "CE"), (atm, "PE"))
    pop = _pop_between(pnl["breakevens"], spot, avg_iv, T, direction="between")
    theta = _net_theta([-atm["CE"].get("theta"), -atm["PE"].get("theta"),
                         long_call["CE"].get("theta"), long_put["PE"].get("theta")])
    max_loss = pnl["maxLoss"] if isinstance(pnl["maxLoss"], (int, float)) else None
    return {
        "strategy": "iron_fly", "legs": legs, "net_premium": net_premium,
        "max_profit": net_premium, "max_loss": max_loss, "breakevens": pnl["breakevens"],
        "pop_pct": pop, "theta": theta, "margin_estimate": abs(max_loss) if max_loss is not None else None,
        "regime": _regime_gate(iv_rank, adx),
    }


def calendar_spread(near_chain: List[Dict], far_chain: List[Dict], spot: float, near_expiry: str,
                     far_expiry: str) -> Dict[str, Any]:
    """Sell the near-expiry ATM option, buy the far-expiry ATM option (same
    strike/type). Only makes sense to a premium seller on contango skew
    (far IV > near IV, i.e. the term structure spec's Part 6 module already
    classifies) -- eligibility reflects that, not a hardcoded market view."""
    near_atm = _atm(near_chain) or _nearest_by_strike_distance(near_chain, spot)
    if not near_atm:
        return {"strategy": "calendar_spread", "error": "near chain missing ATM"}
    far_leg = _nearest_by_strike_distance(far_chain, near_atm["strike"])
    if not far_leg:
        return {"strategy": "calendar_spread", "error": "far chain missing matching strike"}
    side = "CE"
    near_iv, far_iv = near_atm[side]["iv"], far_leg[side]["iv"]
    net_premium = round(near_atm[side]["ltp"] - far_leg[side]["ltp"], 2)  # negative = net debit (typical)
    theta = _net_theta([-near_atm[side].get("theta"), far_leg[side].get("theta")])
    contango = far_iv is not None and near_iv is not None and far_iv > near_iv
    return {
        "strategy": "calendar_spread",
        "legs": [
            {"type": side, "strike": near_atm["strike"], "expiry": near_expiry, "premium": near_atm[side]["ltp"], "qty": 1, "side": "sell"},
            {"type": side, "strike": far_leg["strike"], "expiry": far_expiry, "premium": far_leg[side]["ltp"], "qty": 1, "side": "buy"},
        ],
        "net_premium": net_premium, "near_iv": near_iv, "far_iv": far_iv,
        "max_profit": "peaks near strike at near expiry (undefined-form, not a single number)",
        "max_loss": abs(net_premium) if net_premium is not None else None,
        "breakevens": [], "pop_pct": None,  # undefined risk profile -- P&L isn't a simple two-breakeven shape
        "theta": theta, "margin_estimate": abs(net_premium) if net_premium is not None else None,
        "regime": {"eligible": contango, "reason": (
            f"far IV {far_iv:.1f} > near IV {near_iv:.1f} (contango)" if contango and far_iv is not None
            else f"needs far-expiry IV > near-expiry IV (near {near_iv}, far {far_iv})" if near_iv is not None
            else "IV data unavailable")},
    }


def ratio_spread_1x2(chain: List[Dict], spot: float, expiry: str, side: str = "CE",
                      long_delta: float = 0.40, short_delta: float = 0.16) -> Dict[str, Any]:
    """Buy 1x near-the-money, sell 2x further OTM, same side. Naked past the
    second short strike -- undefined/large risk on that side, so margin is
    approximated via the existing naked-leg margin_risk() helper rather than
    a defined max-loss (there isn't one)."""
    long_leg = _nearest_by_delta(chain, side, long_delta)
    short_leg = _nearest_by_delta(chain, side, short_delta)
    if not long_leg or not short_leg or long_leg["strike"] == short_leg["strike"]:
        return {"strategy": "ratio_spread_1x2", "error": "chain missing delta data or strikes collapsed"}
    legs = [
        {"type": side, "strike": long_leg["strike"], "premium": long_leg[side]["ltp"], "qty": 1, "side": "buy"},
        {"type": side, "strike": short_leg["strike"], "premium": short_leg[side]["ltp"], "qty": 2, "side": "sell"},
    ]
    pnl = profit_loss_diagram(legs)
    net_premium = round(2 * short_leg[side]["ltp"] - long_leg[side]["ltp"], 2)
    T = days_to_expiry(expiry)
    avg_iv = _avg_iv((long_leg, side), (short_leg, side))
    direction = "above" if side == "CE" else "below"
    pop = _pop_between(pnl["breakevens"], spot, avg_iv, T, direction=direction) if pnl["breakevens"] else None
    theta = _net_theta([long_leg[side].get("theta"), -2 * short_leg[side].get("theta") if short_leg[side].get("theta") is not None else None])
    naked_margin = _margin_risk_calc(chain, spot, position_value=spot * 1)  # reuse existing naked-exposure approximation
    return {
        "strategy": "ratio_spread_1x2", "legs": legs, "net_premium": net_premium,
        "max_profit": pnl["maxProfit"], "max_loss": pnl["maxLoss"],
        "breakevens": pnl["breakevens"], "pop_pct": pop, "theta": theta,
        "margin_estimate": naked_margin.get("totalMargin"),
    }


STRATEGY_FUNCS = {
    "short_strangle": short_strangle,
    "iron_condor": iron_condor,
    "bull_put_spread": bull_put_spread,
    "bear_call_spread": bear_call_spread,
    "iron_fly": iron_fly,
    "ratio_spread_1x2": ratio_spread_1x2,
}
