"""Pydantic models and normalized market data schema."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

# Provider-independent normalized tick
class MarketTick(BaseModel):
    symbol: str
    token: int
    timestamp: datetime
    ltp: float
    last_quantity: Optional[int] = 0
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = Field(default=None, alias="previousClose")
    volume: Optional[int] = 0
    total_value: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_qty: Optional[int] = None
    ask_qty: Optional[int] = None
    oi: Optional[int] = None
    instrument: Optional[str] = None
    trading_status: Optional[str] = "tradable"

    class Config:
        populate_by_name = True

class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: int  # minutes

class IndicatorSnapshot(BaseModel):
    vwap: Optional[float] = None
    vwap_upper1: Optional[float] = None
    vwap_lower1: Optional[float] = None
    vwap_upper2: Optional[float] = None
    vwap_lower2: Optional[float] = None
    ema9: Optional[float] = None
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    rsi: Optional[float] = None
    rsi_divergence: Optional[str] = None  # bullish | bearish | None
    atr: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    macd_cross: Optional[str] = None  # bullish_cross | bearish_cross | None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_width_pct: Optional[float] = None  # (upper-lower)/middle * 100
    adx: Optional[float] = None
    di_plus: Optional[float] = None
    di_minus: Optional[float] = None
    supertrend: Optional[float] = None
    supertrend_direction: Optional[int] = None  # 1 uptrend, -1 downtrend
    supertrend_signal: Optional[str] = None  # BUY | SELL | HOLD

class MomentumMetrics(BaseModel):
    ret_1m: Optional[float] = None
    ret_3m: Optional[float] = None
    ret_5m: Optional[float] = None
    ret_15m: Optional[float] = None
    ret_30m: Optional[float] = None
    opening_range_breakout: Optional[bool] = None
    day_high_breakout: Optional[bool] = None
    day_low_breakdown: Optional[bool] = None
    vwap_breakout: Optional[bool] = None
    or15_high: Optional[float] = None
    or15_low: Optional[float] = None
    or30_high: Optional[float] = None
    or30_low: Optional[float] = None

class StockState(BaseModel):
    symbol: str
    token: int
    company: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: str = "NSE"
    ltp: float = 0
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = None
    previous_day_high: Optional[float] = None
    previous_day_low: Optional[float] = None
    oi: Optional[int] = None
    previous_day_oi: Optional[int] = None
    oi_change_pct: Optional[float] = None
    oi_buildup: Optional[str] = None  # long_buildup | short_buildup | short_covering | long_unwinding
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: int = 0
    avg_price: Optional[float] = None  # for VWAP calculation raw
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_qty: Optional[int] = None
    ask_qty: Optional[int] = None
    last_quantity: Optional[int] = None
    timestamp: Optional[datetime] = None
    freshness: str = "NO_DATA"  # LIVE | DELAYED | STALE | NO_DATA
    distance_from_high_pct: Optional[float] = None
    distance_from_low_pct: Optional[float] = None
    range_pct: Optional[float] = None
    gap_pct: Optional[float] = None
    rel_volume: Optional[float] = None
    volume_spike: Optional[bool] = None
    indicators: IndicatorSnapshot = Field(default_factory=IndicatorSnapshot)
    momentum: MomentumMetrics = Field(default_factory=MomentumMetrics)
    score: float = 0
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    signal: str = "NEUTRAL"  # STRONG_BUY | BUY | NEUTRAL | SELL | STRONG_SELL | BREAKOUT | BREAKDOWN | VOLUME_SPIKE
    signal_strength: float = 0
    rank: Optional[int] = None
    alerts: List[str] = Field(default_factory=list)

class AlertType(str, Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    VOLUME_SPIKE = "volume_spike"
    UNUSUAL_VOLUME = "unusual_volume"
    VWAP_CROSS = "vwap_cross"
    MOMENTUM_ACCELERATION = "momentum_acceleration"
    RSI_THRESHOLD = "rsi_threshold"
    DAY_HIGH = "day_high"
    DAY_LOW = "day_low"
    PCT_MOVEMENT = "pct_movement"

class Alert(BaseModel):
    id: str
    symbol: str
    token: int
    type: AlertType
    message: str
    timestamp: datetime
    ltp: float
    change_pct: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MarketStatusEnum(str, Enum):
    PRE_OPEN = "pre_open"
    OPEN = "open"
    CLOSED = "closed"
    POST_CLOSE = "post_close"
    HOLIDAY = "holiday"

class MarketStatusResponse(BaseModel):
    status: MarketStatusEnum
    is_live: bool
    label: str  # LIVE | MARKET CLOSED
    last_data_received: Optional[datetime] = None
    server_time_ist: datetime
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None

class ScreenerResult(BaseModel):
    symbol: str
    token: int
    ltp: float
    change_pct: Optional[float]
    volume: int
    rel_volume: Optional[float]
    score: float
    signal: str
    reason: Optional[str] = None

class MarketOverview(BaseModel):
    total: int
    advancing: int
    declining: int
    unchanged: int
    top_gainers: List[ScreenerResult]
    top_losers: List[ScreenerResult]
    highest_volume: List[ScreenerResult]
    highest_rel_volume: List[ScreenerResult]
    strongest_momentum: List[ScreenerResult]
    weakest_momentum: List[ScreenerResult]
    above_vwap: int
    below_vwap: int
    breakouts: int
    breakdowns: int
    sector_performance: Dict[str, Any]
