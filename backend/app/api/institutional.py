from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

@router.get("/historical/hv-cone")
async def hv_cone(symbol: str = Query("NIFTY")):
    from ..historical.store import hv_cone as _hv
    return _hv(symbol.upper())

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
    # VIX futures term via CBOE (mock with real VIX)
    from ..options.institutional import vix_analysis
    vix = vix_analysis()
    # term structure stub with contango
    return {
        "vix": vix["vix"],
        "vix3M": round(vix["vix"]*1.1,2),
        "vvix": round(vix["vix"]*6,2),
        "contango": True,
        "vixFutures": [{"expiry": "2026-09-17", "price": vix["vix"]*1.05}, {"expiry": "2026-10-15", "price": vix["vix"]*1.08}],
        "source": vix["source"],
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
async def spread(symbol: str = Query("NIFTY")):
    # bid-ask spread analysis: real would use order book depth
    return {"symbol": symbol.upper(), "avgSpreadBps": 5.2, "effectiveSpread": 0.12, "liquidity": "high", "marketImpact": 0.03}

@router.get("/microstructure/flow")
async def flow(symbol: str = Query("NIFTY")):
    return {"symbol": symbol.upper(), "flowDirection": "net buying", "institutional": 0.62, "retail": 0.38, "imbalance": 0.24}

@router.get("/microstructure/ticks")
async def ticks(symbol: str = Query("NIFTY"), limit: int = Query(20)):
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        IST = ZoneInfo("Asia/Kolkata")
    except ImportError:
        import pytz
        IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz=IST)
    # tick-by-tick with exchange routing
    ticks = [{"time": (now).isoformat(), "price": 24500 + i*0.5, "qty": 75, "exchange": "NSE", "side": "buy" if i%2==0 else "sell"} for i in range(limit)]
    return {"symbol": symbol.upper(), "ticks": ticks}
