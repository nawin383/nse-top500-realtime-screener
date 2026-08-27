from backend.app.models import StockState, IndicatorSnapshot, MomentumMetrics
from backend.app.scoring import score_stock

def make_state(change_pct=2.5, volume=2000000, rel_volume=2.5, vwap=100, ltp=102, range_pct=3):
    s=StockState(symbol="TEST", token=123, ltp=ltp, change_pct=change_pct, volume=volume, rel_volume=rel_volume, range_pct=range_pct)
    s.indicators=IndicatorSnapshot(vwap=vwap, rsi=65, atr=1.5)
    s.momentum=MomentumMetrics(ret_1m=0.5, ret_3m=1.0, ret_5m=1.8, day_high_breakout=True)
    s.volume_spike=True
    return s

def test_score_high():
    s=make_state()
    score, br, sig, strength = score_stock(s)
    assert 0 <= score <= 100
    assert score > 60  # breakout + high momentum should be high
    assert sig in ["STRONG_BUY","BUY","BREAKOUT","VOLUME_SPIKE"]

def test_score_low():
    s=StockState(symbol="FLAT", token=1, ltp=100, change_pct=0.1, volume=10000, rel_volume=0.5)
    s.indicators=IndicatorSnapshot(vwap=100)
    score,br,sig,strength=score_stock(s)
    assert score < 40
    assert sig=="NEUTRAL"

def test_score_weights():
    s=make_state()
    w={"momentum":25,"volume":25,"rel_volume":20,"breakout":15,"vwap":10,"volatility":5}
    score,br,sig,strength=score_stock(s, weights=w)
    assert sum(br.values()) <= 100.5  # allow rounding
    assert score==round(sum(br.values()),2) or score==min(100,round(sum(br.values()),2))
