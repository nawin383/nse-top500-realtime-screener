"""AI-powered unusual-activity alerts (stub - pluggable ML)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List

@dataclass
class AIAlert:
    symbol: str
    score: float
    reason: str
    features: dict

def detect_unusual(state, history: List[float] | None = None) -> AIAlert | None:
    """Simple z-score anomaly; replace with sklearn IsolationForest in prod."""
    try:
        rel = state.rel_volume or 0
        rsi = (state.indicators.rsi or 50)
        vol_spike = bool(state.volume_spike)
        # heuristic: relVolume >3 or volume_spike + RSI extreme
        if rel > 3.5 or (vol_spike and (rsi > 70 or rsi < 30)):
            return AIAlert(state.symbol, score=min(99, rel*18 + abs(rsi-50)), reason="unusual volume/RSI divergence", features={"relVolume": rel, "rsi": rsi, "volSpike": vol_spike})
        # optional rolling z-score if history provided
        if history and len(history) > 20:
            import statistics
            m, sd = statistics.mean(history), statistics.pstdev(history) or 1
            z = (state.ltp - m) / sd if state.ltp else 0
            if abs(z) > 3:
                return AIAlert(state.symbol, score=min(95, abs(z)*20), reason=f"price z-score {z:.1f}", features={"z": z})
    except Exception:
        pass
    return None

# TODO: train IsolationForest on (relVolume, rsi, ret_5m, gap) weekly
