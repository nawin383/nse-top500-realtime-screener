"""Real-time alert engine with cooldown/debounce."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid
import logging
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

from .models import StockState, Alert, AlertType

logger = logging.getLogger(__name__)

# default cooldowns in seconds per alert type
DEFAULT_COOLDOWN = {
    AlertType.BREAKOUT: 300,
    AlertType.BREAKDOWN: 300,
    AlertType.VOLUME_SPIKE: 600,
    AlertType.UNUSUAL_VOLUME: 600,
    AlertType.VWAP_CROSS: 300,
    AlertType.MOMENTUM_ACCELERATION: 300,
    AlertType.RSI_THRESHOLD: 600,
    AlertType.DAY_HIGH: 300,
    AlertType.DAY_LOW: 300,
    AlertType.PCT_MOVEMENT: 300,
}

class AlertEngine:
    def __init__(self, max_alerts: int=1000, cooldowns: Dict[AlertType,int]=None):
        self.max_alerts = max_alerts
        self.cooldowns = cooldowns or DEFAULT_COOLDOWN.copy()
        self._last_alert: Dict[tuple, datetime] = {}  # (symbol, type) -> ts
        self.alerts: List[Alert] = []
        # config thresholds
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.pct_move_threshold = 2.0
        self.volume_spike_threshold = 2.0
        self.momentum_threshold = 1.5

    def _allow(self, symbol: str, atype: AlertType, now: datetime) -> bool:
        key = (symbol, atype)
        last = self._last_alert.get(key)
        if last is None:
            return True
        cd = self.cooldowns.get(atype, 300)
        return (now - last).total_seconds() >= cd

    def _record(self, alert: Alert):
        self.alerts.append(alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        self._last_alert[(alert.symbol, AlertType(alert.type))] = alert.timestamp
        logger.info(f"Alert {alert.type} {alert.symbol} {alert.message}")

    def check(self, prev: Optional[StockState], curr: StockState, now: datetime=None) -> List[Alert]:
        if now is None:
            now = datetime.now(tz=IST)
        generated=[]
        s = curr

        # Breakout day high
        if s.momentum.day_high_breakout and (prev is None or not prev.momentum.day_high_breakout):
            if self._allow(s.symbol, AlertType.BREAKOUT, now):
                a=Alert(id=str(uuid.uuid4()), symbol=s.symbol, token=s.token, type=AlertType.BREAKOUT,
                        message=f"{s.symbol} Day High breakout at {s.ltp}", timestamp=now, ltp=s.ltp, change_pct=s.change_pct)
                self._record(a); generated.append(a)
        # Breakdown
        if s.momentum.day_low_breakdown and (prev is None or not prev.momentum.day_low_breakdown):
            if self._allow(s.symbol, AlertType.BREAKDOWN, now):
                a=Alert(id=str(uuid.uuid4()), symbol=s.symbol, token=s.token, type=AlertType.BREAKDOWN,
                        message=f"{s.symbol} Day Low breakdown at {s.ltp}", timestamp=now, ltp=s.ltp, change_pct=s.change_pct)
                self._record(a); generated.append(a)
        # Volume spike
        if (s.rel_volume or 0) >= self.volume_spike_threshold and s.volume_spike:
            if self._allow(s.symbol, AlertType.VOLUME_SPIKE, now):
                a=Alert(id=str(uuid.uuid4()), symbol=s.symbol, token=s.token, type=AlertType.VOLUME_SPIKE,
                        message=f"{s.symbol} volume spike RelVol {s.rel_volume:.2f}x", timestamp=now, ltp=s.ltp, change_pct=s.change_pct, metadata={"rel_volume": s.rel_volume})
                self._record(a); generated.append(a)
        # VWAP cross
        if prev and prev.indicators.vwap and s.indicators.vwap:
            prev_above = prev.ltp > prev.indicators.vwap
            curr_above = s.ltp > s.indicators.vwap
            if prev_above != curr_above:
                if self._allow(s.symbol, AlertType.VWAP_CROSS, now):
                    dir_str = "above" if curr_above else "below"
                    a=Alert(id=str(uuid.uuid4()), symbol=s.symbol, token=s.token, type=AlertType.VWAP_CROSS,
                            message=f"{s.symbol} crossed {dir_str} VWAP {s.indicators.vwap:.2f}", timestamp=now, ltp=s.ltp)
                    self._record(a); generated.append(a)
        # RSI threshold
        rsi = s.indicators.rsi
        if rsi is not None:
            if rsi >= self.rsi_overbought or rsi <= self.rsi_oversold:
                if self._allow(s.symbol, AlertType.RSI_THRESHOLD, now):
                    a=Alert(id=str(uuid.uuid4()), symbol=s.symbol, token=s.token, type=AlertType.RSI_THRESHOLD,
                            message=f"{s.symbol} RSI {rsi:.1f}", timestamp=now, ltp=s.ltp, metadata={"rsi": rsi})
                    self._record(a); generated.append(a)
        # pct movement
        if s.change_pct is not None and abs(s.change_pct) >= self.pct_move_threshold:
            # only if just crossed threshold vs prev
            prev_pct = prev.change_pct if prev else None
            if prev_pct is None or abs(prev_pct) < self.pct_move_threshold:
                if self._allow(s.symbol, AlertType.PCT_MOVEMENT, now):
                    a=Alert(id=str(uuid.uuid4()), symbol=s.symbol, token=s.token, type=AlertType.PCT_MOVEMENT,
                            message=f"{s.symbol} moved {s.change_pct:.2f}%", timestamp=now, ltp=s.ltp, change_pct=s.change_pct)
                    self._record(a); generated.append(a)
        # Momentum acceleration
        if s.momentum.ret_5m is not None and abs(s.momentum.ret_5m) >= self.momentum_threshold:
            if prev and prev.momentum.ret_5m is not None and abs(prev.momentum.ret_5m) < self.momentum_threshold:
                if self._allow(s.symbol, AlertType.MOMENTUM_ACCELERATION, now):
                    a=Alert(id=str(uuid.uuid4()), symbol=s.symbol, token=s.token, type=AlertType.MOMENTUM_ACCELERATION,
                            message=f"{s.symbol} momentum {s.momentum.ret_5m:.2f}% 5m", timestamp=now, ltp=s.ltp)
                    self._record(a); generated.append(a)

        return generated

    def get_recent(self, limit=100, symbol: str=None, atype: str=None) -> List[Alert]:
        res = self.alerts[::-1]  # newest first
        if symbol:
            res = [a for a in res if a.symbol==symbol]
        if atype:
            res = [a for a in res if a.type==atype]
        return res[:limit]

    def clear(self):
        self.alerts.clear()
        self._last_alert.clear()
