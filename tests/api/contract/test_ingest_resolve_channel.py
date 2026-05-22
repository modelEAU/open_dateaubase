"""Contract tests for resolve-channel endpoints.

Covers both tagged (/resolve-channel) and tagless (/resolve-channel-tagless):
- 422 for unknown channel_kind / parameter / unit -- fired before any DB write
- 200 happy path returns {channel_id, warnings}
- Warnings present when DAS or SignalInterface auto-created
- No data is written (value_repository never called)

Tests run without a live database using dependency_overrides and patch.
"""

from __future__ import annotations

import contextlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_REPO = "api.v1.endpoints.ingest.signal_interface_repository"
_ING_REPO = "api.v1.endpoints.ingest.ingestion_repository"
_VAL_REPO = "api.v1.endpoints.ingest.value_repository"

_TAGGED_PAYLOAD = {
    "das_name": "PlantSCADA",
    "tag": "TIT-101",
    "channel_kind": "value",
    "parameter_name": "temperature",
    "unit_name": "degC",
    "data_provenance_kind_id": 1,
    "processing_kind_id": 1,
}

_TAGLESS_PAYLOAD = {
    "das_name": "DirectStation",
    "equipment_name": "Probe_A",
    "parameter_name": "dissolved oxygen",
    "unit_name": "mg/L",
    "data_provenance_kind_id": 1,
    "processing_kind_id": 1,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_conn():
    from unittest.mock import MagicMock

    conn = MagicMock()
    conn.cursor.return_value = MagicMock()

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    yield conn
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _patch_tagged_resolved(
    *,
    channel_kind_id: int = 1,
    param_id: int = 7,
    unit_id: int = 3,
    das_created: bool = False,
    si_created: bool = False,
    channel_id: int = 42,
):
    with (
        patch(f"{_REPO}.find_channel_kind_by_name", return_value=channel_kind_id),
        patch(f"{_REPO}.find_parameter_by_name", return_value=param_id),
        patch(f"{_REPO}.find_unit_by_name", return_value=unit_id),
        patch(f"{_REPO}.find_or_create_das", return_value=(10, das_created)),
        patch(
            f"{_REPO}.find_signal_interface_by_das_and_name",
            return_value=None if si_created else 20,
        ),
        patch(
            f"{_REPO}.find_or_create_signal_interface", return_value=(20, si_created)
        ),
        patch(f"{_ING_REPO}.find_or_create_sensor_metadata", return_value=channel_id),
    ):
        yield


@contextlib.contextmanager
def _patch_tagless_resolved(
    *,
    param_id: int = 5,
    unit_id: int = 2,
    das_created: bool = False,
    equip_created: bool = False,
    si_created: bool = False,
    channel_id: int = 42,
):
    with (
        patch(f"{_REPO}.find_parameter_by_name", return_value=param_id),
        patch(f"{_REPO}.find_unit_by_name", return_value=unit_id),
        patch(f"{_REPO}.find_or_create_das", return_value=(10, das_created)),
        patch(
            f"{_REPO}.find_or_create_equipment_by_identifier",
            return_value=(20, equip_created),
        ),
        patch(
            f"{_REPO}.find_active_equipment_wiring",
            return_value=None if si_created else (30, None),
        ),
        patch(
            f"{_REPO}.generate_tagless_tagname", return_value="probe_a/dissolved oxygen"
        ),
        patch(
            f"{_REPO}.find_or_create_signal_interface", return_value=(30, si_created)
        ),
        patch(f"{_REPO}.open_equipment_wiring_history", return_value=1),
        patch(f"{_ING_REPO}.find_or_create_sensor_metadata", return_value=channel_id),
    ):
        yield


# ---------------------------------------------------------------------------
# Tagged -- validation errors
# ---------------------------------------------------------------------------


class TestTaggedValidationErrors:
    def test_unknown_channel_kind_returns_422(self, client, mock_conn):
        payload = {**_TAGGED_PAYLOAD, "channel_kind": "not_a_type"}
        with (
            patch(f"{_REPO}.find_channel_kind_by_name", return_value=None),
            patch(f"{_REPO}.find_parameter_by_name") as mock_param,
            patch(f"{_REPO}.find_unit_by_name") as mock_unit,
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
            patch(f"{_VAL_REPO}.insert_scalar_values") as mock_vals,
        ):
            resp = client.post("/api/v1/ingest/resolve-channel", json=payload)

        assert resp.status_code == 422
        assert "channel_kind" in resp.json()["detail"].lower()
        mock_param.assert_not_called()
        mock_unit.assert_not_called()
        mock_das.assert_not_called()
        mock_chan.assert_not_called()
        mock_vals.assert_not_called()

    def test_unknown_parameter_returns_422(self, client, mock_conn):
        payload = {**_TAGGED_PAYLOAD, "parameter_name": "xyzzy"}
        with (
            patch(f"{_REPO}.find_channel_kind_by_name", return_value=1),
            patch(f"{_REPO}.find_parameter_by_name", return_value=None),
            patch(f"{_REPO}.find_unit_by_name") as mock_unit,
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
            patch(f"{_VAL_REPO}.insert_scalar_values") as mock_vals,
        ):
            resp = client.post("/api/v1/ingest/resolve-channel", json=payload)

        assert resp.status_code == 422
        assert "parameter_name" in resp.json()["detail"].lower()
        mock_unit.assert_not_called()
        mock_das.assert_not_called()
        mock_chan.assert_not_called()
        mock_vals.assert_not_called()

    def test_unknown_unit_returns_422(self, client, mock_conn):
        payload = {**_TAGGED_PAYLOAD, "unit_name": "flurbs"}
        with (
            patch(f"{_REPO}.find_channel_kind_by_name", return_value=1),
            patch(f"{_REPO}.find_parameter_by_name", return_value=7),
            patch(f"{_REPO}.find_unit_by_name", return_value=None),
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
            patch(f"{_VAL_REPO}.insert_scalar_values") as mock_vals,
        ):
            resp = client.post("/api/v1/ingest/resolve-channel", json=payload)

        assert resp.status_code == 422
        assert "unit_name" in resp.json()["detail"].lower()
        mock_das.assert_not_called()
        mock_chan.assert_not_called()
        mock_vals.assert_not_called()


# ---------------------------------------------------------------------------
# Tagged -- happy path
# ---------------------------------------------------------------------------


class TestTaggedHappyPath:
    def test_returns_channel_id_and_warnings(self, client, mock_conn):
        with _patch_tagged_resolved(channel_id=42):
            resp = client.post("/api/v1/ingest/resolve-channel", json=_TAGGED_PAYLOAD)

        assert resp.status_code == 200
        body = resp.json()
        assert body["channel_id"] == 42
        assert "warnings" in body

    def test_no_warnings_when_all_exist(self, client, mock_conn):
        with _patch_tagged_resolved(das_created=False, si_created=False):
            resp = client.post("/api/v1/ingest/resolve-channel", json=_TAGGED_PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["warnings"] == []

    def test_warning_when_das_auto_created(self, client, mock_conn):
        with _patch_tagged_resolved(das_created=True, si_created=False):
            resp = client.post("/api/v1/ingest/resolve-channel", json=_TAGGED_PAYLOAD)

        assert resp.status_code == 200
        warnings = resp.json()["warnings"]
        assert len(warnings) == 1
        assert "PlantSCADA" in warnings[0]

    def test_warning_when_signal_interface_auto_created(self, client, mock_conn):
        with _patch_tagged_resolved(das_created=False, si_created=True):
            resp = client.post("/api/v1/ingest/resolve-channel", json=_TAGGED_PAYLOAD)

        assert resp.status_code == 200
        warnings = resp.json()["warnings"]
        assert len(warnings) == 1
        assert "TIT-101" in warnings[0]

    def test_two_warnings_when_both_auto_created(self, client, mock_conn):
        with _patch_tagged_resolved(das_created=True, si_created=True):
            resp = client.post("/api/v1/ingest/resolve-channel", json=_TAGGED_PAYLOAD)

        assert resp.status_code == 200
        assert len(resp.json()["warnings"]) == 2

    def test_value_repository_never_called(self, client, mock_conn):
        with (
            _patch_tagged_resolved(),
            patch(f"{_VAL_REPO}.insert_scalar_values") as mock_vals,
        ):
            resp = client.post("/api/v1/ingest/resolve-channel", json=_TAGGED_PAYLOAD)

        assert resp.status_code == 200
        mock_vals.assert_not_called()


# ---------------------------------------------------------------------------
# Tagless -- validation errors
# ---------------------------------------------------------------------------


class TestTaglessValidationErrors:
    def test_unknown_parameter_returns_422(self, client, mock_conn):
        payload = {**_TAGLESS_PAYLOAD, "parameter_name": "xyzzy_unknown"}
        with (
            patch(f"{_REPO}.find_parameter_by_name", return_value=None),
            patch(f"{_REPO}.find_unit_by_name") as mock_unit,
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
            patch(f"{_VAL_REPO}.insert_scalar_values") as mock_vals,
        ):
            resp = client.post("/api/v1/ingest/resolve-channel-tagless", json=payload)

        assert resp.status_code == 422
        assert "parameter_name" in resp.json()["detail"].lower()
        mock_unit.assert_not_called()
        mock_das.assert_not_called()
        mock_chan.assert_not_called()
        mock_vals.assert_not_called()

    def test_unknown_unit_returns_422(self, client, mock_conn):
        payload = {**_TAGLESS_PAYLOAD, "unit_name": "flurbs_unknown"}
        with (
            patch(f"{_REPO}.find_parameter_by_name", return_value=5),
            patch(f"{_REPO}.find_unit_by_name", return_value=None),
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
            patch(f"{_VAL_REPO}.insert_scalar_values") as mock_vals,
        ):
            resp = client.post("/api/v1/ingest/resolve-channel-tagless", json=payload)

        assert resp.status_code == 422
        assert "unit_name" in resp.json()["detail"].lower()
        mock_das.assert_not_called()
        mock_chan.assert_not_called()
        mock_vals.assert_not_called()


# ---------------------------------------------------------------------------
# Tagless -- happy path
# ---------------------------------------------------------------------------


class TestTaglessHappyPath:
    def test_returns_channel_id_and_warnings(self, client, mock_conn):
        with _patch_tagless_resolved(channel_id=99):
            resp = client.post(
                "/api/v1/ingest/resolve-channel-tagless", json=_TAGLESS_PAYLOAD
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["channel_id"] == 99
        assert "warnings" in body

    def test_no_warnings_when_all_exist(self, client, mock_conn):
        with _patch_tagless_resolved(
            das_created=False, equip_created=False, si_created=False
        ):
            resp = client.post(
                "/api/v1/ingest/resolve-channel-tagless", json=_TAGLESS_PAYLOAD
            )

        assert resp.status_code == 200
        assert resp.json()["warnings"] == []

    def test_warning_when_das_auto_created(self, client, mock_conn):
        with _patch_tagless_resolved(das_created=True):
            resp = client.post(
                "/api/v1/ingest/resolve-channel-tagless", json=_TAGLESS_PAYLOAD
            )

        assert resp.status_code == 200
        assert any("DirectStation" in w for w in resp.json()["warnings"])

    def test_warning_when_equipment_auto_created(self, client, mock_conn):
        with _patch_tagless_resolved(equip_created=True):
            resp = client.post(
                "/api/v1/ingest/resolve-channel-tagless", json=_TAGLESS_PAYLOAD
            )

        assert resp.status_code == 200
        assert any("Probe_A" in w for w in resp.json()["warnings"])

    def test_value_repository_never_called(self, client, mock_conn):
        with (
            _patch_tagless_resolved(),
            patch(f"{_VAL_REPO}.insert_scalar_values") as mock_vals,
        ):
            resp = client.post(
                "/api/v1/ingest/resolve-channel-tagless", json=_TAGLESS_PAYLOAD
            )

        assert resp.status_code == 200
        mock_vals.assert_not_called()
