"""Contract tests for tagless-mode sensor ingest (issue #6).

Covers:
- Deterministic synthetic tag generation from equipment_name + parameter_name
- Validation error for unrecognised parameter_name fires before any DB write
- Validation error for unrecognised unit_name fires before any DB write
- Auto-create warnings for DAS and Equipment are returned in IngestResponse.warnings
- Warning for new SignalInterface is returned
- Response shape matches IngestResponse schema
- Repeated ingest with same inputs returns no additional warnings (idempotent path)

Tests run without a live database using dependency_overrides and patch.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_REPO = "api.v1.endpoints.ingest.signal_interface_repository"
_ING_REPO = "api.v1.endpoints.ingest.ingestion_repository"
_VAL_REPO = "api.v1.endpoints.ingest.value_repository"

_VALID_PAYLOAD = {
    "das_name": "DirectStation",
    "equipment_name": "Probe_A",
    "parameter_name": "dissolved oxygen",
    "unit_name": "mg/L",
    "data_provenance_kind_id": 1,
    "processing_kind_id": 1,
    "values": [{"timestamp": "2024-01-01T00:00:00", "value": 8.1}],
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
def _patch_tagless_resolved(
    *,
    param_id: int = 5,
    unit_id: int = 2,
    das_created: bool = False,
    equip_created: bool = False,
    si_created: bool = False,
    channel_id: int = 42,
    rows: int = 1,
):
    """Patch all repo calls for a happy-path tagless ingest."""
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
        patch(f"{_ING_REPO}.find_or_create_sensor_metadata", return_value=channel_id),
        patch(f"{_VAL_REPO}.insert_scalar_values", return_value=rows),
    ):
        yield


# ---------------------------------------------------------------------------
# Tag generation (pure function -- no DB needed)
# ---------------------------------------------------------------------------


class TestTagGeneration:
    def test_basic_generation(self):
        from api.v1.repositories.signal_interface_repository import (
            generate_tagless_tagname,
        )

        assert generate_tagless_tagname("Probe_A", "DO") == "probe_a/do"

    def test_strips_whitespace(self):
        from api.v1.repositories.signal_interface_repository import (
            generate_tagless_tagname,
        )

        # AC example: "Probe_A " + " DO " -> "probe_a/do"
        assert generate_tagless_tagname("Probe_A ", " DO ") == "probe_a/do"

    def test_lowercases_both_parts(self):
        from api.v1.repositories.signal_interface_repository import (
            generate_tagless_tagname,
        )

        assert (
            generate_tagless_tagname("PROBE_A", "Dissolved Oxygen")
            == "probe_a/dissolved oxygen"
        )

    def test_deterministic(self):
        from api.v1.repositories.signal_interface_repository import (
            generate_tagless_tagname,
        )

        tag1 = generate_tagless_tagname("Probe_A", "DO")
        tag2 = generate_tagless_tagname("Probe_A", "DO")
        assert tag1 == tag2

    def test_separator_is_slash(self):
        from api.v1.repositories.signal_interface_repository import (
            generate_tagless_tagname,
        )

        tag = generate_tagless_tagname("station1", "temperature")
        assert "/" in tag
        equipment_part, param_part = tag.split("/", 1)
        assert equipment_part == "station1"
        assert param_part == "temperature"


# ---------------------------------------------------------------------------
# Validation errors -- fired before any DB write
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_unknown_parameter_returns_422(self, client, mock_conn):
        payload = {**_VALID_PAYLOAD, "parameter_name": "xyzzy_unknown"}
        with (
            patch(f"{_REPO}.find_parameter_by_name", return_value=None),
            patch(f"{_REPO}.find_unit_by_name") as mock_unit,
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_REPO}.find_or_create_equipment_by_identifier") as mock_equip,
            patch(f"{_REPO}.find_active_equipment_wiring") as mock_wiring,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
        ):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=payload)

        assert resp.status_code == 422
        assert "parameter_name" in resp.json()["detail"].lower()
        # Nothing written
        mock_unit.assert_not_called()
        mock_das.assert_not_called()
        mock_equip.assert_not_called()
        mock_wiring.assert_not_called()
        mock_chan.assert_not_called()

    def test_unknown_unit_returns_422(self, client, mock_conn):
        payload = {**_VALID_PAYLOAD, "unit_name": "flurbs_unknown"}
        with (
            patch(f"{_REPO}.find_parameter_by_name", return_value=5),
            patch(f"{_REPO}.find_unit_by_name", return_value=None),
            patch(f"{_REPO}.find_or_create_das") as mock_das,
            patch(f"{_REPO}.find_or_create_equipment_by_identifier") as mock_equip,
            patch(f"{_REPO}.find_active_equipment_wiring") as mock_wiring,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
        ):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=payload)

        assert resp.status_code == 422
        assert "unit_name" in resp.json()["detail"].lower()
        mock_das.assert_not_called()
        mock_equip.assert_not_called()
        mock_wiring.assert_not_called()
        mock_chan.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path -- response shape and warnings
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_returns_channel_id_rows_and_warnings(self, client, mock_conn):
        with _patch_tagless_resolved(channel_id=42, rows=1):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        body = resp.json()
        assert body["channel_id"] == 42
        assert body["rows_written"] == 1
        assert "warnings" in body

    def test_no_warnings_when_all_exist(self, client, mock_conn):
        with _patch_tagless_resolved(
            das_created=False, equip_created=False, si_created=False
        ):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        assert resp.json()["warnings"] == []

    def test_warning_when_das_auto_created(self, client, mock_conn):
        with _patch_tagless_resolved(
            das_created=True, equip_created=False, si_created=False
        ):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        warnings = resp.json()["warnings"]
        assert len(warnings) == 1
        assert "DirectStation" in warnings[0]

    def test_warning_when_equipment_auto_created(self, client, mock_conn):
        with _patch_tagless_resolved(
            das_created=False, equip_created=True, si_created=False
        ):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        warnings = resp.json()["warnings"]
        assert len(warnings) == 1
        assert "Probe_A" in warnings[0]

    def test_warning_when_signal_interface_auto_created(self, client, mock_conn):
        with _patch_tagless_resolved(
            das_created=False, equip_created=False, si_created=True
        ):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        warnings = resp.json()["warnings"]
        assert len(warnings) == 1
        assert "probe_a/dissolved oxygen" in warnings[0]

    def test_three_warnings_when_all_auto_created(self, client, mock_conn):
        with _patch_tagless_resolved(
            das_created=True, equip_created=True, si_created=True
        ):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        assert len(resp.json()["warnings"]) == 3

    def test_equipment_wiring_opened_on_new_interface(self, client, mock_conn):
        """open_equipment_wiring_history must be called when no active wiring exists."""
        with (
            patch(f"{_REPO}.find_parameter_by_name", return_value=5),
            patch(f"{_REPO}.find_unit_by_name", return_value=2),
            patch(f"{_REPO}.find_or_create_das", return_value=(10, False)),
            patch(
                f"{_REPO}.find_or_create_equipment_by_identifier",
                return_value=(20, False),
            ),
            patch(f"{_REPO}.find_active_equipment_wiring", return_value=None),
                patch(f"{_REPO}.generate_tagless_tagname", return_value="probe_a/do"),
            patch(f"{_REPO}.find_or_create_signal_interface", return_value=(30, True)),
            patch(f"{_REPO}.open_equipment_wiring_history") as mock_history,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata", return_value=42),
            patch(f"{_VAL_REPO}.insert_scalar_values", return_value=1),
        ):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        # wiring is backdated to the batch's earliest observation timestamp
        mock_history.assert_called_once_with(
            mock_conn, 20, 30, None, valid_from=datetime(2024, 1, 1, 0, 0, 0)
        )

    def test_equipment_wiring_not_opened_on_existing_wiring(self, client, mock_conn):
        """open_equipment_wiring_history must NOT be called when active wiring already exists."""
        with (
            patch(f"{_REPO}.find_parameter_by_name", return_value=5),
            patch(f"{_REPO}.find_unit_by_name", return_value=2),
            patch(f"{_REPO}.find_or_create_das", return_value=(10, False)),
            patch(
                f"{_REPO}.find_or_create_equipment_by_identifier",
                return_value=(20, False),
            ),
            patch(f"{_REPO}.find_active_equipment_wiring", return_value=(30, None)),
            patch(f"{_REPO}.generate_tagless_tagname", return_value="probe_a/do"),
            patch(f"{_REPO}.open_equipment_wiring_history") as mock_history,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata", return_value=42),
            patch(f"{_VAL_REPO}.insert_scalar_values", return_value=1),
        ):
            resp = client.post("/api/v1/ingest/sensor-tagless", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        mock_history.assert_not_called()
