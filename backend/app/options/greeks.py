"""Black-Scholes Greeks for NSE options (European)."""
from __future__ import annotations
import math
from typing import Dict

# N(x) - cumulative normal
def _norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def black_scholes_greeks(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    volatility: float,  # e.g. 0.2 = 20%
    risk_free_rate: float = 0.06,
    option_type: str = "CE",  # CE or PE
) -> Dict[str, float]:
    """
    Returns dict with price, delta, gamma, theta, vega, rho, iv (input iv).
    Handles edge cases: T=0, vol=0, deep ITM/OTM.
    """
    if spot <= 0 or strike <= 0 or time_to_expiry_years <= 0 or volatility <= 0:
        # degenerate: intrinsic only
        intrinsic = max(spot - strike, 0) if option_type == "CE" else max(strike - spot, 0)
        delta = 1.0 if option_type == "CE" and spot > strike else (0.0 if option_type == "CE" else (-1.0 if spot < strike else 0.0))
        return {
            "price": round(intrinsic, 2),
            "delta": round(delta, 4),
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0,
            "iv": volatility,
        }
    try:
        S, K, T, sigma, r = spot, strike, time_to_expiry_years, volatility, risk_free_rate
        sqrtT = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
        d2 = d1 - sigma * sqrtT

        Nd1 = _norm_cdf(d1)
        Nd2 = _norm_cdf(d2)
        N_minus_d1 = _norm_cdf(-d1)
        N_minus_d2 = _norm_cdf(-d2)
        pdf_d1 = _norm_pdf(d1)

        # price
        if option_type == "CE":
            price = S * Nd1 - K * math.exp(-r * T) * Nd2
            delta = Nd1
            rho = K * T * math.exp(-r * T) * Nd2 / 100  # per 1% change
        else:
            price = K * math.exp(-r * T) * N_minus_d2 - S * N_minus_d1
            delta = Nd1 - 1  # alternative -N(-d1)
            rho = -K * T * math.exp(-r * T) * N_minus_d2 / 100

        gamma = pdf_d1 / (S * sigma * sqrtT)
        # theta per day (approx)
        # CE theta
        term1 = -(S * pdf_d1 * sigma) / (2 * sqrtT)
        if option_type == "CE":
            term2 = -r * K * math.exp(-r * T) * Nd2
            theta_annual = term1 + term2
        else:
            term2 = r * K * math.exp(-r * T) * N_minus_d2
            theta_annual = term1 + term2
        theta = theta_annual / 365  # per day
        vega = S * pdf_d1 * sqrtT / 100  # per 1% vol

        return {
            "price": round(max(price, 0.05), 2),
            "delta": round(delta, 4),
            "gamma": round(gamma, 5),
            "theta": round(theta, 4),
            "vega": round(vega, 4),
            "rho": round(rho, 4),
            "iv": volatility,
        }
    except Exception:
        intrinsic = max(spot - strike, 0) if option_type == "CE" else max(strike - spot, 0)
        return {"price": round(intrinsic,2), "delta": 0, "gamma":0, "theta":0, "vega":0, "rho":0, "iv": volatility}

def days_to_expiry(expiry_str: str) -> float:
    """expiry_str like 2026-08-28 or 28Aug2026, returns years."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        IST = ZoneInfo("Asia/Kolkata")
    except ImportError:
        import pytz
        IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz=IST)
    # try ISO
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d%b%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            exp = datetime.strptime(expiry_str, fmt)
            exp = exp.replace(hour=15, minute=30, second=0, microsecond=0, tzinfo=IST)
            break
        except:
            continue
    else:
        # fallback: assume 7 days
        return 7/365
    delta = (exp - now).total_seconds() / (365*24*3600)
    return max(delta, 1/365)  # at least 1 day
