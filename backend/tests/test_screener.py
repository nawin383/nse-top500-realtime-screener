from backend.app.models import StockState, IndicatorSnapshot, MomentumMetrics
from backend.app.screeners import top_gainers, top_losers, volume_spike, breakout_stocks

def make(s, chg, vol, rv, breakout=False):
    st=StockState(symbol=s, token=hash(s)%9000000, ltp=100+chg, change_pct=chg, volume=vol, rel_volume=rv)
    st.indicators=IndicatorSnapshot(vwap=100 if breakout else 105)
    st.momentum=MomentumMetrics(day_high_breakout=breakout)
    st.score=50
    st.signal="NEUTRAL"
    return st

def test_gainers():
    states=[make(f"S{i}", chg=i, vol=1000000, rv=1) for i in range(-5,6)]
    g=top_gainers(states, limit=3)
    assert g[0].change_pct==5
    assert len(g)==3
    assert g[0].symbol=="S5"

def test_losers():
    states=[make(f"S{i}", chg=i, vol=1000000, rv=1) for i in range(-5,6)]
    l=top_losers(states, limit=2)
    assert l[0].change_pct==-5

def test_volume_spike():
    states=[make("A",1,1000000,0.5), make("B",1,1000000,2.5), make("C",1,1000000,3.0)]
    v=volume_spike(states, threshold=1.5)
    assert len(v)==2
    assert v[0].symbol=="C"

def test_breakout():
    states=[make("A",1,1000,1,True), make("B",1,1000,1,False), make("C",2,1000,1,True)]
    b=breakout_stocks(states)
    assert len(b)==2
    assert "A" in [x.symbol for x in b]
