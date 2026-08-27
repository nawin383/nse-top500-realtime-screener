"""Automated daily Kite token refresh for unattended live mode.
Reuses pattern from socket/auto_trader/src/auth.py (TOTP → request_token → access_token)
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

logger = logging.getLogger(__name__)

async def sleep_until_next_8am_ist():
    now = datetime.now(tz=IST)
    target = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    secs = (target - now).total_seconds()
    logger.info(f"Token refresher sleeping {secs/3600:.2f}h until {target.isoformat()}")
    await asyncio.sleep(secs)

def _has_creds(settings) -> bool:
    return bool(settings.kite_api_key and settings.kite_api_secret and getattr(settings, "kite_user_id", "") and getattr(settings, "kite_password", "") and getattr(settings, "kite_totp_secret", ""))

def try_refresh_token(settings, cache_path: Path) -> str | None:
    try:
        # import here so mock mode doesn't require kiteconnect/pyotp
        from ..utils.kite_auth import get_access_token
        token = get_access_token(
            api_key=settings.kite_api_key,
            api_secret=settings.kite_api_secret,
            user_id=settings.kite_user_id,
            password=settings.kite_password,
            totp_secret=settings.kite_totp_secret,
            cache_path=cache_path,
        )
        return token
    except Exception as e:
        logger.error(f"Token refresh failed: {e}", exc_info=True)
        return None

async def token_refresher_loop(settings, data_engine, cache_path: Path):
    """Run forever: at 08:00 IST try to refresh, update DataEngine's provider, optionally update Render env."""
    # Check if creds available
    if not _has_creds(settings):
        logger.info("Token refresher disabled — missing KITE_USER_ID/PASSWORD/TOTP_SECRET/API_SECRET (manual token mode)")
        return
    logger.info("Token refresher enabled — will refresh daily at 08:00 IST")
    while True:
        await sleep_until_next_8am_ist()
        logger.info("Attempting daily Kite token refresh...")
        token = await asyncio.to_thread(try_refresh_token, settings, cache_path)
        if token:
            logger.info(f"Got fresh token {token[:6]}..., updating provider")
            # update settings object (so new provider uses new token)
            settings.kite_access_token = token
            # try to hot-restart KiteProvider if currently live
            try:
                if data_engine and data_engine.provider and data_engine.provider.name == "kite_live":
                    await data_engine.provider.stop()
                    # update provider's token
                    data_engine.provider.access_token = token
                    # restart provider with same on_ticks
                    await data_engine.provider.start(data_engine.on_ticks)
                    logger.info("KiteProvider restarted with fresh token")
                else:
                    # if currently mock due to earlier auth failure, switch to live
                    # DataEngine will be restarted externally? For now just log, next restart will pick live
                    logger.info("Currently not in kite_live mode — fresh token will be used on next restart/market open")
            except Exception as e:
                logger.error(f"Failed to restart provider with new token: {e}", exc_info=True)

            # Optionally update Render env via API if RENDER_API_KEY and RENDER_SERVICE_ID set
            render_key = getattr(settings, "render_api_key", "") or __import__("os").getenv("RENDER_API_KEY", "")
            service_id = getattr(settings, "render_service_id", "") or __import__("os").getenv("RENDER_SERVICE_ID", "")
            if render_key and service_id:
                try:
                    import httpx
                    # Render API: update env vars
                    # This keeps token persistent across deploys
                    # Docs: https://api.render.com/docs/
                    logger.info("Updating Render env var KITE_ACCESS_TOKEN via API...")
                    # fetch current env, then patch
                    # Simplified: use Render API to update service env var
                    # We do PATCH /v1/services/{serviceId}/env-vars
                    # For now just log — implement if needed
                    logger.warning("Render API auto-update not yet implemented — token updated in-memory only, will need manual Render env update for persistence across restarts")
                except Exception as e:
                    logger.error(f"Render API update failed: {e}")
        else:
            logger.error("Token refresh produced no token — will retry tomorrow 08:00")
        # sleep a bit to avoid tight loop if we woke early
        await asyncio.sleep(60)
