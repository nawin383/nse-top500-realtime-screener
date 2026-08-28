import math
import statistics
from datetime import date
from backend.app.options.seller_premium import (
    vix_mean_reversion_zscore, real_iv_rv_spread, premium_selling_favorability_score, expiry_day_pin_risk,
)


def test_vix_zscore_insufficient_history():
    r = vix_mean_reversion_zscore([12, 13, 14], current_vix=15.0)
    assert r["z_score"] is None
    assert "insufficient" in r["reason"]


def test_vix_zscore_exact_hand_computed():
    hist = [10.0, 12.0, 14.0, 16.0, 18.0] * 10  # mean=14, pstdev=sqrt(8) ~=2.828427
    r = vix_mean_reversion_zscore(hist, current_vix=20.0)
    expected_mean = statistics.mean(hist)
    expected_std = statistics.pstdev(hist)
    expected_z = (20.0 - expected_mean) / expected_std
    assert r["mean"] == round(expected_mean, 2)
    assert r["std"] == round(expected_std, 2)
    assert r["z_score"] == round(expected_z, 2)
    assert r["interpretation"] == "elevated (favors selling)"


def test_vix_zscore_near_mean_interpretation():
    hist = [15.0] * 40
    # zero variance -- z_score undefined, not "near mean" via division by zero
    r = vix_mean_reversion_zscore(hist, current_vix=15.0)
    assert r["z_score"] is None
    assert r["std"] == 0.0


def test_vix_zscore_depressed():
    hist = [10.0, 12.0, 14.0, 16.0, 18.0] * 10
    r = vix_mean_reversion_zscore(hist, current_vix=8.0)
    assert r["z_score"] < -1
    assert r["interpretation"] == "depressed (favors buying)"


def test_iv_rv_spread_insufficient_history():
    r = real_iv_rv_spread([100, 101, 102], current_iv_pct=20.0)
    assert r["realized_vol"] is None
    assert r["spread"] is None


def test_iv_rv_spread_rich_iv():
    # flat prices -> ~0 realized vol; IV far above realized -> rich
    closes = [100.0] * 40
    r = real_iv_rv_spread(closes, current_iv_pct=20.0, rv_window=20)
    assert r["realized_vol"] == 0.0
    assert r["spread"] == 20.0
    assert r["interpretation"] == "IV rich vs realized (favors selling)"


def test_iv_rv_spread_series_length_capped():
    import random
    rnd = random.Random(3)
    closes = [100.0]
    for _ in range(150):
        closes.append(closes[-1] * (1 + rnd.uniform(-0.01, 0.01)))
    r = real_iv_rv_spread(closes, current_iv_pct=18.0, rv_window=20)
    assert len(r["realized_vol_series"]) <= 90
    assert r["realized_vol"] is not None and r["realized_vol"] > 0


def test_favorability_score_none_when_nothing_available():
    r = premium_selling_favorability_score(None, None, None, None, None)
    assert r["score"] is None


def test_favorability_score_all_favorable_is_high():
    r = premium_selling_favorability_score(iv_rank=90, iv_rv_spread=8, adx=12, vix_zscore=1.8, term_structure_backwardation=True)
    assert r["score"] >= 80
    assert r["label"] == "favorable for premium selling"
    assert r["coverage_pct"] == 100.0


def test_favorability_score_all_unfavorable_is_low():
    r = premium_selling_favorability_score(iv_rank=5, iv_rv_spread=-8, adx=38, vix_zscore=-1.8, term_structure_backwardation=False)
    assert r["score"] <= 20
    assert r["label"] == "favorable for premium buying"


def test_favorability_score_partial_coverage_renormalizes():
    r = premium_selling_favorability_score(iv_rank=90, iv_rv_spread=None, adx=None, vix_zscore=None, term_structure_backwardation=None)
    assert r["score"] == 90.0  # the only available component (iv_rank=90/100) is the entire score
    assert r["coverage_pct"] == 30.0  # only the 30-weight iv_rank component was available


def test_pin_risk_missing_inputs():
    r = expiry_day_pin_risk([], spot=100.0, expiry="2026-09-25", max_pain=None)
    assert r["pin_risk_score"] is None


def test_pin_risk_high_when_spot_at_max_pain_and_oi_concentrated():
    chain = [
        {"strike": 99, "CE": {"oi": 5000}, "PE": {"oi": 5000}},
        {"strike": 100, "CE": {"oi": 20000}, "PE": {"oi": 20000}},
        {"strike": 101, "CE": {"oi": 5000}, "PE": {"oi": 5000}},
    ]
    r = expiry_day_pin_risk(chain, spot=100.0, expiry="2020-01-01", max_pain=100.0)
    assert r["distance_to_max_pain_pct"] == 0.0
    assert r["pin_risk_score"] > 60
    assert r["label"] == "high pin risk"
    assert r["is_expiry_day"] is False  # 2020-01-01 is not "today"


def test_pin_risk_low_when_far_from_max_pain():
    chain = [
        {"strike": 90, "CE": {"oi": 1000}, "PE": {"oi": 1000}},
        {"strike": 100, "CE": {"oi": 1000}, "PE": {"oi": 1000}},
        {"strike": 110, "CE": {"oi": 20000}, "PE": {"oi": 20000}},
    ]
    r = expiry_day_pin_risk(chain, spot=100.0, expiry="2020-01-01", max_pain=110.0)
    assert r["distance_to_max_pain_pct"] > 5
    assert r["label"] == "low pin risk"


def test_pin_risk_detects_actual_expiry_day():
    today_str = date.today().strftime("%Y-%m-%d")
    chain = [{"strike": 100, "CE": {"oi": 1000}, "PE": {"oi": 1000}}]
    r = expiry_day_pin_risk(chain, spot=100.0, expiry=today_str, max_pain=100.0)
    assert r["is_expiry_day"] is True
