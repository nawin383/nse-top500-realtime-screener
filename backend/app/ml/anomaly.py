"""Anomaly detection + pattern recognition + LSTM momentum + sentiment stubs."""
from __future__ import annotations
import math
from typing import List, Optional, Dict
try:
    from .anomaly_detection import MLAnomalyDetector, SimpleAnomalyDetector, PatternRecognizer, calculate_z_score
except: 
    MLAnomalyDetector=None; SimpleAnomalyDetector=None; PatternRecognizer=None
    def calculate_z_score(v,c): return 0.0

def zscore_anomaly(values: List[float], current: float, thresh: float=3.0) -> dict:
    z=calculate_z_score(values, current)
    return {"z": z, "is_anomaly": abs(z)>thresh, "score": min(abs(z)/5,1.0)}

def isolation_score(values: List[float], current: float) -> float:
    try:
        if MLAnomalyDetector and len(values)>20:
            d=MLAnomalyDetector()
            for v in values[-50:]: d.add_observation(v,1000,0.5,0.1,1.0)
            r=d.detect(current,1000,0.5,0.1,1.0)
            return r.anomaly_score
    except: pass
    # fallback zscore normalized
    z=calculate_z_score(values, current)
    return 1/(1+math.exp(-abs(z)))

def detect_patterns(highs: List[float], lows: List[float], closes: List[float]) -> Dict[str,Optional[str]]:
    out={}
    try:
        if PatternRecognizer:
            out["head_shoulders"]=PatternRecognizer.detect_head_and_shoulders(highs,lows)
            out["double"]=PatternRecognizer.detect_double_top_bottom(closes)
            out["triangle"]=PatternRecognizer.detect_triangle(highs,lows)
            # flag: tight range then breakout
            if len(closes)>=20:
                rng=max(highs[-10:])-min(lows[-10:])
                if rng < (max(highs[-20:])-min(lows[-20:]))*0.5: out["flag"]="FLAG"
                else: out["flag"]=None
            else: out["flag"]=None
    except: out={"head_shoulders":None,"double":None,"triangle":None,"flag":None}
    return out

def lstm_momentum_score(closes: List[float]) -> float:
    """Stub LSTM: weighted momentum."""
    if len(closes)<10: return 0.0
    rets=[(closes[i]-closes[i-1])/closes[i-1] for i in range(1,len(closes)) if closes[i-1]]
    if not rets: return 0.0
    # exponential weighted last 5 vs earlier
    recent=sum(rets[-5:])/5 if len(rets)>=5 else sum(rets)/len(rets)
    earlier=sum(rets[-10:-5])/5 if len(rets)>=10 else 0
    trend=recent-earlier
    score=max(-1,min(1, trend*100))
    return round(score,3)

def sentiment_placeholder(symbol: str) -> dict:
    return {"symbol":symbol,"sentiment":"NEUTRAL","score":0.0,"source":"stub"}

__all__=["zscore_anomaly","isolation_score","detect_patterns","lstm_momentum_score","sentiment_placeholder","MLAnomalyDetector","SimpleAnomalyDetector","PatternRecognizer"]
