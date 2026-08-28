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

def _cred_presence(settings) -> dict[str, bool]:
    """Which of the 5 required env vars the process actually sees as non-empty right
    now — deliberately reports presence only, never the values, so this is safe to log."""
    return {
        "KITE_API_KEY": bool(settings.kite_api_key),
        "KITE_API_SECRET": bool(settings.kite_api_secret),
        "KITE_USER_ID": bool(getattr(settings, "kite_user_id", "")),
        "KITE_PASSWORD": bool(getattr(settings, "kite_password", "")),
        "KITE_TOTP_SECRET": bool(getattr(settings, "kite_totp_secret", "")),
    }

def _has_creds(settings) -> bool:
    return all(_cred_presence(settings).values())

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

async def _attempt_refresh(settings, data_engine, cache_path: Path) -> bool:
    """One refresh attempt: get a fresh token and hot-swap it into the live KiteProvider
    if one is running. Returns True on success."""
    token = await asyncio.to_thread(try_refresh_token, settings, cache_path)
    if not token:
        logger.error("Token refresh produced no token")
        return False
    logger.info(f"Got fresh token {token[:6]}..., updating provider")
    settings.kite_access_token = token
    try:
        if data_engine and data_engine.provider and data_engine.provider.name == "kite_live":
            await data_engine.provider.stop()
            data_engine.provider.access_token = token
            await data_engine.provider.start(data_engine.on_ticks)
            logger.info("KiteProvider restarted with fresh token")
        else:
            logger.info("Currently not in kite_live mode — fresh token will be used on next restart/market open")
    except Exception as e:
        logger.error(f"Failed to restart provider with new token: {e}", exc_info=True)

    # Optionally update Render env via API if RENDER_API_KEY and RENDER_SERVICE_ID set
    render_key = getattr(settings, "render_api_key", "") or __import__("os").getenv("RENDER_API_KEY", "")
    service_id = getattr(settings, "render_service_id", "") or __import__("os").getenv("RENDER_SERVICE_ID", "")
    if render_key and service_id:
        logger.warning("Render API auto-update not yet implemented — token updated in-memory only, will need manual Render env update for persistence across restarts")
    return True

async def token_refresher_loop(settings, data_engine, cache_path: Path):
    """Run forever: refresh once immediately at boot (so a stale KITE_ACCESS_TOKEN
    pasted in manually gets replaced right away instead of waiting for the next
    08:00 IST slot — important since a free-tier host can be asleep exactly then),
    then keep refreshing daily at 08:00 IST for as long as the process stays up."""
    presence = _cred_presence(settings)
    if not all(presence.values()):
        missing = [k for k, v in presence.items() if not v]
        logger.info(f"Token refresher disabled (manual token mode) — not set: {', '.join(missing)}")
        return
    logger.info("Token refresher enabled — refreshing now, then daily at 08:00 IST")
    logger.info("Attempting immediate Kite token refresh at boot...")
    await _attempt_refresh(settings, data_engine, cache_path)
    while True:
        await sleep_until_next_8am_ist()
        logger.info("Attempting daily Kite token refresh...")
        await _attempt_refresh(settings, data_engine, cache_path)
        # sleep a bit to avoid tight loop if we woke early
        await asyncio.sleep(60)
