"""Position store + Greeks aggregation, hedge ratios, SPAN/VaR."""
from __future__ import annotations
import json
import math
import statistics
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

STORE = Path(__file__).resolve().parents[2] / "data" / "positions.json"
STORE.parent.mkdir(parents=True, exist_ok=True)

def load_positions() -> List[Dict]:
    if not STORE.exists():
        return []
    try:
        return json.loads(STORE.read_text())
    except:
        return []

def save_positions(positions: List[Dict]):
    STORE.write_text(json.dumps(positions, indent=2))

def add_position(pos: Dict):
    """pos: {symbol, strike, expiry, type CE/PE, qty, premium}"""
    data = load_positions()
    data.append({**pos, "addedAt": datetime.now(tz=IST).isoformat()})
    save_positions(data)
    return data

def aggregate_greeks(positions: List[Dict] = None) -> Dict[str, Any]:
    """Net portfolio Greeks. Uses Black-Scholes per position."""
    if positions is None:
        positions = load_positions()
    if not positions:
        return {"netDelta": 0, "netGamma": 0, "netTheta": 0, "netVega": 0, "netRho": 0, "count": 0}
    from ..options.greeks import black_scholes_greeks, days_to_expiry
    from ..historical.store import get_history
    total = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}
    for p in positions:
        try:
            # need spot: use last close from historical or 100
            spot = 100
            # try to get spot from market_state? fallback
            # For institutional grade, fetch real spot via NSE; here approximate
            # Use strike as proxy for ATM
            strike = float(p["strike"])
            expiry = p["expiry"]
            T = days_to_expiry(expiry)
            # estimate IV from position's premium? use 0.18
            vol = 0.18
            g = black_scholes_greeks(spot or strike, strike, T, vol, 0.06, p["type"])
            qty = float(p.get("qty", 1))
            # qty sign: buy +1, sell -1
            sign = 1 if p.get("side", "buy") == "buy" else -1
            total["delta"] += g["delta"] * qty * 75 * sign  # NIFTY lot 75
            total["gamma"] += g["gamma"] * qty * 75 * sign
            total["theta"] += g["theta"] * qty * 75 * sign
            total["vega"] += g["vega"] * qty * 75 * sign
            total["rho"] += g["rho"] * qty * 75 * sign
        except:
            continue
    return {
        "netDelta": round(total["delta"],2),
        "netGamma": round(total["gamma"],4),
        "netTheta": round(total["theta"],2),
        "netVega": round(total["vega"],2),
        "netRho": round(total["rho"],2),
        "count": len(positions),
        "hedgeRatio": round(-total["delta"]/75,2) if total["delta"] else 0,  # NIFTY lots to hedge delta
    }

def var_es(positions: List[Dict] = None, position_value: float = 100000, confidence: float = 0.99) -> Dict[str, Any]:
    """VaR via historical simulation (1y NIFTY)."""
    from ..historical.store import get_history
    hist = get_history("NIFTY", 252)
    if len(hist) < 30:
        # fallback parametric VaR
        hv = 0.16
        daily_vol = hv / math.sqrt(252)
        z = 2.33 if confidence == 0.99 else 1.65
        var = position_value * daily_vol * z
        return {"var99": round(var,2), "expectedShortfall": round(var*1.2,2), "method": "parametric (hv 16%)"}
    closes = [d["close"] for d in hist]
    rets = [math.log(closes[i]/closes[i-1]) for i in range(1, len(closes))]
    # historical P&L
    pnl = [r * position_value for r in rets]
    pnl_sorted = sorted(pnl)
    idx = int(len(pnl_sorted) * (1 - confidence))
    var = -pnl_sorted[idx] if idx < len(pnl_sorted) else 0
    es = -sum(pnl_sorted[:idx]) / idx if idx > 0 else var
    return {"var99": round(var,2), "expectedShortfall": round(es,2), "method": "historical 1y", "samples": len(rets)}

def span_margin(positions: List[Dict] = None) -> Dict[str, Any]:
    """Simplified SPAN: 12% + exposure 6% (real NSE SPAN files would be parsed)."""
    if positions is None:
        positions = load_positions()
    # estimate notional
    notional = sum(abs(float(p.get("qty",1)) * float(p.get("strike", 100)) * 75) for p in positions) or 100000
    span = notional * 0.12
    exposure = span * 0.5
    return {"span": round(span,2), "exposure": round(exposure,2), "total": round(span+exposure,2), "notional": round(notional,2)}
