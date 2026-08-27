"""Comprehensive test suite for backend."""
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.market_state import MarketState
from backend.app.indicators import calculate_vwap, calculate_rsi, calculate_ema
from backend.app.indicators_advanced import calculate_supertrend, calculate_ichimoku, calculate_fibonacci_levels
from backend.app.scoring import calculate_score
from backend.app.screeners import apply_screener


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy","ok") or data.get("healthy") is True


def test_api_info(client):
    """Test API info endpoint."""
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "NSE Top 500 Realtime Screener"
    assert data["version"] == "2.0.0"
    assert "features" in data


def test_market_status(client):
    """Test market status endpoint."""
    response = client.get("/api/market/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "is_open" in data


def test_stocks_endpoint(client):
    """Test stocks listing endpoint."""
    response = client.get("/api/stocks")
    assert response.status_code == 200
    data = response.json()
    assert "stocks" in data or isinstance(data, list)


def test_screeners_list(client):
    """Test screeners listing."""
    response = client.get("/api/screener")
    assert response.status_code == 200


def test_vwap_calculation():
    """Test VWAP calculation."""
    prices = [100.0, 101.0, 102.0, 103.0]
    volumes = [1000, 1100, 1200, 1300]

    vwap = calculate_vwap(prices, volumes)
    assert vwap is not None
    assert isinstance(vwap, float)
    assert vwap > 0


def test_rsi_calculation():
    """Test RSI calculation."""
    closes = [100 + i * 0.5 for i in range(30)]

    rsi = calculate_rsi(closes)
    assert rsi is not None
    assert 0 <= rsi <= 100


def test_ema_calculation():
    """Test EMA calculation."""
    prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]

    ema = calculate_ema(prices, period=9)
    assert ema is not None
    assert isinstance(ema, float)


def test_supertrend_calculation():
    """Test Supertrend indicator."""
    highs = [105.0, 106.0, 107.0, 108.0, 109.0] * 3
    lows = [95.0, 96.0, 97.0, 98.0, 99.0] * 3
    closes = [100.0, 101.0, 102.0, 103.0, 104.0] * 3

    result = calculate_supertrend(highs, lows, closes)
    assert result is not None
    assert result.direction in [1, -1]
    assert result.signal in ["BUY", "SELL", "HOLD"]


def test_ichimoku_calculation():
    """Test Ichimoku Cloud."""
    highs = [105.0 + i * 0.1 for i in range(60)]
    lows = [95.0 + i * 0.1 for i in range(60)]
    closes = [100.0 + i * 0.1 for i in range(60)]

    result = calculate_ichimoku(highs, lows, closes)
    assert result is not None
    assert result.signal in ["BULLISH", "BEARISH", "NEUTRAL", "STRONG_BULLISH", "STRONG_BEARISH"]


def test_fibonacci_levels():
    """Test Fibonacci retracement levels."""
    highs = [110.0, 115.0, 120.0, 125.0, 130.0]
    lows = [90.0, 92.0, 95.0, 97.0, 100.0]

    result = calculate_fibonacci_levels(highs, lows)
    assert result is not None
    assert result.high > result.low
    assert result.level_382 > result.level_618  # higher retrace => lower price


def test_score_calculation():
    """Test scoring system."""
    score_data = {
        "momentum_5m": 2.5,
        "rel_volume": 3.0,
        "is_breakout": True,
        "is_above_vwap": True,
        "volatility": 1.5,
        "volume": 1000000
    }

    score = calculate_score(score_data)
    assert 0 <= score <= 100


def test_screener_gainers():
    """Test gainers screener."""
    stocks = [
        {"symbol": "RELIANCE", "changePercent": 3.5, "volume": 1000000},
        {"symbol": "TCS", "changePercent": -1.2, "volume": 800000},
        {"symbol": "INFY", "changePercent": 2.1, "volume": 900000},
    ]

    result = apply_screener(stocks, "gainer")
    assert len(result) > 0
    assert all(s["changePercent"] > 0 for s in result)


def test_rate_limiting(client):
    """Test rate limiting."""
    # Make multiple requests
    for _ in range(10):
        response = client.get("/api/health")
        assert response.status_code in [200, 429]


@pytest_asyncio.fixture
async def market_state():
    """Create market state for testing."""
    universe = [
        {
            "symbol": "RELIANCE",
            "instrument_token": 738561,
            "company": "Reliance Industries",
            "sector": "Energy"
        }
    ]
    return MarketState(universe)


@pytest.mark.asyncio
async def test_market_state_update(market_state):
    """Test market state updates."""
    tick = {
        "token": 738561,
        "ltp": 2500.0,
        "volume": 1000000,
        "high": 2550.0,
        "low": 2450.0,
        "open": 2480.0
    }

    market_state.update_tick(tick)
    state = market_state.get_state(738561)

    assert state is not None
    assert state.ltp == 2500.0


def test_webhooks_create(client):
    """Test webhook creation."""
    webhook_data = {
        "url": "https://example.com/webhook",
        "name": "Test Webhook",
        "events": ["alert"]
    }

    response = client.post("/api/webhooks", json=webhook_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Webhook"


def test_watchlist_create(client):
    """Test watchlist creation."""
    watchlist_data = {
        "name": "My Watchlist",
        "description": "Test watchlist"
    }

    response = client.post("/api/watchlists", json=watchlist_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Watchlist"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=backend/app"])
