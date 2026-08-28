"""Live ETF screener.

Ported from a standalone local script (research/legacy_scripts/etf_tracker.py)
that ran its own KiteConnect session, wrote CSV files, and auto-opened an
Excel dashboard. The actual signal here -- live change%, prev-day/weekly-high
breakout detection, a simple composite score -- is real and worth keeping;
the local-file/Excel/rich-console machinery has no equivalent in a web app
and was dropped. This reuses the app's existing Kite REST client instead of
opening a second KiteConnect session.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..config import settings
from ..services.kite_rest import fetch_quote, fetch_historical, get_kite_client

logger = logging.getLogger(__name__)

# Curated liquid NSE ETFs across the categories the legacy script tracked.
# A real, fixed universe rather than "all ETFs" -- keeps this to one /quote
# batch call and a handful of historical calls per refresh.
ETF_UNIVERSE: Dict[str, str] = {
    "GOLDBEES": "GOLD", "HDFCGOLD": "GOLD", "SILVERBEES": "SILVER", "HDFCSILVER": "SILVER",
    "NIFTYBEES": "NIFTY50", "HDFCNIFTY": "NIFTY50", "JUNIORBEES": "NIFTY_NEXT50",
    "BANKBEES": "BANK", "PSUBNKBEES": "BANK",
    "ITBEES": "IT", "AUTOBEES": "AUTO", "PHARMABEES": "PHARMA", "INFRABEES": "INFRA",
    "LIQUIDBEES": "LIQUID", "MID150BEES": "MIDCAP", "MOM100": "MOMENTUM", "ALPHA": "ALPHA",
    "LOWVOL1": "LOWVOL", "QUAL30IETF": "QUALITY",
}

_historical_cache: Dict[str, Any] = {"date": None, "data": {}}


async def _refresh_historical(kite, quotes: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Prev-day/weekly high-low per ETF, cached for the rest of the calendar
    day. `quotes` (one already-fetched /quote batch) supplies instrument
    tokens so this doesn't need its own per-symbol lookup call."""
    today_key = datetime.now().strftime("%Y-%m-%d")
    if _historical_cache["date"] == today_key and _historical_cache["data"]:
        return _historical_cache["data"]

    out: Dict[str, Dict[str, float]] = {}
    to_dt = datetime.now()
    from_dt = to_dt - timedelta(days=10)
    for symbol in ETF_UNIVERSE:
        q = quotes.get(f"NSE:{symbol}")
        token = q.get("instrument_token") if q else None
        if not token:
            continue
        try:
            candles = await fetch_historical(kite, token, from_dt, to_dt, interval="day")
            if len(candles) >= 2:
                prev_day = candles[-2]
                week = candles[-5:] if len(candles) >= 5 else candles
                out[symbol] = {
                    "prevDayHigh": prev_day[2],
                    "prevDayLow": prev_day[3],
                    "weeklyHigh": max(c[2] for c in week),
                    "weeklyLow": min(c[3] for c in week),
                }
        except Exception as e:
            logger.warning(f"ETF historical fetch failed for {symbol}: {e}")

    if out:
        _historical_cache.update({"date": today_key, "data": out})
    return out or _historical_cache["data"]


def _score(change_pct: float, range_position_pct: float, breakout_strength: int) -> float:
    score = min(abs(change_pct) * 10, 40)
    score += min(abs(range_position_pct - 50) / 50 * 20, 20)
    score += breakout_strength
    return round(min(100, max(0, score)), 1)


async def screener() -> Dict[str, Any]:
    kite = get_kite_client(settings.kite_api_key, settings.kite_access_token)
    if not kite:
        return {"available": False, "reason": "Kite credentials not configured", "data": []}

    quotes = await fetch_quote(kite, [f"NSE:{s}" for s in ETF_UNIVERSE])
    if not quotes:
        return {"available": False, "reason": "No live quotes returned", "data": []}
    historical = await _refresh_historical(kite, quotes)

    rows: List[Dict[str, Any]] = []
    for symbol, category in ETF_UNIVERSE.items():
        q = quotes.get(f"NSE:{symbol}")
        if not q:
            continue
        ohlc = q.get("ohlc") or {}
        ltp = q.get("last_price")
        prev_close = ohlc.get("close")
        day_high, day_low = ohlc.get("high"), ohlc.get("low")
        if ltp is None or not prev_close:
            continue

        change_pct = round((ltp - prev_close) / prev_close * 100, 2)
        range_position_pct = None
        if day_high is not None and day_low is not None and day_high != day_low:
            range_position_pct = round((ltp - day_low) / (day_high - day_low) * 100, 1)

        hist = historical.get(symbol)
        signals: List[str] = []
        breakout_strength = 0
        if hist:
            if day_high is not None and hist.get("prevDayHigh") and day_high > hist["prevDayHigh"]:
                signals.append("PDH")
                breakout_strength += 20
            if day_high is not None and hist.get("weeklyHigh") and day_high > hist["weeklyHigh"]:
                signals.append("WHB")
                breakout_strength += 25

        rows.append({
            "symbol": symbol,
            "category": category,
            "ltp": ltp,
            "changePct": change_pct,
            "dayHigh": day_high,
            "dayLow": day_low,
            "volume": q.get("volume"),
            "rangePositionPct": range_position_pct,
            "prevDayHigh": hist.get("prevDayHigh") if hist else None,
            "weeklyHigh": hist.get("weeklyHigh") if hist else None,
            "breakoutStrength": breakout_strength,
            "signals": signals,
            "etfScore": _score(change_pct, range_position_pct or 50, breakout_strength),
        })

    rows.sort(key=lambda r: r["etfScore"], reverse=True)

    gainers = sum(1 for r in rows if r["changePct"] > 0)
    losers = sum(1 for r in rows if r["changePct"] < 0)
    avg_change = round(sum(r["changePct"] for r in rows) / len(rows), 2) if rows else 0
    sentiment = "BULLISH" if gainers > len(rows) * 0.6 else "BEARISH" if losers > len(rows) * 0.6 else "NEUTRAL"

    return {
        "available": True,
        "data": rows,
        "summary": {
            "totalEtfs": len(rows),
            "gainers": gainers,
            "losers": losers,
            "strongBreakouts": sum(1 for r in rows if r["breakoutStrength"] > 30),
            "avgChangePct": avg_change,
            "sentiment": sentiment,
            "topEtf": rows[0]["symbol"] if rows else None,
        },
        "generatedAt": datetime.now().isoformat(),
    }
