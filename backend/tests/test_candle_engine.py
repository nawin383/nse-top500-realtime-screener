from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")
from backend.app.candle_engine import CandleEngine, floor_to_interval

def test_floor():
    dt=datetime(2026,8,27,10,7,45,tzinfo=IST)
    f=floor_to_interval(dt,5)
    assert f.minute==5 and f.second==0
    f1=floor_to_interval(dt,1)
    assert f1.minute==7

def test_candle_single():
    eng=CandleEngine(intervals=[1,5])
    ts=datetime(2026,8,27,9,15,10,tzinfo=IST)
    eng.on_tick("RELIANCE", 100, 1000, ts)
    assert len(eng.get_candles("RELIANCE",1))==1
    c=eng.get_candles("RELIANCE",1)[0]
    assert c.open==100 and c.close==100
    # same bucket update
    ts2=datetime(2026,8,27,9,15,30,tzinfo=IST)
    eng.on_tick("RELIANCE", 105, 1500, ts2)
    c2=eng.get_candles("RELIANCE",1)[0]
    assert c2.high==105 and c2.close==105
    # next minute
    ts3=datetime(2026,8,27,9,16,5,tzinfo=IST)
    eng.on_tick("RELIANCE", 102, 2000, ts3)
    assert len(eng.get_candles("RELIANCE",1))==2

def test_candle_5min():
    eng=CandleEngine(intervals=[5])
    for minute in [0,1,2,3,4,6]:
        ts=datetime(2026,8,27,9,15+minute,0,tzinfo=IST)
        eng.on_tick("TCS", 100+minute, 1000+minute*100, ts)
    candles=eng.get_candles("TCS",5)
    # 9:15-9:19 is one bucket, 9:20 next? 9:15 bucket is 9:15, 9:20 bucket...
    # Actually 9:15 bucket includes 9:15-9:19, 9:20 includes 9:20+
    # So we have 2 buckets
    assert len(candles)==2

def test_duplicate():
    eng=CandleEngine(intervals=[1])
    ts=datetime(2026,8,27,10,0,0,tzinfo=IST)
    eng.on_tick("INFY", 1500, 1000, ts)
    eng.on_tick("INFY", 1500, 1000, ts)  # duplicate
    assert len(eng.get_candles("INFY",1))==1

def test_market_boundaries():
    eng=CandleEngine(intervals=[1])
    # market open and close handling - just ensure no crash
    for h,m in [(9,15),(9,16),(15,29),(15,30)]:
        ts=datetime(2026,8,27,h,m,0,tzinfo=IST)
        eng.on_tick("SBIN", 500+m, 1000, ts)
    assert len(eng.get_candles("SBIN",1))>=2
