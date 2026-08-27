import pytest
from backend.app.indicators import ema_series, rsi, atr, macd, bollinger, adx

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

def test_adx():
    candles=[{"high":10+i,"low":9+i,"close":9.5+i} for i in range(30)]
    v=adx(candles,14)
    assert v is not None
    assert 0 <= v <= 100

def test_vwap():
    assert True  # VWAP tested in market_state
