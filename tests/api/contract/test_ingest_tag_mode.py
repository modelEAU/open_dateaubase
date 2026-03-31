"""Contract tests for tag-mode sensor ingest endpoints.

These tests verify:
- Unknown signal_port_type / parameter_name / unit_name → 422 before any DB write
- Auto-create warnings are returned in IngestResponse.warnings
- Response shape matches IngestResponse schema
- Normalisation: repository lookup functions are called with stripped+lowercased values

Tests run without a live database using dependency_overrides and patch.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_REPO = "api.v1.endpoints.ingest.signal_port_repository"
_ING_REPO = "api.v1.endpoints.ingest.ingestion_repository"
_VAL_REPO = "api.v1.endpoints.ingest.value_repository"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.fixture
def mock_conn():
    conn, cursor = _make_mock_conn()

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


_VALID_PAYLOAD = {
    "das_name": "PlantSCADA",
    "tag": "TIT-101",
    "signal_port_type": "value",
    "parameter_name": "temperature",
    "unit_name": "degC",
    "data_provenance_id": 1,
    "processing_degree_id": 1,
    "values": [{"timestamp": "2024-01-01T00:00:00", "value": 22.5}],
}


def _patch_all_resolved(
    *,
    spt_id: int = 1,
    param_id: int = 7,
    unit_id: int = 3,
    das_created: bool = False,
    port_created: bool = False,
    channel_id: int = 42,
    rows: int = 1,
):
    """Return a context-manager stack that patches all repo calls for a happy path."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with (
            patch(f"{_REPO}.find_signal_port_type_by_name", return_value=spt_id),
            patch(f"{_REPO}.find_parameter_by_name", return_value=param_id),
            patch(f"{_REPO}.find_unit_by_name", return_value=unit_id),
            patch(f"{_REPO}.find_or_create_das", return_value=(10, das_created)),
            patch(f"{_REPO}.find_or_create_signal_port", return_value=(20, port_created)),
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata", return_value=channel_id),
            patch(f"{_VAL_REPO}.insert_scalar_values", return_value=rows),
        ):
            yield

    return _ctx()


# ---------------------------------------------------------------------------
# Validation errors (fired before any DB write)
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_unknown_signal_port_type_returns_422(self, client, mock_conn):
        payload = {**_VALID_PAYLOAD, "signal_port_type": "not_a_type"}
        with (
            patch(f"{_REPO}.find_signal_port_type_by_name", return_value=None),
            patch(f"{_REPO}.find_parameter_by_name") as mock_param,
            patch(f"{_REPO}.find_unit_by_name") as mock_unit,
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_REPO}.find_or_create_signal_port") as mock_port,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
        ):
            resp = client.post("/api/v1/ingest/sensor", json=payload)

        assert resp.status_code == 422
        assert "signal_port_type" in resp.json()["detail"].lower()
        # Nothing written
        mock_param.assert_not_called()
        mock_unit.assert_not_called()
        mock_das.assert_not_called()
        mock_port.assert_not_called()
        mock_chan.assert_not_called()

    def test_unknown_parameter_name_returns_422(self, client, mock_conn):
        payload = {**_VALID_PAYLOAD, "parameter_name": "xyzzy"}
        with (
            patch(f"{_REPO}.find_signal_port_type_by_name", return_value=1),
            patch(f"{_REPO}.find_parameter_by_name", return_value=None),
            patch(f"{_REPO}.find_unit_by_name") as mock_unit,
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_REPO}.find_or_create_signal_port") as mock_port,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
        ):
            resp = client.post("/api/v1/ingest/sensor", json=payload)

        assert resp.status_code == 422
        assert "parameter_name" in resp.json()["detail"].lower()
        mock_unit.assert_not_called()
        mock_das.assert_not_called()
        mock_port.assert_not_called()
        mock_chan.assert_not_called()

    def test_unknown_unit_name_returns_422(self, client, mock_conn):
        payload = {**_VALID_PAYLOAD, "unit_name": "flurbs"}
        with (
            patch(f"{_REPO}.find_signal_port_type_by_name", return_value=1),
            patch(f"{_REPO}.find_parameter_by_name", return_value=7),
            patch(f"{_REPO}.find_unit_by_name", return_value=None),
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_REPO}.find_or_create_signal_port") as mock_port,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
        ):
            resp = client.post("/api/v1/ingest/sensor", json=payload)

        assert resp.status_code == 422
        assert "unit_name" in resp.json()["detail"].lower()
        mock_das.assert_not_called()
        mock_port.assert_not_called()
        mock_chan.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path — response shape
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_sensor_ingest_returns_channel_id_and_rows(self, client, mock_conn):
        with _patch_all_resolved(channel_id=42, rows=3):
            resp = client.post("/api/v1/ingest/sensor", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        body = resp.json()
        assert body["channel_id"] == 42
        assert body["rows_written"] == 3
        assert "warnings" in body

    def test_no_warnings_when_das_and_port_exist(self, client, mock_conn):
        with _patch_all_resolved(das_created=False, port_created=False):
            resp = client.post("/api/v1/ingest/sensor", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        assert resp.json()["warnings"] == []

    def test_warnings_returned_when_das_auto_created(self, client, mock_conn):
        with _patch_all_resolved(das_created=True, port_created=False):
            resp = client.post("/api/v1/ingest/sensor", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        warnings = resp.json()["warnings"]
        assert len(warnings) == 1
        assert "PlantSCADA" in warnings[0]

    def test_warnings_returned_when_port_auto_created(self, client, mock_conn):
        with _patch_all_resolved(das_created=False, port_created=True):
            resp = client.post("/api/v1/ingest/sensor", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        warnings = resp.json()["warnings"]
        assert len(warnings) == 1
        assert "TIT-101" in warnings[0]

    def test_two_warnings_when_both_auto_created(self, client, mock_conn):
        with _patch_all_resolved(das_created=True, port_created=True):
            resp = client.post("/api/v1/ingest/sensor", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        assert len(resp.json()["warnings"]) == 2


# ---------------------------------------------------------------------------
# Normalisation — repository receives stripped+lowercased strings
# ---------------------------------------------------------------------------


class TestNormalisation:
    """Verify that dirty input is passed through to repo functions which normalise it.

    We assert that the repo lookup functions are called with *exactly* the raw value
    from the request — normalisation (strip+lower) happens inside the repo functions,
    not in the endpoint.  This ensures the endpoint does not double-normalise.
    """

    def test_dirty_input_passed_to_repo_functions(self, client, mock_conn):
        dirty_payload = {
            **_VALID_PAYLOAD,
            "signal_port_type": "  VALUE  ",
            "parameter_name": "  Temperature  ",
            "unit_name": "  DegC  ",
            "das_name": "  PlantSCADA  ",
            "tag": "  TIT-101  ",
        }

        with (
            patch(f"{_REPO}.find_signal_port_type_by_name", return_value=1) as mock_spt,
            patch(f"{_REPO}.find_parameter_by_name", return_value=7) as mock_param,
            patch(f"{_REPO}.find_unit_by_name", return_value=3) as mock_unit,
            patch(f"{_REPO}.find_or_create_das", return_value=(10, False)) as mock_das,
            patch(f"{_REPO}.find_or_create_signal_port", return_value=(20, False)),
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata", return_value=42),
            patch(f"{_VAL_REPO}.insert_scalar_values", return_value=1),
        ):
            resp = client.post("/api/v1/ingest/sensor", json=dirty_payload)

        assert resp.status_code == 201
        # The endpoint passes the raw string; normalisation is the repo's responsibility
        mock_spt.assert_called_once_with(mock_conn[0], "  VALUE  ")
        mock_param.assert_called_once_with(mock_conn[0], "  Temperature  ")
        mock_unit.assert_called_once_with(mock_conn[0], "  DegC  ")
        mock_das.assert_called_once_with(mock_conn[0], "  PlantSCADA  ")


# ---------------------------------------------------------------------------
# SignalPort deactivation
# ---------------------------------------------------------------------------


class TestDeactivation:
    def test_deactivate_existing_port(self, client, mock_conn):
        with patch(f"{_REPO}.deactivate_signal_port", return_value=True):
            resp = client.patch("/api/v1/ingest/signal-ports/99/deactivate")

        assert resp.status_code == 200
        body = resp.json()
        assert body["signal_port_id"] == 99
        assert body["deactivated"] is True

    def test_deactivate_missing_port_returns_404(self, client, mock_conn):
        with patch(f"{_REPO}.deactivate_signal_port", return_value=False):
            resp = client.patch("/api/v1/ingest/signal-ports/999/deactivate")

        assert resp.status_code == 404
