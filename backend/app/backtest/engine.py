"""Backtesting engine for screener strategies (stub)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List

@dataclass
class Trade: symbol: str; entry: float; exit: float; pnl: float; bars: int

@dataclass
class BacktestResult: trades: List[Trade]; win_rate: float; total_pnl: float; max_dd: float

def backtest(candles: List[dict], entry_fn: Callable[[dict], bool], exit_fn: Callable[[dict, float], bool]) -> BacktestResult:
    trades: List[Trade] = []
    pos = None
    for i, c in enumerate(candles):
        close = c.get("close") or c.get("ltp") or 0
        if pos is None and entry_fn(c):
            pos = {"entry": close, "idx": i}
        elif pos and exit_fn(c, pos["entry"]):
            pnl = close - pos["entry"]
            trades.append(Trade(c.get("symbol","?"), pos["entry"], close, pnl, i - pos["idx"]))
            pos = None
    wins = sum(1 for t in trades if t.pnl > 0)
    wr = wins / len(trades) if trades else 0
    total = sum(t.pnl for t in trades)
    # naive max drawdown
    cum, peak, dd = 0, 0, 0
    for t in trades:
        cum += t.pnl
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return BacktestResult(trades, wr, total, dd)

# Example: if RSI<30 and price>VWAP then entry; exit after +2% or 10 bars
