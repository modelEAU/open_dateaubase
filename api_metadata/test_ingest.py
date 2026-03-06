# test_ingest.py
import pytest
from fastapi.testclient import TestClient
from api_metadata.main import app, UI_ADMIN_USER, UI_ADMIN_PASSWORD

client = TestClient(app)


def _get_token() -> str:
    resp = client.post("/auth/login", json={
        "username": UI_ADMIN_USER,
        "password": UI_ADMIN_PASSWORD,
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers():
    return {"Authorization": f"Bearer {_get_token()}"}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_invalid():
    resp = client.post("/auth/login", json={"username": "bad", "password": "bad"})
    assert resp.status_code == 401


def test_ingest_requires_auth():
    payload = {
        "equipment_id": 1, "parameter_id": 1, "unit_id": 1,
        "purpose_id": 1,   "sampling_point_id": 1, "project_id": 1,
        "value": 1.0,      "timestamp": "2025-11-30T01:30:00",
    }
    resp = client.post("/ingest", json=payload)
    assert resp.status_code == 401


def test_ingest_metadata_not_found(auth_headers):
    """Doit retourner 400 quand aucun metadata ne correspond."""
    payload = {
        "equipment_id": 9999, "parameter_id": 9999, "unit_id": 9999,
        "purpose_id": 9999,   "sampling_point_id": 9999, "project_id": 9999,
        "value": 1.0,         "timestamp": "2025-11-30T01:30:00",
    }
    resp = client.post("/ingest", json=payload, headers=auth_headers)
    assert resp.status_code == 400


def test_ingest_ok(auth_headers):
    """Ingestion valide avec les données seed (Metadata_ID=1)."""
    payload = {
        "equipment_id": 1, "parameter_id": 1, "unit_id": 1,
        "purpose_id": 1,   "sampling_point_id": 1, "project_id": 1,
        "value": 12.34,    "timestamp": "2025-11-30T01:30:00",
    }
    resp = client.post("/ingest", json=payload, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "inserted"
    assert "metadata_id" in data