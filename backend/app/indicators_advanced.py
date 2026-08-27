"""Advanced technical indicators: Supertrend, Ichimoku, Fibonacci, Volume Profile."""
from __future__ import annotations
from typing import List, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class SupertrendResult:
    """Supertrend indicator result."""
    value: float
    direction: int  # 1 for uptrend, -1 for downtrend
    signal: str  # BUY, SELL, HOLD


@dataclass
class IchimokuCloud:
    """Ichimoku Cloud components."""
    tenkan_sen: Optional[float] = None  # Conversion Line
    kijun_sen: Optional[float] = None   # Base Line
    senkou_span_a: Optional[float] = None  # Leading Span A
    senkou_span_b: Optional[float] = None  # Leading Span B
    chikou_span: Optional[float] = None    # Lagging Span
    signal: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL


@dataclass
class FibonacciLevels:
    """Fibonacci retracement levels."""
    high: float
    low: float
    level_236: float
    level_382: float
    level_500: float
    level_618: float
    level_786: float


def calculate_supertrend(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 10,
    multiplier: float = 3.0
) -> Optional[SupertrendResult]:
    """Calculate Supertrend indicator."""
    if len(closes) < period:
        return None

    # Calculate ATR
    tr_values = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        tr_values.append(tr)

    if len(tr_values) < period:
        return None

    atr = sum(tr_values[-period:]) / period

    # Calculate basic bands
    hl_avg = (highs[-1] + lows[-1]) / 2
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)

    # Determine trend
    close = closes[-1]
    if close > upper_band:
        direction = 1
        value = lower_band
        signal = "BUY"
    elif close < lower_band:
        direction = -1
        value = upper_band
        signal = "SELL"
    else:
        # Check previous trend
        prev_close = closes[-2] if len(closes) > 1 else close
        if prev_close > hl_avg:
            direction = 1
            value = lower_band
            signal = "HOLD"
        else:
            direction = -1
            value = upper_band
            signal = "HOLD"

    return SupertrendResult(value=value, direction=direction, signal=signal)


def calculate_ichimoku(
    highs: List[float],
    lows: List[float],
    closes: List[float]
) -> IchimokuCloud:
    """Calculate Ichimoku Cloud components."""
    result = IchimokuCloud()

    # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    if len(highs) >= 9:
        result.tenkan_sen = (max(highs[-9:]) + min(lows[-9:])) / 2

    # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    if len(highs) >= 26:
        result.kijun_sen = (max(highs[-26:]) + min(lows[-26:])) / 2

    # Senkou Span A: (Tenkan-sen + Kijun-sen) / 2, projected 26 periods ahead
    if result.tenkan_sen and result.kijun_sen:
        result.senkou_span_a = (result.tenkan_sen + result.kijun_sen) / 2

    # Senkou Span B: (52-period high + 52-period low) / 2, projected 26 periods ahead
    if len(highs) >= 52:
        result.senkou_span_b = (max(highs[-52:]) + min(lows[-52:])) / 2

    # Chikou Span: Current close, projected 26 periods back
    if len(closes) >= 26:
        result.chikou_span = closes[-1]

    # Determine signal
    close = closes[-1]
    if result.senkou_span_a and result.senkou_span_b:
        if close > result.senkou_span_a and close > result.senkou_span_b:
            if result.tenkan_sen and result.kijun_sen and result.tenkan_sen > result.kijun_sen:
                result.signal = "STRONG_BULLISH"
            else:
                result.signal = "BULLISH"
        elif close < result.senkou_span_a and close < result.senkou_span_b:
            if result.tenkan_sen and result.kijun_sen and result.tenkan_sen < result.kijun_sen:
                result.signal = "STRONG_BEARISH"
            else:
                result.signal = "BEARISH"

    return result


def calculate_fibonacci_levels(highs: List[float], lows: List[float]) -> Optional[FibonacciLevels]:
    """Calculate Fibonacci retracement levels based on swing high/low."""
    if not highs or not lows:
        return None

    high = max(highs[-50:] if len(highs) >= 50 else highs)
    low = min(lows[-50:] if len(lows) >= 50 else lows)
    diff = high - low

    return FibonacciLevels(
        high=high,
        low=low,
        level_236=high - (diff * 0.236),
        level_382=high - (diff * 0.382),
        level_500=high - (diff * 0.500),
        level_618=high - (diff * 0.618),
        level_786=high - (diff * 0.786)
    )


@dataclass
class VolumeProfile:
    """Volume profile analysis."""
    poc: float  # Point of Control (price with highest volume)
    vah: float  # Value Area High
    val: float  # Value Area Low
    volume_clusters: List[Tuple[float, int]]  # (price, volume) pairs


def calculate_volume_profile(
    closes: List[float],
    volumes: List[int],
    num_bins: int = 20
) -> Optional[VolumeProfile]:
    """Calculate volume profile with POC and value areas."""
    if len(closes) < 20 or len(volumes) < 20:
        return None

    # Create price bins
    min_price = min(closes)
    max_price = max(closes)
    bin_size = (max_price - min_price) / num_bins

    if bin_size == 0:
        return None

    # Aggregate volume by price level
    volume_at_price = {}
    for price, vol in zip(closes, volumes):
        bin_price = round((price - min_price) / bin_size) * bin_size + min_price
        volume_at_price[bin_price] = volume_at_price.get(bin_price, 0) + vol

    if not volume_at_price:
        return None

    # Find POC (Point of Control)
    poc_price = max(volume_at_price, key=volume_at_price.get)

    # Calculate Value Area (70% of volume)
    total_volume = sum(volume_at_price.values())
    target_volume = total_volume * 0.70

    sorted_prices = sorted(volume_at_price.items(), key=lambda x: x[1], reverse=True)
    value_area_volume = 0
    value_area_prices = []

    for price, vol in sorted_prices:
        value_area_prices.append(price)
        value_area_volume += vol
        if value_area_volume >= target_volume:
            break

    vah = max(value_area_prices) if value_area_prices else poc_price
    val = min(value_area_prices) if value_area_prices else poc_price

    clusters = sorted(volume_at_price.items(), key=lambda x: x[1], reverse=True)[:5]

    return VolumeProfile(
        poc=poc_price,
        vah=vah,
        val=val,
        volume_clusters=clusters
    )


def calculate_pivot_points(high: float, low: float, close: float) -> dict:
    """Calculate pivot points and support/resistance levels."""
    pivot = (high + low + close) / 3
    return {"pivot": pivot,"r1": 2*pivot-low,"r2": pivot+(high-low),"r3": high+2*(pivot-low),"s1": 2*pivot-high,"s2": pivot-(high-low),"s3": low-2*(high-pivot)}

def calculate_ichimoku_advanced(highs,lows,closes): return calculate_ichimoku(highs,lows,closes)
def supertrend(highs,lows,closes, period=10, multiplier=3.0): return calculate_supertrend(highs,lows,closes,period,multiplier)
def pivot_points(high,low,close): return calculate_pivot_points(high,low,close)
def volume_profile(closes,volumes,nbins=20): return calculate_volume_profile(closes,volumes,nbins)
def fibonacci(highs,lows): return calculate_fibonacci_levels(highs,lows)

# custom indicator builder registry
_registry: dict={}
def register_indicator(name: str, fn):
    _registry[name]=fn
    return fn
def get_indicator(name): return _registry.get(name)
def list_indicators(): return list(_registry.keys())
def apply_custom(name, *a, **kw):
    fn=_registry.get(name)
    if not fn: raise KeyError(f"unknown indicator {name}")
    return fn(*a, **kw)
