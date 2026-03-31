"""Integration tests for tagless-mode signal ingest (Issue #6).

Tests run against a live MSSQL container at the v3.0.0 schema.
Skipped automatically when the container is unavailable.

Covers all acceptance criteria:
  AC1  resolve_tagless generates deterministic synthetic tag
  AC2  First ingest creates SignalPort with auto-generated tag and opens
       SignalPortEquipmentHistory row linking the equipment
  AC3  Repeated ingest is idempotent — no duplicate SignalPort or
       SignalPortEquipmentHistory rows created
  AC4  Unrecognised equipment identifier warns and auto-creates Equipment;
       does not error
  AC5  Unrecognised parameter name returns None (caller raises 422)
"""

from __future__ import annotations

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
    """Database at v3.0.0 schema with minimal seed data for tagless ingest tests."""
    conn, db_name = fresh_db

    run_sql_file(conn, MIGRATIONS_DIR / "v1.0.0_create_mssql.sql")
    run_sql_file(conn, MIGRATIONS_DIR / "v1.0.0_to_v3.0.0_mssql.sql")

    cursor = conn.cursor()
    cursor.execute("INSERT INTO [dbo].[Parameter] ([Parameter]) VALUES (?)", "Dissolved Oxygen")
    cursor.execute("INSERT INTO [dbo].[Unit] ([Unit]) VALUES (?)", "mg/L")
    conn.commit()

    yield conn, db_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _port_count_by_tag(conn, das_id: int, tag: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[SignalPort]"
        " WHERE [DataAcquisitionSystem_ID] = ?"
        "   AND LOWER(LTRIM(RTRIM([Tag]))) = ?",
        das_id,
        tag.lower(),
    )
    return cursor.fetchone()[0]


def _history_count(conn, signal_port_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[SignalPortEquipmentHistory]"
        " WHERE [SignalPort_ID] = ?",
        signal_port_id,
    )
    return cursor.fetchone()[0]


def _active_history_count(conn, signal_port_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[SignalPortEquipmentHistory]"
        " WHERE [SignalPort_ID] = ? AND [EndTime] IS NULL",
        signal_port_id,
    )
    return cursor.fetchone()[0]


def _equipment_count_by_identifier(conn, identifier: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[Equipment]"
        " WHERE LOWER(LTRIM(RTRIM([Identifier]))) = ?",
        identifier.strip().lower(),
    )
    return cursor.fetchone()[0]


# ---------------------------------------------------------------------------
# AC1 — Deterministic synthetic tag generation
# ---------------------------------------------------------------------------


class TestTagGeneration:
    def test_generate_tagless_tag_strips_and_lowercases(self):
        from api.v1.repositories.signal_port_repository import generate_tagless_tag

        assert generate_tagless_tag("Probe_A ", " DO ") == "probe_a/do"

    def test_generate_tagless_tag_is_deterministic(self):
        from api.v1.repositories.signal_port_repository import generate_tagless_tag

        assert generate_tagless_tag("Station1", "Temperature") == generate_tagless_tag(
            "Station1", "Temperature"
        )


# ---------------------------------------------------------------------------
# AC2 — First ingest creates SignalPort + SignalPortEquipmentHistory
# ---------------------------------------------------------------------------


class TestFirstTaglessIngest:
    def test_first_ingest_creates_port_with_synthetic_tag(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_equipment_by_identifier,
            find_or_create_signal_port,
            find_signal_port_type_by_name,
            generate_tagless_tag,
            open_port_equipment_history,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "DirectStation-A")
        equip_id, _ = find_or_create_equipment_by_identifier(conn, "Probe_X")
        spt_id = find_signal_port_type_by_name(conn, "value")
        assert spt_id is not None

        tag = generate_tagless_tag("Probe_X", "Dissolved Oxygen")
        assert tag == "probe_x/dissolved oxygen"

        port_id, created = find_or_create_signal_port(conn, das_id, tag, spt_id)
        assert created is True
        assert port_id > 0
        assert _port_count_by_tag(conn, das_id, tag) == 1

        # Open equipment history
        history_id = open_port_equipment_history(conn, port_id, equip_id)
        assert history_id > 0
        assert _history_count(conn, port_id) == 1
        assert _active_history_count(conn, port_id) == 1

    def test_first_ingest_history_row_links_correct_equipment(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_equipment_by_identifier,
            find_or_create_signal_port,
            find_signal_port_type_by_name,
            generate_tagless_tag,
            open_port_equipment_history,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "DirectStation-B")
        equip_id, _ = find_or_create_equipment_by_identifier(conn, "ProbeWithHistory")
        spt_id = find_signal_port_type_by_name(conn, "value")
        tag = generate_tagless_tag("ProbeWithHistory", "Dissolved Oxygen")
        port_id, _ = find_or_create_signal_port(conn, das_id, tag, spt_id)
        open_port_equipment_history(conn, port_id, equip_id)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Equipment_ID] FROM [dbo].[SignalPortEquipmentHistory]"
            " WHERE [SignalPort_ID] = ? AND [EndTime] IS NULL",
            port_id,
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == equip_id


# ---------------------------------------------------------------------------
# AC3 — Repeated ingest is idempotent
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_repeated_ingest_does_not_duplicate_port(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_signal_port,
            find_signal_port_type_by_name,
            generate_tagless_tag,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "IdempotentDAS")
        spt_id = find_signal_port_type_by_name(conn, "value")
        tag = generate_tagless_tag("Probe_Idem", "Dissolved Oxygen")

        port_id1, c1 = find_or_create_signal_port(conn, das_id, tag, spt_id)
        port_id2, c2 = find_or_create_signal_port(conn, das_id, tag, spt_id)

        assert c1 is True
        assert c2 is False
        assert port_id1 == port_id2
        assert _port_count_by_tag(conn, das_id, tag) == 1

    def test_repeated_ingest_does_not_open_extra_history_row(self, db_at_v300):
        """Only one SignalPortEquipmentHistory row per port (opened on first creation only)."""
        from api.v1.repositories.signal_port_repository import (
            find_or_create_das,
            find_or_create_equipment_by_identifier,
            find_or_create_signal_port,
            find_signal_port_type_by_name,
            generate_tagless_tag,
            open_port_equipment_history,
        )

        conn, _ = db_at_v300
        das_id, _ = find_or_create_das(conn, "HistoryIdempotentDAS")
        equip_id, _ = find_or_create_equipment_by_identifier(conn, "Probe_HistIdem")
        spt_id = find_signal_port_type_by_name(conn, "value")
        tag = generate_tagless_tag("Probe_HistIdem", "Dissolved Oxygen")

        port_id, created = find_or_create_signal_port(conn, das_id, tag, spt_id)
        assert created is True
        open_port_equipment_history(conn, port_id, equip_id)

        # Second ingest — port already exists, so we do NOT call open_port_equipment_history
        _, created2 = find_or_create_signal_port(conn, das_id, tag, spt_id)
        assert created2 is False
        # History row count unchanged
        assert _history_count(conn, port_id) == 1


# ---------------------------------------------------------------------------
# AC4 — Unrecognised equipment identifier warns and auto-creates Equipment
# ---------------------------------------------------------------------------


class TestEquipmentAutoCreate:
    def test_unknown_equipment_identifier_auto_creates(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_equipment_by_identifier,
        )

        conn, _ = db_at_v300
        identifier = "BrandNewProbeXYZ"
        assert _equipment_count_by_identifier(conn, identifier) == 0

        equip_id, created = find_or_create_equipment_by_identifier(conn, identifier)

        assert created is True
        assert equip_id > 0
        assert _equipment_count_by_identifier(conn, identifier) == 1

    def test_known_equipment_identifier_returns_created_false(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_equipment_by_identifier,
        )

        conn, _ = db_at_v300
        id1, _ = find_or_create_equipment_by_identifier(conn, "ExistingProbe")
        id2, created = find_or_create_equipment_by_identifier(conn, "ExistingProbe")

        assert created is False
        assert id1 == id2

    def test_equipment_lookup_case_insensitive(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_equipment_by_identifier,
        )

        conn, _ = db_at_v300
        id1, _ = find_or_create_equipment_by_identifier(conn, "CaseProbe")
        id2, created = find_or_create_equipment_by_identifier(conn, "CASEPROBE")
        assert created is False
        assert id1 == id2

    def test_equipment_lookup_trims_whitespace(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import (
            find_or_create_equipment_by_identifier,
        )

        conn, _ = db_at_v300
        id1, _ = find_or_create_equipment_by_identifier(conn, "TrimProbe")
        id2, created = find_or_create_equipment_by_identifier(conn, "  TrimProbe  ")
        assert created is False
        assert id1 == id2


# ---------------------------------------------------------------------------
# AC5 — Unrecognised parameter name returns None (caller raises 422)
# ---------------------------------------------------------------------------


class TestValidationLookups:
    def test_unknown_parameter_returns_none(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_parameter_by_name

        conn, _ = db_at_v300
        assert find_parameter_by_name(conn, "nonexistent_param_tagless_xyz") is None

    def test_known_parameter_returns_id(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_parameter_by_name

        conn, _ = db_at_v300
        assert find_parameter_by_name(conn, "dissolved oxygen") is not None

    def test_unknown_unit_returns_none(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_unit_by_name

        conn, _ = db_at_v300
        assert find_unit_by_name(conn, "nonexistent_unit_tagless_xyz") is None

    def test_known_unit_returns_id(self, db_at_v300):
        from api.v1.repositories.signal_port_repository import find_unit_by_name

        conn, _ = db_at_v300
        assert find_unit_by_name(conn, "mg/l") is not None
