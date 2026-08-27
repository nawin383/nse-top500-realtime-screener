import pytest
from fastapi.testclient import TestClient
import json, pathlib
from backend.app.main import app

client=TestClient(app)

def test_health_without_lifespan():
    # health endpoint should work even before lifespan (it does not depend on state)
    # But lifespan not run in TestClient without context manager? Use with.
    pass

def test_api_with_lifespan():
    with TestClient(app) as c:
        r=c.get("/api/health")
        assert r.status_code==200
        assert r.json()["status"]=="ok"

        r=c.get("/")
        assert r.status_code==200
        # "/" now serves frontend HTML in production (if dist exists), otherwise JSON fallback
        # Accept either HTML or JSON for backward compatibility
        try:
            j=r.json()
            assert "NSE" in j.get("name","") or "NSE" in str(j)
        except:
            # HTML response
            assert "NSE" in r.text or "Top500" in r.text or "<html" in r.text.lower()

        # JSON info also available at /api/info
        r=c.get("/api/info")
        assert r.status_code==200
        assert "NSE" in r.json()["name"]

        r=c.get("/api/config")
        assert r.status_code==200
        assert "data_mode" in r.json()

        r=c.get("/api/stocks?limit=5")
        assert r.status_code==200
        data=r.json()
        assert "data" in data
        assert data["count"]<=5

        # screener
        r=c.get("/api/screener")
        assert r.status_code==200
        assert "available" in r.json()

        r=c.get("/api/screener/gainers?limit=2")
        assert r.status_code==200
        assert "data" in r.json()

        r=c.get("/api/alerts")
        assert r.status_code==200
        assert "data" in r.json()
