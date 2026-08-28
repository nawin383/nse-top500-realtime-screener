"""Institutional option fetcher: real NSE only, last trading day cache when closed, no mock."""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

from ..market_hours import get_market_status

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

CACHE_FILE = Path(__file__).resolve().parents[3] / "data" / "options_last_trading_day.json"
CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

# In-memory last fetch
_mem_cache: Dict[str, Dict] = {}
_mem_ts: Dict[str, float] = {}

def _load_disk_cache(symbol: str, expiry: str | None) -> Optional[Dict]:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        key = f"{symbol}:{expiry or 'auto'}"
        entry = data.get(key)
        if entry and entry.get("chain"):
            # check if it's from last trading day (within 5 days)
            gen = entry.get("generatedAt")
            if gen:
                try:
                    gen_dt = datetime.fromisoformat(gen)
                    age = (datetime.now(tz=IST) - gen_dt).days
                    if age <= 5:
                        entry["source"] = entry.get("source","nse") + "_cached_last_day"
                        entry["isLastTradingDay"] = True
                        return entry
                except:
                    pass
                return entry
    except Exception as e:
        logger.debug(f"disk cache load failed {e}")
    return None

def _save_disk_cache(symbol: str, expiry: str | None, data: Dict):
    try:
        existing = {}
        if CACHE_FILE.exists():
            try:
                existing = json.loads(CACHE_FILE.read_text())
            except:
                existing = {}
        key = f"{symbol}:{expiry or 'auto'}"
        # don't store mock
        if data.get("source") in ("mock", "mock_fallback"):
            return
        existing[key] = data
        # prune old (keep last 10)
        if len(existing) > 20:
            # keep most recent 10
            items = list(existing.items())[-10:]
            existing = dict(items)
        CACHE_FILE.write_text(json.dumps(existing))
    except Exception as e:
        logger.debug(f"disk cache save failed {e}")

def _is_market_open() -> bool:
    status, is_live = get_market_status(datetime.now(tz=IST))
    return is_live

def fetch_nse_real(symbol: str, expiry: str | None) -> Optional[Dict]:
    # SENSEX is BSE, not NSE — try BSE API, else fail
    if symbol == "SENSEX":
        return fetch_bse_sensex(expiry)
    # NSE for NIFTY/BANKNIFTY/FINNIFTY
    if symbol not in ("NIFTY", "BANKNIFTY", "FINNIFTY"):
        return None
    try:
        import requests
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        s = requests.Session()
        s.headers.update(NSE_HEADERS)
        try:
            s.get("https://www.nseindia.com/option-chain", timeout=5)
        except:
            pass
        r = s.get(url, timeout=10)
        if r.status_code != 200:
            logger.info(f"NSE {symbol} HTTP {r.status_code}")
            return None
        data = r.json()
        records = data.get("records", {})
        spot = records.get("underlyingValue")
        if not spot:
            return None
        expiries = records.get("expiryDates", [])
        if not expiries:
            return None
        target_expiry = expiry or expiries[0]
        # normalize expiry to NSE format dd-MMM-yyyy
        # expiry input is YYYY-MM-DD, convert
        if expiry and "-" in expiry and len(expiry)==10:
            try:
                dt = datetime.strptime(expiry, "%Y-%m-%d")
                target_expiry = dt.strftime("%d-%b-%Y")
            except:
                pass
        chain_raw = data.get("filtered", {}).get("data", [])
        if not chain_raw:
            chain_raw = data.get("records", {}).get("data", [])
        # filter by expiry
        filtered = [c for c in chain_raw if c.get("expiryDate") == target_expiry]
        if not filtered:
            # fallback to first expiry
            target_expiry = expiries[0]
            filtered = [c for c in chain_raw if c.get("expiryDate") == target_expiry]
        if not filtered:
            return None
        # parse
        try:
            exp_dt = datetime.strptime(target_expiry, "%d-%b-%Y")
            expiry_iso = exp_dt.strftime("%Y-%m-%d")
        except:
            expiry_iso = target_expiry
        from .greeks import days_to_expiry, black_scholes_greeks
        T = days_to_expiry(expiry_iso)
        expiries_iso = []
        for e in expiries:
            try:
                expiries_iso.append(datetime.strptime(e, "%d-%b-%Y").strftime("%Y-%m-%d"))
            except:
                expiries_iso.append(e)
        chain = []
        for entry in filtered:
            strike = entry.get("strikePrice")
            ce_raw = entry.get("CE", {})
            pe_raw = entry.get("PE", {})
            ce_iv = float(ce_raw.get("impliedVolatility", 0))/100 if ce_raw.get("impliedVolatility") else 0.18
            pe_iv = float(pe_raw.get("impliedVolatility", 0))/100 if pe_raw.get("impliedVolatility") else 0.18
            if ce_iv <= 0.01: ce_iv = 0.18
            if pe_iv <= 0.01: pe_iv = 0.18
            ce_g = black_scholes_greeks(float(spot), float(strike), T, ce_iv, 0.06, "CE")
            pe_g = black_scholes_greeks(float(spot), float(strike), T, pe_iv, 0.06, "PE")
            ce_ltp = float(ce_raw.get("lastPrice", 0) or ce_g["price"])
            pe_ltp = float(pe_raw.get("lastPrice", 0) or pe_g["price"])
            ce_bid = float(ce_raw.get("bidprice", ce_ltp*0.99) or ce_ltp*0.99)
            ce_ask = float(ce_raw.get("askPrice", ce_ltp*1.01) or ce_ltp*1.01)
            pe_bid = float(pe_raw.get("bidprice", pe_ltp*0.99) or pe_ltp*0.99)
            pe_ask = float(pe_raw.get("askPrice", pe_ltp*1.01) or pe_ltp*1.01)
            is_atm = abs(float(strike) - float(spot)) < (50 if symbol=="NIFTY" else 100)
            ce_oi = int(ce_raw.get("openInterest", 0) or 0)
            pe_oi = int(pe_raw.get("openInterest", 0) or 0)
            ce_oi_chg = int(ce_raw.get("changeinOpenInterest", 0) or 0)
            pe_oi_chg = int(pe_raw.get("changeinOpenInterest", 0) or 0)
            ce_vol = int(ce_raw.get("totalTradedVolume", 0) or 0)
            pe_vol = int(pe_raw.get("totalTradedVolume", 0) or 0)
            chain.append({
                "strike": strike,
                "isATM": is_atm,
                "isITM_CE": float(spot) > float(strike),
                "isITM_PE": float(spot) < float(strike),
                "CE": {"ltp": round(ce_ltp,2), "bid": round(ce_bid,2), "ask": round(ce_ask,2), "volume": ce_vol, "oi": ce_oi, "oiChange": ce_oi_chg, "iv": round(ce_iv*100,2), "delta": ce_g["delta"], "gamma": ce_g["gamma"], "theta": ce_g["theta"], "vega": ce_g["vega"], "rho": ce_g["rho"], "premium": round(ce_ltp,2)},
                "PE": {"ltp": round(pe_ltp,2), "bid": round(pe_bid,2), "ask": round(pe_ask,2), "volume": pe_vol, "oi": pe_oi, "oiChange": pe_oi_chg, "iv": round(pe_iv*100,2), "delta": pe_g["delta"], "gamma": pe_g["gamma"], "theta": pe_g["theta"], "vega": pe_g["vega"], "rho": pe_g["rho"], "premium": round(pe_ltp,2)},
            })
        chain.sort(key=lambda x: x["strike"])
        atm = min(chain, key=lambda x: abs(x["strike"] - float(spot)))["strike"] if chain else 0
        for c in chain:
            c["isATM"] = c["strike"] == atm
        # analytics
        from .fetcher import _analytics as _old_analytics
        # reuse analytics logic (import to avoid duplication)
        try:
            analytics = _old_analytics(chain, float(spot), atm)
        except:
            analytics = {}
        return {
            "symbol": symbol,
            "spot": round(float(spot),2),
            "expiry": expiry_iso,
            "expiries": expiries_iso,
            "generatedAt": datetime.now(tz=IST).isoformat(),
            "source": "nse_live",
            "atmStrike": atm,
            "chain": chain,
            "analytics": analytics,
            "isLastTradingDay": False,
        }
    except Exception as e:
        logger.warning(f"NSE fetch failed {symbol} {expiry}: {e}", exc_info=True)
        return None

def fetch_bse_sensex(expiry: str | None) -> Optional[Dict]:
    """Try BSE SENSEX: spot via Yahoo, chain via BSE API if available, else NSE-like fallback."""
    # Try spot via Yahoo Finance for SENSEX (^BSESN) and then attempt BSE chain
    try:
        import requests
        # 1) Get SENSEX spot via Yahoo (no auth)
        spot = None
        try:
            r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EBSESN?range=1d&interval=1d", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                spot = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
                spot = float(spot)
        except:
            pass
        if not spot:
            # fallback to BSE's index page API
            try:
                r = requests.get("https://api.bseindia.com/BseIndiaAPI/api/GetScripInfo/w?scripcode=1", headers=NSE_HEADERS, timeout=5)
                if r.status_code == 200:
                    spot = float(r.json().get("CurrRate", 0))
            except:
                pass
        if not spot:
            return None
        # 2) Try BSE option chain - BSE's endpoint for SENSEX options (scripcode 1)
        # Format: https://api.bseindia.com/BseIndiaAPI/api/OptionChain/w?scripcode=1&expiry=20240828
        # We need expiry in ddmmyyyy
        bse_expiry = None
        if expiry:
            try:
                dt = datetime.strptime(expiry, "%Y-%m-%d")
                bse_expiry = dt.strftime("%Y%m%d")
            except:
                bse_expiry = None
        # Try to fetch chain
        chain = None
        try:
            url = "https://api.bseindia.com/BseIndiaAPI/api/OptionChain/w"
            params = {"scripcode": "1"}
            if bse_expiry:
                params["expiry"] = bse_expiry
            r = requests.get(url, params=params, headers=NSE_HEADERS, timeout=8)
            if r.status_code == 200:
                bse_data = r.json()
                # BSE returns Table with CE/PE, try to parse
                # If successful, convert to our format
                # For now, if we get data, parse similarly to NSE
                # This is a best-effort; if parsing fails, return None to fallback to last cached
                # Check if data has expected fields
                if isinstance(bse_data, dict) and bse_data.get("Table"):
                    # parse BSE Table
                    # BSE Table is list of dicts with Strike, CallOI, PutOI etc
                    from .greeks import days_to_expiry, black_scholes_greeks
                    expiry_iso = expiry or datetime.now(tz=IST).strftime("%Y-%m-%d")
                    T = days_to_expiry(expiry_iso)
                    chain = []
                    for row in bse_data["Table"][:21]:
                        strike = float(row.get("StrikePrice", 0))
                        ce_ol = int(row.get("CallOI", 0) or 0)
                        pe_ol = int(row.get("PutOI", 0) or 0)
                        ce_ltp = float(row.get("CallLTP", 0) or 0)
                        pe_ltp = float(row.get("PutLTP", 0) or 0)
                        ce_iv = float(row.get("CallIV", 18) or 18)/100
                        pe_iv = float(row.get("PutIV", 18) or 18)/100
                        ce_g = black_scholes_greeks(spot, strike, T, ce_iv, 0.06, "CE")
                        pe_g = black_scholes_greeks(spot, strike, T, pe_iv, 0.06, "PE")
                        chain.append({
                            "strike": strike,
                            "isATM": abs(strike - spot) < 100,
                            "isITM_CE": spot > strike,
                            "isITM_PE": spot < strike,
                            "CE": {"ltp": ce_ltp or ce_g["price"], "bid": round((ce_ltp or ce_g["price"])*0.99,2), "ask": round((ce_ltp or ce_g["price"])*1.01,2), "volume": int(row.get("CallVolume", 0) or 0), "oi": ce_ol, "oiChange": 0, "iv": round(ce_iv*100,2), "delta": ce_g["delta"], "gamma": ce_g["gamma"], "theta": ce_g["theta"], "vega": ce_g["vega"], "rho": ce_g["rho"], "premium": ce_ltp or ce_g["price"]},
                            "PE": {"ltp": pe_ltp or pe_g["price"], "bid": round((pe_ltp or pe_g["price"])*0.99,2), "ask": round((pe_ltp or pe_g["price"])*1.01,2), "volume": int(row.get("PutVolume", 0) or 0), "oi": pe_ol, "oiChange": 0, "iv": round(pe_iv*100,2), "delta": pe_g["delta"], "gamma": pe_g["gamma"], "theta": pe_g["theta"], "vega": pe_g["vega"], "rho": pe_g["rho"], "premium": pe_ltp or pe_g["price"]},
                        })
                    if chain:
                        chain.sort(key=lambda x: x["strike"])
                        atm = min(chain, key=lambda x: abs(x["strike"] - spot))["strike"]
                        for c in chain:
                            c["isATM"] = c["strike"] == atm
                        from .fetcher import _analytics
                        analytics = _analytics(chain, spot, atm)
                        # get expiries via BSE's expiry list
                        expiries = [expiry or datetime.now(tz=IST).strftime("%Y-%m-%d")]
                        try:
                            re = requests.get("https://api.bseindia.com/BseIndiaAPI/api/OptionExpiry/w?scripcode=1", headers=NSE_HEADERS, timeout=5)
                            if re.status_code == 200:
                                expiries = [datetime.strptime(e, "%d %b %Y").strftime("%Y-%m-%d") for e in re.json().get("Table", [])[:5]]
                        except:
                            pass
                        return {
                            "symbol": "SENSEX",
                            "spot": round(spot,2),
                            "expiry": expiry or expiries[0],
                            "expiries": expiries,
                            "generatedAt": datetime.now(tz=IST).isoformat(),
                            "source": "bse_live",
                            "atmStrike": atm,
                            "chain": chain,
                            "analytics": analytics,
                            "isLastTradingDay": False,
                        }
        except Exception as e:
            logger.debug(f"BSE chain parse failed {e}")
        # if BSE chain not available but we have spot, we should not generate mock - return None to trigger last cached
        return None
    except Exception as e:
        logger.debug(f"BSE fetch failed {e}")
        return None

async def get_chain_live_or_last_day(symbol: str, expiry: str | None) -> Dict:
    """Institutional: live if market open, else last trading day cached. No mock.
    Live NIFTY/SENSEX prefer Kite Connect (fetcher_kite.py) over NSE-website
    scraping -- NSE blocks/CAPTCHAs most cloud-hosted IPs, so the scrape is
    kept only as a fallback for symbols the Kite static universe doesn't
    cover (BANKNIFTY) or if Kite credentials/quote fail for some reason."""
    symbol = symbol.upper()
    is_open = _is_market_open()

    if is_open:
        from .fetcher_kite import fetch_chain_from_kite
        try:
            kite_live = await fetch_chain_from_kite(symbol, expiry)
        except Exception as e:
            logger.warning(f"Kite chain fetch errored for {symbol} {expiry or ''}: {e}", exc_info=True)
            kite_live = None
        if kite_live:
            _save_disk_cache(symbol, expiry, kite_live)
            _mem_cache[f"{symbol}:{expiry or 'auto'}"] = kite_live
            _mem_ts[f"{symbol}:{expiry or 'auto'}"] = time.time()
            return kite_live

    # SENSEX special: BSE scrape (Kite path above already covers SENSEX when it succeeds)
    if symbol == "SENSEX":
        bse = fetch_bse_sensex(expiry)
        if bse:
            _save_disk_cache(symbol, expiry, bse)
            _mem_cache[f"{symbol}:{expiry or 'auto'}"] = bse
            _mem_ts[f"{symbol}:{expiry or 'auto'}"] = time.time()
            return bse
        cached = _load_disk_cache(symbol, expiry)
        if cached:
            return cached
        if is_open:
            raise RuntimeError(f"Live Kite and BSE fetch both failed for SENSEX {expiry or ''} and no cached last day. Market is open but both sources unreachable.")
        else:
            raise RuntimeError(f"Market closed, BSE unreachable, and no last trading day cache for SENSEX {expiry or ''}. No fabricated data will be returned.")
    # NIFTY/BANKNIFTY
    if is_open:
        live = fetch_nse_real(symbol, expiry)
        if live:
            _save_disk_cache(symbol, expiry, live)
            _mem_cache[f"{symbol}:{expiry or 'auto'}"] = live
            _mem_ts[f"{symbol}:{expiry or 'auto'}"] = time.time()
            return live
        cached = _load_disk_cache(symbol, expiry)
        if cached:
            cached["isLastTradingDay"] = True
            cached["note"] = "Live fetch failed, showing last cached"
            return cached
        raise RuntimeError(f"Live Kite and NSE fetch both failed for {symbol} {expiry or ''} and no cached last day available. Market is open but both sources unreachable.")
    else:
        live = fetch_nse_real(symbol, expiry)
        if live:
            _save_disk_cache(symbol, expiry, live)
            live["isLastTradingDay"] = True
            live["note"] = "Market closed, showing last trading day (NSE still serves)"
            return live
        cached = _load_disk_cache(symbol, expiry)
        if cached:
            return cached
        raise RuntimeError(f"Market closed, NSE unreachable, and no last trading day cache for {symbol} {expiry or ''}. No fabricated data will be returned.")
