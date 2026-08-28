"""India VIX first-10-minutes volatility analysis.

Ported from a standalone local script (research/legacy_scripts/
india_vix_first10min_analyzer.py) that fetched 1-minute India VIX candles via
a hand-rolled aiohttp session against api.kite.trade and wrote the result to
an Excel file. This module keeps the actual analysis (opening-vs-9:25 move,
volatility classification, day-of-week breakdown) but runs it through the
app's existing Kite REST client and returns JSON instead of a spreadsheet.

Real data only: every number here comes from Kite's own historical minute
candles for the India VIX instrument (token 264969). A day with no candles
(holiday, feed gap) is simply skipped rather than filled in with a guess.
"""
from __future__ import annotations

import asyncio
import logging
import statistics
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..config import settings
from ..services.kite_rest import fetch_historical, get_kite_client

logger = logging.getLogger(__name__)

VIX_INSTRUMENT_TOKEN = 264969
FIRST_10_MINUTES = {"09:15", "09:16", "09:17", "09:18", "09:19", "09:20", "09:21", "09:22", "09:23", "09:24", "09:25"}

_cache: Dict[str, Any] = {"date": None, "days": None, "result": None}


def _last_trading_days(n: int) -> List[datetime]:
    days: List[datetime] = []
    cur = datetime.now() - timedelta(days=1)
    while len(days) < n:
        if cur.weekday() < 5:
            days.append(cur)
        cur -= timedelta(days=1)
    days.reverse()
    return days


def _classify(pct_change: float) -> str:
    a = abs(pct_change)
    if a >= 5:
        return "EXTREME"
    if a >= 3:
        return "HIGH"
    if a >= 1.5:
        return "MODERATE"
    if a >= 0.5:
        return "LOW"
    return "MINIMAL"


async def _fetch_day(kite, day: datetime) -> Optional[Dict[str, Any]]:
    date_str = day.strftime("%Y-%m-%d")
    from_dt = datetime.strptime(f"{date_str} 09:15:00", "%Y-%m-%d %H:%M:%S")
    to_dt = datetime.strptime(f"{date_str} 09:30:00", "%Y-%m-%d %H:%M:%S")
    candles = await fetch_historical(kite, VIX_INSTRUMENT_TOKEN, from_dt, to_dt, interval="minute")
    if not candles:
        return None
    first_10 = []
    for c in candles:
        ts = c[0]
        t = ts.strftime("%H:%M") if hasattr(ts, "strftime") else str(ts)[11:16]
        if t in FIRST_10_MINUTES:
            first_10.append({"time": t, "open": c[1], "high": c[2], "low": c[3], "close": c[4]})
    if not first_10:
        return None
    first_10.sort(key=lambda x: x["time"])
    opening = first_10[0]["open"]
    closing = first_10[-1]["close"]
    highs = [c["high"] for c in first_10]
    lows = [c["low"] for c in first_10]
    max_v, min_v = max(highs), min(lows)
    abs_change = closing - opening
    pct_change = (abs_change / opening) * 100 if opening else 0
    range_pct = ((max_v - min_v) / opening) * 100 if opening else 0
    return {
        "date": date_str,
        "dayOfWeek": day.strftime("%A"),
        "opening": round(opening, 2),
        "tenMinClose": round(closing, 2),
        "max": round(max_v, 2),
        "min": round(min_v, 2),
        "absChange": round(abs_change, 2),
        "pctChange": round(pct_change, 2),
        "rangePct": round(range_pct, 2),
        "volatilityClass": _classify(pct_change),
        "direction": "UP" if abs_change > 0 else "DOWN" if abs_change < 0 else "FLAT",
    }


async def analyze(days: int = 60) -> Dict[str, Any]:
    """Analyze the first-10-minutes India VIX move over the last `days` trading
    days. Cached for the rest of the calendar day it's first computed on --
    completed trading days never change, so there's no reason to re-fetch
    dozens of historical-candle calls on every page load."""
    today_key = datetime.now().strftime("%Y-%m-%d")
    if _cache["date"] == today_key and _cache["days"] == days and _cache["result"] is not None:
        return _cache["result"]

    kite = get_kite_client(settings.kite_api_key, settings.kite_access_token)
    if not kite:
        return {"available": False, "reason": "Kite credentials not configured", "days": []}

    trading_days = _last_trading_days(days)
    results: List[Dict[str, Any]] = []
    for day in trading_days:
        row = await _fetch_day(kite, day)
        if row:
            results.append(row)
        await asyncio.sleep(0.35)  # stay under Kite's ~3 req/s historical rate limit

    if not results:
        return {"available": False, "reason": "No candles returned for the requested window", "days": []}

    pct_changes = [r["pctChange"] for r in results]
    range_pcts = [r["rangePct"] for r in results]
    class_counts: Dict[str, int] = {}
    dir_counts: Dict[str, int] = {}
    dow_ranges: Dict[str, List[float]] = {}
    for r in results:
        class_counts[r["volatilityClass"]] = class_counts.get(r["volatilityClass"], 0) + 1
        dir_counts[r["direction"]] = dir_counts.get(r["direction"], 0) + 1
        dow_ranges.setdefault(r["dayOfWeek"], []).append(r["rangePct"])

    dow_avg = {k: round(statistics.mean(v), 2) for k, v in dow_ranges.items()}
    best_day = max(dow_avg, key=dow_avg.get) if dow_avg else None
    worst_day = min(dow_avg, key=dow_avg.get) if dow_avg else None

    high_vol_days = sum(1 for r in results if r["rangePct"] >= 3.0)
    extreme_move_days = sum(1 for r in results if abs(r["pctChange"]) >= 2.0)

    result = {
        "available": True,
        "totalDays": len(results),
        "avgOpeningVix": round(statistics.mean([r["opening"] for r in results]), 2),
        "avgPctChange": round(statistics.mean(pct_changes), 2),
        "avgRangePct": round(statistics.mean(range_pcts), 2),
        "maxRangePct": round(max(range_pcts), 2),
        "volatilityDistribution": class_counts,
        "directionDistribution": dir_counts,
        "dayOfWeekAvgRangePct": dow_avg,
        "bestDay": best_day,
        "worstDay": worst_day,
        "highVolatilityProbabilityPct": round(high_vol_days / len(results) * 100, 1),
        "extremeMoveProbabilityPct": round(extreme_move_days / len(results) * 100, 1),
        "days": sorted(results, key=lambda r: r["date"], reverse=True),
        "generatedAt": datetime.now().isoformat(),
    }
    _cache.update({"date": today_key, "days": days, "result": result})
    return result
