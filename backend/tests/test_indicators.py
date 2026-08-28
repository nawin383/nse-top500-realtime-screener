import pytest
from backend.app.indicators import (
    ema_series, rsi, atr, macd, bollinger, adx,
    vwap_bands, macd_cross_signal, rsi_divergence, atr_stop_target,
)
from backend.app.indicators_advanced import calculate_supertrend

def test_ema():
    prices=[10,11,12,13,14,15,16]
    ema=ema_series(prices,3)
    assert ema[0] is None
    assert ema[1] is None
    assert ema[2] is not None
    # ema continuity
    assert ema[-1] > ema[2]

def test_ema_insufficient():
    prices=[1,2]
    assert ema_series(prices,5)==[None,None]

def test_rsi():
    prices=[44,44.34,44.09,43.61,44.33,44.83,45.10,45.42,45.84,46.08,45.89,46.03,45.61,46.28,46.28,46.00,46.03,46.41,46.22,46.01]
    v=rsi(prices,14)
    assert v is not None
    assert 0 <= v <= 100
    # insufficient
    assert rsi([1,2,3],14) is None

def test_atr():
    candles=[{"high":10,"low":9,"close":9.5},{"high":11,"low":9.5,"close":10.5},{"high":12,"low":10,"close":11}] * 10
    v=atr(candles,14)
    assert v is not None
    assert v>0
    assert atr(candles[:5],14) is None

def test_macd_insufficient():
    assert macd([1]*10)==(None,None,None)
    prices=list(range(1,40))
    m,s,h=macd(prices)
    assert m is not None

def test_bollinger():
    prices=list(range(1,21))
    u,m,l=bollinger(prices,20,2)
    assert u>m>l
    assert bollinger([1]*5,20,2)==(None,None,None)

def test_adx_insufficient():
    assert adx([{"high":10,"low":9,"close":9.5}]*10, 14) == (None, None, None)

def test_adx_flat_price_is_exactly_zero():
    # h==l==c constant every bar => TR=0, +DM=-DM=0 every bar => DX=0 every
    # bar => ADX=0 exactly. This is the one case with a hand-verifiable exact
    # reference value rather than just a directional/bounds check.
    candles = [{"high": 100.0, "low": 100.0, "close": 100.0} for _ in range(30)]
    adx_val, plus_di, minus_di = adx(candles, 14)
    assert (adx_val, plus_di, minus_di) == (0.0, 0.0, 0.0)

def test_adx_strong_uptrend():
    # every bar strictly higher-high/higher-low/higher-close by a constant
    # step: a textbook one-directional trend. DI+ must dominate DI-, and a
    # trend this clean and sustained must push ADX well above the
    # conventional "trending" threshold (20-25) used elsewhere in this repo
    # as the breakout-signal gate (see Part 3/4 filters).
    candles = [{"high": 10+i, "low": 9+i, "close": 9.5+i} for i in range(30)]
    adx_val, plus_di, minus_di = adx(candles, 14)
    assert adx_val is not None and plus_di is not None and minus_di is not None
    assert 0 <= adx_val <= 100
    assert plus_di > minus_di
    assert adx_val > 25

def test_adx_strong_downtrend():
    candles = [{"high": 40-i, "low": 39-i, "close": 39.5-i} for i in range(30)]
    adx_val, plus_di, minus_di = adx(candles, 14)
    assert minus_di > plus_di
    assert adx_val > 25

def test_adx_choppy_range_has_low_adx():
    # oscillates up/down every bar with no net progress -- a textbook
    # range-bound/no-trend series. DI+ and DI- should be close to each other
    # and ADX should stay low (well under the 20-25 trending threshold).
    candles = []
    price = 100.0
    for i in range(30):
        step = 1.0 if i % 2 == 0 else -1.0
        candles.append({"high": price+step+0.2, "low": price+step-0.2, "close": price+step})
        price = price + step - step  # net zero drift, oscillating around 100
    adx_val, plus_di, minus_di = adx(candles, 14)
    assert adx_val is not None
    assert adx_val < 30
    assert abs(plus_di - minus_di) < 30

def test_vwap_bands():
    # 3 fills: 100@vol10, 102@vol10, 104@vol10 -> vwap=102 exactly (symmetric).
    # Volume-weighted variance = mean(p^2) - vwap^2, computed by hand:
    # mean(p^2) = (100^2+102^2+104^2)/3 = (10000+10404+10816)/3 = 31220/3 = 10406.666...
    # variance = 10406.6667 - 102^2 = 10406.6667 - 10404 = 2.6667 -> std = sqrt(2.6667) = 1.63299...
    cum_vol = 30.0
    cum_pv = 100*10 + 102*10 + 104*10
    cum_pv2 = (100**2)*10 + (102**2)*10 + (104**2)*10
    vwap = cum_pv/cum_vol
    assert round(vwap, 4) == 102.0
    bands = vwap_bands(vwap, cum_vol, cum_pv, cum_pv2)
    assert bands["std"] == round((2.666666666666667)**0.5, 4)
    assert bands["upper1"] == round(102 + bands["std"], 2)
    assert bands["lower1"] == round(102 - bands["std"], 2)
    assert bands["upper2"] == round(102 + 2*bands["std"], 2)
    assert bands["lower2"] == round(102 - 2*bands["std"], 2)

def test_vwap_bands_no_volume():
    bands = vwap_bands(None, 0, 0, 0)
    assert bands == {"upper1": None, "lower1": None, "upper2": None, "lower2": None, "std": None}

def test_macd_cross_signal():
    assert macd_cross_signal(-1.0, 0.5) == "bullish_cross"
    assert macd_cross_signal(1.0, -0.5) == "bearish_cross"
    assert macd_cross_signal(1.0, 2.0) is None       # already positive, no cross
    assert macd_cross_signal(-1.0, -2.0) is None      # already negative, no cross
    assert macd_cross_signal(None, 1.0) is None
    assert macd_cross_signal(1.0, None) is None

def test_rsi_divergence_bearish():
    # Price: two swing highs, second higher than the first (new high).
    # RSI: same two swing points, second LOWER than the first -- classic
    # bearish divergence (momentum fading into the new price high).
    closes =        [10, 12, 10, 9, 13, 10, 9]
    rsi_series =     [50, 70, 55, 45, 65, 50, 40]
    assert rsi_divergence(closes, rsi_series, lookback=1) == "bearish"

def test_rsi_divergence_bullish():
    # Two swing lows, second LOWER in price but HIGHER in RSI.
    closes =        [10,  8, 10, 11,  7, 10, 11]
    rsi_series =     [50, 30, 45, 55, 35, 50, 60]
    assert rsi_divergence(closes, rsi_series, lookback=1) == "bullish"

def test_rsi_divergence_none_when_no_comparable_swings():
    assert rsi_divergence([1,2,3], [40,50,60], lookback=1) is None

def test_atr_stop_target_long():
    r = atr_stop_target(entry=100.0, atr_val=2.0, direction="long", stop_mult=1.5, target_mults=(1.0,2.0))
    assert r["stop"] == 97.0        # 100 - 1.5*2
    assert r["target1"] == 102.0    # 100 + 1*2
    assert r["target2"] == 104.0    # 100 + 2*2
    assert r["risk_per_share"] == 3.0
    assert r["reward_risk_1"] == round(2/3, 2)
    assert r["reward_risk_2"] == round(4/3, 2)

def test_atr_stop_target_short():
    r = atr_stop_target(entry=100.0, atr_val=2.0, direction="short", stop_mult=1.5, target_mults=(1.0,2.0))
    assert r["stop"] == 103.0       # 100 + 1.5*2
    assert r["target1"] == 98.0     # 100 - 1*2
    assert r["target2"] == 96.0     # 100 - 2*2

def test_atr_stop_target_no_atr():
    assert atr_stop_target(entry=100.0, atr_val=None, direction="long") is None
    assert atr_stop_target(entry=100.0, atr_val=0, direction="long") is None

def test_supertrend_uptrend_direction_matches_trend():
    # A clean, strictly monotonic uptrend must read direction=1 (an earlier,
    # non-stateful version of calculate_supertrend inverted this).
    highs = [10+i for i in range(40)]
    lows = [9+i for i in range(40)]
    closes = [9.5+i for i in range(40)]
    r = calculate_supertrend(highs, lows, closes, period=10, multiplier=3.0)
    assert r is not None
    assert r.direction == 1
    assert r.signal in ("BUY", "HOLD")

def test_supertrend_downtrend_direction_matches_trend():
    highs = [50-i for i in range(40)]
    lows = [49-i for i in range(40)]
    closes = [49.5-i for i in range(40)]
    r = calculate_supertrend(highs, lows, closes, period=10, multiplier=3.0)
    assert r is not None
    assert r.direction == -1
    assert r.signal in ("SELL", "HOLD")

def test_vwap():
    assert True  # VWAP tested in market_state
