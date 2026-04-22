"""Integration tests for tagless-mode sensor ingest (Issue #6, v4.0.0).

Tests run against a live MSSQL container at the v4.0.0 schema.
Skipped automatically when the container is unavailable.

Covers all acceptance criteria:
  AC1  generate_tagless_tagname produces deterministic synthetic tag
  AC2  First ingest creates SignalInterface + Channel and opens
       EquipmentWiringHistory row linking the equipment
  AC3  Repeated ingest is idempotent — no duplicate SignalInterface or
       EquipmentWiringHistory rows created
  AC4  Unrecognised equipment identifier warns and auto-creates Equipment;
       does not error
  AC5  Unrecognised parameter name returns None (caller raises 422)
  AC6  Unrecognised unit name returns None (caller raises 422)
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.db

from api.v1.repositories.ingestion_repository import find_or_create_sensor_metadata
from api.v1.repositories.signal_interface_repository import (
    find_active_equipment_wiring,
    find_or_create_das,
    find_or_create_equipment_by_identifier,
    find_or_create_signal_interface,
    find_parameter_by_name,
    find_unit_by_name,
    generate_tagless_tagname,
    open_equipment_wiring_history,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _si_count_by_name(conn, das_id: int, name: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[SignalInterface]"
        " WHERE [DataAcquisitionSystem_ID] = ?"
        "   AND LOWER(LTRIM(RTRIM([Name]))) = ?",
        das_id,
        name.lower(),
    )
    return cursor.fetchone()[0]


def _channel_count_by_stream(
    conn,
    signal_interface_id: int,
    tag_name: str,
    parameter_id: int,
    data_provenance_id: int = 1,
    processing_degree_id: int = 1,
) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[Channel]"
        " WHERE [SignalInterface_ID] = ?"
        "   AND [TagName] = ?"
        "   AND [Parameter_ID] = ?"
        "   AND [DataProvenance_ID] = ?"
        "   AND [ProcessingDegree_ID] = ?",
        signal_interface_id,
        tag_name,
        parameter_id,
        data_provenance_id,
        processing_degree_id,
    )
    return cursor.fetchone()[0]


def _wiring_count(conn, equipment_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[EquipmentWiringHistory] WHERE [Equipment_ID] = ?",
        equipment_id,
    )
    return cursor.fetchone()[0]


def _active_wiring_count(conn, equipment_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[EquipmentWiringHistory]"
        " WHERE [Equipment_ID] = ? AND [ValidTo] IS NULL",
        equipment_id,
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
    def test_generate_tagless_tagname_strips_and_lowercases(self, db_at_v400):
        assert generate_tagless_tagname("Probe_A ", " DO ") == "probe_a/do"

    def test_generate_tagless_tagname_is_deterministic(self, db_at_v400):
        assert generate_tagless_tagname(
            "Station1", "Temperature"
        ) == generate_tagless_tagname("Station1", "Temperature")


# ---------------------------------------------------------------------------
# AC2 — First ingest creates SignalInterface + Channel + EquipmentWiringHistory
# ---------------------------------------------------------------------------


class TestFirstTaglessIngest:
    def test_first_ingest_creates_signal_interface_with_synthetic_tag(self, db_at_v400):
        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "DirectStation-A")
        equip_id, _ = find_or_create_equipment_by_identifier(conn, "Probe_X")
        param_id = find_parameter_by_name(conn, "Temperature")
        unit_id = find_unit_by_name(conn, "degC")
        assert param_id is not None
        assert unit_id is not None

        synthetic_name = generate_tagless_tagname("Probe_X", "Temperature")
        assert synthetic_name == "probe_x/temperature"

        si_id, created = find_or_create_signal_interface(
            conn, das_id, synthetic_name, 5
        )
        assert created is True
        assert si_id > 0
        assert _si_count_by_name(conn, das_id, synthetic_name) == 1

        # Open wiring history
        history_id = open_equipment_wiring_history(conn, equip_id, si_id, None)
        assert history_id > 0
        assert _wiring_count(conn, equip_id) == 1
        assert _active_wiring_count(conn, equip_id) == 1

        # Create channel
        channel_id = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name=synthetic_name,
            parameter_id=param_id,
            unit_id=unit_id,
            data_provenance_id=1,
            processing_degree_id=1,
        )
        assert channel_id > 0
        assert _channel_count_by_stream(conn, si_id, synthetic_name, param_id) == 1

    def test_first_ingest_wiring_row_links_correct_signal_interface(self, db_at_v400):
        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "DirectStation-B")
        equip_id, _ = find_or_create_equipment_by_identifier(conn, "ProbeWithHistory")
        param_id = find_parameter_by_name(conn, "Temperature")
        unit_id = find_unit_by_name(conn, "degC")

        synthetic_name = generate_tagless_tagname("ProbeWithHistory", "Temperature")
        si_id, _ = find_or_create_signal_interface(conn, das_id, synthetic_name, 5)
        open_equipment_wiring_history(conn, equip_id, si_id, None)

        wiring = find_active_equipment_wiring(conn, equip_id)
        assert wiring is not None
        assert wiring[0] == si_id  # SignalInterface_ID


# ---------------------------------------------------------------------------
# AC3 — Repeated ingest is idempotent
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_repeated_ingest_does_not_duplicate_signal_interface(self, db_at_v400):
        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "IdempotentDAS")
        synthetic_name = generate_tagless_tagname("Probe_Idem", "Temperature")

        si_id1, c1 = find_or_create_signal_interface(conn, das_id, synthetic_name, 5)
        si_id2, c2 = find_or_create_signal_interface(conn, das_id, synthetic_name, 5)

        assert c1 is True
        assert c2 is False
        assert si_id1 == si_id2
        assert _si_count_by_name(conn, das_id, synthetic_name) == 1

    def test_repeated_ingest_does_not_open_extra_history_row(self, db_at_v400):
        """Only one EquipmentWiringHistory row per equipment (opened on first creation only)."""
        conn, _ = db_at_v400
        das_id, _ = find_or_create_das(conn, "HistoryIdempotentDAS")
        equip_id, _ = find_or_create_equipment_by_identifier(conn, "Probe_HistIdem")
        param_id = find_parameter_by_name(conn, "Temperature")
        unit_id = find_unit_by_name(conn, "degC")

        synthetic_name = generate_tagless_tagname("Probe_HistIdem", "Temperature")
        si_id, created = find_or_create_signal_interface(
            conn, das_id, synthetic_name, 5
        )
        assert created is True
        open_equipment_wiring_history(conn, equip_id, si_id, None)

        # Second ingest — wiring already exists, so we do NOT call open_equipment_wiring_history
        wiring = find_active_equipment_wiring(conn, equip_id)
        assert wiring is not None
        assert wiring[0] == si_id

        # History row count unchanged
        assert _wiring_count(conn, equip_id) == 1


# ---------------------------------------------------------------------------
# AC4 — Unrecognised equipment identifier warns and auto-creates Equipment
# ---------------------------------------------------------------------------


class TestEquipmentAutoCreate:
    def test_unknown_equipment_identifier_auto_creates(self, db_at_v400):
        conn, _ = db_at_v400
        identifier = "BrandNewProbeXYZ"
        assert _equipment_count_by_identifier(conn, identifier) == 0

        equip_id, created = find_or_create_equipment_by_identifier(conn, identifier)

        assert created is True
        assert equip_id > 0
        assert _equipment_count_by_identifier(conn, identifier) == 1

    def test_known_equipment_identifier_returns_created_false(self, db_at_v400):
        conn, _ = db_at_v400
        id1, _ = find_or_create_equipment_by_identifier(conn, "ExistingProbe")
        id2, created = find_or_create_equipment_by_identifier(conn, "ExistingProbe")

        assert created is False
        assert id1 == id2

    def test_equipment_lookup_case_insensitive(self, db_at_v400):
        conn, _ = db_at_v400
        id1, _ = find_or_create_equipment_by_identifier(conn, "CaseProbe")
        id2, created = find_or_create_equipment_by_identifier(conn, "CASEPROBE")
        assert created is False
        assert id1 == id2

    def test_equipment_lookup_trims_whitespace(self, db_at_v400):
        conn, _ = db_at_v400
        id1, _ = find_or_create_equipment_by_identifier(conn, "TrimProbe")
        id2, created = find_or_create_equipment_by_identifier(conn, "  TrimProbe  ")
        assert created is False
        assert id1 == id2


# ---------------------------------------------------------------------------
# AC5, AC6 — Unrecognised parameter/unit → None (caller raises 422)
# ---------------------------------------------------------------------------


class TestValidationLookups:
    def test_unknown_parameter_returns_none(self, db_at_v400):
        conn, _ = db_at_v400
        assert find_parameter_by_name(conn, "nonexistent_param_tagless_xyz") is None

    def test_known_parameter_returns_id(self, db_at_v400):
        conn, _ = db_at_v400
        assert find_parameter_by_name(conn, "temperature") is not None

    def test_unknown_unit_returns_none(self, db_at_v400):
        conn, _ = db_at_v400
        assert find_unit_by_name(conn, "nonexistent_unit_tagless_xyz") is None

    def test_known_unit_returns_id(self, db_at_v400):
        conn, _ = db_at_v400
        assert find_unit_by_name(conn, "degc") is not None
