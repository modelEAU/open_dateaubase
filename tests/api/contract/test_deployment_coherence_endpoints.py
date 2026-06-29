"""Contract tests for the F1/F13 detection endpoints.

  GET /das/{id}/move-conflicts?site_id=  — equipment a DAS move would strand
  GET /equipment/{id}/active-campaign     — running campaign that placed equipment
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_THR = "api.v1.repositories.temporal_history_repository"


@pytest.fixture
def client():
    conn = MagicMock()
    conn.cursor.return_value = MagicMock()

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- F1: /das/{id}/move-conflicts ------------------------------------------

def test_move_conflicts_lists_stranded_equipment(client):
    rows = [
        {
            "equipment_id": 5,
            "equipment_identifier": "pH-01",
            "sampling_point_id": 7,
            "sampling_point_name": "Influent",
            "current_site_id": 2,
            "current_site_name": "Plant A",
        }
    ]
    with patch(
        f"{_THR}.get_das_move_equipment_conflicts", return_value=rows
    ) as m:
        resp = client.get("/api/v1/das/3/move-conflicts", params={"site_id": 9})
    assert resp.status_code == 200
    body = resp.json()
    assert body["das_id"] == 3 and body["site_id"] == 9
    assert body["stranded_equipment"][0]["equipment_identifier"] == "pH-01"
    # site_id forwarded as new_site_id
    assert m.call_args.kwargs == {"das_id": 3, "new_site_id": 9}


def test_move_conflicts_empty_is_coherent(client):
    with patch(f"{_THR}.get_das_move_equipment_conflicts", return_value=[]):
        resp = client.get("/api/v1/das/3/move-conflicts", params={"site_id": 9})
    assert resp.status_code == 200
    assert resp.json()["stranded_equipment"] == []


# --- F13: /equipment/{id}/active-campaign ----------------------------------

def test_active_campaign_returns_running_campaign(client):
    row = {
        "campaign_id": 12,
        "campaign_name": "Pilot 2026",
        "equipment_location_history_id": 88,
        "sampling_point_id": 7,
        "sampling_point_name": "Influent",
    }
    with patch(f"{_THR}.get_active_campaign_deployment", return_value=row):
        resp = client.get("/api/v1/equipment/5/active-campaign")
    assert resp.status_code == 200
    assert resp.json()["campaign_name"] == "Pilot 2026"


def test_active_campaign_null_when_none(client):
    with patch(f"{_THR}.get_active_campaign_deployment", return_value=None):
        resp = client.get("/api/v1/equipment/5/active-campaign")
    assert resp.status_code == 200
    assert resp.json()["campaign_id"] is None
