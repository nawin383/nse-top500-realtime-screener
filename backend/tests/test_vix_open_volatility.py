import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from backend.app.analytics import vix_open_volatility as vix_mod


def _candle(t, o, h, l, c):
    return [datetime.strptime(f"2026-08-01 {t}:00", "%Y-%m-%d %H:%M:%S"), o, h, l, c, 0]


def _day_candles(open_v, close_v, high_v, low_v):
    # 11 one-minute candles from 09:15 to 09:25, matching FIRST_10_MINUTES
    times = ["09:15", "09:16", "09:17", "09:18", "09:19", "09:20", "09:21", "09:22", "09:23", "09:24", "09:25"]
    candles = []
    for i, t in enumerate(times):
        o = open_v if i == 0 else close_v
        c = close_v
        candles.append(_candle(t, o, high_v, low_v, c))
    return candles


@pytest.fixture(autouse=True)
def clear_cache():
    vix_mod._cache.update({"date": None, "days": None, "result": None})
    yield
    vix_mod._cache.update({"date": None, "days": None, "result": None})


@pytest.mark.asyncio
async def test_no_credentials_returns_unavailable():
    with patch.object(vix_mod, "get_kite_client", return_value=None):
        result = await vix_mod.analyze(days=10)
    assert result["available"] is False
    assert "credentials" in result["reason"].lower()


@pytest.mark.asyncio
async def test_no_candles_returns_unavailable():
    with patch.object(vix_mod, "get_kite_client", return_value=MagicMock()), \
         patch.object(vix_mod, "fetch_historical", AsyncMock(return_value=[])):
        result = await vix_mod.analyze(days=5)
    assert result["available"] is False
    assert result["days"] == []


@pytest.mark.asyncio
async def test_classifies_extreme_volatility_day():
    # opening 13.0 -> closing 14.0 is a +7.7% move -> EXTREME
    candles = _day_candles(open_v=13.0, close_v=14.0, high_v=14.2, low_v=12.9)
    with patch.object(vix_mod, "get_kite_client", return_value=MagicMock()), \
         patch.object(vix_mod, "fetch_historical", AsyncMock(return_value=candles)), \
         patch("asyncio.sleep", AsyncMock()):
        result = await vix_mod.analyze(days=3)
    assert result["available"] is True
    assert result["totalDays"] == 3
    assert result["volatilityDistribution"].get("EXTREME") == 3
    assert result["avgOpeningVix"] == 13.0
    assert result["highVolatilityProbabilityPct"] == 100.0


@pytest.mark.asyncio
async def test_result_is_cached_for_the_day():
    candles = _day_candles(open_v=13.0, close_v=13.05, high_v=13.1, low_v=12.95)
    fetch_mock = AsyncMock(return_value=candles)
    with patch.object(vix_mod, "get_kite_client", return_value=MagicMock()), \
         patch.object(vix_mod, "fetch_historical", fetch_mock), \
         patch("asyncio.sleep", AsyncMock()):
        first = await vix_mod.analyze(days=2)
        call_count_after_first = fetch_mock.call_count
        second = await vix_mod.analyze(days=2)
    assert first == second
    assert fetch_mock.call_count == call_count_after_first  # no new fetches on cache hit
