import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.analytics import elite_quant as eq

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(eq, "CACHE_DIR", tmp_path)
    yield


def test_elite_quant_endpoint_with_no_cache_is_honest_about_it():
    r = client.get("/api/analytics/elite-quant?market=IN")
    assert r.status_code == 200
    j = r.json()
    assert j["available"] is False
    assert j["rows"] == []


def test_elite_quant_endpoint_serves_cached_rows_and_respects_limit():
    rows = [{"symbol": f"SYM{i}", "eliteComposite": 10 - i} for i in range(5)]
    eq._write_cache("US", {"available": True, "market": "US", "generatedAt": "2026-01-01T00:00:00", "analyzed": 5, "failed": 0, "rows": rows})

    r = client.get("/api/analytics/elite-quant?market=US&limit=2")
    assert r.status_code == 200
    j = r.json()
    assert j["available"] is True
    assert len(j["rows"]) == 2
    assert j["rows"][0]["symbol"] == "SYM0"


def test_elite_quant_status_reflects_cache_state():
    r = client.get("/api/analytics/elite-quant/status")
    assert r.status_code == 200
    j = r.json()
    assert set(j.keys()) == {"IN", "US"}
    assert j["IN"]["stale"] is True
    assert j["IN"]["generatedAt"] is None

    eq._write_cache("IN", {"available": True, "market": "IN", "generatedAt": "2026-01-01T00:00:00", "analyzed": 3, "failed": 0, "rows": []})
    r2 = client.get("/api/analytics/elite-quant/status")
    assert r2.json()["IN"]["analyzed"] == 3


def test_invalid_market_rejected():
    r = client.get("/api/analytics/elite-quant?market=EU")
    assert r.status_code == 422
