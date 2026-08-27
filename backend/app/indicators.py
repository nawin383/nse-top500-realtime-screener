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

def adx(candles, period=14) -> Optional[float]:
    # simplified ADX
    if len(candles) < 2*period:
        return None
    # compute +DM, -DM, TR
    trs=[]; plus_dm=[]; minus_dm=[]
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
        return None
    # Wilder
    atr_val = sum(trs[:period])/period
    p_dm = sum(plus_dm[:period])/period
    m_dm = sum(minus_dm[:period])/period
    for i in range(period, len(trs)):
        atr_val = (atr_val*(period-1)+trs[i])/period
        p_dm = (p_dm*(period-1)+plus_dm[i])/period
        m_dm = (m_dm*(period-1)+minus_dm[i])/period
    if atr_val == 0:
        return None
    plus_di = 100 * p_dm/atr_val
    minus_di = 100 * m_dm/atr_val
    if plus_di+minus_di == 0:
        return 0
    dx = 100 * abs(plus_di-minus_di)/(plus_di+minus_di)
    # For simplicity return DX as ADX proxy (true ADX would smooth DX)
    return dx

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
