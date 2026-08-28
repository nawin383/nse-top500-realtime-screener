import pytest
from backend.app.intraday_strategies import (
    orb15, vwap_reversion, supertrend_flip, gap_classifier, StrategyTracker, StrategySignal,
)
from backend.app.models import StockState


def make_state(symbol="TEST", ltp=100.0, **kw):
    s = StockState(symbol=symbol, token=1, ltp=ltp)
    for k, v in kw.items():
        if k.startswith("mom_"):
            setattr(s.momentum, k[4:], v)
        elif k.startswith("ind_"):
            setattr(s.indicators, k[4:], v)
        else:
            setattr(s, k, v)
    return s


# --- orb15 ---

def test_orb15_no_range_returns_none():
    assert orb15(make_state()) is None

def test_orb15_inside_range_is_watching():
    s = make_state(ltp=100.0, mom_or15_high=105.0, mom_or15_low=95.0)
    sig = orb15(s)
    assert sig.status == "WATCHING" and sig.direction is None

def test_orb15_break_gated_triggers():
    s = make_state(ltp=106.0, mom_or15_high=105.0, mom_or15_low=95.0, rel_volume=2.0, ind_atr=1.0)
    sig = orb15(s)
    assert sig.status == "TRIGGERED"
    assert sig.direction == "long"
    assert sig.entry == 106.0 and sig.stop < sig.entry and sig.target1 > sig.entry

def test_orb15_break_ungated_is_weak():
    s = make_state(ltp=106.0, mom_or15_high=105.0, mom_or15_low=95.0, rel_volume=0.5)
    sig = orb15(s)
    assert sig.status == "WEAK"
    assert sig.entry is None


# --- vwap_reversion ---

def test_vwap_reversion_trending_not_applicable():
    s = make_state(ltp=110.0, ind_adx=30.0, ind_vwap=100.0, ind_vwap_upper2=108.0, ind_vwap_lower2=92.0)
    sig = vwap_reversion(s)
    assert sig.status == "NOT_APPLICABLE"

def test_vwap_reversion_inside_bands_watching():
    s = make_state(ltp=101.0, ind_adx=15.0, ind_vwap=100.0, ind_vwap_upper2=108.0, ind_vwap_lower2=92.0)
    sig = vwap_reversion(s)
    assert sig.status == "WATCHING" and sig.direction is None

def test_vwap_reversion_above_upper_band_fades_short():
    s = make_state(ltp=110.0, ind_adx=15.0, ind_vwap=100.0, ind_vwap_upper2=108.0, ind_vwap_lower2=92.0)
    sig = vwap_reversion(s)
    assert sig.status == "TRIGGERED"
    assert sig.direction == "short"
    assert sig.target1 == 100.0  # fades back to VWAP
    assert sig.stop > sig.entry  # stop above entry for a short


# --- supertrend_flip ---

def test_supertrend_flip_hold_returns_none():
    s = make_state(ind_supertrend_signal="HOLD")
    assert supertrend_flip(s) is None

def test_supertrend_flip_buy_triggers_long():
    s = make_state(ltp=100.0, ind_supertrend_signal="BUY", ind_atr=2.0)
    sig = supertrend_flip(s)
    assert sig.status == "TRIGGERED" and sig.direction == "long"
    assert sig.stop < sig.entry


# --- gap_classifier ---

def test_gap_classifier_no_gap_returns_none():
    s = make_state(gap_pct=0.05, open=100.0, previous_close=100.0)
    assert gap_classifier(s) is None

def test_gap_classifier_gap_and_go_long():
    s = make_state(ltp=103.0, open=102.0, previous_close=100.0, gap_pct=2.0, rel_volume=2.0, ind_atr=1.0)
    sig = gap_classifier(s)
    assert sig.status == "TRIGGERED"
    assert sig.direction == "long"
    assert "Gap And Go" in sig.reason

def test_gap_classifier_gap_fade_short():
    # gapped up to 102 open, but has now fallen all the way back below prior close 100
    s = make_state(ltp=99.0, open=102.0, previous_close=100.0, gap_pct=2.0, rel_volume=2.0, ind_atr=1.0)
    sig = gap_classifier(s)
    assert sig.status == "TRIGGERED"
    assert sig.direction == "short"
    assert "Gap Fade" in sig.reason


# --- StrategyTracker ---

def test_pullback_first_touch_then_suppressed():
    tracker = StrategyTracker()
    s = make_state(ltp=100.0, ind_vwap=100.01, mom_ret_15m=1.0)  # within 0.15% of vwap, strong move
    sig = tracker.vwap_pullback(s)
    assert sig.status == "TRIGGERED"
    # second call for the same symbol: already seen today, no more signals
    assert tracker.vwap_pullback(s) is None

def test_pullback_watching_until_near_vwap():
    tracker = StrategyTracker()
    s = make_state(ltp=110.0, ind_vwap=100.0, mom_ret_15m=1.0)  # far from vwap
    sig = tracker.vwap_pullback(s)
    assert sig.status == "WATCHING"

def test_hit_rate_empty_is_provisional():
    tracker = StrategyTracker()
    hr = tracker.hit_rate("orb15")
    assert hr["sample_size"] == 0 and hr["provisional"] is True

def test_register_and_update_tracks_win():
    tracker = StrategyTracker()
    sig = StrategySignal("orb15", "AAA", "long", "TRIGGERED", "test", entry=100.0, stop=98.0, target1=103.0)
    states = {"AAA": make_state(symbol="AAA", ltp=100.0)}
    tracker.register_and_update([sig], states)
    # price rallies to hit target
    states["AAA"].ltp = 103.5
    tracker.register_and_update([], states)
    hr = tracker.hit_rate("orb15")
    assert hr["sample_size"] == 1 and hr["win_rate_pct"] == 100.0

def test_register_and_update_tracks_loss():
    tracker = StrategyTracker()
    sig = StrategySignal("orb15", "BBB", "long", "TRIGGERED", "test", entry=100.0, stop=98.0, target1=103.0)
    states = {"BBB": make_state(symbol="BBB", ltp=100.0)}
    tracker.register_and_update([sig], states)
    states["BBB"].ltp = 97.5  # stopped out
    tracker.register_and_update([], states)
    hr = tracker.hit_rate("orb15")
    assert hr["sample_size"] == 1 and hr["win_rate_pct"] == 0.0
