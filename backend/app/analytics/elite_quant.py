"""Elite quant scoring — a once-a-day batch job, not a live endpoint.

Ported from two standalone local scripts (research/legacy_scripts/
elite_quant_india.py, elite_quant_usa.py) that pulled 5 years of daily
history + fundamentals per symbol from yfinance for ~2000/~1000 symbols and
wrote the result to a matplotlib/seaborn report. That per-request shape
never worked for a web app (Yahoo rate-limits hard and a page load can't
wait on thousands of sequential fetches) — the fix here is the one the user
asked for: run it as a background job once a day over a curated top-100
universe per market, cache the result, and serve the cache instantly.

Kept from the originals: Fama-French beta/alpha vs. a real benchmark,
behavioral-finance indicators (momentum, volume-price correlation, an
overconfidence/anchoring/herding composite), VaR/CVaR, volatility-regime
detection, tail risk (skew/kurtosis/expected shortfall), fundamental/
technical/valuation/performance metrics, composite quality scores, and a
templated investment thesis — all computed from the same real 5y history
and fundamentals the originals used, nothing fabricated.

Dropped from the originals: matplotlib/seaborn plotting (meaningless for a
JSON API), the separate multi-symbol PCA/clustering/anomaly-detection
utility class (never wired into the per-symbol pipeline in the source
either), and the "stress testing" scenarios (2008 crisis -50%, covid -35%,
...) applied as the *same fixed shock* to every symbol regardless of its
own actual risk profile — that's not a per-stock number, it's a constant.
The real per-stock equivalent already computed here (Max_Drawdown, the
worst peak-to-trough move actually observed in 5 years of that stock's own
history) is used instead of a canned scenario.
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "elite_quant"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# How often to re-fetch the exchange-wide symbol list (it barely changes
# day to day, unlike the scores themselves).
UNIVERSE_REFRESH_HOURS = 7 * 24
# Write a partial cache every N symbols so a multi-hour scan (thousands of
# symbols) still leaves usable data behind if the process restarts partway
# (e.g. a free-tier host spinning down on inactivity) instead of losing the
# whole run.
CHECKPOINT_EVERY = 200

# Emergency fallback lists, used only if BOTH a live universe fetch and any
# previously cached universe are unavailable (e.g. first run with no network
# access to the exchange's symbol directory yet). Top-100 (mega/large cap
# first, matching the original source scripts' own ordering).
UNIVERSE_LIMIT = 100

_FALLBACK_INDIA_SYMBOLS = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'BHARTIARTL', 'ICICIBANK', 'INFY', 'SBIN', 'HINDUNILVR',
    'BAJFINANCE', 'ITC', 'LT', 'KOTAKBANK', 'AXISBANK', 'MARUTI', 'SUNPHARMA', 'TITAN',
    'ASIANPAINT', 'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BEL',
    'CIPLA', 'COALINDIA', 'DRREDDY', 'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCLIFE', 'HEROMOTOCO',
    'HINDALCO', 'INDUSINDBK', 'JSWSTEEL', 'M&M', 'NESTLEIND', 'NTPC', 'ONGC', 'POWERGRID',
    'SBILIFE', 'SHRIRAMFIN', 'TATACONSUM', 'TATAMOTORS', 'TATASTEEL', 'TECHM', 'TRENT',
    'ULTRACEMCO', 'WIPRO', 'ABB', 'ADANIENSOL', 'ADANIGREEN', 'ADANIPOWER', 'AMBUJACEM',
    'BANKBARODA', 'BOSCHLTD', 'BPCL', 'BRITANNIA', 'CANBK', 'CGPOWER', 'CHOLAFIN', 'DABUR',
    'DIVISLAB', 'DLF', 'DMART', 'GAIL', 'GODREJCP', 'HAL', 'HAVELLS', 'ICICIGI', 'ICICIPRULI',
    'INDHOTEL', 'INDIGO', 'IOC', 'IRFC', 'JINDALSTEL', 'JSWENERGY', 'LICI', 'LODHA', 'LTIM',
    'MOTHERSON', 'NAUKRI', 'PFC', 'PIDILITIND', 'PNB', 'RECLTD', 'SHREECEM', 'SIEMENS',
    'TATAPOWER', 'TORNTPHARM', 'TVSMOTOR', 'UNITDSPR', 'VBL', 'VEDL', 'ZYDUSLIFE', 'ACC',
    'ASHOKLEY', 'AUROPHARMA', 'BALKRISIND', 'BANDHANBNK', 'BERGEPAINT', 'COLPAL', 'CONCOR',
    'CUMMINSIND', 'ESCORTS',
][:UNIVERSE_LIMIT]

_FALLBACK_US_SYMBOLS = [
    'AAPL', 'MSFT', 'NVDA', 'GOOG', 'GOOGL', 'AMZN', 'META', 'BRK.B', 'LLY', 'AVGO',
    'TSLA', 'WMT', 'JPM', 'V', 'XOM', 'UNH', 'MA', 'ORCL', 'COST', 'HD',
    'PG', 'NFLX', 'JNJ', 'ABBV', 'BAC', 'CRM', 'CVX', 'MRK', 'KO', 'AMD',
    'PEP', 'TMO', 'LIN', 'CSCO', 'MCD', 'ADBE', 'ACN', 'ABT', 'WFC', 'TMUS',
    'GE', 'DIS', 'PM', 'INTC', 'QCOM', 'NOW', 'VZ', 'CAT', 'CMCSA', 'IBM',
    'INTU', 'TXN', 'NEE', 'AMGN', 'AMAT', 'HON', 'UNP', 'ISRG', 'LOW', 'COP',
    'PFE', 'SPGI', 'RTX', 'BKNG', 'MS', 'BA', 'GS', 'UBER', 'SYK', 'AXP',
    'BLK', 'T', 'PLD', 'DE', 'ELV', 'LRCX', 'VRTX', 'TJX', 'MDT', 'GILD',
    'SCHW', 'ADI', 'ADP', 'BSX', 'REGN', 'PANW', 'C', 'MMC', 'CB', 'CI',
    'KLAC', 'SO', 'SBUX', 'MDLZ', 'CME', 'ETN', 'MU', 'ZTS', 'PGR', 'DUK',
][:UNIVERSE_LIMIT]


def _load_local_nse500() -> List[str]:
    """The app's own real, already-vetted NSE Top 500 list (config/nse_top500.json)
    -- a much better default than the 100-symbol fallback, and needs no network
    call since it's a local file already used by the main screener."""
    try:
        from ..config import UNIVERSE_PATH
        data = json.loads(UNIVERSE_PATH.read_text())
        symbols = sorted({row["symbol"] for row in data if row.get("symbol")})
        if symbols:
            return symbols
    except Exception as e:
        logger.warning(f"Elite quant: could not load local NSE 500 list, using {UNIVERSE_LIMIT}-symbol fallback: {e}")
    return _FALLBACK_INDIA_SYMBOLS


@dataclass
class MarketConfig:
    key: str
    label: str
    symbols: List[str]
    symbol_suffix: str
    benchmark: str
    risk_free_rate: float


MARKETS: Dict[str, MarketConfig] = {
    "IN": MarketConfig(key="IN", label="India", symbols=_load_local_nse500(), symbol_suffix=".NS", benchmark="^NSEI", risk_free_rate=0.07),
    "US": MarketConfig(key="US", label="United States", symbols=list(_FALLBACK_US_SYMBOLS), symbol_suffix="", benchmark="SPY", risk_free_rate=0.045),
}

# ------------------------------------------------------------- universe --

def _fetch_india_universe(max_size: int) -> Optional[List[str]]:
    """All real NSE-listed equities via Zerodha Kite's public (unauthenticated)
    instrument dump -- the same source backend/../scripts/fetch_real_universe.py
    already uses to build config/nse_top500.json, just unfiltered by index
    membership so it covers the full exchange (~2000 symbols), not just the
    top 500."""
    try:
        import requests
        r = requests.get("https://api.kite.trade/instruments/NSE", timeout=30)
        r.raise_for_status()
        rows = csv.DictReader(r.text.splitlines())
        symbols = sorted({
            row["tradingsymbol"] for row in rows
            if row.get("instrument_type") == "EQ" and row.get("segment") == "NSE" and row.get("tradingsymbol")
        })
        return symbols[:max_size] if symbols else None
    except Exception as e:
        logger.warning(f"Elite quant: full NSE universe fetch failed: {e}")
        return None


def _fetch_us_universe(max_size: int) -> Optional[List[str]]:
    """Real US-listed common stocks via NASDAQ Trader's public symbol
    directory (nasdaqlisted.txt covers Nasdaq, otherlisted.txt covers
    NYSE/NYSE American/ARCA/BATS) -- the standard free source for a full
    US ticker list. Excludes ETFs and test issues; the trailing file-creation
    footer line and any oddly-formed symbol are skipped rather than crashing."""
    try:
        import re
        import requests
        out = set()
        sources = [
            ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "Symbol", "Test Issue"),
            ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "ACT Symbol", "Test Issue"),
        ]
        for url, sym_col, test_col in sources:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            for row in csv.DictReader(r.text.splitlines(), delimiter="|"):
                sym = (row.get(sym_col) or "").strip().replace("/", "-")
                if not sym or not re.match(r"^[A-Z]{1,6}(-[A-Z])?$", sym):
                    continue
                if row.get(test_col, "N").strip() == "Y" or row.get("ETF", "N").strip() == "Y":
                    continue
                out.add(sym)
        return sorted(out)[:max_size] if out else None
    except Exception as e:
        logger.warning(f"Elite quant: full US universe fetch failed: {e}")
        return None


def _universe_cache_path(market: str) -> Path:
    return CACHE_DIR / f"universe_{market}.json"


def refresh_universe_if_needed(market: str, max_size: int) -> None:
    """Keeps MARKETS[market].symbols pointed at the real, full exchange
    universe. Tries a fresh fetch first; on failure, falls back to whatever
    was last cached (even if stale) rather than shrinking back down to the
    small emergency list, since a week-old full universe is far more useful
    than a 100-symbol snapshot."""
    cfg = MARKETS[market]
    cache_path = _universe_cache_path(market)
    cached = None
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
        except Exception:
            cached = None

    if cached and (time.time() - cached.get("fetchedAt", 0)) < UNIVERSE_REFRESH_HOURS * 3600:
        cfg.symbols = cached["symbols"][:max_size]
        return

    fetch_fn = _fetch_india_universe if market == "IN" else _fetch_us_universe
    fresh = fetch_fn(max_size)
    if fresh:
        cfg.symbols = fresh
        cache_path.write_text(json.dumps({"symbols": fresh, "fetchedAt": time.time()}))
        logger.info(f"Elite quant: refreshed {market} universe to {len(fresh)} real symbols")
    elif cached:
        cfg.symbols = cached["symbols"][:max_size]
        logger.info(f"Elite quant: fresh {market} universe fetch failed, reusing stale cache ({len(cfg.symbols)} symbols)")
    else:
        logger.warning(f"Elite quant: no cached {market} universe and fetch failed -- using {len(cfg.symbols)}-symbol default")

# ---------------------------------------------------------------- factors --

def _fama_french(returns: pd.Series, market_returns: pd.Series, rf: float) -> Dict[str, float]:
    try:
        excess = returns - rf / 252
        excess_mkt = market_returns - rf / 252
        cov = np.cov(excess, excess_mkt)[0, 1]
        var = np.var(excess_mkt)
        beta = cov / var if var != 0 else np.nan
        alpha = float(np.mean(excess - beta * excess_mkt) * 252) if not np.isnan(beta) else np.nan
        return {
            "beta": beta, "alpha": alpha,
            "r_squared": float(np.corrcoef(excess, excess_mkt)[0, 1] ** 2),
            "trackingError": float(np.std(excess - beta * excess_mkt) * np.sqrt(252)) if not np.isnan(beta) else np.nan,
        }
    except Exception:
        return {"beta": np.nan, "alpha": np.nan, "r_squared": np.nan, "trackingError": np.nan}


def _behavioral_bias_score(returns: pd.Series) -> float:
    try:
        vol_clustering = returns.rolling(5).std().std()
        rolling_max = returns.expanding().max()
        rolling_min = returns.expanding().min()
        span = rolling_max.iloc[-1] - rolling_min.iloc[-1]
        current_pos = (returns.iloc[-1] - rolling_min.iloc[-1]) / span if span else 0.5
        ma20 = returns.rolling(20).mean()
        herd_corr = abs(returns.corr(ma20))
        score = vol_clustering * 30 + (1 - current_pos) * 30 + herd_corr * 40
        return float(min(100, max(0, score)))
    except Exception:
        return float("nan")


def _behavioral_indicators(prices: pd.Series, volume: pd.Series) -> Dict[str, float]:
    try:
        returns = prices.pct_change().dropna()
        momentum_1m = returns.rolling(21).sum()
        momentum_3m = returns.rolling(63).sum()
        if volume is not None and len(volume) > 0:
            unusual_volume = volume / volume.rolling(20).mean()
        else:
            unusual_volume = pd.Series([np.nan])
        extreme_returns = returns.abs() > returns.rolling(252).std() * 2
        up_vol = returns[returns > 0].std() * np.sqrt(252)
        down_vol = returns[returns < 0].std() * np.sqrt(252)
        return {
            "momentum1m": float(momentum_1m.iloc[-1]) if len(momentum_1m) else np.nan,
            "momentum3m": float(momentum_3m.iloc[-1]) if len(momentum_3m) else np.nan,
            "unusualVolumeRatio": float(unusual_volume.iloc[-1]) if len(unusual_volume) else np.nan,
            "extremeReturnFrequencyPct": float(extreme_returns.sum() / len(extreme_returns) * 100),
            "volatilityAsymmetry": float(down_vol / up_vol) if up_vol else np.nan,
            "behavioralBiasScore": _behavioral_bias_score(returns),
        }
    except Exception:
        return {"momentum1m": np.nan, "momentum3m": np.nan, "unusualVolumeRatio": np.nan,
                "extremeReturnFrequencyPct": np.nan, "volatilityAsymmetry": np.nan, "behavioralBiasScore": np.nan}


def _var_cvar(returns: pd.Series) -> Dict[str, float]:
    try:
        if len(returns) < 30:
            return {"var95": np.nan, "cvar95": np.nan}
        sorted_r = np.sort(returns)
        idx = int(0.05 * len(sorted_r))
        return {"var95": float(abs(sorted_r[idx]) * 100), "cvar95": float(abs(sorted_r[:idx].mean()) * 100)}
    except Exception:
        return {"var95": np.nan, "cvar95": np.nan}


def _regime(returns: pd.Series, lookback: int = 252) -> Dict[str, Any]:
    try:
        if len(returns) < lookback:
            return {"regime": "insufficient_data", "volatilityPercentile": np.nan}
        rolling_vol = returns.rolling(lookback).std()
        current_vol = rolling_vol.iloc[-1]
        hist_vol = rolling_vol.dropna()
        if current_vol > hist_vol.quantile(0.75):
            regime = "high_volatility"
        elif current_vol < hist_vol.quantile(0.25):
            regime = "low_volatility"
        else:
            regime = "normal"
        return {"regime": regime, "volatilityPercentile": float(stats.percentileofscore(hist_vol, current_vol))}
    except Exception:
        return {"regime": "unknown", "volatilityPercentile": np.nan}


def _tail_risk(returns: pd.Series) -> Dict[str, float]:
    try:
        if len(returns) < 50:
            return {}
        skewness = float(stats.skew(returns))
        kurtosis = float(stats.kurtosis(returns))
        left_5 = np.percentile(returns, 5)
        right_95 = np.percentile(returns, 95)
        es_5 = returns[returns <= left_5].mean()
        return {
            "skewness": skewness, "excessKurtosis": kurtosis,
            "tailRatio9505": float(right_95 / abs(left_5)) if left_5 else np.nan,
            "expectedShortfall5pct": float(abs(es_5) * 100),
            "fatTail": kurtosis > 3,
        }
    except Exception:
        return {}


# ------------------------------------------------------------- fundamentals --

def _fundamentals(info: Dict[str, Any]) -> Dict[str, float]:
    def pct(key):
        v = info.get(key)
        return v * 100 if isinstance(v, (int, float)) else np.nan
    return {
        "roe": pct("returnOnEquity"), "roa": pct("returnOnAssets"),
        "grossMargin": pct("grossMargins"), "operatingMargin": pct("operatingMargins"), "netMargin": pct("profitMargins"),
        "revenueGrowth": pct("revenueGrowth"), "earningsGrowth": pct("earningsGrowth"),
        "debtToEquity": info.get("debtToEquity", np.nan), "currentRatio": info.get("currentRatio", np.nan),
    }


def _technical(hist: pd.DataFrame) -> Dict[str, float]:
    prices, volume = hist["Close"], hist.get("Volume", pd.Series())
    current = prices.iloc[-1]
    sma20 = prices.rolling(20).mean()
    sma200 = prices.rolling(200).mean() if len(prices) > 200 else pd.Series([np.nan])
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - (100 / (1 + rs))).iloc[-1] if len(rs) else np.nan
    vol_ratio = (volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]) if len(volume) > 20 else np.nan
    return {
        "priceVsSma20Pct": float((current / sma20.iloc[-1] - 1) * 100) if len(sma20) and not pd.isna(sma20.iloc[-1]) else np.nan,
        "priceVsSma200Pct": float((current / sma200.iloc[-1] - 1) * 100) if len(sma200) and not pd.isna(sma200.iloc[-1]) else np.nan,
        "rsi": float(rsi) if not pd.isna(rsi) else np.nan,
        "volumeRatio": float(vol_ratio) if not pd.isna(vol_ratio) else np.nan,
    }


def _valuation(info: Dict[str, Any]) -> Dict[str, float]:
    return {
        "peRatio": info.get("trailingPE", np.nan), "forwardPe": info.get("forwardPE", np.nan),
        "pbRatio": info.get("priceToBook", np.nan), "pegRatio": info.get("pegRatio", np.nan),
        "dividendYieldPct": (info.get("dividendYield") or 0) * 100,
    }


def _performance(hist: pd.DataFrame, bench_hist: Optional[pd.DataFrame], rf: float) -> Dict[str, float]:
    prices = hist["Close"]
    returns = prices.pct_change().dropna()
    out: Dict[str, float] = {}
    current = prices.iloc[-1]
    for name, days in {"1M": 21, "3M": 63, "6M": 126, "1Y": 252}.items():
        if len(prices) > days:
            past = prices.iloc[-(days + 1)]
            out[f"return{name}"] = float((current - past) / past * 100)
        else:
            out[f"return{name}"] = np.nan

    if len(returns) >= 252:
        annual_return = returns.mean() * 252
        annual_vol = returns.std() * np.sqrt(252)
        out["sharpeRatio"] = float((annual_return - rf) / annual_vol) if annual_vol else np.nan
        rolling_max = prices.expanding().max()
        drawdown = (prices - rolling_max) / rolling_max
        out["maxDrawdownPct"] = float(drawdown.min() * 100)
        out["volatilityPct"] = float(annual_vol * 100)
    else:
        out.update({"sharpeRatio": np.nan, "maxDrawdownPct": np.nan, "volatilityPct": np.nan})

    if bench_hist is not None and not bench_hist.empty:
        bench_returns = bench_hist["Close"].pct_change().dropna()
        n = min(len(returns), len(bench_returns))
        if n > 50:
            sr, mr = returns.tail(n), bench_returns.tail(n)
            cov, var = np.cov(sr, mr)[0, 1], np.var(mr)
            beta = cov / var if var else np.nan
            out["beta"] = float(beta) if not np.isnan(beta) else np.nan
    return out


def _quality_scores(fund: Dict, tech: Dict, perf: Dict, ff: Dict, behavioral: Dict) -> Dict[str, float]:
    def band(v, *thresholds_scores):
        v = v or 0
        for threshold, score in thresholds_scores:
            if v > threshold:
                return score
        return 0

    financial = min(10, band(fund.get("roe"), (20, 3), (15, 2.5), (10, 2), (5, 1))
                     + band(-(fund.get("debtToEquity") or 100), (-0.5, 2), (-1.0, 1.5), (-2.0, 1))
                     + band(fund.get("currentRatio"), (2, 2), (1.5, 1.5), (1, 1)))
    growth = min(10, (band(fund.get("revenueGrowth"), (25, 3), (15, 2.5), (10, 2), (5, 1))
                       + band(fund.get("earningsGrowth"), (20, 2), (10, 1.5), (5, 1))) * 1.5)
    momentum = min(10, (band(tech.get("rsi", 50) if 40 < (tech.get("rsi") or 50) < 80 else 0, (0, 1 if 50 < (tech.get("rsi") or 0) < 70 else 0))
                         + band(perf.get("return1Y"), (30, 3), (15, 2), (0, 1))) * 2)
    risk_adj = min(10, (band(perf.get("sharpeRatio"), (2, 3), (1, 2), (0, 1))
                         + band(perf.get("maxDrawdownPct", -100), (-10, 3), (-20, 2), (-30, 1))) * 1.5)
    alpha_gen = min(10, (band(ff.get("alpha"), (10, 3), (5, 2), (0, 1))
                          + band(-(ff.get("trackingError") or 100), (-10, 2), (-20, 1))) * 2)
    bias = behavioral.get("behavioralBiasScore", 50) or 50
    behavioral_opp = 8 if bias < 30 else 6 if bias < 50 else 4 if bias < 70 else 2

    components = [financial, growth, momentum, risk_adj, alpha_gen, behavioral_opp]
    elite = float(np.mean(components))

    vol = perf.get("volatilityPct", 50) or 50
    hf_appeal = min(10, (2 if (ff.get("alpha") or 0) > 5 else 0) + 1
                     + (2 if 15 < vol < 35 else 1 if 10 < vol < 50 else 0)
                     + (2 if financial > 7 else 0) + (1 if momentum > 6 else 0))

    return {
        "financialQuality": round(financial, 1), "growthQuality": round(growth, 1),
        "momentumQuality": round(momentum, 1), "riskAdjusted": round(risk_adj, 1),
        "alphaGeneration": round(alpha_gen, 1), "behavioralOpportunity": round(behavioral_opp, 1),
        "eliteComposite": round(elite, 2), "hedgeFundAppeal": round(hf_appeal, 1),
    }


def _investment_thesis(symbol: str, quality: Dict, fund: Dict, perf: Dict, regime: Dict) -> Dict[str, str]:
    elite = quality["eliteComposite"]
    hf = quality["hedgeFundAppeal"]
    if elite >= 8 and hf >= 7:
        category, thesis = "CONVICTION BUY", f"{symbol} exhibits exceptional quality across all metrics with strong hedge fund appeal. "
    elif elite >= 7:
        category, thesis = "STRONG BUY", f"{symbol} demonstrates strong fundamentals with good risk-adjusted returns. "
    elif elite >= 6:
        category, thesis = "BUY", f"{symbol} shows solid prospects with moderate risk profile. "
    elif elite >= 5:
        category, thesis = "HOLD", f"{symbol} presents mixed signals requiring careful monitoring. "
    elif elite >= 4:
        category, thesis = "WEAK HOLD", f"{symbol} shows concerning metrics but may have turnaround potential. "
    else:
        category, thesis = "AVOID", f"{symbol} exhibits weak fundamentals and poor risk-reward profile. "

    roe = fund.get("roe") or 0
    if roe > 20:
        thesis += f"Exceptional ROE of {roe:.1f}% indicates superior capital efficiency. "
    sharpe = perf.get("sharpeRatio") or 0
    if sharpe > 1.5:
        thesis += f"Strong risk-adjusted returns (Sharpe: {sharpe:.2f}) demonstrate quality management. "

    regime_name = regime.get("regime", "unknown")
    if regime_name == "high_volatility":
        thesis += "Current high volatility regime suggests defensive positioning. "
    elif regime_name == "low_volatility":
        thesis += "Low volatility environment favors momentum strategies. "

    max_dd = perf.get("maxDrawdownPct") or 0
    if max_dd < -30:
        risk_level = "HIGH"
        thesis += f"Significant drawdown risk ({max_dd:.1f}%) requires careful position sizing. "
    elif max_dd < -20:
        risk_level = "MEDIUM-HIGH"
    elif max_dd < -10:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    if elite >= 8 and risk_level in ("LOW", "MEDIUM"):
        position_size = "3-5%"
    elif elite >= 7:
        position_size = "2-3%"
    elif elite >= 6:
        position_size = "1-2%"
    else:
        position_size = "<1%"

    time_horizon = "2-3 years" if quality["growthQuality"] > 7 else "1-2 years" if quality["financialQuality"] > 7 else "6-12 months"

    catalysts = []
    if (fund.get("revenueGrowth") or 0) > 20:
        catalysts.append("Earnings momentum")
    if (perf.get("return3M") or 0) > 15:
        catalysts.append("Technical breakout")
    if (fund.get("debtToEquity") or 1) < 0.3:
        catalysts.append("Balance sheet strength")

    return {
        "thesis": f"{category}: {thesis}".strip(), "category": category, "riskLevel": risk_level,
        "timeHorizon": time_horizon, "positionSize": position_size,
        "catalysts": ", ".join(catalysts) if catalysts else "Monitor for developments",
    }


def _clean(d: Dict[str, Any]) -> Dict[str, Any]:
    """NaN isn't valid JSON -- yfinance/pandas produce it constantly for
    missing fundamentals. Null it out honestly instead of crashing the
    response or silently dropping the key."""
    out = {}
    for k, v in d.items():
        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            out[k] = None
        elif isinstance(v, (np.floating,)):
            out[k] = float(v) if np.isfinite(v) else None
        elif isinstance(v, (np.integer,)):
            out[k] = int(v)
        elif isinstance(v, np.bool_):
            out[k] = bool(v)
        else:
            out[k] = v
    return out


def _build_recommendations(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic, rule-based highlight lists computed from the same real
    per-symbol fields already in `rows` -- not a separate model, just
    different sort/filter views of one scan's real output. Mirrors the
    project's existing "AI insights" table, which is templated from real
    fields rather than an LLM call."""
    def pick(pool: List[Dict[str, Any]], n: int, extra_field: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for r in pool[:n]:
            item = {
                "symbol": r["symbol"], "sector": r.get("sector"), "price": r.get("price"),
                "eliteComposite": r.get("eliteComposite"), "category": r.get("category"),
            }
            if extra_field:
                item[extra_field] = r.get(extra_field)
            out.append(item)
        return out

    conviction = sorted(
        [r for r in rows if r.get("category") in ("CONVICTION BUY", "STRONG BUY")],
        key=lambda r: r.get("eliteComposite") or 0, reverse=True,
    )
    by_sharpe = sorted([r for r in rows if r.get("sharpeRatio") is not None], key=lambda r: r["sharpeRatio"], reverse=True)
    by_momentum = sorted([r for r in rows if r.get("momentum3m") is not None], key=lambda r: r["momentum3m"], reverse=True)
    value_pool = sorted(
        [r for r in rows if (r.get("peRatio") or 0) > 0 and (r.get("roe") or 0) > 0],
        key=lambda r: (r.get("roe") or 0) / (r.get("peRatio") or 1), reverse=True,
    )
    defensive_pool = sorted(
        [r for r in rows if r.get("maxDrawdownPct") is not None and (r.get("eliteComposite") or 0) >= 5],
        key=lambda r: r["maxDrawdownPct"], reverse=True,  # least negative (shallowest drawdown) first
    )

    sector_leaders: Dict[str, Dict[str, Any]] = {}
    for r in sorted(rows, key=lambda r: r.get("eliteComposite") or 0, reverse=True):
        sec = r.get("sector") or "N/A"
        if sec not in sector_leaders:
            sector_leaders[sec] = {"symbol": r["symbol"], "eliteComposite": r.get("eliteComposite"), "category": r.get("category")}

    return {
        "convictionBuys": pick(conviction, 10),
        "bestRiskAdjusted": pick(by_sharpe, 10, "sharpeRatio"),
        "momentumLeaders": pick(by_momentum, 10, "momentum3m"),
        "valuePicks": pick(value_pool, 10, "peRatio"),
        "lowDrawdownQuality": pick(defensive_pool, 10, "maxDrawdownPct"),
        "sectorLeaders": sector_leaders,
    }


def _analyze_symbol(yf_module, cfg: MarketConfig, symbol: str, bench_hist: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
    """Blocking (runs in a thread) -- one symbol's full analysis, mirroring
    enhanced_stock_analysis() from the source scripts."""
    ticker_symbol = f"{symbol}{cfg.symbol_suffix}"
    ticker = yf_module.Ticker(ticker_symbol)
    hist = ticker.history(period="5y", timeout=30)
    if hist.empty or len(hist) < 100:
        return None
    info = ticker.info if hasattr(ticker, "info") else {}

    returns = hist["Close"].pct_change().dropna()
    if bench_hist is not None and not bench_hist.empty:
        bench_returns = bench_hist["Close"].pct_change().dropna()
        n = min(len(returns), len(bench_returns))
        ff = _fama_french(returns.tail(n), bench_returns.tail(n), cfg.risk_free_rate)
    else:
        ff = {"beta": None, "alpha": None, "r_squared": None, "trackingError": None}

    behavioral = _behavioral_indicators(hist["Close"], hist.get("Volume", pd.Series()))
    fund = _fundamentals(info)
    tech = _technical(hist)
    val = _valuation(info)
    perf = _performance(hist, bench_hist, cfg.risk_free_rate)
    regime = _regime(returns)
    quality = _quality_scores(fund, tech, perf, ff, behavioral)
    thesis = _investment_thesis(symbol, quality, fund, perf, regime)

    row = {
        "symbol": symbol, "price": float(hist["Close"].iloc[-1]),
        "sector": info.get("sector", "N/A"), "industry": info.get("industry", "N/A"),
        "marketCap": info.get("marketCap"),
        **ff, **behavioral, **_var_cvar(returns), **regime, **_tail_risk(returns),
        **fund, **tech, **val, **perf, **quality, **thesis,
        "dataPoints": len(hist),
    }
    return _clean(row)


async def run_scan(market: str, on_progress=None) -> Dict[str, Any]:
    """Full daily scan for one market. Runs the blocking yfinance calls in a
    thread pool so it never blocks the API server's event loop; paced at
    ~3 symbols/second to stay well under Yahoo's informal rate limits."""
    cfg = MARKETS[market]
    try:
        import yfinance as yf
    except ImportError:
        return {"available": False, "reason": "yfinance not installed", "rows": []}

    def fetch_benchmark():
        try:
            return yf.Ticker(cfg.benchmark).history(period="5y")
        except Exception as e:
            logger.warning(f"Elite quant: benchmark fetch failed for {cfg.benchmark}: {e}")
            return None

    bench_hist = await asyncio.to_thread(fetch_benchmark)

    rows: List[Dict[str, Any]] = []
    failures = 0
    total = len(cfg.symbols)
    for i, symbol in enumerate(cfg.symbols):
        try:
            row = await asyncio.to_thread(_analyze_symbol, yf, cfg, symbol, bench_hist)
            if row:
                rows.append(row)
            else:
                failures += 1
        except Exception as e:
            failures += 1
            logger.warning(f"Elite quant: {symbol} failed: {e}")
        if on_progress:
            on_progress(i + 1, total)
        if (i + 1) % CHECKPOINT_EVERY == 0 and (i + 1) < total:
            sorted_rows = sorted(rows, key=lambda r: r.get("eliteComposite") or 0, reverse=True)
            _write_cache(market, {
                "available": True, "partial": True, "market": market, "label": cfg.label,
                "universeSize": total, "analyzed": len(rows), "failed": failures,
                "generatedAt": datetime.now().isoformat(), "rows": sorted_rows,
                "recommendations": _build_recommendations(sorted_rows),
            })
            logger.info(f"Elite quant: {market} checkpoint {i + 1}/{total} ({len(rows)} analyzed, {failures} failed)")
        await asyncio.sleep(0.35)

    rows.sort(key=lambda r: r.get("eliteComposite") or 0, reverse=True)
    result = {
        "available": True, "partial": False, "market": market, "label": cfg.label,
        "universeSize": total, "analyzed": len(rows), "failed": failures,
        "generatedAt": datetime.now().isoformat(), "rows": rows,
        "recommendations": _build_recommendations(rows),
    }
    _write_cache(market, result)
    return result


def _cache_path(market: str) -> Path:
    return CACHE_DIR / f"{market}.json"


def _write_cache(market: str, result: Dict[str, Any]) -> None:
    try:
        _cache_path(market).write_text(json.dumps(result))
    except Exception as e:
        logger.error(f"Elite quant: failed to write cache for {market}: {e}")


def read_cache(market: str) -> Optional[Dict[str, Any]]:
    p = _cache_path(market)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def is_stale(market: str, max_age_hours: float = 24.0) -> bool:
    cached = read_cache(market)
    if not cached:
        return True
    try:
        generated = datetime.fromisoformat(cached["generatedAt"])
    except Exception:
        return True
    return (datetime.now() - generated).total_seconds() > max_age_hours * 3600
