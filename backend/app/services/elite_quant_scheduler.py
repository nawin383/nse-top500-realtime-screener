"""Runs the elite-quant scan (backend/app/analytics/elite_quant.py) once a
day per market, in the background, so the API only ever serves a cache.

Mirrors token_refresher_loop's shape: a background asyncio task started from
main.py's lifespan, sleeping between runs rather than being triggered by
request traffic.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

RUN_INTERVAL_SECONDS = 24 * 3600


async def elite_quant_scheduler_loop(settings):
    if not settings.enable_elite_quant:
        logger.info("Elite quant scheduler not started — ENABLE_ELITE_QUANT is off")
        return
    try:
        import yfinance  # noqa: F401
    except ImportError:
        logger.info("Elite quant scheduler not started — yfinance not installed")
        return

    from ..analytics import elite_quant

    max_universe = {"IN": settings.elite_quant_max_universe_in, "US": settings.elite_quant_max_universe_us}

    while True:
        for market in elite_quant.MARKETS:
            if not elite_quant.is_stale(market):
                continue
            try:
                await asyncio.to_thread(elite_quant.refresh_universe_if_needed, market, max_universe[market])
                symbols = elite_quant.MARKETS[market].symbols
                logger.info(f"Elite quant scan starting for {market} ({len(symbols)} symbols)")
                result = await elite_quant.run_scan(market)
                logger.info(f"Elite quant scan complete for {market}: {result['analyzed']} analyzed, {result['failed']} failed")
            except Exception as e:
                logger.error(f"Elite quant scan failed for {market}: {e}", exc_info=True)
        await asyncio.sleep(RUN_INTERVAL_SECONDS)
