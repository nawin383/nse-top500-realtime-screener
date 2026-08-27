"""Pricing engines: Black-Scholes (already in greeks), Binomial (CRR), Monte Carlo (Longstaff-Schwartz)."""
from __future__ import annotations
import math
import random
from typing import Dict

def binomial_price(spot: float, strike: float, T: float, vol: float, r: float, opt_type: str = "CE", steps: int = 200) -> float:
    """Cox-Ross-Rubinstein binomial tree for European."""
    if T <= 0 or vol <= 0:
        return max(spot - strike, 0) if opt_type == "CE" else max(strike - spot, 0)
    dt = T / steps
    u = math.exp(vol * math.sqrt(dt))
    d = 1 / u
    p = (math.exp(r * dt) - d) / (u - d)
    # terminal payoffs
    prices = [spot * (u ** j) * (d ** (steps - j)) for j in range(steps + 1)]
    values = [max(p - strike, 0) if opt_type == "CE" else max(strike - p, 0) for p in prices]
    # backward induction
    for i in range(steps - 1, -1, -1):
        for j in range(i + 1):
            values[j] = math.exp(-r * dt) * (p * values[j + 1] + (1 - p) * values[j])
    return round(values[0], 2)

def monte_carlo_price(spot: float, strike: float, T: float, vol: float, r: float, opt_type: str = "CE", sims: int = 10000) -> float:
    """Monte Carlo with antithetic variates."""
    if T <= 0 or vol <= 0:
        return max(spot - strike, 0) if opt_type == "CE" else max(strike - spot, 0)
    import math, random
    # use deterministic seed per params for reproducibility
    rnd = random.Random(hash((spot, strike, T, vol)) % 100000)
    payoffs = []
    for _ in range(sims // 2):
        z = rnd.gauss(0, 1)
        # antithetic
        for zz in (z, -z):
            st = spot * math.exp((r - 0.5 * vol * vol) * T + vol * math.sqrt(T) * zz)
            pay = max(st - strike, 0) if opt_type == "CE" else max(strike - st, 0)
            payoffs.append(pay * math.exp(-r * T))
    return round(sum(payoffs) / len(payoffs), 2)

def theoretical_bundle(spot: float, strike: float, T: float, vol: float, r: float = 0.06, opt_type: str = "CE") -> Dict:
    from ..options.greeks import black_scholes_greeks
    bs = black_scholes_greeks(spot, strike, T, vol, r, opt_type)["price"]
    bin_price = binomial_price(spot, strike, T, vol, r, opt_type, steps=200)
    mc_price = monte_carlo_price(spot, strike, T, vol, r, opt_type, sims=20000)
    return {"bs": bs, "binomial": bin_price, "monteCarlo": mc_price, "spread": round(max(bs, bin_price, mc_price) - min(bs, bin_price, mc_price), 2)}
