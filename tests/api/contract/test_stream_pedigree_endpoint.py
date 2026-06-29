"""Contract test for GET /lineage/streams/{id}/pedigree (stream pedigree)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_REPO = "api.v1.endpoints.lineage.channel_repository"


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


def _pedigree():
    return {
        "stream_id": 42,
        "kind": "sensor",
        "parameter": "TSS",
        "unit": "mg/L",
        "value_kind": "Scalar",
        "label": "CH-TSS",
        "deployments": [
            {
                "valid_from": "2026-01-01T00:00:00", "valid_to": "2026-04-01T00:00:00",
                "equipment_identifier": "EQ5",
                "sampling_location": {"sampling_point_id": 99, "name": "Effluent",
                                      "latitude": 46.78, "longitude": -71.27},
                "process_unit": {"process_unit_id": 7, "tag": "R-210",
                                 "name": "Bioreactor", "kind": "Tank"},
                "site": {"site_id": 3, "name": "pilEAU", "city": "Quebec",
                         "province": "QC", "country": "Canada"},
                "campaign": {"campaign_id": 5, "name": "Winter 2026",
                             "kind": "Experiment", "start": "2026-01-01T00:00:00",
                             "end": "2026-04-01T00:00:00"},
                "responsible_person": {"person_id": 11, "name": "Jean Tremblay",
                                       "email": "jt@x.io", "role": "PI",
                                       "company": "modelEAU"},
            }
        ],
    }


def test_pedigree_returns_deployment_timeline(client):
    with patch(f"{_REPO}.get_stream_pedigree", return_value=_pedigree()):
        resp = client.get("/api/v1/lineage/streams/42/pedigree")
    assert resp.status_code == 200
    body = resp.json()
    assert body["kind"] == "sensor"
    seg = body["deployments"][0]
    assert seg["sampling_location"]["name"] == "Effluent"
    assert seg["process_unit"]["tag"] == "R-210"
    assert seg["site"]["name"] == "pilEAU"
    assert seg["campaign"]["name"] == "Winter 2026"
    assert seg["responsible_person"]["name"] == "Jean Tremblay"


def test_pedigree_forwards_window_to_repo(client):
    with patch(f"{_REPO}.get_stream_pedigree", return_value=_pedigree()) as m:
        client.get(
            "/api/v1/lineage/streams/42/pedigree",
            params={"from": "2026-02-01T00:00:00", "to": "2026-03-01T00:00:00"},
        )
    _, kwargs = m.call_args
    assert kwargs["from_dt"] is not None
    assert kwargs["to_dt"] is not None


def test_pedigree_404(client):
    with patch(f"{_REPO}.get_stream_pedigree", return_value=None):
        resp = client.get("/api/v1/lineage/streams/999/pedigree")
    assert resp.status_code == 404
