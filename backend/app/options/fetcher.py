"""Option chain fetcher: NSE public API (no auth) + Kite fallback + mock."""
from __future__ import annotations
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import math

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

logger = logging.getLogger(__name__)

# NSE headers required
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}

# cache: symbol -> {key: chain}
_cache = {"NIFTY": {}, "SENSEX": {}, "BANKNIFTY": {}, "FINNIFTY": {}, "ts": 0}
CACHE_TTL = 8  # seconds

def _mock_spot(symbol: str) -> float:
    if symbol == "NIFTY":
        return 24500 + random.uniform(-150, 150)
    if symbol == "SENSEX":
        return 80000 + random.uniform(-400, 400)
    if symbol == "BANKNIFTY":
        return 51000 + random.uniform(-300, 300)
    return 1000 + random.uniform(-50, 50)

def _mock_expiries(symbol: str) -> List[str]:
    now = datetime.now(tz=IST)
    # weekly expiries for NIFTY/SENSEX (Thu), monthly last Thu
    expiries = []
    for i in range(5):
        # next Thursday
        days_ahead = 3 - now.weekday()  # Thu = 3
        if days_ahead <= 0:
            days_ahead += 7
        exp = now + timedelta(days=days_ahead + i*7)
        expiries.append(exp.strftime("%Y-%m-%d"))
    return expiries

def _mock_chain(symbol: str, spot: float, expiry: str) -> Dict[str, Any]:
    # strikes around spot
    step = 50 if symbol == "NIFTY" else (100 if symbol == "SENSEX" else 100)
    # around ATM ±10 strikes
    atm = round(spot / step) * step
    strikes = [atm + step * i for i in range(-10, 11)]
    # expiries need T
    from .greeks import days_to_expiry, black_scholes_greeks
    T = days_to_expiry(expiry)
    chain = []
    for strike in strikes:
        # distance from spot
        dist = abs(strike - spot) / spot
        # IV smile: ATM 16%, OTM higher
        base_iv = 0.16 + dist * 0.8 + random.uniform(-0.02, 0.02)
        base_iv = max(0.12, min(0.6, base_iv))
        # premium via BS
        ce_greeks = black_scholes_greeks(spot, strike, T, base_iv, 0.06, "CE")
        pe_greeks = black_scholes_greeks(spot, strike, T, base_iv, 0.06, "PE")
        # add market micro noise to LTP
        ce_ltp = max(0.05, ce_greeks["price"] * random.uniform(0.9, 1.1))
        pe_ltp = max(0.05, pe_greeks["price"] * random.uniform(0.9, 1.1))
        # OI: max at ATM, decays outward
        oi_factor = math.exp(- (abs(strike - spot) / (spot*0.02)))
        ce_oi = int(random.uniform(800000, 3000000) * (0.5 + 0.5*oi_factor))
        pe_oi = int(random.uniform(800000, 3000000) * (0.5 + 0.5*oi_factor))
        ce_oi_chg = random.randint(-50000, 100000)
        pe_oi_chg = random.randint(-50000, 100000)
        # volume
        ce_vol = int(random.uniform(50000, 500000) * (0.7 + 0.3*oi_factor))
        pe_vol = int(random.uniform(50000, 500000) * (0.7 + 0.3*oi_factor))
        # bid/ask spread 0.3%
        ce_bid = round(ce_ltp * 0.998, 2)
        ce_ask = round(ce_ltp * 1.002, 2)
        pe_bid = round(pe_ltp * 0.998, 2)
        pe_ask = round(pe_ltp * 1.002, 2)
        is_atm = strike == atm
        chain.append({
            "strike": strike,
            "isATM": is_atm,
            "isITM_CE": spot > strike,
            "isITM_PE": spot < strike,
            "CE": {
                "ltp": round(ce_ltp,2),
                "bid": ce_bid, "ask": ce_ask,
                "volume": ce_vol, "oi": ce_oi, "oiChange": ce_oi_chg,
                "iv": round(base_iv*100,2),
                "delta": ce_greeks["delta"], "gamma": ce_greeks["gamma"],
                "theta": ce_greeks["theta"], "vega": ce_greeks["vega"], "rho": ce_greeks["rho"],
                "premium": round(ce_ltp,2),
            },
            "PE": {
                "ltp": round(pe_ltp,2),
                "bid": pe_bid, "ask": pe_ask,
                "volume": pe_vol, "oi": pe_oi, "oiChange": pe_oi_chg,
                "iv": round(base_iv*100,2),
                "delta": pe_greeks["delta"], "gamma": pe_greeks["gamma"],
                "theta": pe_greeks["theta"], "vega": pe_greeks["vega"], "rho": pe_greeks["rho"],
                "premium": round(pe_ltp,2),
            }
        })
    # sort by strike
    chain.sort(key=lambda x: x["strike"])
    # ATM index
    atm_idx = next((i for i, c in enumerate(chain) if c["isATM"]), len(chain)//2)
    return {
        "symbol": symbol,
        "spot": round(spot,2),
        "expiry": expiry,
        "expiries": _mock_expiries(symbol),
        "generatedAt": datetime.now(tz=IST).isoformat(),
        "source": "mock",
        "atmStrike": atm,
        "chain": chain,
        "analytics": _analytics(chain, spot, atm),
    }

def _analytics(chain: List[Dict], spot: float, atm: int) -> Dict[str, Any]:
    # PCR, max pain, OI totals, ATM premium
    total_ce_oi = sum(c["CE"]["oi"] for c in chain)
    total_pe_oi = sum(c["PE"]["oi"] for c in chain)
    pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi else 0
    # max pain: strike where (CE OI * distance + PE OI * distance) minimal
    best = None
    best_val = float("inf")
    for c in chain:
        pain = 0
        strike = c["strike"]
        for o in chain:
            s = o["strike"]
            if s > strike:
                pain += o["CE"]["oi"] * (s - strike)
            elif s < strike:
                pain += o["PE"]["oi"] * (strike - s)
        if pain < best_val:
            best_val = pain
            best = strike
    atm_row = next((c for c in chain if c["strike"] == atm), chain[len(chain)//2])
    return {
        "pcr": pcr,
        "totalCeOi": total_ce_oi,
        "totalPeOi": total_pe_oi,
        "maxPain": best,
        "atmCePremium": atm_row["CE"]["ltp"],
        "atmPePremium": atm_row["PE"]["ltp"],
        "atmStraddle": round(atm_row["CE"]["ltp"] + atm_row["PE"]["ltp"],2),
        "spot": round(spot,2),
        "atmStrike": atm,
    }

def fetch_nse_chain(symbol: str, expiry: str = None) -> Optional[Dict]:
    """Try NSE public API, return parsed or None."""
    # NSE endpoint
    # https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY
    # For SENSEX, BSE not NSE, NSE has no SENSEX options, but BSE has SENSEX, we can fallback to mock for SENSEX or use NSE for BANKNIFTY
    # SENSEX options are on BSE, use mock or try BSE API
    # For now, only try NSE for NIFTY/BANKNIFTY
    if symbol not in ("NIFTY", "BANKNIFTY", "FINNIFTY"):
        return None
    try:
        import requests
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        # need session with cookies
        s = requests.Session()
        s.headers.update(NSE_HEADERS)
        # first hit main page to get cookies
        try:
            s.get("https://www.nseindia.com/option-chain", timeout=5)
        except:
            pass
        r = s.get(url, timeout=8)
        if r.status_code != 200:
            logger.debug(f"NSE chain {symbol} status {r.status_code}")
            return None
        data = r.json()
        # parse
        records = data.get("records", {})
        spot = records.get("underlyingValue", 0)
        expiries = records.get("expiryDates", [])
        if not expiries:
            return None
        target_expiry = expiry or expiries[0]
        # find data for target_expiry
        chain_raw = data.get("filtered", {}).get("data", [])
        # if filtered empty, use all
        if not chain_raw:
            chain_raw = data.get("records", {}).get("data", [])
        # filter by expiry
        chain_raw = [c for c in chain_raw if c.get("expiryDate") == target_expiry]
        if not chain_raw:
            # fallback to first expiry's data
            chain_raw = [c for c in data.get("records", {}).get("data", []) if c.get("expiryDate") == expiries[0]][:21]
            target_expiry = expiries[0]
        # convert expiry to YYYY-MM-DD
        try:
            exp_dt = datetime.strptime(target_expiry, "%d-%b-%Y")
            expiry_iso = exp_dt.strftime("%Y-%m-%d")
        except:
            expiry_iso = target_expiry
        # build T shape
        from .greeks import days_to_expiry, black_scholes_greeks
        T = days_to_expiry(expiry_iso)
        chain = []
        expiries_iso = []
        for e in expiries:
            try:
                expiries_iso.append(datetime.strptime(e, "%d-%b-%Y").strftime("%Y-%m-%d"))
            except:
                expiries_iso.append(e)
        for entry in chain_raw:
            strike = entry.get("strikePrice")
            ce_raw = entry.get("CE", {})
            pe_raw = entry.get("PE", {})
            # NSE provides iv, delta etc? but we compute greeks
            # need lastPrice, bidQty etc
            ce_iv = float(ce_raw.get("impliedVolatility", 0))/100 if ce_raw.get("impliedVolatility") else 0.18
            pe_iv = float(pe_raw.get("impliedVolatility", 0))/100 if pe_raw.get("impliedVolatility") else 0.18
            if ce_iv <= 0.01:
                ce_iv = 0.18
            if pe_iv <= 0.01:
                pe_iv = 0.18
            # compute greeks if not provided
            ce_g = black_scholes_greeks(spot, strike, T, ce_iv, 0.06, "CE")
            pe_g = black_scholes_greeks(spot, strike, T, pe_iv, 0.06, "PE")
            # use NSE's lastPrice if available else greeks price
            ce_ltp = float(ce_raw.get("lastPrice", 0) or ce_g["price"])
            pe_ltp = float(pe_raw.get("lastPrice", 0) or pe_g["price"])
            ce_bid = float(ce_raw.get("bidQty", 0))  # NSE doesn't give bid price directly, use lastPrice - 0.5
            # NSE fields: bidQty, bidprice, askQty, askPrice not always present; fallback
            ce_bid_price = float(ce_raw.get("bidprice", ce_ltp*0.99) or ce_ltp*0.99)
            ce_ask_price = float(ce_raw.get("askPrice", ce_ltp*1.01) or ce_ltp*1.01)
            pe_bid_price = float(pe_raw.get("bidprice", pe_ltp*0.99) or pe_ltp*0.99)
            pe_ask_price = float(pe_raw.get("askPrice", pe_ltp*1.01) or pe_ltp*1.01)
            is_atm = abs(strike - spot) < (50 if symbol=="NIFTY" else 100)
            # OI
            ce_oi = int(ce_raw.get("openInterest", 0) or 0)
            pe_oi = int(pe_raw.get("openInterest", 0) or 0)
            ce_oi_chg = int(ce_raw.get("changeinOpenInterest", 0) or 0)
            pe_oi_chg = int(pe_raw.get("changeinOpenInterest", 0) or 0)
            ce_vol = int(ce_raw.get("totalTradedVolume", 0) or 0)
            pe_vol = int(pe_raw.get("totalTradedVolume", 0) or 0)
            chain.append({
                "strike": strike,
                "isATM": is_atm,
                "isITM_CE": spot > strike,
                "isITM_PE": spot < strike,
                "CE": {
                    "ltp": round(ce_ltp,2),
                    "bid": round(ce_bid_price,2), "ask": round(ce_ask_price,2),
                    "volume": ce_vol, "oi": ce_oi, "oiChange": ce_oi_chg,
                    "iv": round(ce_iv*100,2),
                    "delta": ce_g["delta"], "gamma": ce_g["gamma"], "theta": ce_g["theta"], "vega": ce_g["vega"], "rho": ce_g["rho"],
                    "premium": round(ce_ltp,2),
                },
                "PE": {
                    "ltp": round(pe_ltp,2),
                    "bid": round(pe_bid_price,2), "ask": round(pe_ask_price,2),
                    "volume": pe_vol, "oi": pe_oi, "oiChange": pe_oi_chg,
                    "iv": round(pe_iv*100,2),
                    "delta": pe_g["delta"], "gamma": pe_g["gamma"], "theta": pe_g["theta"], "vega": pe_g["vega"], "rho": pe_g["rho"],
                    "premium": round(pe_ltp,2),
                }
            })
        chain.sort(key=lambda x: x["strike"])
        atm = min(chain, key=lambda x: abs(x["strike"] - spot))["strike"] if chain else 0
        for c in chain:
            c["isATM"] = c["strike"] == atm
        return {
            "symbol": symbol,
            "spot": round(float(spot),2),
            "expiry": expiry_iso,
            "expiries": expiries_iso,
            "generatedAt": datetime.now(tz=IST).isoformat(),
            "source": "nse",
            "atmStrike": atm,
            "chain": chain,
            "analytics": _analytics(chain, float(spot), atm),
        }
    except Exception as e:
        logger.debug(f"NSE fetch failed {symbol}: {e}", exc_info=True)
        return None

def get_chain(symbol: str = "NIFTY", expiry: str = None, force_mock: bool = False) -> Dict:
    symbol = symbol.upper()
    if symbol == "SENSEX":
        spot = _mock_spot(symbol)
        exp = expiry or _mock_expiries(symbol)[0]
        return _mock_chain(symbol, spot, exp)
    now = time.time()
    global _cache
    key = f"{symbol}:{expiry or 'auto'}"
    # ensure symbol cache exists
    if symbol not in _cache:
        _cache[symbol] = {}
    if not force_mock and now - _cache.get("ts", 0) < CACHE_TTL and key in _cache.get(symbol, {}):
        return _cache[symbol][key]
    if not force_mock:
        try:
            nse = fetch_nse_chain(symbol, expiry)
            if nse:
                _cache[symbol][key] = nse
                _cache["ts"] = now
                return nse
        except Exception as e:
            logger.debug(f"NSE fetch exception {symbol}: {e}")
    # fallback mock
    spot = _mock_spot(symbol)
    exp = expiry or _mock_expiries(symbol)[0]
    mock = _mock_chain(symbol, spot, exp)
    mock["source"] = "mock" if force_mock else "mock_fallback"
    _cache[symbol][key] = mock
    _cache["ts"] = now
    return mock

def get_expiries(symbol: str) -> List[str]:
    chain = get_chain(symbol)
    return chain.get("expiries", [])
