"""Technical indicator calculations - correct handling of insufficient data.
"""
from __future__ import annotations
from typing import List, Optional, Dict
import math

def ema_series(prices: List[float], period: int) -> List[Optional[float]]:
    if not prices or len(prices) < period:
        return [None]*len(prices)
    k = 2/(period+1)
    ema = []
    # SMA for first
    sma = sum(prices[:period])/period
    for i in range(len(prices)):
        if i < period-1:
            ema.append(None)
        elif i == period-1:
            ema.append(sma)
        else:
            prev = ema[i-1]
            ema.append(prices[i]*k + prev*(1-k))
    return ema

def rsi(prices: List[float], period: int=14) -> Optional[float]:
    if len(prices) < period+1:
        return None
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        gains.append(max(delta,0))
        losses.append(max(-delta,0))
    # Wilder smoothing
    avg_gain = sum(gains[:period])/period
    avg_loss = sum(losses[:period])/period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain*(period-1) + gains[i])/period
        avg_loss = (avg_loss*(period-1) + losses[i])/period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

def atr(candles, period: int=14) -> Optional[float]:
    # candles: list of dict with high, low, close
    if len(candles) < period+1:
        return None
    trs=[]
    for i in range(1, len(candles)):
        h=candles[i]["high"]; l=candles[i]["low"]; pc=candles[i-1]["close"]
        tr = max(h-l, abs(h-pc), abs(l-pc))
        trs.append(tr)
    if len(trs) < period:
        return None
    # Wilder smoothing
    atr_val = sum(trs[:period])/period
    for i in range(period, len(trs)):
        atr_val = (atr_val*(period-1) + trs[i])/period
    return atr_val

def macd(prices: List[float], fast=12, slow=26, signal=9):
    if len(prices) < slow+signal:
        return None, None, None
    ema_fast = ema_series(prices, fast)
    ema_slow = ema_series(prices, slow)
    macd_line=[]
    for f,s in zip(ema_fast, ema_slow):
        if f is None or s is None:
            macd_line.append(None)
        else:
            macd_line.append(f-s)
    # filter None
    valid = [x for x in macd_line if x is not None]
    if len(valid) < signal:
        return macd_line[-1] if macd_line[-1] is not None else None, None, None
    ema_signal = ema_series(valid, signal)
    # align: pad
    # we want last values
    if ema_signal[-1] is None:
        return macd_line[-1], None, None
    hist = macd_line[-1] - ema_signal[-1] if macd_line[-1] is not None and ema_signal[-1] is not None else None
    return macd_line[-1], ema_signal[-1], hist

def bollinger(prices: List[float], period=20, std=2):
    if len(prices) < period:
        return None, None, None
    window = prices[-period:]
    sma = sum(window)/period
    var = sum((x - sma)**2 for x in window)/period
    sd = math.sqrt(var)
    return sma+std*sd, sma, sma-std*sd

def adx(candles, period=14) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """True Wilder ADX(period) + DI+/DI-. Returns (adx, plus_di, minus_di).

    ADX is the Wilder-smoothed moving average of the DX series, not a single
    DX value -- computing DX once at the last bar (as this function used to)
    is a materially different, noisier number. Needs `period` bars to seed
    +DI/-DI/ATR, then `period` more DX values to smooth into ADX, so
    2*period bars minimum; between period and 2*period bars we can still
    return real DI+/DI- (useful on their own as directional bias) with
    adx=None rather than withholding everything.
    """
    if len(candles) < period + 1:
        return None, None, None
    trs: List[float] = []; plus_dm: List[float] = []; minus_dm: List[float] = []
    for i in range(1, len(candles)):
        h=candles[i]["high"]; l=candles[i]["low"]; ph=candles[i-1]["high"]; pl=candles[i-1]["low"]; pc=candles[i-1]["close"]
        tr = max(h-l, abs(h-pc), abs(l-pc))
        trs.append(tr)
        up = h - ph
        down = pl - l
        plus = up if up>down and up>0 else 0
        minus = down if down>up and down>0 else 0
        plus_dm.append(plus)
        minus_dm.append(minus)
    if len(trs) < period:
        return None, None, None

    def _dx(atr_val, p_dm, m_dm):
        if atr_val == 0:
            return 0.0, 0.0, 0.0
        plus_di = 100 * p_dm / atr_val
        minus_di = 100 * m_dm / atr_val
        denom = plus_di + minus_di
        dx = 100 * abs(plus_di - minus_di) / denom if denom else 0.0
        return dx, plus_di, minus_di

    # Wilder-seed TR/+DM/-DM over the first `period` bars, then smooth bar by
    # bar, recording a DX value at every step so we have a DX series to
    # smooth into ADX (not just the final bar's DX).
    atr_val = sum(trs[:period]) / period
    p_dm = sum(plus_dm[:period]) / period
    m_dm = sum(minus_dm[:period]) / period
    dx, plus_di, minus_di = _dx(atr_val, p_dm, m_dm)
    dx_series = [dx]
    for i in range(period, len(trs)):
        atr_val = (atr_val*(period-1) + trs[i]) / period
        p_dm = (p_dm*(period-1) + plus_dm[i]) / period
        m_dm = (m_dm*(period-1) + minus_dm[i]) / period
        dx, plus_di, minus_di = _dx(atr_val, p_dm, m_dm)
        dx_series.append(dx)

    plus_di_r, minus_di_r = round(plus_di, 2), round(minus_di, 2)
    if len(dx_series) < period:
        return None, plus_di_r, minus_di_r  # DI+/DI- valid, ADX needs more bars to smooth
    adx_val = sum(dx_series[:period]) / period
    for i in range(period, len(dx_series)):
        adx_val = (adx_val*(period-1) + dx_series[i]) / period
    return round(adx_val, 2), plus_di_r, minus_di_r

def vwap_bands(vwap: Optional[float], cum_vol: float, cum_pv: float, cum_pv2: float) -> Dict[str, Optional[float]]:
    """VWAP +/- 1 and 2 volume-weighted standard deviations.

    Variance of price around VWAP, volume-weighted: E[p^2] - E[p]^2, where
    E[.] is the cumulative-volume-weighted mean (cum_pv2/cum_vol tracks
    sum(volume_delta * price^2), the same running-sum pattern already used
    for VWAP itself via cum_pv = sum(volume_delta * price)).
    """
    if not vwap or not cum_vol:
        return {"upper1": None, "lower1": None, "upper2": None, "lower2": None, "std": None}
    mean_p2 = cum_pv2 / cum_vol
    variance = mean_p2 - vwap*vwap
    std = math.sqrt(variance) if variance > 0 else 0.0
    return {
        "upper1": round(vwap + std, 2), "lower1": round(vwap - std, 2),
        "upper2": round(vwap + 2*std, 2), "lower2": round(vwap - 2*std, 2),
        "std": round(std, 4),
    }

def macd_cross_signal(prev_hist: Optional[float], curr_hist: Optional[float]) -> Optional[str]:
    """Bullish/bearish MACD histogram zero-line crossover between two ticks."""
    if prev_hist is None or curr_hist is None:
        return None
    if prev_hist <= 0 < curr_hist:
        return "bullish_cross"
    if prev_hist >= 0 > curr_hist:
        return "bearish_cross"
    return None

def _swing_points(values: List[float], lookback: int = 2) -> List[tuple]:
    """Local maxima/minima: (index, value, 'high'|'low'), value strictly greater/
    less than `lookback` neighbors on each side (a standard swing-pivot definition)."""
    points = []
    n = len(values)
    for i in range(lookback, n - lookback):
        window = values[i-lookback:i+lookback+1]
        if values[i] == max(window) and window.count(values[i]) == 1:
            points.append((i, values[i], "high"))
        elif values[i] == min(window) and window.count(values[i]) == 1:
            points.append((i, values[i], "low"))
    return points

def rsi_divergence(closes: List[float], rsi_series: List[Optional[float]], lookback: int = 2) -> Optional[str]:
    """Compare the last two comparable swing points of price vs RSI.

    Bearish divergence: price makes a higher high while RSI makes a lower
    high (momentum fading into the new high). Bullish divergence: price
    makes a lower low while RSI makes a higher low. Returns None if there
    aren't two swings of the same type to compare, or if RSI is unavailable
    at those points (still warming up).
    """
    n = min(len(closes), len(rsi_series))
    if n < lookback*2 + 3:
        return None
    closes = closes[-n:]; rsi_series = rsi_series[-n:]
    price_swings = _swing_points(closes, lookback)

    def rsi_at(i):
        return rsi_series[i] if 0 <= i < len(rsi_series) else None

    highs = [p for p in price_swings if p[2] == "high"]
    lows = [p for p in price_swings if p[2] == "low"]
    if len(highs) >= 2:
        (i1, p1, _), (i2, p2, _) = highs[-2], highs[-1]
        r1, r2 = rsi_at(i1), rsi_at(i2)
        if r1 is not None and r2 is not None and p2 > p1 and r2 < r1:
            return "bearish"
    if len(lows) >= 2:
        (i1, p1, _), (i2, p2, _) = lows[-2], lows[-1]
        r1, r2 = rsi_at(i1), rsi_at(i2)
        if r1 is not None and r2 is not None and p2 < p1 and r2 > r1:
            return "bullish"
    return None

def atr_stop_target(entry: float, atr_val: Optional[float], direction: str, stop_mult: float = 1.5, target_mults: tuple = (1.0, 2.0)) -> Optional[Dict[str, float]]:
    """Size a stop-loss and two targets off ATR for a generated signal.
    direction: 'long' or 'short'."""
    if not atr_val or atr_val <= 0 or not entry:
        return None
    sign = 1 if direction == "long" else -1
    stop = entry - sign*stop_mult*atr_val
    targets = [entry + sign*m*atr_val for m in target_mults]
    risk = abs(entry - stop)
    return {
        "stop": round(stop, 2),
        "target1": round(targets[0], 2),
        "target2": round(targets[1], 2),
        "risk_per_share": round(risk, 2),
        "reward_risk_1": round(abs(targets[0]-entry)/risk, 2) if risk else None,
        "reward_risk_2": round(abs(targets[1]-entry)/risk, 2) if risk else None,
    }

def vwap_from_ticks(ticks_price_vol: List[tuple]) -> Optional[float]:
    # ticks_price_vol: list of (price, volume delta or price*vol)
    # Here we expect cumulative VWAP computed externally; this is helper for candle-based
    if not ticks_price_vol:
        return None
    sum_pv = sum(p*v for p,v in ticks_price_vol)
    sum_v = sum(v for _,v in ticks_price_vol)
    if sum_v == 0:
        return None
    return sum_pv/sum_v

def calc_vwap_incremental(prev_vwap: Optional[float], prev_cum_vol: int, ltp: float, vol_delta: int, cum_pv: float):
    # maintain externally
    pass

# Compatibility wrappers for test_comprehensive
def calculate_vwap(prices, volumes):
    return vwap_from_ticks(list(zip(prices, volumes)))

def calculate_rsi(closes, period=14):
    return rsi(closes, period)

def calculate_ema(prices, period=9):
    s = ema_series(prices, period)
    return next((x for x in reversed(s) if x is not None), None)
