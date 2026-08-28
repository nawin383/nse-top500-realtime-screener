from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter()

@router.get("/historical/hv-cone")
async def hv_cone(symbol: str = Query("NIFTY")):
    from ..historical.store import hv_cone as _hv
    current_iv = None
    try:
        from ..options.fetcher_v2 import get_chain_live_or_last_day
        data = await get_chain_live_or_last_day(symbol.upper(), None)
        current_iv = next((c["CE"]["iv"] for c in data["chain"] if c["isATM"]), None)
    except Exception:
        pass
    return _hv(symbol.upper(), current_iv)

@router.get("/historical/iv-percentile")
async def iv_percentile(symbol: str = Query("NIFTY"), iv: float = Query(16.0)):
    from ..historical.store import iv_percentile as _ivp
    return _ivp(symbol.upper(), iv)

@router.get("/historical/earnings-iv")
async def earnings_iv(symbol: str = Query("NIFTY")):
    from ..historical.store import earnings_iv_crush
    return earnings_iv_crush(symbol.upper())

@router.get("/historical/bhavcopy")
async def bhavcopy(date: str = Query(None, description="YYYY-MM-DD")):
    from ..historical.store import ingest_nse_bhavcopy, get_history
    if date:
        ok = ingest_nse_bhavcopy(date)
        return {"date": date, "ingested": ok, "history": get_history("NIFTY", 5)[-2:]}
    return {"history": get_history("NIFTY", 10)}

@router.get("/vix/term-structure")
async def vix_term():
    from ..options.institutional import vix_analysis
    vix = vix_analysis()
    return {
        "vix": vix["vix"],
        "vix3M": None, "vvix": None, "contango": None, "vixFutures": None,
        "source": vix["source"],
        "note": "India VIX futures aren't published by NSE the way CBOE VIX futures are — term structure is unavailable, not fabricated.",
    }

@router.get("/pricing/theoretical")
async def pricing_theoretical(
    spot: float = Query(24500),
    strike: float = Query(24500),
    expiry: str = Query("2026-09-03"),
    vol: float = Query(0.18),
    r: float = Query(0.06),
    type: str = Query("CE"),
):
    from ..options.greeks import days_to_expiry
    from ..pricing.engine import theoretical_bundle
    T = days_to_expiry(expiry)
    return theoretical_bundle(spot, strike, T, vol, r, type)

@router.get("/portfolio/positions")
async def portfolio_positions():
    from ..portfolio.store import load_positions, aggregate_greeks, var_es, span_margin
    pos = load_positions()
    return {"positions": pos, "greeks": aggregate_greeks(pos), "var": var_es(pos), "margin": span_margin(pos)}

@router.post("/portfolio/positions")
async def portfolio_add(position: dict):
    from fastapi import HTTPException
    from ..portfolio.store import add_position, load_positions, aggregate_greeks
    # validation - prevent garbage / injection
    allowed = {"symbol","strike","expiry","type","qty","premium","side"}
    if not position or "symbol" not in position or "strike" not in position:
        raise HTTPException(400, "symbol and strike required")
    # sanitize symbol
    sym = str(position.get("symbol","")).upper().strip()
    if len(sym) > 20 or not sym.replace("_","").replace("-","").isalnum():
        raise HTTPException(400, "invalid symbol")
    try:
        strike = float(position.get("strike"))
        qty = int(position.get("qty", 1))
        if not (0 < strike < 1000000 and -1000 < qty < 1000 and qty!=0):
            raise HTTPException(400, "strike/qty out of range")
    except HTTPException: raise
    except: raise HTTPException(400, "invalid numeric fields")
    # expiry simple check YYYY-MM-DD
    if position.get("expiry"):
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(position["expiry"])):
            raise HTTPException(400, "expiry must be YYYY-MM-DD")
        if position.get("type") not in ("CE","PE",None):
            raise HTTPException(400, "type must be CE or PE")
    clean = {k: position[k] for k in allowed if k in position}
    clean["symbol"]=sym
    data = add_position(clean)
    return {"added": clean, "count": len(data), "greeks": aggregate_greeks(data)}

@router.get("/portfolio/correlation")
async def portfolio_corr(symbols: str = Query("NIFTY,SENSEX,BANKNIFTY,RELIANCE,TCS")):
    from ..options.institutional import correlation_matrix
    syms = [s.strip().upper() for s in symbols.split(",")]
    return correlation_matrix(syms)

@router.get("/microstructure/spread")
async def spread(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    """Real ATM bid-ask spread from the live option chain (NSE bidprice/askPrice),
    not a fixed placeholder number."""
    from ..options.fetcher_v2 import get_chain_live_or_last_day
    try:
        data = await get_chain_live_or_last_day(symbol.upper(), expiry)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    atm = next((c for c in data["chain"] if c["isATM"]), None)
    if not atm:
        return {"symbol": symbol.upper(), "avgSpreadBps": None, "note": "No ATM strike found in the live chain"}
    ce_mid = (atm["CE"]["bid"] + atm["CE"]["ask"]) / 2
    pe_mid = (atm["PE"]["bid"] + atm["PE"]["ask"]) / 2
    ce_bps = round((atm["CE"]["ask"] - atm["CE"]["bid"]) / ce_mid * 10000, 1) if ce_mid else None
    pe_bps = round((atm["PE"]["ask"] - atm["PE"]["bid"]) / pe_mid * 10000, 1) if pe_mid else None
    return {"symbol": symbol.upper(), "atmStrike": atm["strike"], "ceSpreadBps": ce_bps, "peSpreadBps": pe_bps,
            "avgSpreadBps": round(statistics_mean([x for x in (ce_bps, pe_bps) if x is not None]), 1) if (ce_bps or pe_bps) else None,
            "source": data["source"]}

def statistics_mean(xs):
    return sum(xs) / len(xs)

@router.get("/microstructure/flow")
async def flow(symbol: str = Query("NIFTY")):
    return {"symbol": symbol.upper(), "flowDirection": None, "institutional": None, "retail": None, "imbalance": None,
            "note": "Institutional/retail order-flow attribution isn't available from Kite's public market data — NSE doesn't expose participant-level trade tagging to retail API access."}

@router.get("/microstructure/ticks")
async def ticks(symbol: str = Query("NIFTY"), limit: int = Query(20)):
    return {"symbol": symbol.upper(), "ticks": [],
            "note": "Tick-by-tick trade prints aren't exposed by Kite Connect's REST/WS API for index underlyings; live per-tick data is available for subscribed tradable instruments via the /ws stream instead."}
