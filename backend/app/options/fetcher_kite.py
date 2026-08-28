"""Kite Connect-based option chain fetcher.

Replaces fetcher_v2.py's NSE-website-scraping path as the primary live
source: NSE's public option-chain API aggressively blocks/CAPTCHAs requests
from cloud-hosted IPs (Render, AWS, GCP, etc.) via Akamai bot protection,
even though the exact same code works from a home/office IP -- this is a
well-documented, common failure mode, not something specific to this app.
This fetcher instead reuses the same authenticated Kite Connect account
already powering the live equity tick stream (kite_provider.py) via the
batched REST /quote endpoint (services/kite_rest.fetch_quote), and the
static option-instrument metadata already loaded from
config/nifty_sensex_options.json (tradingsymbol/instrument_token/underlying/
expiry/strike/type) -- the same file kite_provider.py subscribes from.

Kite's /quote gives real last price, volume, OI, and market depth for every
instrument in one batched call (no dependency on whether a WS tick has
happened to arrive for a given strike yet), but does not include IV or
greeks -- only NSE's website computes and exposes those. Both are computed
here for real via greeks.implied_volatility's bisection inversion of
Black-Scholes from the live LTP, never fabricated.

Only NIFTY and SENSEX are covered (the two underlyings present in
config/nifty_sensex_options.json); BANKNIFTY and anything else falls back
to fetcher_v2's NSE-scrape path, and last-trading-day cache still applies
when the market is closed (Kite ticks/quotes aren't live then either).
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

from .greeks import black_scholes_greeks, implied_volatility, days_to_expiry
from ..services.kite_rest import fetch_quote, get_kite_client
from ..config import settings

logger = logging.getLogger(__name__)

_OPTIONS_FILE = Path(__file__).resolve().parents[3] / "config" / "nifty_sensex_options.json"
_universe_cache: Optional[Dict[str, Any]] = None

# Kite's documented quote symbols for these indices.
INDEX_QUOTE_SYMBOL = {"NIFTY": "NSE:NIFTY 50", "SENSEX": "BSE:SENSEX"}

RISK_FREE_RATE = 0.06

# First-observed-today OI per contract, used as an intraday baseline for
# oiChange since Kite's /quote doesn't give a previous-day-close OI figure
# the way NSE's website does. Keyed by "YYYY-MM-DD:tradingsymbol" so a new
# trading day naturally gets a fresh baseline without needing an explicit
# reset hook wired in from elsewhere.
_oi_baseline: Dict[str, int] = {}


def _load_option_universe() -> Dict[str, Any]:
    """Cache successful loads only -- a transient failure (e.g. filesystem not
    ready yet at cold start) must not permanently wedge this at {} for the rest
    of the process's life; only cache once we actually have real contracts."""
    global _universe_cache
    if _universe_cache:
        return _universe_cache
    try:
        _universe_cache = json.loads(_OPTIONS_FILE.read_text())
    except Exception as e:
        logger.warning(f"failed to load options universe from {_OPTIONS_FILE}: {e}")
        return {}
    return _universe_cache


def _get_kite():
    return get_kite_client(settings.kite_api_key, settings.kite_access_token)


async def fetch_chain_from_kite(symbol: str, expiry: Optional[str]) -> Optional[Dict[str, Any]]:
    symbol = symbol.upper()
    index_symbol = INDEX_QUOTE_SYMBOL.get(symbol)
    if not index_symbol:
        logger.info(f"Kite chain skip {symbol}: not in the static NIFTY/SENSEX universe, falling back to NSE scrape")
        return None  # BANKNIFTY etc -- not in the static universe, fall back to NSE scrape

    kite = _get_kite()
    if not kite:
        logger.warning(f"Kite chain skip {symbol}: no Kite client (missing/invalid KITE_API_KEY or KITE_ACCESS_TOKEN)")
        return None  # no live Kite credentials configured

    universe = _load_option_universe()
    contracts = universe.get(symbol)
    if not contracts:
        logger.warning(f"Kite chain skip {symbol}: config/nifty_sensex_options.json has no contracts for this symbol "
                        f"(loaded keys: {list(universe.keys())})")
        return None

    expiries = sorted({c["expiry"] for c in contracts})
    if not expiries:
        logger.warning(f"Kite chain skip {symbol}: contracts loaded but none have an expiry field")
        return None
    target_expiry = expiry if expiry in expiries else expiries[0]
    strikes_for_expiry = [c for c in contracts if c["expiry"] == target_expiry]
    if not strikes_for_expiry:
        logger.warning(f"Kite chain skip {symbol} {target_expiry}: no contracts match this expiry (available: {expiries})")
        return None

    instrument_keys = [f"{c['exchange']}:{c['tradingsymbol']}" for c in strikes_for_expiry]
    try:
        quotes = await fetch_quote(kite, instrument_keys + [index_symbol])
    except Exception as e:
        logger.warning(f"Kite chain {symbol} {target_expiry}: fetch_quote raised {type(e).__name__}: {e}", exc_info=True)
        return None
    if not quotes:
        logger.warning(f"Kite chain {symbol} {target_expiry}: fetch_quote returned empty "
                        f"(requested {len(instrument_keys)+1} instruments) -- check Kite API permissions/rate limit")
        return None
    spot_quote = quotes.get(index_symbol)
    spot = spot_quote.get("last_price") if spot_quote else None
    if not spot:
        logger.warning(f"Kite chain {symbol} {target_expiry}: no last_price for index quote '{index_symbol}' "
                        f"(got keys: {list(quotes.keys())[:5]}...)")
        return None
    logger.info(f"Kite chain {symbol} {target_expiry}: spot={spot}, {len(quotes)-1}/{len(instrument_keys)} option quotes returned")

    T = days_to_expiry(target_expiry)
    today_str = date.today().isoformat()
    by_strike: Dict[float, Dict[str, Any]] = {}

    for c in strikes_for_expiry:
        key = f"{c['exchange']}:{c['tradingsymbol']}"
        q = quotes.get(key)
        if not q:
            continue
        ltp = q.get("last_price") or 0
        oi = q.get("oi") or 0
        volume = q.get("volume") or 0
        depth = q.get("depth") or {}
        buy_side = depth.get("buy") or []
        sell_side = depth.get("sell") or []
        bid = buy_side[0]["price"] if buy_side and buy_side[0].get("price") else None
        ask = sell_side[0]["price"] if sell_side and sell_side[0].get("price") else None

        baseline_key = f"{today_str}:{c['tradingsymbol']}"
        if baseline_key not in _oi_baseline:
            _oi_baseline[baseline_key] = oi
        oi_change = oi - _oi_baseline[baseline_key]

        iv = implied_volatility(ltp, spot, c["strike"], T, RISK_FREE_RATE, c["type"]) if ltp else None
        g = black_scholes_greeks(spot, c["strike"], T, iv if iv is not None else 0.18, RISK_FREE_RATE, c["type"])

        entry = by_strike.setdefault(c["strike"], {"strike": c["strike"]})
        entry[c["type"]] = {
            "ltp": round(ltp, 2),
            "bid": round(bid, 2) if bid else round(ltp * 0.99, 2),
            "ask": round(ask, 2) if ask else round(ltp * 1.01, 2),
            "volume": volume,
            "oi": oi,
            "oiChange": oi_change,
            "iv": round(iv * 100, 2) if iv is not None else None,
            "delta": g["delta"], "gamma": g["gamma"], "theta": g["theta"], "vega": g["vega"], "rho": g["rho"],
            "premium": round(ltp, 2),
        }

    chain = [v for v in by_strike.values() if "CE" in v and "PE" in v]
    if not chain:
        logger.warning(f"Kite chain {symbol} {target_expiry}: quotes came back but no strike had both CE and PE "
                        f"-- likely stale/expired instrument tokens in config/nifty_sensex_options.json")
        return None
    chain.sort(key=lambda x: x["strike"])
    atm = min(chain, key=lambda x: abs(x["strike"] - spot))["strike"]
    for c in chain:
        c["isATM"] = c["strike"] == atm
        c["isITM_CE"] = spot > c["strike"]
        c["isITM_PE"] = spot < c["strike"]
        # IV fell back to a 0.18 placeholder inside black_scholes_greeks only for the
        # *greeks* calc when the market price couldn't be inverted (stale/bad quote);
        # the displayed iv field itself stays honestly null in that case (see above).

    from .fetcher import _analytics
    try:
        analytics = _analytics(chain, float(spot), atm)
    except Exception:
        analytics = {}

    return {
        "symbol": symbol,
        "spot": round(float(spot), 2),
        "expiry": target_expiry,
        "expiries": expiries,
        "generatedAt": datetime.now(tz=IST).isoformat(),
        "source": "kite_live",
        "atmStrike": atm,
        "chain": chain,
        "analytics": analytics,
        "isLastTradingDay": False,
    }
