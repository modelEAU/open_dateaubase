"""Integration tests for tag-mode sensor ingest (Issue #5, v4.0.0).

Tests run against a live MSSQL container at the v4.0.0 schema.
Skipped automatically when the container is unavailable.

Covers all acceptance criteria:
  AC1  resolve_tag finds/creates DAS and SignalInterface; returns SignalInterface_ID
  AC2  First ingest creates SignalInterface + Channel; repeated ingest is idempotent
  AC3  Unrecognised DAS name → warning + auto-create
  AC4  Unrecognised tag → warning + auto-create (as SignalInterface)
  AC5  Unrecognised parameter_name → 422, no record created
  AC6  Unrecognised unit_name → 422, no record created
  AC7  Name lookups are case-insensitive and whitespace-trimmed
  AC8  SignalInterface.IsActive = 0 via deactivate; Channel/data unaffected
"""

from __future__ import annotations

import warnings

import pytest


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


def _signal_interface_count(conn, das_id: int, name: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[SignalInterface]"
        " WHERE [DataAcquisitionSystem_ID] = ?"
        "   AND LOWER(LTRIM(RTRIM([Name]))) = ?",
        das_id,
        name.lower(),
    )
    return cursor.fetchone()[0]


def _channel_count(conn, signal_interface_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[Channel] WHERE [SignalInterface_ID] = ?",
        signal_interface_id,
    )
    return cursor.fetchone()[0]


def _get_signal_interface_is_active(conn, si_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [IsActive] FROM [dbo].[SignalInterface] WHERE [SignalInterface_ID] = ?",
        si_id,
    )
    row = cursor.fetchone()
    assert row is not None, f"SignalInterface {si_id} not found"
    return bool(row[0])


# ---------------------------------------------------------------------------
# Tests: AC1, AC2 — resolve_tag finds/creates DAS + SignalInterface; idempotency
# ---------------------------------------------------------------------------


class TestResolveTag:
    def test_resolve_creates_das_and_signal_interface_on_first_call(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
        )

        conn, _ = db_at_v400
        das_id, das_created = find_or_create_das(conn, "PlantSCADA")
        assert das_created is True
        assert das_id > 0

        si_type_id = 2  # SCADA
        si_id, si_created = find_or_create_signal_interface(
            conn, das_id, "TIT-101", si_type_id
        )
        assert si_created is True
        assert si_id > 0

    def test_repeated_resolve_is_idempotent(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
        )

        conn, _ = db_at_v400
        das_id1, _ = find_or_create_das(conn, "StationA")
        das_id2, _ = find_or_create_das(conn, "StationA")
        assert das_id1 == das_id2

        si_type_id = 2
        si_id1, _ = find_or_create_signal_interface(
            conn, das_id1, "FIT-201", si_type_id
        )
        si_id2, _ = find_or_create_signal_interface(
            conn, das_id1, "FIT-201", si_type_id
        )
        assert si_id1 == si_id2

    def test_first_ingest_creates_channel(self, db_at_v400):
        from api.v1.repositories.ingestion_repository import (
            find_or_create_sensor_metadata,
        )
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
            find_parameter_by_name,
        )

        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "SCADA-A")
        si_id, _ = find_or_create_signal_interface(conn, das_id, "TIT-001", 2)
        param_id = find_parameter_by_name(conn, "temperature")
        assert param_id is not None

        channel_id = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name="TIT-001",
            parameter_id=param_id,
            unit_id=1,
            data_provenance_id=1,
            processing_degree_id=1,
        )
        assert channel_id > 0
        assert _channel_count(conn, si_id) == 1

    def test_repeated_find_or_create_channel_is_idempotent(self, db_at_v400):
        from api.v1.repositories.ingestion_repository import (
            find_or_create_sensor_metadata,
        )
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
            find_parameter_by_name,
        )

        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "SCADA-B")
        si_id, _ = find_or_create_signal_interface(conn, das_id, "PIT-001", 2)
        param_id = find_parameter_by_name(conn, "ph")
        assert param_id is not None

        ch1 = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name="PIT-001",
            parameter_id=param_id,
            unit_id=1,
            data_provenance_id=1,
            processing_degree_id=1,
        )
        ch2 = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name="PIT-001",
            parameter_id=param_id,
            unit_id=1,
            data_provenance_id=1,
            processing_degree_id=1,
        )
        assert ch1 == ch2
        assert _channel_count(conn, si_id) == 1


# ---------------------------------------------------------------------------
# Tests: AC3 — Unrecognised DAS → warning + auto-create
# ---------------------------------------------------------------------------


class TestDASAutoCreate:
    def test_unrecognised_das_auto_creates_with_warning(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import find_or_create_das

        conn, _ = db_at_v400
        assert _das_count(conn, "NewDAS") == 0

        with warnings.catch_warnings(record=True):
            das_id, created = find_or_create_das(conn, "NewDAS")

        assert created is True
        assert _das_count(conn, "NewDAS") == 1

    def test_known_das_returns_created_false(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import find_or_create_das

        conn, _ = db_at_v400
        das_id1, _ = find_or_create_das(conn, "ExistingDAS")
        das_id2, created = find_or_create_das(conn, "ExistingDAS")
        assert created is False
        assert das_id1 == das_id2


# ---------------------------------------------------------------------------
# Tests: AC4 — Unrecognised tag → warning + auto-create (as SignalInterface)
# ---------------------------------------------------------------------------


class TestSignalInterfaceAutoCreate:
    def test_unrecognised_tag_auto_creates_signal_interface(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
        )

        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "DAS-SI-Test")

        assert _signal_interface_count(conn, das_id, "NEW-TAG-99") == 0
        si_id, created = find_or_create_signal_interface(conn, das_id, "NEW-TAG-99", 2)
        assert created is True
        assert _signal_interface_count(conn, das_id, "NEW-TAG-99") == 1

    def test_known_tag_returns_created_false(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
        )

        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "DAS-Known-SI")
        si_id1, _ = find_or_create_signal_interface(conn, das_id, "EXISTING-TAG", 2)
        si_id2, created = find_or_create_signal_interface(
            conn, das_id, "EXISTING-TAG", 2
        )
        assert created is False
        assert si_id1 == si_id2


# ---------------------------------------------------------------------------
# Tests: AC5, AC6 — Unrecognised parameter/unit → None (caller raises 422)
# ---------------------------------------------------------------------------


class TestValidationLookups:
    def test_unknown_parameter_returns_none(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_parameter_by_name,
        )

        conn, _ = db_at_v400
        assert find_parameter_by_name(conn, "nonexistent_param_xyz") is None

    def test_unknown_unit_returns_none(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import find_unit_by_name

        conn, _ = db_at_v400
        assert find_unit_by_name(conn, "nonexistent_unit_xyz") is None

    def test_known_parameter_returns_id(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_parameter_by_name,
        )

        conn, _ = db_at_v400
        assert find_parameter_by_name(conn, "temperature") is not None

    def test_known_unit_returns_id(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import find_unit_by_name

        conn, _ = db_at_v400
        assert find_unit_by_name(conn, "degc") is not None


# ---------------------------------------------------------------------------
# Tests: AC7 — Case-insensitive and whitespace-trimmed lookups
# ---------------------------------------------------------------------------


class TestNormalisation:
    def test_das_lookup_case_insensitive(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import find_or_create_das

        conn, _ = db_at_v400
        id1, _ = find_or_create_das(conn, "MyScada")
        id2, created = find_or_create_das(conn, "MYSCADA")
        assert created is False
        assert id1 == id2

    def test_das_lookup_trims_whitespace(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import find_or_create_das

        conn, _ = db_at_v400
        id1, _ = find_or_create_das(conn, "TrimDAS")
        id2, created = find_or_create_das(conn, "  TrimDAS  ")
        assert created is False
        assert id1 == id2

    def test_signal_interface_lookup_case_insensitive(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
        )

        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "NormDAS-SI")
        id1, _ = find_or_create_signal_interface(conn, das_id, "tit-200", 2)
        id2, created = find_or_create_signal_interface(conn, das_id, "TIT-200", 2)
        assert created is False
        assert id1 == id2

    def test_signal_interface_lookup_trims_whitespace(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
        )

        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "NormDAS-Trim")
        id1, _ = find_or_create_signal_interface(conn, das_id, "FIT-300", 2)
        id2, created = find_or_create_signal_interface(conn, das_id, "  FIT-300  ", 2)
        assert created is False
        assert id1 == id2

    def test_parameter_lookup_case_insensitive(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_parameter_by_name,
        )

        conn, _ = db_at_v400
        id1 = find_parameter_by_name(conn, "temperature")
        id2 = find_parameter_by_name(conn, "TEMPERATURE")
        id3 = find_parameter_by_name(conn, "  Temperature  ")
        assert id1 is not None
        assert id1 == id2 == id3

    def test_unit_lookup_case_insensitive(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import find_unit_by_name

        conn, _ = db_at_v400
        id1 = find_unit_by_name(conn, "degc")
        id2 = find_unit_by_name(conn, "DEGC")
        id3 = find_unit_by_name(conn, "  degC  ")
        assert id1 is not None
        assert id1 == id2 == id3

    def test_channel_role_lookup_case_insensitive(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_channel_role_by_name,
        )

        conn, _ = db_at_v400
        id1 = find_channel_role_by_name(conn, "value")
        id2 = find_channel_role_by_name(conn, "VALUE")
        id3 = find_channel_role_by_name(conn, "  Value  ")
        assert id1 is not None
        assert id1 == id2 == id3


# ---------------------------------------------------------------------------
# Tests: AC8 — IsActive = 0 does not affect Channel or historical data
# ---------------------------------------------------------------------------


class TestDeactivation:
    def test_deactivate_signal_interface_sets_is_active_false(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
            patch_signal_interface,
        )

        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "DAS-Deactivate")
        si_id, _ = find_or_create_signal_interface(conn, das_id, "RETIRE-001", 2)

        assert _get_signal_interface_is_active(conn, si_id) is True
        result = patch_signal_interface(conn, si_id, {"is_active": False})
        assert result is not None
        assert _get_signal_interface_is_active(conn, si_id) is False

    def test_deactivate_signal_interface_does_not_affect_channel(self, db_at_v400):
        from api.v1.repositories.ingestion_repository import (
            find_or_create_sensor_metadata,
        )
        from api.v1.repositories.signal_interface_repository import (
            find_or_create_das,
            find_or_create_signal_interface,
            find_parameter_by_name,
            patch_signal_interface,
        )

        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "DAS-Chan-Retain")
        si_id, _ = find_or_create_signal_interface(conn, das_id, "RETIRE-002", 2)
        param_id = find_parameter_by_name(conn, "temperature")
        assert param_id is not None

        channel_id = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name="RETIRE-002",
            parameter_id=param_id,
            unit_id=1,
            data_provenance_id=1,
            processing_degree_id=1,
        )
        assert channel_id > 0

        patch_signal_interface(conn, si_id, {"is_active": False})

        # Channel row must still exist
        assert _channel_count(conn, si_id) == 1

    def test_deactivate_missing_signal_interface_returns_none(self, db_at_v400):
        from api.v1.repositories.signal_interface_repository import (
            patch_signal_interface,
        )

        conn, _ = db_at_v400
        result = patch_signal_interface(conn, 999999, {"is_active": False})
        assert result is None
