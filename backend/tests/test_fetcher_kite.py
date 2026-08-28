import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from backend.app.options import fetcher_kite
from backend.app.options.greeks import black_scholes_greeks, days_to_expiry


NIFTY_UNIVERSE = [
    {"tradingsymbol": "NIFTY26SEP24500CE", "instrument_token": 1, "underlying": "NIFTY",
     "expiry": "2026-09-30", "strike": 24500.0, "type": "CE", "exchange": "NFO", "segment": "NFO-OPT"},
    {"tradingsymbol": "NIFTY26SEP24500PE", "instrument_token": 2, "underlying": "NIFTY",
     "expiry": "2026-09-30", "strike": 24500.0, "type": "PE", "exchange": "NFO", "segment": "NFO-OPT"},
    {"tradingsymbol": "NIFTY26SEP24600CE", "instrument_token": 3, "underlying": "NIFTY",
     "expiry": "2026-09-30", "strike": 24600.0, "type": "CE", "exchange": "NFO", "segment": "NFO-OPT"},
    {"tradingsymbol": "NIFTY26SEP24600PE", "instrument_token": 4, "underlying": "NIFTY",
     "expiry": "2026-09-30", "strike": 24600.0, "type": "PE", "exchange": "NFO", "segment": "NFO-OPT"},
]


def _mock_quote_response(spot=24550.0):
    # must match fetcher_kite's own days_to_expiry("2026-09-30") computed from
    # "now" -- a mismatched T here would make the IV solver correctly recover
    # a different (but internally consistent) IV than this mock assumes.
    T = days_to_expiry("2026-09-30")
    ce1 = black_scholes_greeks(spot, 24500.0, T, 0.15, 0.06, "CE")["price"]
    pe1 = black_scholes_greeks(spot, 24500.0, T, 0.15, 0.06, "PE")["price"]
    ce2 = black_scholes_greeks(spot, 24600.0, T, 0.16, 0.06, "CE")["price"]
    pe2 = black_scholes_greeks(spot, 24600.0, T, 0.16, 0.06, "PE")["price"]
    return {
        "NSE:NIFTY 50": {"last_price": spot},
        "NFO:NIFTY26SEP24500CE": {"last_price": ce1, "oi": 100000, "volume": 5000,
                                   "depth": {"buy": [{"price": ce1 - 0.5}], "sell": [{"price": ce1 + 0.5}]}},
        "NFO:NIFTY26SEP24500PE": {"last_price": pe1, "oi": 90000, "volume": 4000,
                                   "depth": {"buy": [{"price": pe1 - 0.5}], "sell": [{"price": pe1 + 0.5}]}},
        "NFO:NIFTY26SEP24600CE": {"last_price": ce2, "oi": 80000, "volume": 3000,
                                   "depth": {"buy": [{"price": ce2 - 0.5}], "sell": [{"price": ce2 + 0.5}]}},
        "NFO:NIFTY26SEP24600PE": {"last_price": pe2, "oi": 70000, "volume": 2000,
                                   "depth": {"buy": [{"price": pe2 - 0.5}], "sell": [{"price": pe2 + 0.5}]}},
    }


@pytest.fixture(autouse=True)
def _reset_state():
    fetcher_kite._universe_cache = {"NIFTY": NIFTY_UNIVERSE, "SENSEX": [], "total": len(NIFTY_UNIVERSE)}
    fetcher_kite._oi_baseline.clear()
    yield
    fetcher_kite._universe_cache = None
    fetcher_kite._oi_baseline.clear()


@pytest.mark.asyncio
async def test_no_kite_client_returns_none():
    with patch.object(fetcher_kite, "_get_kite", return_value=None):
        result = await fetcher_kite.fetch_chain_from_kite("NIFTY", None)
    assert result is None


@pytest.mark.asyncio
async def test_banknifty_unsupported_returns_none():
    # BANKNIFTY isn't in config/nifty_sensex_options.json's static universe
    result = await fetcher_kite.fetch_chain_from_kite("BANKNIFTY", None)
    assert result is None


@pytest.mark.asyncio
async def test_assembles_real_chain_shape():
    with patch.object(fetcher_kite, "_get_kite", return_value=MagicMock()), \
         patch.object(fetcher_kite, "fetch_quote", new=AsyncMock(return_value=_mock_quote_response())):
        result = await fetcher_kite.fetch_chain_from_kite("NIFTY", "2026-09-30")

    assert result is not None
    assert result["source"] == "kite_live"
    assert result["symbol"] == "NIFTY"
    assert result["spot"] == 24550.0
    assert len(result["chain"]) == 2
    strikes = {c["strike"] for c in result["chain"]}
    assert strikes == {24500.0, 24600.0}
    atm = next(c for c in result["chain"] if c["isATM"])
    assert atm["strike"] == 24500.0  # closer to spot 24550 than 24600
    # IV should have been solved (real bisection inversion), not left null,
    # since these prices came from a real BS calculation at a real vol.
    assert atm["CE"]["iv"] is not None
    assert abs(atm["CE"]["iv"] - 15.0) < 0.5  # priced at 15% vol above
    assert atm["CE"]["oi"] == 100000
    assert atm["PE"]["oi"] == 90000


@pytest.mark.asyncio
async def test_oi_change_baseline_tracked_across_calls():
    quotes1 = _mock_quote_response()
    with patch.object(fetcher_kite, "_get_kite", return_value=MagicMock()), \
         patch.object(fetcher_kite, "fetch_quote", new=AsyncMock(return_value=quotes1)):
        result1 = await fetcher_kite.fetch_chain_from_kite("NIFTY", "2026-09-30")
    atm1 = next(c for c in result1["chain"] if c["isATM"])
    assert atm1["CE"]["oiChange"] == 0  # first call of the day: baseline == current

    quotes2 = _mock_quote_response()
    quotes2["NFO:NIFTY26SEP24500CE"]["oi"] = 130000  # OI built up since the first call
    with patch.object(fetcher_kite, "_get_kite", return_value=MagicMock()), \
         patch.object(fetcher_kite, "fetch_quote", new=AsyncMock(return_value=quotes2)):
        result2 = await fetcher_kite.fetch_chain_from_kite("NIFTY", "2026-09-30")
    atm2 = next(c for c in result2["chain"] if c["isATM"])
    assert atm2["CE"]["oiChange"] == 30000


@pytest.mark.asyncio
async def test_missing_spot_quote_returns_none():
    quotes = _mock_quote_response()
    del quotes["NSE:NIFTY 50"]
    with patch.object(fetcher_kite, "_get_kite", return_value=MagicMock()), \
         patch.object(fetcher_kite, "fetch_quote", new=AsyncMock(return_value=quotes)):
        result = await fetcher_kite.fetch_chain_from_kite("NIFTY", "2026-09-30")
    assert result is None


@pytest.mark.asyncio
async def test_empty_quotes_returns_none():
    with patch.object(fetcher_kite, "_get_kite", return_value=MagicMock()), \
         patch.object(fetcher_kite, "fetch_quote", new=AsyncMock(return_value={})):
        result = await fetcher_kite.fetch_chain_from_kite("NIFTY", "2026-09-30")
    assert result is None
