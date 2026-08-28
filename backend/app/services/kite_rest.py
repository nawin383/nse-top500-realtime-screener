"""Shared Kite Connect REST client for the fallback/warmup paths.

The live tick stream comes from KiteProvider's WebSocket (kite_provider.py). This
module wraps the same account's REST endpoints (quote/ohlc, quote/ltp, historical)
for the cases the docs call out as needing a plain HTTP fallback:
  - snapshotting real last-trading-day OHLC instead of guessing (market_state init)
  - polling LTP/OHLC when the WebSocket is down or the market is closed
  - warming up candles/averages from historical data at boot

Kite limits (per api.kite.trade/docs/connect/v3): /quote up to 500 instruments,
/quote/ohlc and /quote/ltp up to 1000 per request; historical calls are per
instrument and should be paced (~3 req/s) to stay under the account's rate limit.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_client = None
_client_key = None


def get_kite_client(api_key: str, access_token: str):
    """Return a process-wide KiteConnect client, rebuilding it only if the token changed
    (the daily token refresher rotates access_token without restarting the process)."""
    global _client, _client_key
    if not api_key or not access_token:
        return None
    key = (api_key, access_token)
    if _client is not None and _client_key == key:
        return _client
    try:
        from kiteconnect import KiteConnect
    except ImportError:
        logger.error("kiteconnect package not installed — REST fallback disabled")
        return None
    client = KiteConnect(api_key=api_key)
    client.set_access_token(access_token)
    _client = client
    _client_key = key
    return client


def _chunks(items: List[str], size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


async def fetch_ohlc(kite, instruments: List[str]) -> Dict[str, Any]:
    """Batched GET /quote/ohlc (<=1000 instruments/request). instruments are
    'EXCHANGE:TRADINGSYMBOL' strings. Returns {instrument: {last_price, ohlc:{...}}}."""
    if not kite or not instruments:
        return {}
    out: Dict[str, Any] = {}
    for batch in _chunks(instruments, 1000):
        try:
            res = await asyncio.to_thread(kite.ohlc, batch)
            out.update(res or {})
        except Exception as e:
            logger.warning(f"quote/ohlc batch failed ({len(batch)} instruments): {e}")
    return out


async def fetch_ltp(kite, instruments: List[str]) -> Dict[str, Any]:
    """Batched GET /quote/ltp (<=1000 instruments/request)."""
    if not kite or not instruments:
        return {}
    out: Dict[str, Any] = {}
    for batch in _chunks(instruments, 1000):
        try:
            res = await asyncio.to_thread(kite.ltp, batch)
            out.update(res or {})
        except Exception as e:
            logger.warning(f"quote/ltp batch failed ({len(batch)} instruments): {e}")
    return out


async def fetch_quote(kite, instruments: List[str]) -> Dict[str, Any]:
    """Batched GET /quote (<=500 instruments/request) — full depth/OI/volume snapshot."""
    if not kite or not instruments:
        return {}
    out: Dict[str, Any] = {}
    for batch in _chunks(instruments, 500):
        try:
            res = await asyncio.to_thread(kite.quote, batch)
            out.update(res or {})
        except Exception as e:
            logger.warning(f"quote batch failed ({len(batch)} instruments): {e}")
    return out


async def fetch_historical(kite, instrument_token: int, from_dt, to_dt, interval: str = "minute") -> List[Dict[str, Any]]:
    """GET /instruments/historical/:token/:interval for one instrument over one
    date range. Kite paces this per-instrument (no batching), so callers doing
    many days/instruments should space calls out themselves (~3 req/s)."""
    if not kite:
        return []
    try:
        candles = await asyncio.to_thread(
            kite.historical_data, instrument_token, from_dt, to_dt, interval
        )
        return candles or []
    except Exception as e:
        logger.warning(f"historical_data failed (token={instrument_token}, {from_dt}..{to_dt}): {e}")
        return []
