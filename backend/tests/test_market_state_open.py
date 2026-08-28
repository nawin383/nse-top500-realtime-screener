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


def test_oi_buildup_tracked_from_ticks_carrying_oi():
    """Equity spot ticks never carry OI (None forever, correctly). An F&O
    instrument's ticks do -- this exercises that path directly."""
    universe = [{"symbol": "NIFTY26SEPFUT", "instrument_token": 9, "prev_close": 100.0, "avg_volume": 10000}]
    ms = MarketState(universe)
    t1 = MarketTick(symbol="NIFTY26SEPFUT", token=9, timestamp=datetime(2026, 8, 28, 3, 45, tzinfo=timezone.utc),
                     ltp=100.0, volume=1000, open=100.0, previousClose=100.0, oi=100000)
    ms.on_tick(t1)
    assert ms.states["NIFTY26SEPFUT"].oi == 100000
    assert ms.states["NIFTY26SEPFUT"].oi_buildup is None  # no OI change yet on the first tick

    t2 = MarketTick(symbol="NIFTY26SEPFUT", token=9, timestamp=datetime(2026, 8, 28, 3, 50, tzinfo=timezone.utc),
                     ltp=103.0, volume=2000, open=100.0, previousClose=100.0, oi=120000)
    ms.on_tick(t2)
    state = ms.states["NIFTY26SEPFUT"]
    assert state.oi == 120000
    assert state.oi_change_pct == 20.0
    assert state.oi_buildup == "long_buildup"  # price up + OI up


def test_equity_ticks_never_carry_oi():
    universe = [{"symbol": "EQTEST", "instrument_token": 8, "prev_close": 100.0, "avg_volume": 10000}]
    ms = MarketState(universe)
    t1 = MarketTick(symbol="EQTEST", token=8, timestamp=datetime(2026, 8, 28, 3, 45, tzinfo=timezone.utc),
                     ltp=101.0, volume=1000, open=100.0, previousClose=100.0)
    ms.on_tick(t1)
    assert ms.states["EQTEST"].oi is None
    assert ms.states["EQTEST"].oi_buildup is None


def test_dynamic_option_state_creation_survives_first_tick():
    """Regression test: on_tick's auto-create branch for unrecognized symbols
    (NIFTY/BANKNIFTY/SENSEX option contracts arriving over the WS for the
    first time, before any state exists for them) referenced tick.previousClose
    -- MarketTick's actual Python attribute is previous_close (previousClose
    is only the alias used for JSON/kwarg population, not a valid attribute
    access in Pydantic v2 regardless of populate_by_name). Every single first
    tick for every option contract crashed here with AttributeError, was
    caught by data_engine's per-tick try/except and logged as 'tick
    processing error', and since the state was never created, the *next*
    tick for that same contract hit the exact same code path and crashed
    again -- a 100% failure rate for every option contract, forever. This
    stayed dormant and unnoticed until config/nifty_sensex_options.json's
    path bug was fixed and option ticks actually started arriving."""
    universe = [{"symbol": "RELIANCE", "instrument_token": 1, "prev_close": 100.0, "avg_volume": 10000}]
    ms = MarketState(universe)
    tick = MarketTick(symbol="NIFTY26SEP24500CE", token=12007682, timestamp=datetime.now(timezone.utc),
                       ltp=150.5, volume=1000, previousClose=140.0)
    ms.on_tick(tick)  # must not raise
    state = ms.states["NIFTY26SEP24500CE"]
    assert state.previous_close == 140.0
    assert state.ltp == 150.5
    assert state.sector == "Options"


def test_init_universe_live_branch_survives_missing_prev_close():
    """Regression test: _init_universe's live-market branch used to set
    ltp=prev_close with no None guard (unlike the closed-market branch's
    ltp=prev_close or 0), so constructing MarketState -- and therefore
    booting the whole app -- while the market happens to be live would
    crash entirely on any universe entry missing prev_close (e.g. a new
    listing, or a data-loading gap)."""
    universe = [{"symbol": "NEWLISTING", "instrument_token": 99}]  # no prev_close at all
    from unittest.mock import patch
    with patch("backend.app.market_hours.get_market_status", return_value=("open", True)):
        ms = MarketState(universe)  # must not raise
    assert ms.states["NEWLISTING"].ltp == 0


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
