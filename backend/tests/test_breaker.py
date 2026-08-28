import pytest
from backend.app.breaker import BreakerEngine, _score
from backend.app.models import StockState


def make_state(symbol="TEST", ltp=100.0, prev_high=100.0, prev_low=90.0,
                rvol=2.0, adx=25.0, vwap=95.0, atr=2.0):
    s = StockState(symbol=symbol, token=1, ltp=ltp, previous_day_high=prev_high, previous_day_low=prev_low,
                   rel_volume=rvol)
    s.indicators.adx = adx
    s.indicators.vwap = vwap
    s.indicators.atr = atr
    return s


def candle(close, high=None, low=None):
    return type("C", (), {"close": close, "high": high or close, "low": low or close})()


def test_no_level_returns_none():
    eng = BreakerEngine()
    s = StockState(symbol="X", token=1, ltp=100.0)
    assert eng.evaluate(s, []) is None


def test_price_inside_range_is_watching():
    eng = BreakerEngine()
    s = make_state(ltp=95.0)  # between prev_low=90 and prev_high=100
    sig = eng.evaluate(s, [])
    assert sig.status == "WATCHING"
    assert sig.direction is None


def test_break_without_gating_is_weak():
    # breaks above prev_high=100 but rvol below the 1.5x gate
    s = make_state(ltp=101.0, rvol=1.0, adx=25.0)
    eng = BreakerEngine()
    sig = eng.evaluate(s, [])
    assert sig.status == "WEAK_BREAK"
    assert sig.direction == "long"


def test_break_with_gating_but_no_retest_is_pending():
    s = make_state(ltp=101.0, rvol=2.0, adx=25.0)
    eng = BreakerEngine()
    sig = eng.evaluate(s, [])  # no candle history yet to confirm retest-hold
    assert sig.status == "PENDING_RETEST"
    assert sig.direction == "long"
    assert sig.entry is None  # not confirmed yet, no entry sizing


def test_break_confirmed_after_retest_hold():
    s = make_state(ltp=101.0, rvol=2.0, adx=25.0)
    eng = BreakerEngine()
    # two closed 1m candles both holding above the level=100
    candles = [candle(100.5), candle(101.2)]
    sig = eng.evaluate(s, candles)
    assert sig.status == "CONFIRMED"
    assert sig.direction == "long"
    assert sig.entry == 101.0
    assert sig.stop is not None and sig.stop < sig.entry
    assert sig.target1 > sig.entry


def test_false_breakout_then_fallback_marks_failed():
    eng = BreakerEngine()
    s = make_state(ltp=101.0, rvol=2.0, adx=25.0)
    eng.evaluate(s, [])  # PENDING_RETEST
    s2 = make_state(ltp=98.0, rvol=2.0, adx=25.0)  # falls back inside range
    sig2 = eng.evaluate(s2, [])
    assert sig2.status == "FAILED"
    assert sig2.direction == "long"  # retains which attempt failed for display


def test_failed_decays_to_watching_next_check():
    eng = BreakerEngine()
    s = make_state(ltp=101.0, rvol=2.0, adx=25.0)
    eng.evaluate(s, [])
    s2 = make_state(ltp=98.0, rvol=2.0, adx=25.0)
    eng.evaluate(s2, [])  # FAILED
    sig3 = eng.evaluate(s2, [])  # still inside range on next check
    assert sig3.status == "WATCHING"
    assert sig3.direction is None


def test_confirmed_breakout_that_reverses_becomes_failed():
    eng = BreakerEngine()
    s = make_state(ltp=101.0, rvol=2.0, adx=25.0)
    eng.evaluate(s, [candle(100.5), candle(101.2)])  # CONFIRMED
    s2 = make_state(ltp=95.0, rvol=2.0, adx=25.0)  # stopped out, back inside range
    sig2 = eng.evaluate(s2, [])
    assert sig2.status == "FAILED"
    assert sig2.direction == "long"


def test_short_breakdown_confirmed():
    s = make_state(ltp=89.0, rvol=2.0, adx=25.0, vwap=95.0)
    eng = BreakerEngine()
    candles = [candle(89.5), candle(88.8)]
    sig = eng.evaluate(s, candles)
    assert sig.status == "CONFIRMED"
    assert sig.direction == "short"
    assert sig.stop > sig.entry
    assert sig.target1 < sig.entry


def test_score_zero_when_no_direction():
    assert _score(2.0, 25.0, 5.0, None, None) == 0.0


def test_score_scales_with_rvol_and_adx():
    low = _score(rvol=1.5, adx=20.0, vwap_dist=0.5, oi_trend_score=None, direction="long")
    high = _score(rvol=3.0, adx=40.0, vwap_dist=0.5, oi_trend_score=None, direction="long")
    assert 0 <= low <= 100 and 0 <= high <= 100
    assert high > low


def test_score_penalizes_misaligned_vwap_distance():
    # long breakout but price is below VWAP (misaligned) -- vwap component should not count
    aligned = _score(rvol=2.0, adx=25.0, vwap_dist=2.0, oi_trend_score=None, direction="long")
    misaligned = _score(rvol=2.0, adx=25.0, vwap_dist=-2.0, oi_trend_score=None, direction="long")
    assert aligned > misaligned
