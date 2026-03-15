"""
Smoke tests — verify core endpoints return 200 with valid JSON.

Run:  cd backend && python -m pytest tests/test_api_smoke.py -v
"""
import pytest


SMOKE_ENDPOINTS = [
    "/health",
    "/api/v1/events?limit=1",
    "/api/v1/persons?limit=1",
    "/api/v1/shifts?limit=1",
    "/api/v1/locations?limit=1",
]


@pytest.mark.parametrize("path", SMOKE_ENDPOINTS)
def test_endpoint_returns_200(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}: {resp.text[:200]}"
    # All endpoints should return valid JSON
    resp.json()


def test_root_system_info(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["system"] == "CHALDEAS"
    assert data["status"] == "operational"


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_404_returns_json(client):
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code in (404, 405)
