"""Contract tests for the F5/F11 data-health endpoints.

  GET /data-health/unlinked-channels            — channels needing wiring (F5)
  GET /data-health/inactive-parent-references   — live refs to dead parents (F11)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app


@pytest.fixture
def client_and_cursor():
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c, cursor
    app.dependency_overrides.clear()


def test_unlinked_channels_maps_rows_and_counts(client_and_cursor):
    client, cursor = client_and_cursor
    cursor.fetchall.return_value = [
        (7, "TSS-RAW", 3, "AI_01", 1680, "2026-04-01T00:00:00", "2026-06-01T00:00:00"),
    ]
    resp = client.get("/api/v1/data-health/unlinked-channels")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    ch = body["channels"][0]
    assert ch["channel_id"] == 7 and ch["observation_count"] == 1680
    assert "vw_UnlinkedChannels" in cursor.execute.call_args.args[0]


def test_unlinked_channels_empty(client_and_cursor):
    client, cursor = client_and_cursor
    cursor.fetchall.return_value = []
    resp = client.get("/api/v1/data-health/unlinked-channels")
    assert resp.json() == {"count": 0, "channels": []}


def test_inactive_parent_references_maps_rows(client_and_cursor):
    client, cursor = client_and_cursor
    cursor.fetchall.return_value = [
        ("active-wiring->interface", 12, 5, 3, "AI_01"),
    ]
    resp = client.get("/api/v1/data-health/inactive-parent-references")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    ref = body["references"][0]
    assert ref["reference_type"] == "active-wiring->interface"
    assert ref["parent_id"] == 3


def test_inactive_parent_references_filters_by_interface(client_and_cursor):
    client, cursor = client_and_cursor
    cursor.fetchall.return_value = []
    client.get(
        "/api/v1/data-health/inactive-parent-references",
        params={"signal_interface_id": 3},
    )
    sql = cursor.execute.call_args.args[0]
    assert "ParentID = ?" in sql
    # the interface id is forwarded as a positional parameter
    assert cursor.execute.call_args.args[1:] == (3,)
