from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter()

# ---------- Core: live or last trading day (no mock) ----------
def _get_chain_live(symbol: str, expiry: str | None):
    from ..options.fetcher_v2 import get_chain_live_or_last_day
    try:
        return get_chain_live_or_last_day(symbol.upper(), expiry)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/options/expiries")
async def expiries(symbol: str = Query("NIFTY", description="NIFTY, SENSEX, BANKNIFTY")):
    data = _get_chain_live(symbol, None)
    return {"symbol": symbol.upper(), "expiries": data["expiries"], "count": len(data["expiries"]), "source": data["source"], "isLastTradingDay": data.get("isLastTradingDay", False)}

@router.get("/options/chain")
async def chain(
    symbol: str = Query("NIFTY"),
    expiry: Optional[str] = Query(None, description="YYYY-MM-DD"),
    mock: bool = Query(False, description="force mock (deprecated, live only)"),
):
    if mock:
        from ..options.fetcher import get_chain as _old
        return _old(symbol.upper(), expiry, force_mock=True)
    return _get_chain_live(symbol, expiry)

@router.get("/options/tshape")
async def tshape(
    symbol: str = Query("NIFTY"),
    expiry: Optional[str] = Query(None),
    window: int = Query(10, ge=5, le=20),
):
    data = _get_chain_live(symbol, expiry)
    chain = data["chain"]
    atm = data["atmStrike"]
    idx = next((i for i, c in enumerate(chain) if c["strike"] == atm), len(chain)//2)
    lo = max(0, idx - window)
    hi = min(len(chain), idx + window + 1)
    data["chain"] = chain[lo:hi]
    data["window"] = window
    return data

@router.get("/options/analytics")
async def analytics(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    data = _get_chain_live(symbol, expiry)
    return {
        "symbol": data["symbol"],
        "spot": data["spot"],
        "expiry": data["expiry"],
        "atmStrike": data["atmStrike"],
        "analytics": data["analytics"],
        "source": data["source"],
        "isLastTradingDay": data.get("isLastTradingDay", False),
        "generatedAt": data["generatedAt"],
    }

# ---------- Institutional Advanced ----------
@router.get("/options/atm-premium")
async def atm_premium(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import atm_premium_analysis
    data = _get_chain_live(symbol, expiry)
    res = atm_premium_analysis(data["chain"], data["spot"], data["expiries"])
    res.update({"symbol": symbol.upper(), "spot": data["spot"], "expiry": data["expiry"], "source": data["source"], "isLastTradingDay": data.get("isLastTradingDay", False)})
    return res

@router.get("/options/vol-surface")
async def vol_surface(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import volatility_surface
    data = _get_chain_live(symbol, expiry)
    res = volatility_surface(data["chain"], data["spot"], data["expiry"])
    res.update({"symbol": symbol.upper(), "expiry": data["expiry"]})
    return res

@router.get("/options/greeks-dashboard")
async def greeks_dashboard(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import greeks_dashboard as _gd
    data = _get_chain_live(symbol, expiry)
    return _gd(data["chain"])

@router.get("/options/iv-hv")
async def iv_hv(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import iv_vs_hv
    data = _get_chain_live(symbol, expiry)
    # try to get spot history from market_state if available (NIFTY spot history)
    return iv_vs_hv(data["chain"])

@router.get("/options/vix")
async def vix():
    from ..options.institutional import vix_analysis
    return vix_analysis()

@router.get("/options/moneyness")
async def moneyness(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import moneyness_analysis
    data = _get_chain_live(symbol, expiry)
    return moneyness_analysis(data["chain"], data["spot"])

@router.get("/options/pcr")
async def pcr(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import pcr_analysis
    data = _get_chain_live(symbol, expiry)
    return pcr_analysis(data["chain"])

@router.get("/options/oi-analysis")
async def oi_analysis(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import oi_analytics
    data = _get_chain_live(symbol, expiry)
    return oi_analytics(data["chain"], data["spot"])

@router.get("/options/unusual")
async def unusual(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import unusual_activity
    data = _get_chain_live(symbol, expiry)
    return {"symbol": symbol.upper(), "expiry": data["expiry"], "unusual": unusual_activity(data["chain"])}

@router.get("/options/term-structure")
async def term_structure(symbol: str = Query("NIFTY"), max_expiries: int = Query(6, ge=1, le=10)):
    from ..options.institutional import term_structure as _ts
    from ..options.greeks import days_to_expiry
    data = _get_chain_live(symbol, None)
    points = []
    for exp in data["expiries"][:max_expiries]:
        try:
            exp_data = data if exp == data["expiry"] else _get_chain_live(symbol, exp)
            atm_iv = next((c["CE"]["iv"] for c in exp_data["chain"] if c["isATM"]), None)
            days = round(days_to_expiry(exp) * 365)
        except Exception:
            atm_iv, days = None, None
        points.append({"expiry": exp, "atmIv": atm_iv, "days": days})
    return _ts(points)

@router.get("/options/scenario")
async def scenario(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import scenario_analysis
    data = _get_chain_live(symbol, expiry)
    return scenario_analysis(data["spot"])

@router.get("/options/correlation")
async def correlation():
    from ..options.institutional import correlation_matrix
    return correlation_matrix()

@router.get("/options/margin-risk")
async def margin_risk(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import margin_risk as _mr
    data = _get_chain_live(symbol, expiry)
    return _mr(data["chain"], data["spot"])

@router.get("/options/theoretical")
async def theoretical(
    symbol: str = Query("NIFTY"),
    strike: float = Query(..., description="Strike"),
    expiry: str = Query(..., description="YYYY-MM-DD"),
    vol: float = Query(0.18, description="IV e.g. 0.18 for 18%"),
    r: float = Query(0.06),
    type: str = Query("CE", description="CE or PE"),
):
    from ..options.institutional import theoretical_value
    from ..options.greeks import days_to_expiry
    # get spot
    data = _get_chain_live(symbol, expiry)
    spot = data["spot"]
    T = days_to_expiry(expiry)
    return theoretical_value(spot, strike, T, vol, r, type)

@router.get("/options/mispricing")
async def mispricing(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import mispricing_scanner
    data = _get_chain_live(symbol, expiry)
    return {"symbol": symbol.upper(), "expiry": data["expiry"], "mispriced": mispricing_scanner(data["chain"], data["spot"], data["expiry"])}

@router.get("/options/synthetics")
async def synthetics(symbol: str = Query("NIFTY"), strike: float = Query(None), expiry: Optional[str] = None):
    from ..options.institutional import synthetic_positions
    data = _get_chain_live(symbol, expiry)
    k = strike or data["atmStrike"]
    return synthetic_positions(data["spot"], k, data["expiry"])

@router.get("/options/pnl")
async def pnl(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.institutional import profit_loss_diagram
    # demo: long ATM straddle
    data = _get_chain_live(symbol, expiry)
    atm = data["atmStrike"]
    legs = [{"type": "CE", "strike": atm, "premium": data["analytics"]["atmCePremium"], "qty": 1, "side": "buy"}, {"type": "PE", "strike": atm, "premium": data["analytics"]["atmPePremium"], "qty": 1, "side": "buy"}]
    return profit_loss_diagram(legs)

@router.get("/options/screeners")
async def screeners(
    symbol: str = Query("NIFTY"),
    expiry: Optional[str] = None,
    iv_gt: float = Query(None),
    volume_surge: bool = Query(False),
):
    from ..options.institutional import custom_screener
    data = _get_chain_live(symbol, expiry)
    filt = {}
    if iv_gt is not None: filt["iv_gt"] = iv_gt
    if volume_surge: filt["volume_surge"] = True
    return {"symbol": symbol.upper(), "results": custom_screener(data["chain"], filt)}

@router.get("/options/strategies")
async def strategies(
    symbol: str = Query("NIFTY"),
    expiry: Optional[str] = None,
    adx: Optional[float] = Query(None, description="underlying's current ADX, if known -- gates regime-sensitive strategies"),
    far_expiry: Optional[str] = Query(None, description="second expiry for the calendar spread; defaults to the next available expiry"),
):
    """Part 5 options strategy panel: prices short_strangle, iron_condor,
    bull_put_spread, bear_call_spread, iron_fly, calendar_spread and
    ratio_spread_1x2 off the live chain. IV rank comes from the existing
    historical.store.iv_percentile (real-or-null); ADX is passed in by the
    caller (e.g. the underlying index's screener row) since this module
    doesn't track underlying-index technicals itself."""
    from ..options.strategies import (
        short_strangle, iron_condor, bull_put_spread, bear_call_spread,
        iron_fly, calendar_spread, ratio_spread_1x2,
    )
    from ..historical.store import iv_percentile
    data = _get_chain_live(symbol, expiry)
    chain, spot, exp = data["chain"], data["spot"], data["expiry"]
    atm_iv = next((c["CE"]["iv"] for c in chain if c["isATM"]), None)
    iv_rank = iv_percentile(symbol.upper(), atm_iv).get("ivRank1Y") if atm_iv is not None else None

    result = {
        "symbol": symbol.upper(), "spot": spot, "expiry": exp,
        "iv_rank_1y": iv_rank, "adx": adx,
        "short_strangle": short_strangle(chain, spot, exp, iv_rank, adx),
        "iron_condor": iron_condor(chain, spot, exp, iv_rank, adx),
        "bull_put_spread": bull_put_spread(chain, spot, exp),
        "bear_call_spread": bear_call_spread(chain, spot, exp),
        "iron_fly": iron_fly(chain, spot, exp, iv_rank, adx),
        "ratio_spread_1x2": ratio_spread_1x2(chain, spot, exp),
    }
    far = far_expiry or next((e for e in data["expiries"] if e != exp), None)
    if far:
        try:
            far_data = _get_chain_live(symbol, far)
            result["calendar_spread"] = calendar_spread(chain, far_data["chain"], spot, exp, far)
        except Exception as e:
            result["calendar_spread"] = {"strategy": "calendar_spread", "error": str(e)}
    else:
        result["calendar_spread"] = {"strategy": "calendar_spread", "error": "no second expiry available"}
    return result


@router.get("/options/sellers-premium-dashboard")
async def sellers_premium_dashboard(
    symbol: str = Query("NIFTY"),
    expiry: Optional[str] = None,
    adx: Optional[float] = Query(None, description="underlying's current ADX, if known"),
):
    """Part 6: extends vix_analysis/iv_percentile/term_structure/oi_analytics
    (already real-data-or-null) with VIX mean-reversion z-score, real IV-RV
    spread, a composite premium-selling favorability score, and expiry-day
    pin risk. See options/seller_premium.py module docstring for what is and
    isn't fabricated when historical data is unavailable."""
    from ..options.institutional import vix_analysis, oi_analytics
    from ..options.seller_premium import (
        vix_mean_reversion_zscore, real_iv_rv_spread, premium_selling_favorability_score, expiry_day_pin_risk,
    )
    from ..historical.store import iv_percentile, get_history

    data = _get_chain_live(symbol, expiry)
    chain, spot, exp = data["chain"], data["spot"], data["expiry"]
    atm_iv = next((c["CE"]["iv"] for c in chain if c["isATM"]), None)

    vix = vix_analysis()
    vix_hist = [d["close"] for d in get_history("INDIAVIX", 252)]
    vix_z = vix_mean_reversion_zscore(vix_hist, vix.get("vix"))

    underlying_closes = [d["close"] for d in get_history(symbol.upper(), 252)]
    iv_rv = real_iv_rv_spread(underlying_closes, atm_iv)

    iv_rank = iv_percentile(symbol.upper(), atm_iv).get("ivRank1Y") if atm_iv is not None else None
    term_backwardation = None  # would need a 2nd expiry's ATM IV compared here; left null rather than guessed

    favorability = premium_selling_favorability_score(iv_rank, iv_rv.get("spread"), adx, vix_z.get("z_score"), term_backwardation)

    oi = oi_analytics(chain, spot)
    pin_risk = expiry_day_pin_risk(chain, spot, exp, oi.get("maxPain"))

    return {
        "symbol": symbol.upper(), "spot": spot, "expiry": exp,
        "vix": vix, "vix_mean_reversion": vix_z,
        "iv_rank_1y": iv_rank, "iv_rv_spread": iv_rv,
        "favorability_score": favorability,
        "expiry_pin_risk": pin_risk,
    }


@router.get("/options/earnings")
async def earnings():
    from ..options.institutional import earnings_calendar
    return earnings_calendar()
