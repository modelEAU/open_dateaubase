"""Contract test for GET /equipment/{id}/story (Equipment Story aggregate).

Repository layer patched — asserts the endpoint contract and status codes, not
the SQL (verified in the browser pass against the seeded DB).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_REPO = "api.v1.endpoints.equipment.equipment_repository"


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


def _story():
    return {
        "equipment": {
            "equipment_id": 12, "identifier": "EXO2 #A12", "serial_number": "18C103456",
            "model": "YSI EXO2", "manufacturer": "YSI", "owner": "modelEAU",
            "purchase_date": "2019-03-14", "is_active": True, "current_location": "Inlet",
        },
        "campaigns": [{"id": 7, "name": "Verdun CSO", "kind": "Monitoring", "role": "Primary",
                       "start": "2026-01-05T00:00:00", "end": None}],
        "location_history": [{"location": "Inlet", "valid_from": "2026-01-05T00:00:00",
                              "valid_to": None, "campaign": "Verdun CSO", "notes": None}],
        "events": [{"id": 1, "kind": "Calibration", "start": "2025-11-20T00:00:00",
                    "end": None, "instantaneous": True, "notes": "Annual cal"}],
        "streams": [{"stream_id": 101, "parameter_name": "pH", "unit_name": "pH",
                     "channel_kind": "Value", "point_count": 14210}],
        "annotations": [{"id": 1, "kind": "Fault", "color": "#DC2626", "title": "Cell drift",
                         "comment": "masked", "start_time": "2026-06-02T00:00:00",
                         "end_time": None, "anchor": "Conductivity"}],
    }


def test_story_returns_assembled_lifetime(client):
    with patch(f"{_REPO}.get_equipment_story", return_value=_story()):
        resp = client.get("/api/v1/equipment/12/story")
    assert resp.status_code == 200
    body = resp.json()
    assert body["equipment"]["identifier"] == "EXO2 #A12"
    assert body["campaigns"][0]["name"] == "Verdun CSO"
    assert body["streams"][0]["point_count"] == 14210
    assert body["annotations"][0]["anchor"] == "Conductivity"


def test_story_404_for_unknown_equipment(client):
    with patch(f"{_REPO}.get_equipment_story", return_value=None):
        resp = client.get("/api/v1/equipment/999/story")
    assert resp.status_code == 404
