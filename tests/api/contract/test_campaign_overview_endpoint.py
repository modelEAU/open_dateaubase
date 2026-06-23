"""Contract test for GET /campaigns/{id}/overview (Campaign Story aggregate).

No live DB — the repository layer is patched, so this asserts the endpoint
contract (assembly + status codes), not the SQL. The SQL is exercised in the
browser-verify pass against the seeded demo database.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_REPO = "api.v1.endpoints.campaigns.campaign_repository"


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


def _campaign():
    return {
        "campaign_id": 7, "campaign_kind_id": 2, "campaign_kind_name": "Monitoring",
        "site_id": 3, "site_name": "Verdun WRRF", "name": "Verdun CSO Monitoring",
        "description": None, "start_date": None, "end_date": None,
        "responsible_person_id": None, "responsible_person_name": None,
    }


def _overview():
    return {
        "watershed": {"id": 1, "name": "Rivière St-Pierre"},
        "sampling_points": [{"id": 1, "name": "Inlet", "lat": 45.45, "lon": -73.57, "role": "Inlet"}],
        "data_acquisition_systems": [{"id": 1, "name": "CommCube-A", "kind": "Logger", "valid_from": None}],
        "equipment": [{
            "equipment_id": 12, "identifier": "EXO2 #A12", "model": "YSI EXO2",
            "role": "Primary sonde", "location": "Inlet", "is_active": True,
            "ongoing_event": None,
        }],
        "lab_series": [{
            "stream_id": 481, "name": "COD at Inlet", "parameter_name": "COD",
            "unit_name": "mg/L", "value_kind_name": "Scalar", "sampling_point_label": "Inlet",
        }],
        "lab_panels": [{"id": 1, "name": "Winter influent panel", "series_count": 3}],
        "annotations": [{
            "id": 1, "kind": "Fault", "color": "#DC2626", "title": "Lamp failure",
            "comment": "Spectro offline", "start_time": "2026-06-18T00:00:00", "end_time": None,
            "anchor": "TEST_ COD at Influent",
        }],
        "freshness": [
            {"stream_id": 101, "kind": "sensor", "label": "pH",
             "first_point": "2026-01-06T00:00:00", "last_point": "2026-06-22T08:40:00"},
            {"stream_id": 481, "kind": "lab", "label": "COD at Inlet",
             "first_point": "2026-02-01T09:00:00", "last_point": "2026-06-19T14:10:00"},
        ],
    }


def test_overview_returns_assembled_story(client):
    with patch(f"{_REPO}.get_campaign_by_id", return_value=_campaign()), \
         patch(f"{_REPO}.get_campaign_overview", return_value=_overview()):
        resp = client.get("/api/v1/campaigns/7/overview")

    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign"]["campaign_id"] == 7
    assert body["watershed"]["name"] == "Rivière St-Pierre"
    assert body["equipment"][0]["identifier"] == "EXO2 #A12"
    assert {f["kind"] for f in body["freshness"]} == {"sensor", "lab"}
    assert body["lab_panels"][0]["series_count"] == 3


def test_overview_404_for_unknown_campaign(client):
    with patch(f"{_REPO}.get_campaign_by_id", return_value=None):
        resp = client.get("/api/v1/campaigns/999/overview")
    assert resp.status_code == 404
