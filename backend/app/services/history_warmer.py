"""Historical warmup: seeds real data at boot so the screener isn't blank/guessing.

Two jobs, both using Kite Connect's /instruments/historical/:token/:interval
(GET /historical/#request-parameters), paced at ~3 requests/sec per the account's
rate limit:

  1. Daily stats (interval=day, ~1 month back) -> real previous close + real
     average daily volume per symbol, replacing the placeholder values that used
     to live in config/nse_top500.json.
  2. Intraday warmup (interval=minute, from today's 09:15 IST to now) -> seeds
     CandleEngine so RSI/EMA/VWAP are populated immediately instead of needing
     to accumulate ticks from a cold start.

Only runs in live mode with valid Kite credentials; no-ops (and does not fabricate
anything) otherwise.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

from .kite_rest import get_kite_client, fetch_ohlc
from ..models import Candle

logger = logging.getLogger(__name__)

REQUEST_PACING_SEC = 0.34  # ~3 req/s, matches Kite's historical API rate limit


async def snapshot_last_close(market_state, universe: List[Dict[str, Any]], api_key: str, access_token: str):
    """Replace the flat CLOSED placeholder with a real last-trading-day OHLC snapshot
    via GET /quote/ohlc, batched 1000 instruments/request. Runs regardless of market
    hours — it's a no-op the moment a live tick starts flowing for a symbol."""
    kite = get_kite_client(api_key, access_token)
    if not kite:
        return
    by_instrument = {f"{e.get('exchange','NSE')}:{e['symbol']}": e["symbol"] for e in universe}
    instruments = list(by_instrument.keys())
    result = await fetch_ohlc(kite, instruments)
    applied = 0
    for key, sym in by_instrument.items():
        data = result.get(key)
        if not data:
            continue
        market_state.apply_last_close_snapshot(sym, data.get("ohlc", {}), prev_close=data.get("ohlc", {}).get("close"))
        applied += 1
    logger.info(f"History warmer: real last-close snapshot applied for {applied}/{len(universe)} symbols")


async def _historical(kite, token: int, from_dt: datetime, to_dt: datetime, interval: str) -> List[Dict[str, Any]]:
    try:
        return await asyncio.to_thread(kite.historical_data, token, from_dt, to_dt, interval)
    except Exception as e:
        logger.debug(f"historical_data failed token={token} interval={interval}: {e}")
        return []


async def warm_daily_stats(market_state, universe: List[Dict[str, Any]], api_key: str, access_token: str, days: int = 22):
    """Replace placeholder prev_close/avg_volume with real values from daily candles."""
    kite = get_kite_client(api_key, access_token)
    if not kite:
        logger.info("History warmer: no Kite credentials, skipping daily stats warmup")
        return
    now = datetime.now(tz=IST)
    frm = now - timedelta(days=days + 5)
    updated = 0
    for entry in universe:
        sym = entry["symbol"]
        token = entry["instrument_token"]
        candles = await _historical(kite, token, frm, now, "day")
        await asyncio.sleep(REQUEST_PACING_SEC)
        if not candles:
            continue
        candles = candles[-days:]
        volumes = [c.get("volume") for c in candles if c.get("volume")]
        if volumes:
            avg_vol = sum(volumes) / len(volumes)
            market_state.set_avg_volume(sym, avg_vol)
        prev_close = candles[-1].get("close")
        if prev_close:
            market_state._prev_close_map[sym] = prev_close
            state = market_state.states.get(sym)
            if state and state.freshness != "LIVE":
                state.previous_close = prev_close
        updated += 1
    logger.info(f"History warmer: real daily stats applied for {updated}/{len(universe)} symbols")


async def warm_intraday_candles(market_state, universe: List[Dict[str, Any]], api_key: str, access_token: str):
    """Seed CandleEngine 1-minute candles from today's market open to now, so
    indicators are ready before the first live tick arrives."""
    kite = get_kite_client(api_key, access_token)
    if not kite:
        return
    now = datetime.now(tz=IST)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    if now <= market_open:
        logger.info("History warmer: market hasn't opened yet, skipping intraday warmup")
        return
    seeded = 0
    for entry in universe:
        sym = entry["symbol"]
        token = entry["instrument_token"]
        candles = await _historical(kite, token, market_open, now, "minute")
        await asyncio.sleep(REQUEST_PACING_SEC)
        if not candles:
            continue
        for c in candles:
            ts = c.get("date")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except Exception:
                    continue
            candle = Candle(timestamp=ts, open=c["open"], high=c["high"], low=c["low"], close=c["close"], volume=c.get("volume", 0), interval=1)
            market_state.candle_engine._store[sym][1].append(candle)
        market_state._update_indicators(sym)
        seeded += 1
    logger.info(f"History warmer: intraday candles seeded for {seeded}/{len(universe)} symbols")


async def run_warmup(market_state, universe: List[Dict[str, Any]], settings):
    """Fire-and-forget entrypoint called once from the app lifespan on startup."""
    if settings.data_mode.lower() != "live" or not settings.kite_api_key or not settings.kite_access_token:
        logger.info("History warmer: not in live mode or missing credentials, skipping")
        return
    try:
        await snapshot_last_close(market_state, universe, settings.kite_api_key, settings.kite_access_token)
        await warm_daily_stats(market_state, universe, settings.kite_api_key, settings.kite_access_token)
        await warm_intraday_candles(market_state, universe, settings.kite_api_key, settings.kite_access_token)
    except Exception as e:
        logger.error(f"History warmer failed: {e}", exc_info=True)
