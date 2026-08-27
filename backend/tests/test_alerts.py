from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")
from backend.app.models import StockState, IndicatorSnapshot, MomentumMetrics
from backend.app.alerts import AlertEngine, AlertType

def make_state(sym="RELIANCE", ltp=100, chg=0, rv=1, rsi=50, breakout=False, breakdown=False, vwap=100):
    s=StockState(symbol=sym, token=500, ltp=ltp, change_pct=chg, volume=1000000, rel_volume=rv)
    s.indicators=IndicatorSnapshot(vwap=vwap, rsi=rsi)
    s.momentum=MomentumMetrics(day_high_breakout=breakout, day_low_breakdown=breakdown, ret_5m=chg)
    s.volume_spike = rv>2
    return s

def test_breakout_alert():
    eng=AlertEngine()
    prev=make_state(breakout=False, chg=0.5)
    curr=make_state(breakout=True, chg=2.0)
    now=datetime.now(tz=IST)
    alerts=eng.check(prev, curr, now)
    # should have breakout + pct movement
    types=[a.type for a in alerts]
    assert AlertType.BREAKOUT in types

def test_cooldown():
    eng=AlertEngine()
    eng.cooldowns[AlertType.BREAKOUT]=300
    prev=make_state(breakout=False)
    curr=make_state(breakout=True)
    now=datetime.now(tz=IST)
    a1=eng.check(prev,curr,now)
    assert any(x.type==AlertType.BREAKOUT for x in a1)
    # second immediate should be suppressed
    a2=eng.check(prev,curr,now + timedelta(seconds=10))
    assert not any(x.type==AlertType.BREAKOUT for x in a2)
    # after cooldown should fire again (need prev not breakout)
    prev2=make_state(breakout=False)
    curr2=make_state(breakout=True)
    a3=eng.check(prev2,curr2, now+timedelta(seconds=301))
    assert any(x.type==AlertType.BREAKOUT for x in a3)

def test_rsi_alert():
    eng=AlertEngine()
    s1=make_state(rsi=50)
    s2=make_state(rsi=75)
    alerts=eng.check(s1,s2, datetime.now(tz=IST))
    assert any(a.type==AlertType.RSI_THRESHOLD for a in alerts)

def test_vwap_cross():
    eng=AlertEngine()
    prev=make_state(ltp=99, vwap=100)  # below
    curr=make_state(ltp=101, vwap=100) # above
    alerts=eng.check(prev,curr, datetime.now(tz=IST))
    assert any(a.type==AlertType.VWAP_CROSS for a in alerts)
