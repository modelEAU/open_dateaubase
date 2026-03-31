"""Integration tests for the temporal history lifecycle (Issue #7).

Tests run against a live MSSQL container at the v3.0.0 schema.
Skipped automatically when the container is unavailable.

Covers all issue #7 acceptance criteria:

  AC-EQ1   Equipment swap leaves Channel_ID and observations unchanged
  AC-EQ2   Point-in-time query at T_before returns old Equipment; T_after returns new one
  AC-EQ3   Opening a second active PortEquipmentHistory row raises a constraint error
  AC-EQ4   Commission sets Equipment.IsActive=1 and records an EquipmentEvent
  AC-EQ5   Decommission sets Equipment.IsActive=0 and records an EquipmentEvent;
             SignalPort and Channel are unaffected
  AC-LO1   Sensor relocation leaves Channel_ID unchanged
  AC-LO2   Point-in-time query at T_before returns old SamplingPoint; T_after returns new one
  AC-LO3   Opening a second active LocationHistory row raises a constraint error
  AC-LO4   Relocation automatically creates an "Equipment Relocation" Annotation on
             every affected Channel
  AC-LO5   start_time must be provided explicitly (endpoint requires it, no default)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import pyodbc

from .conftest import fresh_db, mssql_engine, run_sql_file  # noqa: F401

# Make repository functions importable directly in tests
from api.v1.repositories import (
    temporal_history_repository,
    annotation_repository,
    equipment_repository as equip_repo,
    signal_port_repository,
    ingestion_repository,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"

# AnnotationType_ID for Equipment Relocation (seeded in migration as ID 11)
ANNOTATION_TYPE_EQUIPMENT_RELOCATION = 11


# ---------------------------------------------------------------------------
# Fixture: v3.0.0 database with minimal seed data
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(fresh_db):  # noqa: F811
    """Database at v3.0.0 with the data needed for lifecycle tests."""
    conn, db_name = fresh_db

    run_sql_file(conn, MIGRATIONS_DIR / "v1.0.0_create_mssql.sql")
    run_sql_file(conn, MIGRATIONS_DIR / "v1.0.0_to_v3.0.0_mssql.sql")

    cursor = conn.cursor()

    # Lookup tables
    cursor.execute("INSERT INTO [dbo].[Parameter] ([Parameter]) VALUES (?)", "Temperature")
    cursor.execute("INSERT INTO [dbo].[Unit] ([Unit]) VALUES (?)", "degC")

    # Two equipment records
    cursor.execute(
        "INSERT INTO [dbo].[Equipment] ([Identifier]) OUTPUT INSERTED.[Equipment_ID]"
        " VALUES (?)", "Probe-A"
    )
    equip_a_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO [dbo].[Equipment] ([Identifier]) OUTPUT INSERTED.[Equipment_ID]"
        " VALUES (?)", "Probe-B"
    )
    equip_b_id = cursor.fetchone()[0]

    # A site and two sampling points
    cursor.execute(
        "INSERT INTO [dbo].[Site] ([Name]) OUTPUT INSERTED.[Site_ID] VALUES (?)",
        "Test Site",
    )
    site_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO [dbo].[SamplingPoint] ([Name], [Site_ID])"
        " OUTPUT INSERTED.[SamplingPoint_ID] VALUES (?, ?)",
        "Inlet", site_id,
    )
    sp_inlet_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO [dbo].[SamplingPoint] ([Name], [Site_ID])"
        " OUTPUT INSERTED.[SamplingPoint_ID] VALUES (?, ?)",
        "Outlet", site_id,
    )
    sp_outlet_id = cursor.fetchone()[0]

    conn.commit()

    yield conn, db_name, {
        "equip_a_id": equip_a_id,
        "equip_b_id": equip_b_id,
        "sp_inlet_id": sp_inlet_id,
        "sp_outlet_id": sp_outlet_id,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_port_and_channel(conn, seed: dict) -> tuple[int, int]:
    """Create a DAS + SignalPort + Channel; return (signal_port_id, channel_id)."""
    das_id, _ = signal_port_repository.find_or_create_das(conn, "TestDAS")
    spt_id = signal_port_repository.find_signal_port_type_by_name(conn, "value")
    port_id, _ = signal_port_repository.find_or_create_signal_port(
        conn, das_id, "TIT-101", spt_id
    )
    param_id = signal_port_repository.find_parameter_by_name(conn, "Temperature")
    unit_id = signal_port_repository.find_unit_by_name(conn, "degC")
    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        signal_port_id=port_id,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=1,
        processing_degree_id=1,
    )
    return port_id, channel_id


def _get_is_active(conn, equip_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [IsActive] FROM [dbo].[Equipment] WHERE [Equipment_ID] = ?", equip_id
    )
    return bool(cursor.fetchone()[0])


def _annotation_count(conn, channel_id: int, annotation_type_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[Annotation]"
        " WHERE [Channel_ID] = ? AND [AnnotationType_ID] = ?",
        channel_id, annotation_type_id,
    )
    return cursor.fetchone()[0]


# ---------------------------------------------------------------------------
# AC-EQ1, AC-EQ2: Equipment swap — Channel_ID unchanged; point-in-time query
# ---------------------------------------------------------------------------


def test_equipment_swap_channel_id_unchanged(db):
    conn, _, seed = db
    port_id, channel_id = _create_port_and_channel(conn, seed)

    t_before = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t_swap = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    t_after = datetime(2024, 9, 1, 9, 0, 0, tzinfo=timezone.utc)

    # Open initial history for Probe-A
    temporal_history_repository.register_equipment_at_port(
        conn, port_id, seed["equip_a_id"],
        start_time=t_before,
    )

    # Swap to Probe-B
    new_id, closed_id = temporal_history_repository.swap_equipment(
        conn, port_id, seed["equip_b_id"], t_swap
    )
    assert new_id is not None
    assert closed_id is not None

    # Channel_ID must not have changed
    cursor = conn.cursor()
    cursor.execute("SELECT [Channel_ID] FROM [dbo].[Channel] WHERE [SignalPort_ID] = ?", port_id)
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == channel_id, "Channel_ID changed after equipment swap!"

    # AC-EQ2: point-in-time — T_before → Probe-A
    eq_before = temporal_history_repository.get_equipment_at_time(conn, port_id, t_before)
    assert eq_before is not None
    assert eq_before["equipment_id"] == seed["equip_a_id"]

    # AC-EQ2: point-in-time — T_after → Probe-B
    eq_after = temporal_history_repository.get_equipment_at_time(conn, port_id, t_after)
    assert eq_after is not None
    assert eq_after["equipment_id"] == seed["equip_b_id"]


# ---------------------------------------------------------------------------
# AC-EQ3: Second active equipment row raises a constraint error
# ---------------------------------------------------------------------------


def test_second_active_equipment_row_raises_constraint_error(db):
    conn, _, seed = db
    port_id, _ = _create_port_and_channel(conn, seed)

    t_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    temporal_history_repository.register_equipment_at_port(
        conn, port_id, seed["equip_a_id"], start_time=t_start
    )

    # Attempting to register a second active row must raise ValueError (app guard)
    with pytest.raises(ValueError, match="already has an active equipment history row"):
        temporal_history_repository.register_equipment_at_port(
            conn, port_id, seed["equip_b_id"], start_time=t_start
        )


# ---------------------------------------------------------------------------
# AC-EQ4: Commission sets IsActive=1 and records an EquipmentEvent
# ---------------------------------------------------------------------------


def test_commission_sets_is_active_and_records_event(db):
    conn, _, seed = db
    equip_id = seed["equip_a_id"]

    # Start decommissioned
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Equipment] SET [IsActive] = 0 WHERE [Equipment_ID] = ?", equip_id
    )
    conn.commit()
    assert not _get_is_active(conn, equip_id)

    result = equip_repo.commission_equipment(conn, equip_id, notes="Commissioning Probe-A")
    assert result["is_active"] is True
    assert result["equipment_id"] == equip_id
    assert isinstance(result["equipment_event_id"], int)

    # Confirm DB state
    assert _get_is_active(conn, equip_id)

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT eet.[EquipmentEventType_Name]
        FROM [dbo].[EquipmentEvent] ee
        JOIN [dbo].[EquipmentEventType] eet ON eet.[EquipmentEventType_ID] = ee.[EquipmentEventType_ID]
        WHERE ee.[EquipmentEvent_ID] = ?
        """,
        result["equipment_event_id"],
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "Commissioning"


# ---------------------------------------------------------------------------
# AC-EQ5: Decommission sets IsActive=0; SignalPort + Channel unaffected
# ---------------------------------------------------------------------------


def test_decommission_sets_is_active_and_channel_unaffected(db):
    conn, _, seed = db
    port_id, channel_id = _create_port_and_channel(conn, seed)
    equip_id = seed["equip_a_id"]

    result = equip_repo.decommission_equipment(conn, equip_id, notes="Retiring Probe-A")
    assert result["is_active"] is False
    assert result["equipment_id"] == equip_id
    assert isinstance(result["equipment_event_id"], int)

    # DB state
    assert not _get_is_active(conn, equip_id)

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT eet.[EquipmentEventType_Name]
        FROM [dbo].[EquipmentEvent] ee
        JOIN [dbo].[EquipmentEventType] eet ON eet.[EquipmentEventType_ID] = ee.[EquipmentEventType_ID]
        WHERE ee.[EquipmentEvent_ID] = ?
        """,
        result["equipment_event_id"],
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "Decommissioning"

    # SignalPort must still be active (IsActive=1)
    cursor.execute(
        "SELECT [IsActive] FROM [dbo].[SignalPort] WHERE [SignalPort_ID] = ?", port_id
    )
    assert bool(cursor.fetchone()[0]) is True

    # Channel must still exist
    cursor.execute("SELECT [Channel_ID] FROM [dbo].[Channel] WHERE [Channel_ID] = ?", channel_id)
    assert cursor.fetchone() is not None


# ---------------------------------------------------------------------------
# AC-LO1, AC-LO2: Sensor relocation — Channel_ID unchanged; point-in-time
# ---------------------------------------------------------------------------


def test_sensor_relocation_channel_id_unchanged(db):
    conn, _, seed = db
    port_id, channel_id = _create_port_and_channel(conn, seed)

    t_install = datetime(2024, 1, 1, tzinfo=timezone.utc)
    t_move = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    t_after = datetime(2024, 9, 1, tzinfo=timezone.utc)

    # Open initial location at Inlet
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[SignalPortLocationHistory]"
        " ([SignalPort_ID], [SamplingPoint_ID], [StartTime])"
        " VALUES (?, ?, ?)",
        port_id, seed["sp_inlet_id"], t_install,
    )
    conn.commit()

    # Relocate to Outlet
    new_id, closed_id, ch_ids = temporal_history_repository.relocate_sensor(
        conn, port_id, seed["sp_outlet_id"], t_move
    )
    assert new_id is not None
    assert closed_id is not None
    assert channel_id in ch_ids

    # Channel_ID must be unchanged
    cursor.execute("SELECT [Channel_ID] FROM [dbo].[Channel] WHERE [Channel_ID] = ?", channel_id)
    assert cursor.fetchone() is not None

    # AC-LO2: point-in-time T_before → Inlet
    loc_before = temporal_history_repository.get_location_at_time(conn, port_id, t_install)
    assert loc_before is not None
    assert loc_before["sampling_point_id"] == seed["sp_inlet_id"]

    # AC-LO2: point-in-time T_after → Outlet
    loc_after = temporal_history_repository.get_location_at_time(conn, port_id, t_after)
    assert loc_after is not None
    assert loc_after["sampling_point_id"] == seed["sp_outlet_id"]


# ---------------------------------------------------------------------------
# AC-LO3: Second active location row raises a constraint error
# ---------------------------------------------------------------------------


def test_second_active_location_row_raises_constraint_error(db):
    conn, _, seed = db
    port_id, _ = _create_port_and_channel(conn, seed)

    t_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[SignalPortLocationHistory]"
        " ([SignalPort_ID], [SamplingPoint_ID], [StartTime])"
        " VALUES (?, ?, ?)",
        port_id, seed["sp_inlet_id"], t_start,
    )
    conn.commit()

    # The DB has a filtered unique index on (SignalPort_ID) WHERE EndTime IS NULL.
    # Attempting a direct INSERT of a second active row must raise IntegrityError.
    with pytest.raises(pyodbc.IntegrityError):
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[SignalPortLocationHistory]"
            " ([SignalPort_ID], [SamplingPoint_ID], [StartTime])"
            " VALUES (?, ?, ?)",
            port_id, seed["sp_outlet_id"], t_start,
        )
        conn.commit()


# ---------------------------------------------------------------------------
# AC-LO4: Relocation auto-creates "Equipment Relocation" Annotation
# ---------------------------------------------------------------------------


def test_relocation_creates_annotation(db):
    conn, _, seed = db
    port_id, channel_id = _create_port_and_channel(conn, seed)

    t_install = datetime(2024, 1, 1, tzinfo=timezone.utc)
    t_move = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[SignalPortLocationHistory]"
        " ([SignalPort_ID], [SamplingPoint_ID], [StartTime])"
        " VALUES (?, ?, ?)",
        port_id, seed["sp_inlet_id"], t_install,
    )
    conn.commit()

    assert _annotation_count(conn, channel_id, ANNOTATION_TYPE_EQUIPMENT_RELOCATION) == 0

    _, _, ch_ids = temporal_history_repository.relocate_sensor(
        conn, port_id, seed["sp_outlet_id"], t_move
    )

    # Auto-annotation must be created for the channel
    assert channel_id in ch_ids
    assert _annotation_count(conn, channel_id, ANNOTATION_TYPE_EQUIPMENT_RELOCATION) == 1

    # Verify annotation content
    from datetime import timedelta as _td
    annots = annotation_repository.get_annotations_for_timeseries(
        conn, channel_id,
        from_dt=t_move - _td(seconds=1),
        to_dt=t_move + _td(seconds=1),
        annotation_type_id=ANNOTATION_TYPE_EQUIPMENT_RELOCATION,
    )
    assert len(annots) == 1
    assert annots[0]["annotation_type_id"] == ANNOTATION_TYPE_EQUIPMENT_RELOCATION
    assert annots[0]["start_time"] == t_move


# ---------------------------------------------------------------------------
# AC-LO5: start_time required on relocation (schema-level validation)
# ---------------------------------------------------------------------------


def test_relocation_start_time_required():
    """The PortRelocateRequest Pydantic model must require start_time."""
    from api.v1.schemas.ports import PortRelocateRequest
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        PortRelocateRequest(sampling_point_id=1)  # missing start_time


# ---------------------------------------------------------------------------
# Late registration: register_equipment_at_port
# ---------------------------------------------------------------------------


def test_late_equipment_registration(db):
    conn, _, seed = db
    port_id, _ = _create_port_and_channel(conn, seed)

    # No active row initially
    active = temporal_history_repository.get_active_equipment_history(conn, port_id)
    assert active is None

    t_start = datetime(2024, 3, 15, 8, 0, tzinfo=timezone.utc)
    history_id = temporal_history_repository.register_equipment_at_port(
        conn, port_id, seed["equip_a_id"], start_time=t_start
    )
    assert isinstance(history_id, int)

    active = temporal_history_repository.get_active_equipment_history(conn, port_id)
    assert active is not None
    assert active["equipment_id"] == seed["equip_a_id"]
    assert active["start_time"] == t_start
    assert active["end_time"] is None
