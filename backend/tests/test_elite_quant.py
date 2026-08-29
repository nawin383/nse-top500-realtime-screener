import json
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock

from backend.app.analytics import elite_quant as eq


def _synthetic_history(n=1260, start=100.0, drift=0.0004, vol=0.015, seed=1):
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    close = start * np.cumprod(1 + rets)
    idx = pd.date_range("2021-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "Open": close * 0.999, "High": close * 1.01, "Low": close * 0.99,
        "Close": close, "Volume": rng.integers(1_000_000, 5_000_000, n),
    }, index=idx)
    return df


class FakeTicker:
    def __init__(self, symbol, hist=None, info=None):
        self._hist = hist if hist is not None else _synthetic_history()
        self.info = info if info is not None else {
            "sector": "Technology", "industry": "Software", "marketCap": 1_000_000_000,
            "returnOnEquity": 0.22, "returnOnAssets": 0.12, "grossMargins": 0.6,
            "operatingMargins": 0.3, "profitMargins": 0.2, "revenueGrowth": 0.18,
            "earningsGrowth": 0.15, "debtToEquity": 0.4, "currentRatio": 1.8,
            "trailingPE": 25.0, "forwardPE": 22.0, "priceToBook": 6.0, "pegRatio": 1.5,
            "dividendYield": 0.01,
        }

    def history(self, period="5y", timeout=30):
        return self._hist


class FakeYF:
    def __init__(self, hist=None, info=None, fail_symbols=None):
        self._hist = hist
        self._info = info
        self.fail_symbols = fail_symbols or set()

    def Ticker(self, symbol):
        if symbol in self.fail_symbols:
            return FakeTicker(symbol, hist=pd.DataFrame())
        return FakeTicker(symbol, hist=self._hist, info=self._info)


@pytest.fixture(autouse=True)
def isolate_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(eq, "CACHE_DIR", tmp_path)
    yield


def test_var_cvar_and_tail_risk_on_real_looking_returns():
    hist = _synthetic_history()
    returns = hist["Close"].pct_change().dropna()
    var_cvar = eq._var_cvar(returns)
    assert var_cvar["var95"] > 0
    assert var_cvar["cvar95"] >= var_cvar["var95"]  # CVaR is the tail average, at least as bad as VaR
    tail = eq._tail_risk(returns)
    assert "skewness" in tail and "excessKurtosis" in tail


def test_regime_detection_needs_full_lookback():
    short_returns = pd.Series(np.random.normal(0, 0.01, 50))
    assert eq._regime(short_returns)["regime"] == "insufficient_data"
    long_returns = pd.Series(np.random.normal(0, 0.01, 300))
    result = eq._regime(long_returns)
    assert result["regime"] in ("high_volatility", "low_volatility", "normal")


def test_quality_scores_reward_strong_fundamentals():
    strong_fund = {"roe": 25, "debtToEquity": 0.3, "currentRatio": 2.2, "revenueGrowth": 30, "earningsGrowth": 25}
    weak_fund = {"roe": 2, "debtToEquity": 3.0, "currentRatio": 0.5, "revenueGrowth": 1, "earningsGrowth": 0}
    perf = {"sharpeRatio": 1.8, "maxDrawdownPct": -8, "return1Y": 25, "volatilityPct": 20}
    ff = {"alpha": 8, "trackingError": 5}
    behavioral = {"behavioralBiasScore": 20}
    tech = {"rsi": 60}

    strong_scores = eq._quality_scores(strong_fund, tech, perf, ff, behavioral)
    weak_scores = eq._quality_scores(weak_fund, tech, perf, ff, behavioral)
    assert strong_scores["eliteComposite"] > weak_scores["eliteComposite"]
    assert 0 <= strong_scores["eliteComposite"] <= 10
    assert 0 <= strong_scores["hedgeFundAppeal"] <= 10


def test_investment_thesis_categorizes_by_elite_score():
    high_quality = {"eliteComposite": 9, "hedgeFundAppeal": 8, "growthQuality": 8, "financialQuality": 8}
    thesis = eq._investment_thesis("TESTCO", high_quality, {"roe": 25, "revenueGrowth": 25, "debtToEquity": 0.1},
                                    {"sharpeRatio": 2, "maxDrawdownPct": -5, "return3M": 20}, {"regime": "normal"})
    assert thesis["category"] == "CONVICTION BUY"
    assert thesis["riskLevel"] == "LOW"
    assert "Earnings momentum" in thesis["catalysts"]

    low_quality = {"eliteComposite": 2, "hedgeFundAppeal": 1, "growthQuality": 1, "financialQuality": 1}
    weak_thesis = eq._investment_thesis("BADCO", low_quality, {}, {"maxDrawdownPct": -40}, {"regime": "high_volatility"})
    assert weak_thesis["category"] == "AVOID"
    assert weak_thesis["riskLevel"] == "HIGH"


def test_clean_replaces_nan_and_inf_with_none():
    dirty = {"a": float("nan"), "b": float("inf"), "c": np.float64(1.5), "d": np.int64(3), "e": "ok"}
    clean = eq._clean(dirty)
    assert clean["a"] is None
    assert clean["b"] is None
    assert clean["c"] == 1.5
    assert clean["d"] == 3
    assert clean["e"] == "ok"


def test_analyze_symbol_returns_none_on_insufficient_history():
    yf = FakeYF(fail_symbols={"BADCO.NS"})
    cfg = eq.MARKETS["IN"]
    result = eq._analyze_symbol(yf, cfg, "BADCO", None)
    assert result is None


def test_analyze_symbol_produces_expected_shape():
    yf = FakeYF()
    cfg = eq.MARKETS["IN"]
    bench_hist = _synthetic_history(seed=2)
    result = eq._analyze_symbol(yf, cfg, "GOODCO", bench_hist)
    assert result is not None
    assert result["symbol"] == "GOODCO"
    assert result["sector"] == "Technology"
    assert "eliteComposite" in result
    assert "thesis" in result
    assert "roe" in result
    for v in result.values():
        assert not (isinstance(v, float) and np.isnan(v))  # _clean already ran


@pytest.mark.asyncio
async def test_run_scan_end_to_end_with_mocked_yfinance(monkeypatch):
    fake_yf = FakeYF()
    monkeypatch.setattr(eq.MARKETS["IN"], "symbols", ["AAA", "BBB"])

    import sys
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    result = await eq.run_scan("IN")
    assert result["available"] is True
    assert result["analyzed"] == 2
    assert result["failed"] == 0
    assert len(result["rows"]) == 2
    # sorted descending by eliteComposite
    scores = [r["eliteComposite"] for r in result["rows"]]
    assert scores == sorted(scores, reverse=True)

    cached = eq.read_cache("IN")
    assert cached is not None
    assert cached["analyzed"] == 2
    assert eq.is_stale("IN") is False


def test_is_stale_true_when_no_cache():
    assert eq.is_stale("US") is True


def test_default_india_universe_loads_real_local_nse500_list():
    # MARKETS["IN"].symbols should default to the app's own real, already-vetted
    # config/nse_top500.json list (500 symbols) rather than the 100-symbol
    # emergency fallback, since that file is local and needs no network call.
    assert len(eq.MARKETS["IN"].symbols) >= 500
    assert "RELIANCE" in eq.MARKETS["IN"].symbols


def test_build_recommendations_shape_and_content():
    rows = [
        {"symbol": "AAA", "sector": "Tech", "price": 100, "eliteComposite": 8.5, "hedgeFundAppeal": 8,
         "category": "CONVICTION BUY", "sharpeRatio": 2.1, "momentum3m": 0.15, "peRatio": 18, "roe": 25, "maxDrawdownPct": -8},
        {"symbol": "BBB", "sector": "Energy", "price": 50, "eliteComposite": 4.0, "hedgeFundAppeal": 3,
         "category": "AVOID", "sharpeRatio": -0.5, "momentum3m": -0.1, "peRatio": 40, "roe": 2, "maxDrawdownPct": -45},
    ]
    rec = eq._build_recommendations(rows)
    assert {"convictionBuys", "bestRiskAdjusted", "momentumLeaders", "valuePicks", "lowDrawdownQuality", "sectorLeaders"} <= rec.keys()
    assert rec["convictionBuys"][0]["symbol"] == "AAA"
    assert rec["bestRiskAdjusted"][0]["symbol"] == "AAA"
    assert rec["sectorLeaders"]["Tech"]["symbol"] == "AAA"
    assert rec["sectorLeaders"]["Energy"]["symbol"] == "BBB"


def test_fetch_india_universe_parses_real_shaped_csv(monkeypatch):
    csv_text = (
        "instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange\n"
        "101,1,RELIANCE,RELIANCE IND,0,,0,0.05,1,EQ,NSE,NSE\n"
        "102,2,TCS,TCS LTD,0,,0,0.05,1,EQ,NSE,NSE\n"
        "103,3,NIFTYFUT,NIFTY FUT,0,,0,0.05,1,FUT,NFO-FUT,NFO\n"
    )

    class FakeResp:
        text = csv_text
        def raise_for_status(self): pass

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp())
    result = eq._fetch_india_universe(max_size=10)
    assert result == ["RELIANCE", "TCS"]


def test_fetch_india_universe_returns_none_on_network_failure(monkeypatch):
    import requests
    def boom(*a, **k):
        raise ConnectionError("blocked")
    monkeypatch.setattr(requests, "get", boom)
    assert eq._fetch_india_universe(max_size=10) is None


def test_fetch_us_universe_filters_etfs_and_test_issues(monkeypatch):
    nasdaq_text = "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\nAAPL|Apple Inc|Q|N|N|100|N|N\nTESTX|Test Co|Q|Y|N|100|N|N\nQQQ|Invesco QQQ|Q|N|N|100|Y|N\nFile Creation Time: 0101202512:00|||||||\n"
    other_text = "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nMSFT|Microsoft|N|MSFT|N|100|N|MSFT\n"

    class FakeResp:
        def __init__(self, text): self.text = text
        def raise_for_status(self): pass

    import requests
    def fake_get(url, timeout=30):
        return FakeResp(nasdaq_text if "nasdaqlisted" in url else other_text)
    monkeypatch.setattr(requests, "get", fake_get)
    result = eq._fetch_us_universe(max_size=10)
    assert result == ["AAPL", "MSFT"]


def test_refresh_universe_if_needed_uses_fresh_fetch(monkeypatch, tmp_path):
    original = list(eq.MARKETS["IN"].symbols)
    try:
        monkeypatch.setattr(eq, "_fetch_india_universe", lambda max_size: ["FRESH1", "FRESH2"])
        eq.refresh_universe_if_needed("IN", max_size=10)
        assert eq.MARKETS["IN"].symbols == ["FRESH1", "FRESH2"]
        assert eq._universe_cache_path("IN").exists()
    finally:
        eq.MARKETS["IN"].symbols = original


def test_refresh_universe_if_needed_falls_back_to_stale_cache_on_fetch_failure(monkeypatch):
    original = list(eq.MARKETS["IN"].symbols)
    try:
        eq._universe_cache_path("IN").write_text(json.dumps({"symbols": ["CACHED1"], "fetchedAt": 0}))
        monkeypatch.setattr(eq, "_fetch_india_universe", lambda max_size: None)
        eq.refresh_universe_if_needed("IN", max_size=10)
        assert eq.MARKETS["IN"].symbols == ["CACHED1"]
    finally:
        eq.MARKETS["IN"].symbols = original


@pytest.mark.asyncio
async def test_run_scan_writes_partial_checkpoint_then_final_result(monkeypatch):
    fake_yf = FakeYF()
    monkeypatch.setattr(eq.MARKETS["US"], "symbols", ["AAA", "BBB", "CCC"])
    monkeypatch.setattr(eq, "CHECKPOINT_EVERY", 1)

    import sys
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    checkpoints = []
    orig_write_cache = eq._write_cache
    def spy_write_cache(market, result):
        checkpoints.append(dict(result))
        orig_write_cache(market, result)
    monkeypatch.setattr(eq, "_write_cache", spy_write_cache)

    result = await eq.run_scan("US")
    assert result["partial"] is False
    assert "recommendations" in result
    assert any(c["partial"] is True for c in checkpoints)
    assert checkpoints[-1]["partial"] is False
