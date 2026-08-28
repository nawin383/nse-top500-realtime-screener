import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from backend.app.analytics import etf_screener as etf_mod


def _day(o, h, l, c):
    return [datetime(2026, 8, 1), o, h, l, c, 0]


@pytest.fixture(autouse=True)
def clear_cache():
    etf_mod._historical_cache.update({"date": None, "data": {}})
    yield
    etf_mod._historical_cache.update({"date": None, "data": {}})


def _quotes():
    q = {}
    for i, symbol in enumerate(etf_mod.ETF_UNIVERSE):
        q[f"NSE:{symbol}"] = {
            "instrument_token": 1000 + i,
            "last_price": 100.0,
            "volume": 50000,
            "ohlc": {"open": 98.0, "high": 101.0, "low": 97.0, "close": 95.0},
        }
    return q


@pytest.mark.asyncio
async def test_no_credentials_returns_unavailable():
    with patch.object(etf_mod, "get_kite_client", return_value=None):
        result = await etf_mod.screener()
    assert result["available"] is False


@pytest.mark.asyncio
async def test_no_quotes_returns_unavailable():
    with patch.object(etf_mod, "get_kite_client", return_value=MagicMock()), \
         patch.object(etf_mod, "fetch_quote", AsyncMock(return_value={})):
        result = await etf_mod.screener()
    assert result["available"] is False


@pytest.mark.asyncio
async def test_screener_computes_change_pct_and_breakout():
    quotes = _quotes()
    # first ETF's historical prev-day-high is below today's high -> breakout
    history_candles = [_day(90, 96, 89, 94), _day(91, 96, 90, 95)]
    with patch.object(etf_mod, "get_kite_client", return_value=MagicMock()), \
         patch.object(etf_mod, "fetch_quote", AsyncMock(return_value=quotes)), \
         patch.object(etf_mod, "fetch_historical", AsyncMock(return_value=history_candles)):
        result = await etf_mod.screener()

    assert result["available"] is True
    assert len(result["data"]) == len(etf_mod.ETF_UNIVERSE)
    row = result["data"][0]
    # ltp=100, prev close=95 -> +5.26%
    assert row["changePct"] == pytest.approx((100.0 - 95.0) / 95.0 * 100, abs=0.01)
    # day high 101 > prev-day-high (candles[-2].high=96) and weekly high 96 -> both breakout signals
    assert "PDH" in row["signals"]
    assert "WHB" in row["signals"]
    assert result["summary"]["totalEtfs"] == len(etf_mod.ETF_UNIVERSE)
    assert result["summary"]["gainers"] == len(etf_mod.ETF_UNIVERSE)


@pytest.mark.asyncio
async def test_missing_historical_data_still_returns_rows_without_breakout():
    quotes = _quotes()
    with patch.object(etf_mod, "get_kite_client", return_value=MagicMock()), \
         patch.object(etf_mod, "fetch_quote", AsyncMock(return_value=quotes)), \
         patch.object(etf_mod, "fetch_historical", AsyncMock(return_value=[])):
        result = await etf_mod.screener()
    assert result["available"] is True
    for row in result["data"]:
        assert row["signals"] == []
        assert row["prevDayHigh"] is None
