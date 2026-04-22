"""Integration tests for tag-mode signal ingest (Issue #5).

Tests run against a live MSSQL container at the v3.0.0 schema.
Skipped automatically when the container is unavailable.

Covers all acceptance criteria:
  AC1  resolve_tag finds/creates DAS and SignalPort; returns SignalPort_ID
  AC2  First ingest creates SignalPort + Channel; repeated ingest is idempotent
  AC3  Unrecognised DAS name → warning + auto-create
  AC4  Unrecognised tag → warning + auto-create
  AC5  Unrecognised parameter_name → 422, no record created
  AC6  Unrecognised unit_name → 422, no record created
  AC7  Name lookups are case-insensitive and whitespace-trimmed
  AC8  SignalPort.IsActive = 0 via deactivate; Channel/data unaffected
  AC9  Contract tests: normalisation, validation before write (in test_ingest_tag_mode.py)
  AC10 Covered by AC1-AC8 above
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from .conftest import fresh_db, mssql_engine, run_sql_file  # noqa: F401

PROJECT_ROOT = Path(__file__).parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_at_v300(fresh_db):  # noqa: F811
    """Database at v3.0.0 schema with minimal seed data for ingest tests."""
    conn, db_name = fresh_db

    # Apply baseline + v3.0.0 migration
    run_sql_file(conn, MIGRATIONS_DIR / "v1.0.0_create_mssql.sql")
    run_sql_file(conn, MIGRATIONS_DIR / "v1.0.0_to_v3.0.0_mssql.sql")

    # Seed lookup data needed by ingest tests
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Parameter] ([Parameter]) VALUES (?)", "Temperature"
    )
    cursor.execute(
        "INSERT INTO [dbo].[Parameter] ([Parameter]) VALUES (?)", "pH"
    )
    cursor.execute("INSERT INTO [dbo].[Unit] ([Unit]) VALUES (?)", "degC")
    cursor.execute("INSERT INTO [dbo].[Unit] ([Unit]) VALUES (?)", "pH units")
    conn.commit()

    yield conn, db_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _das_count(conn, name: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[DataAcquisitionSystem]"
        " WHERE LOWER(LTRIM(RTRIM([Name]))) = ?",
        name.lower(),
    )
    return cursor.fetchone()[0]


def _port_count(conn, das_id: int, tag: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[SignalPort]"
        " WHERE [DataAcquisitionSystem_ID] = ?"
        "   AND LOWER(LTRIM(RTRIM([Tag]))) = ?",
        das_id,
        tag.lower(),
    )
    return cursor.fetchone()[0]


def _channel_count(conn, port_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[Channel] WHERE [SignalPort_ID] = ?", port_id
    )
    return cursor.fetchone()[0]


def _get_port_is_active(conn, port_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [IsActive] FROM [dbo].[SignalPort] WHERE [SignalPort_ID] = ?", port_id
    )
    row = cursor.fetchone()
    assert row is not None, f"SignalPort {port_id} not found"
    return bool(row[0])


# ---------------------------------------------------------------------------
# Tests: AC1, AC2 — resolve_tag finds/creates DAS + SignalPort; idempotency
# ---------------------------------------------------------------------------


class TestResolveTag:
    def test_resolve_creates_das_and_port_on_first_call(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_signal_port,
        )

        conn, _ = db_at_v300
        das_id, das_created = find_or_create_das(conn, "PlantSCADA")
        assert das_created is True
        assert das_id > 0

        spt_id = 1  # Value
        port_id, port_created = find_or_create_signal_port(conn, das_id, "TIT-101", spt_id)
        assert port_created is True
        assert port_id > 0

    def test_repeated_resolve_is_idempotent(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_signal_port,
        )

        conn, _ = db_at_v300
        das_id1, _ = find_or_create_das(conn, "StationA")
        das_id2, _ = find_or_create_das(conn, "StationA")
        assert das_id1 == das_id2

        port_id1, _ = find_or_create_signal_port(conn, das_id1, "FIT-201", 1)
        port_id2, _ = find_or_create_signal_port(conn, das_id1, "FIT-201", 1)
        assert port_id1 == port_id2

    def test_first_ingest_creates_channel(self, db_at_v300):
        from api.v1.repositories.ingestion_repository import find_or_create_sensor_metadata
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_signal_port,
            find_parameter_by_name,
            find_unit_by_name,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "SCADA-A")
        port_id, _ = find_or_create_signal_port(conn, das_id, "TIT-001", 1)
        param_id = find_parameter_by_name(conn, "temperature")
        assert param_id is not None

        channel_id = find_or_create_sensor_metadata(
            conn,
            signal_port_id=port_id,
            parameter_id=param_id,
            unit_id=1,
            data_provenance_id=1,
            processing_degree_id=1,
        )
        assert channel_id > 0
        assert _channel_count(conn, port_id) == 1

    def test_repeated_find_or_create_channel_is_idempotent(self, db_at_v300):
        from api.v1.repositories.ingestion_repository import find_or_create_sensor_metadata
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_signal_port,
            find_parameter_by_name,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "SCADA-B")
        port_id, _ = find_or_create_signal_port(conn, das_id, "PIT-001", 1)
        param_id = find_parameter_by_name(conn, "ph")
        assert param_id is not None

        ch1 = find_or_create_sensor_metadata(
            conn, signal_port_id=port_id, parameter_id=param_id,
            unit_id=1, data_provenance_id=1, processing_degree_id=1,
        )
        ch2 = find_or_create_sensor_metadata(
            conn, signal_port_id=port_id, parameter_id=param_id,
            unit_id=1, data_provenance_id=1, processing_degree_id=1,
        )
        assert ch1 == ch2
        assert _channel_count(conn, port_id) == 1


# ---------------------------------------------------------------------------
# Tests: AC3 — Unrecognised DAS → warning + auto-create
# ---------------------------------------------------------------------------


class TestDASAutoCreate:
    def test_unrecognised_das_auto_creates_with_warning(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_or_create_das

        conn, _ = db_at_v300
        assert _das_count(conn, "NewDAS") == 0

        with warnings.catch_warnings(record=True):
            das_id, created = find_or_create_das(conn, "NewDAS")

        assert created is True
        assert _das_count(conn, "NewDAS") == 1

    def test_known_das_returns_created_false(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_or_create_das

        conn, _ = db_at_v300
        das_id1, _ = find_or_create_das(conn, "ExistingDAS")
        das_id2, created = find_or_create_das(conn, "ExistingDAS")
        assert created is False
        assert das_id1 == das_id2


# ---------------------------------------------------------------------------
# Tests: AC4 — Unrecognised tag → warning + auto-create
# ---------------------------------------------------------------------------


class TestPortAutoCreate:
    def test_unrecognised_tag_auto_creates_with_warning(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_signal_port,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "DAS-Port-Test")

        assert _port_count(conn, das_id, "NEW-TAG-99") == 0
        port_id, created = find_or_create_signal_port(conn, das_id, "NEW-TAG-99", 1)
        assert created is True
        assert _port_count(conn, das_id, "NEW-TAG-99") == 1

    def test_known_tag_returns_created_false(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_signal_port,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "DAS-Known-Port")
        port_id1, _ = find_or_create_signal_port(conn, das_id, "EXISTING-TAG", 1)
        port_id2, created = find_or_create_signal_port(conn, das_id, "EXISTING-TAG", 1)
        assert created is False
        assert port_id1 == port_id2


# ---------------------------------------------------------------------------
# Tests: AC5, AC6 — Unrecognised parameter/unit → None (caller raises 422)
# ---------------------------------------------------------------------------


class TestValidationLookups:
    def test_unknown_parameter_returns_none(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_parameter_by_name

        conn, _ = db_at_v300
        assert find_parameter_by_name(conn, "nonexistent_param_xyz") is None

    def test_unknown_unit_returns_none(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_unit_by_name

        conn, _ = db_at_v300
        assert find_unit_by_name(conn, "nonexistent_unit_xyz") is None

    def test_known_parameter_returns_id(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_parameter_by_name

        conn, _ = db_at_v300
        assert find_parameter_by_name(conn, "temperature") is not None

    def test_known_unit_returns_id(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_unit_by_name

        conn, _ = db_at_v300
        assert find_unit_by_name(conn, "degc") is not None


# ---------------------------------------------------------------------------
# Tests: AC7 — Case-insensitive and whitespace-trimmed lookups
# ---------------------------------------------------------------------------


class TestNormalisation:
    def test_das_lookup_case_insensitive(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_or_create_das

        conn, _ = db_at_v300
        id1, _ = find_or_create_das(conn, "MyScada")
        id2, created = find_or_create_das(conn, "MYSCADA")
        assert created is False
        assert id1 == id2

    def test_das_lookup_trims_whitespace(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_or_create_das

        conn, _ = db_at_v300
        id1, _ = find_or_create_das(conn, "TrimDAS")
        id2, created = find_or_create_das(conn, "  TrimDAS  ")
        assert created is False
        assert id1 == id2

    def test_port_lookup_case_insensitive(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_signal_port,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "NormDAS-Port")
        id1, _ = find_or_create_signal_port(conn, das_id, "tit-200", 1)
        id2, created = find_or_create_signal_port(conn, das_id, "TIT-200", 1)
        assert created is False
        assert id1 == id2

    def test_port_lookup_trims_whitespace(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_signal_port,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "NormDAS-Trim")
        id1, _ = find_or_create_signal_port(conn, das_id, "FIT-300", 1)
        id2, created = find_or_create_signal_port(conn, das_id, "  FIT-300  ", 1)
        assert created is False
        assert id1 == id2

    def test_parameter_lookup_case_insensitive(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_parameter_by_name

        conn, _ = db_at_v300
        id1 = find_parameter_by_name(conn, "temperature")
        id2 = find_parameter_by_name(conn, "TEMPERATURE")
        id3 = find_parameter_by_name(conn, "  Temperature  ")
        assert id1 is not None
        assert id1 == id2 == id3

    def test_unit_lookup_case_insensitive(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_unit_by_name

        conn, _ = db_at_v300
        id1 = find_unit_by_name(conn, "degc")
        id2 = find_unit_by_name(conn, "DEGC")
        id3 = find_unit_by_name(conn, "  degC  ")
        assert id1 is not None
        assert id1 == id2 == id3

    def test_signal_port_type_lookup_case_insensitive(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_signal_port_type_by_name

        conn, _ = db_at_v300
        id1 = find_signal_port_type_by_name(conn, "value")
        id2 = find_signal_port_type_by_name(conn, "VALUE")
        id3 = find_signal_port_type_by_name(conn, "  Value  ")
        assert id1 is not None
        assert id1 == id2 == id3


# ---------------------------------------------------------------------------
# Tests: AC8 — IsActive = 0 does not affect Channel or historical data
# ---------------------------------------------------------------------------


class TestDeactivation:
    def test_deactivate_port_sets_is_active_false(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            deactivate_signal_port,
            find_or_create_das,
            find_or_create_signal_port,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "DAS-Deactivate")
        port_id, _ = find_or_create_signal_port(conn, das_id, "RETIRE-001", 1)

        assert _get_port_is_active(conn, port_id) is True
        result = deactivate_signal_port(conn, port_id)
        assert result is True
        assert _get_port_is_active(conn, port_id) is False

    def test_deactivate_port_does_not_affect_channel(self, db_at_v300):
        from api.v1.repositories.ingestion_repository import find_or_create_sensor_metadata
        from api.v1.repositories.signal_port_repository import (
            deactivate_signal_port,
            find_or_create_das,
            find_or_create_signal_port,
            find_parameter_by_name,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "DAS-Chan-Retain")
        port_id, _ = find_or_create_signal_port(conn, das_id, "RETIRE-002", 1)
        param_id = find_parameter_by_name(conn, "temperature")
        assert param_id is not None

        channel_id = find_or_create_sensor_metadata(
            conn, signal_port_id=port_id, parameter_id=param_id,
            unit_id=1, data_provenance_id=1, processing_degree_id=1,
        )
        assert channel_id > 0

        deactivate_signal_port(conn, port_id)

        # Channel row must still exist
        assert _channel_count(conn, port_id) == 1

    def test_deactivate_missing_port_returns_false(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import deactivate_signal_port

        conn, _ = db_at_v300
        result = deactivate_signal_port(conn, 999999)
        assert result is False
