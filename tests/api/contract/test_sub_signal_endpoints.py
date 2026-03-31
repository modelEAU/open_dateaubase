"""Contract tests for sub-signal grouping endpoints (Issue #8).

Tests run without a live database using dependency_overrides and patch.

Covers:
  - POST /ingest/sensor with parent_tag: sets ParentPort_ID on new sub-signal port
  - parent_tag pointing to unknown tag → 422 before any DB write
  - parent_tag with conflicting parent already set → 422
  - GET /ports/{id}/sub-signals: returns all sub-signals
  - POST /ports/{id}/relocate for sub-signal port → 422
  - POST /ports/{id}/relocate for parent port → succeeds
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_REPO = "api.v1.endpoints.ingest.signal_port_repository"
_ING_REPO = "api.v1.endpoints.ingest.ingestion_repository"
_VAL_REPO = "api.v1.endpoints.ingest.value_repository"

_PORT_REPO = "api.v1.endpoints.ports.signal_port_repository"
_TEMPORAL_REPO = "api.v1.endpoints.ports.temporal_history_repository"
_ANNOT_REPO = "api.v1.endpoints.ports.annotation_repository"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    yield conn, cursor
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_BASE_SENSOR_PAYLOAD = {
    "das_name": "PlantSCADA",
    "tag": "TIT-101.status",
    "signal_port_type": "status",
    "parameter_name": "temperature",
    "unit_name": "degC",
    "data_provenance_id": 1,
    "processing_degree_id": 1,
    "values": [{"timestamp": "2024-01-01T00:00:00", "value": 1.0}],
}


def _patch_ingest_resolved(
    *,
    spt_id: int = 2,  # status type
    param_id: int = 7,
    unit_id: int = 3,
    das_id: int = 10,
    das_created: bool = False,
    port_id: int = 20,
    port_created: bool = True,
    channel_id: int = 42,
    rows: int = 1,
):
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with (
            patch(f"{_REPO}.find_signal_port_type_by_name", return_value=spt_id),
            patch(f"{_REPO}.find_parameter_by_name", return_value=param_id),
            patch(f"{_REPO}.find_unit_by_name", return_value=unit_id),
            patch(f"{_REPO}.find_or_create_das", return_value=(das_id, das_created)),
            patch(f"{_REPO}.find_or_create_signal_port", return_value=(port_id, port_created)),
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata", return_value=channel_id),
            patch(f"{_VAL_REPO}.insert_scalar_values", return_value=rows),
        ):
            yield

    return _ctx()


# ---------------------------------------------------------------------------
# parent_tag handling in ingest
# ---------------------------------------------------------------------------


class TestParentTagIngest:
    def test_parent_tag_found_sets_parent_port(self, client, mock_conn):
        payload = {**_BASE_SENSOR_PAYLOAD, "parent_tag": "TIT-101"}

        with (
            _patch_ingest_resolved(port_id=20, port_created=True),
            patch(f"{_REPO}.find_signal_port_by_tag", return_value=99) as mock_find,
            patch(f"{_REPO}.set_parent_port") as mock_set,
        ):
            resp = client.post("/api/v1/ingest/sensor", json=payload)

        assert resp.status_code == 201
        mock_find.assert_called_once()
        mock_set.assert_called_once_with(mock_conn[0], 20, 99)

    def test_parent_tag_not_found_returns_422(self, client, mock_conn):
        payload = {**_BASE_SENSOR_PAYLOAD, "parent_tag": "NONEXISTENT"}

        with (
            _patch_ingest_resolved(port_id=20, port_created=True),
            patch(f"{_REPO}.find_signal_port_by_tag", return_value=None),
            patch(f"{_REPO}.set_parent_port") as mock_set,
        ):
            resp = client.post("/api/v1/ingest/sensor", json=payload)

        assert resp.status_code == 422
        assert "parent_tag" in resp.json()["detail"].lower()
        mock_set.assert_not_called()

    def test_parent_tag_conflict_returns_422(self, client, mock_conn):
        payload = {**_BASE_SENSOR_PAYLOAD, "parent_tag": "TIT-101"}

        with (
            _patch_ingest_resolved(port_id=20, port_created=False),
            patch(f"{_REPO}.find_signal_port_by_tag", return_value=99),
            patch(
                f"{_REPO}.set_parent_port",
                side_effect=ValueError("already has ParentPort_ID=88"),
            ),
        ):
            resp = client.post("/api/v1/ingest/sensor", json=payload)

        assert resp.status_code == 422
        assert "ParentPort_ID" in resp.json()["detail"]

    def test_no_parent_tag_skips_parent_logic(self, client, mock_conn):
        payload = {**_BASE_SENSOR_PAYLOAD}
        assert "parent_tag" not in payload

        with (
            _patch_ingest_resolved(port_id=20, port_created=True),
            patch(f"{_REPO}.find_signal_port_by_tag") as mock_find,
            patch(f"{_REPO}.set_parent_port") as mock_set,
        ):
            resp = client.post("/api/v1/ingest/sensor", json=payload)

        assert resp.status_code == 201
        mock_find.assert_not_called()
        mock_set.assert_not_called()


# ---------------------------------------------------------------------------
# GET /ports/{id}/sub-signals
# ---------------------------------------------------------------------------


class TestGetSubSignals:
    def test_returns_sub_signals(self, client, mock_conn):
        sub_rows = [
            {
                "SignalPort_ID": 50,
                "Tag": "TIT-101.status",
                "IsActive": 1,
                "Description": None,
                "ParentPort_ID": 10,
                "SignalPortType_ID": 2,
                "signal_port_type_name": "Status",
            },
            {
                "SignalPort_ID": 51,
                "Tag": "TIT-101.alarm",
                "IsActive": 1,
                "Description": None,
                "ParentPort_ID": 10,
                "SignalPortType_ID": 3,
                "signal_port_type_name": "Alarm",
            },
        ]

        with patch(f"{_PORT_REPO}.get_sub_signals", return_value=sub_rows):
            resp = client.get("/api/v1/ports/10/sub-signals")

        assert resp.status_code == 200
        body = resp.json()
        assert body["parent_port_id"] == 10
        assert len(body["sub_signals"]) == 2
        ids = {s["signal_port_id"] for s in body["sub_signals"]}
        assert ids == {50, 51}

    def test_returns_empty_list_when_no_sub_signals(self, client, mock_conn):
        with patch(f"{_PORT_REPO}.get_sub_signals", return_value=[]):
            resp = client.get("/api/v1/ports/99/sub-signals")

        assert resp.status_code == 200
        body = resp.json()
        assert body["parent_port_id"] == 99
        assert body["sub_signals"] == []


# ---------------------------------------------------------------------------
# Relocation guard for sub-signal ports
# ---------------------------------------------------------------------------


class TestRelocateSubSignalGuard:
    _RELOCATE_PAYLOAD = {
        "sampling_point_id": 5,
        "start_time": "2024-06-01T12:00:00",
    }

    def test_relocate_sub_signal_returns_422(self, client, mock_conn):
        with patch(f"{_PORT_REPO}.get_parent_port_id", return_value=10):
            resp = client.post(
                "/api/v1/ports/20/relocate", json=self._RELOCATE_PAYLOAD
            )

        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "sub-signal" in detail.lower()
        assert "ParentPort_ID=10" in detail

    def test_relocate_parent_port_succeeds(self, client, mock_conn):
        with (
            patch(f"{_PORT_REPO}.get_parent_port_id", return_value=None),
            patch(
                f"{_TEMPORAL_REPO}.relocate_sensor",
                return_value=(101, 100, [42]),
            ),
            patch(
                f"{_ANNOT_REPO}.create_annotation",
                return_value={"annotation_id": 999},
            ),
        ):
            resp = client.post(
                "/api/v1/ports/15/relocate", json=self._RELOCATE_PAYLOAD
            )

        assert resp.status_code == 201
        body = resp.json()
        assert body["signal_port_id"] == 15
        assert body["new_location_history_id"] == 101
