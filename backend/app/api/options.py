from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

@router.get("/options/expiries")
async def expiries(symbol: str = Query("NIFTY", description="NIFTY, SENSEX, BANKNIFTY")):
    from ..options.fetcher import get_expiries
    exps = get_expiries(symbol.upper())
    return {"symbol": symbol.upper(), "expiries": exps, "count": len(exps)}

@router.get("/options/chain")
async def chain(
    symbol: str = Query("NIFTY", description="NIFTY/SENSEX/BANKNIFTY"),
    expiry: Optional[str] = Query(None, description="YYYY-MM-DD, e.g. 2026-08-28"),
    mock: bool = Query(False, description="force mock for testing"),
):
    from ..options.fetcher import get_chain
    data = get_chain(symbol.upper(), expiry, force_mock=mock)
    return data

@router.get("/options/analytics")
async def analytics(symbol: str = Query("NIFTY"), expiry: Optional[str] = None):
    from ..options.fetcher import get_chain
    data = get_chain(symbol.upper(), expiry)
    return {
        "symbol": data["symbol"],
        "spot": data["spot"],
        "expiry": data["expiry"],
        "atmStrike": data["atmStrike"],
        "analytics": data["analytics"],
        "source": data["source"],
        "generatedAt": data["generatedAt"],
    }

# T-shape specific endpoint (same as chain but filtered window around ATM)
@router.get("/options/tshape")
async def tshape(
    symbol: str = Query("NIFTY"),
    expiry: Optional[str] = None,
    window: int = Query(10, ge=5, le=20, description="strikes around ATM"),
):
    from ..options.fetcher import get_chain
    data = get_chain(symbol.upper(), expiry)
    chain = data["chain"]
    atm = data["atmStrike"]
    # find ATM index
    idx = next((i for i, c in enumerate(chain) if c["strike"] == atm), len(chain)//2)
    lo = max(0, idx - window)
    hi = min(len(chain), idx + window + 1)
    sliced = chain[lo:hi]
    data["chain"] = sliced
    data["window"] = window
    return data
