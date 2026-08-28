from datetime import datetime, timezone
from backend.app.market_state import MarketState
from backend.app.models import MarketTick


def test_real_open_overwrites_closed_market_placeholder():
    """Regression test: _init_universe pre-fills state.open with the flat
    prev_close placeholder when the server boots with the market closed.
    The first live tick of the new day must still overwrite it with the
    real open (a different price implies a real gap) -- the old
    `if state.open is None` guard never fired again once that placeholder
    was set, silently pinning gap_pct at ~0 forever."""
    universe = [{"symbol": "GAPTEST", "instrument_token": 1, "prev_close": 100.0, "avg_volume": 10000}]
    ms = MarketState(universe)
    # simulate the closed-market boot placeholder explicitly, regardless of
    # this sandbox's wall-clock time relative to real IST market hours
    ms.states["GAPTEST"].open = 100.0
    ms.states["GAPTEST"].previous_close = 100.0
    ms.states["GAPTEST"].freshness = "CLOSED"

    tick = MarketTick(symbol="GAPTEST", token=1, timestamp=datetime.now(timezone.utc),
                       ltp=103.0, volume=5000, open=103.0, high=103.5, low=102.5, previousClose=100.0)
    ms.on_tick(tick)
    state = ms.states["GAPTEST"]
    assert state.open == 103.0
    assert state.gap_pct == 3.0


def test_second_tick_does_not_move_open():
    universe = [{"symbol": "GAPTEST2", "instrument_token": 2, "prev_close": 100.0, "avg_volume": 10000}]
    ms = MarketState(universe)
    t1 = MarketTick(symbol="GAPTEST2", token=2, timestamp=datetime(2026, 8, 28, 3, 45, tzinfo=timezone.utc),
                     ltp=103.0, volume=5000, open=103.0, previousClose=100.0)
    ms.on_tick(t1)
    t2 = MarketTick(symbol="GAPTEST2", token=2, timestamp=datetime(2026, 8, 28, 3, 46, tzinfo=timezone.utc),
                     ltp=105.0, volume=6000, open=999.0, previousClose=100.0)  # a bogus later "open" must be ignored
    ms.on_tick(t2)
    assert ms.states["GAPTEST2"].open == 103.0


def test_reset_day_allows_a_fresh_real_open():
    universe = [{"symbol": "GAPTEST3", "instrument_token": 3, "prev_close": 100.0, "avg_volume": 10000}]
    ms = MarketState(universe)
    t1 = MarketTick(symbol="GAPTEST3", token=3, timestamp=datetime(2026, 8, 28, 3, 45, tzinfo=timezone.utc),
                     ltp=103.0, volume=5000, open=103.0, previousClose=100.0)
    ms.on_tick(t1)
    ms.reset_day()
    t2 = MarketTick(symbol="GAPTEST3", token=3, timestamp=datetime(2026, 8, 29, 3, 45, tzinfo=timezone.utc),
                     ltp=98.0, volume=1000, open=98.0, previousClose=103.0)
    ms.on_tick(t2)
    assert ms.states["GAPTEST3"].open == 98.0
