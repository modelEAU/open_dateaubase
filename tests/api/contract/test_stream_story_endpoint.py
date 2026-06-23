"""Contract test for GET /lineage/streams/{id}/story (Stream Story summary)."""

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


def _story(kind="sensor"):
    return {
        "stream_id": 101,
        "record": {
            "kind": kind, "parameter_name": "pH", "unit_name": "pH",
            "value_kind_name": "Scalar", "label": "pH/raw",
            "first_point": "2024-04-02T00:00:00", "last_point": "2026-06-22T08:40:00",
            "point_count": 14210,
        },
        "location_history": [{"location": "Inlet", "valid_from": "2026-01-05T00:00:00",
                              "valid_to": None, "equipment": "EXO2 #A12"}],
        "annotations": [{"id": 1, "kind": "Mask", "color": "#DC2626", "title": "Fault",
                         "comment": "masked", "start_time": "2026-06-02T00:00:00", "end_time": None}],
    }


def test_stream_story_returns_summary(client):
    with patch(f"{_REPO}.get_stream_story", return_value=_story()):
        resp = client.get("/api/v1/lineage/streams/101/story")
    assert resp.status_code == 200
    body = resp.json()
    assert body["record"]["parameter_name"] == "pH"
    assert body["record"]["point_count"] == 14210
    assert body["location_history"][0]["location"] == "Inlet"
    assert body["annotations"][0]["title"] == "Fault"


def test_stream_story_404(client):
    with patch(f"{_REPO}.get_stream_story", return_value=None):
        resp = client.get("/api/v1/lineage/streams/999/story")
    assert resp.status_code == 404
