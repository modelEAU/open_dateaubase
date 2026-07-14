"""Integration tests for the temporal history lifecycle (Issue #7, v4.0.0).

Tests run against a live MSSQL container at the v4.0.0 schema.
Skipped automatically when the container is unavailable.

Covers all issue #7 acceptance criteria:

  AC-EQ1   Equipment swap leaves Channel_ID and observations unchanged
  AC-EQ2   Point-in-time query at T_before returns old Equipment; T_after returns new one
  AC-EQ3   Opening a second active EquipmentWiringHistory row for the same equipment raises
  AC-EQ4   Commission sets Equipment.IsActive=1 and records an EquipmentEvent
  AC-EQ5   Decommission sets Equipment.IsActive=0; SignalInterface and Channel are unaffected
  AC-LO1   Sensor relocation leaves Channel_ID unchanged
  AC-LO2   Point-in-time query at T_before returns old SamplingPoint; T_after returns new one
  AC-LO3   Opening a second active EquipmentLocationHistory row raises a constraint error
  AC-LO5   valid_from must be provided explicitly (endpoint requires it, no default)

AC-LO4 / AC-ANN (a move auto-annotates every affected Channel) were retired by
ADR-0007: a move is a cause, the history rows are its record, and an Annotation
is a verdict on data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import pyodbc

from api.v1.repositories import (
    equipment_repository as equip_repo,
    temporal_history_repository,
)
from api.v1.repositories.ingestion_repository import find_or_create_sensor_metadata
from api.v1.repositories.signal_interface_repository import (
    find_or_create_das,
    find_or_create_signal_interface,
    find_parameter_by_name,
    find_unit_by_name,
)

pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(db_at_v200):
    """Database at v4.0.0 with the data needed for lifecycle tests."""
    conn, db_name = db_at_v200
    cursor = conn.cursor()

    # Two equipment records
    cursor.execute(
        "INSERT INTO [dbo].[Equipment] ([Identifier]) OUTPUT INSERTED.[Equipment_ID] VALUES (?)",
        "Probe-A",
    )
    equip_a_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO [dbo].[Equipment] ([Identifier]) OUTPUT INSERTED.[Equipment_ID] VALUES (?)",
        "Probe-B",
    )
    equip_b_id = cursor.fetchone()[0]

    # A site and two sampling points
    cursor.execute(
        "INSERT INTO [dbo].[Site] ([Name]) OUTPUT INSERTED.[Site_ID] VALUES (?)",
        "Test Site",
    )
    site_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO [dbo].[SamplingPoint] ([SamplingPoint], [Site_ID])"
        " OUTPUT INSERTED.[SamplingPoint_ID] VALUES (?, ?)",
        "Inlet",
        site_id,
    )
    sp_inlet_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO [dbo].[SamplingPoint] ([SamplingPoint], [Site_ID])"
        " OUTPUT INSERTED.[SamplingPoint_ID] VALUES (?, ?)",
        "Outlet",
        site_id,
    )
    sp_outlet_id = cursor.fetchone()[0]

    conn.commit()

    yield (
        conn,
        db_name,
        {
            "equip_a_id": equip_a_id,
            "equip_b_id": equip_b_id,
            "sp_inlet_id": sp_inlet_id,
            "sp_outlet_id": sp_outlet_id,
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_interface_and_channel(
    conn, seed: dict, tag_name: str = "TIT-101"
) -> tuple[int, int]:
    """Create a DAS + SignalInterface + Channel; return (signal_interface_id, channel_id)."""
    das_id, _ = find_or_create_das(conn, "TestDAS")
    si_id, _ = find_or_create_signal_interface(
        conn, das_id, tag_name)  # DirectConnect
    param_id = find_parameter_by_name(conn, "Temperature")
    unit_id = find_unit_by_name(conn, "°C")
    assert param_id is not None
    assert unit_id is not None
    channel_id = find_or_create_sensor_metadata(
        conn,
        signal_interface_id=si_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=1,
        value_kind_id=1,
    )
    return si_id, channel_id


def _insert_observation_and_value(
    conn, channel_id: int, timestamp: datetime, value: float
) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [ValueKind_ID])"
        " OUTPUT INSERTED.[Observation_ID] VALUES (?, ?, 1)",
        channel_id,
        timestamp,
    )
    obs_id = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO [dbo].[Value] ([Observation_ID], [Value]) VALUES (?, ?)",
        obs_id,
        value,
    )
    conn.commit()
    return obs_id


def _get_equipment_for_observation(conn, obs_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT EquipmentID, Resolution FROM [dbo].[vw_ChannelEquipmentAtTime]"
        " WHERE ObservationID = ?",
        obs_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {"equipment_id": row[0], "resolution": row[1]}


def _get_location_for_observation(conn, obs_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SamplingPointID, SamplingPointName FROM [dbo].[vw_ChannelLocationAtTime]"
        " WHERE ObservationID = ?",
        obs_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {"sampling_point_id": row[0], "sampling_point_name": row[1]}


def _get_is_active(conn, equip_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [IsActive] FROM [dbo].[Equipment] WHERE [Equipment_ID] = ?", equip_id
    )
    return bool(cursor.fetchone()[0])




def _open_wiring(
    conn, equipment_id: int, si_id: int, port_id: int | None, valid_from: datetime
):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[EquipmentWiringHistory]"
        "    ([Equipment_ID], [SignalInterface_ID], [SignalInterfacePort_ID], [ValidFrom])"
        " OUTPUT INSERTED.[EquipmentWiringHistory_ID]"
        " VALUES (?, ?, ?, ?)",
        equipment_id,
        si_id,
        port_id,
        valid_from,
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    return new_id


def _close_wiring(conn, equipment_id: int, valid_to: datetime):
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[EquipmentWiringHistory] SET [ValidTo] = ?"
        " WHERE [Equipment_ID] = ? AND [ValidTo] IS NULL",
        valid_to,
        equipment_id,
    )
    conn.commit()


def _open_location(conn, equipment_id: int, sp_id: int, valid_from: datetime):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[EquipmentLocationHistory]"
        "    ([Equipment_ID], [SamplingPoint_ID], [ValidFrom])"
        " OUTPUT INSERTED.[EquipmentLocationHistory_ID]"
        " VALUES (?, ?, ?)",
        equipment_id,
        sp_id,
        valid_from,
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    return new_id


# ---------------------------------------------------------------------------
# AC-EQ1, AC-EQ2: Equipment swap — Channel_ID unchanged; point-in-time query
# ---------------------------------------------------------------------------


def test_equipment_swap_channel_id_unchanged(db):
    conn, _, seed = db
    si_id, channel_id = _create_interface_and_channel(conn, seed)

    t_before = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t_swap = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    t_after = datetime(2024, 9, 1, 9, 0, 0, tzinfo=timezone.utc)

    # Wire Probe-A to the interface
    _open_wiring(conn, seed["equip_a_id"], si_id, None, t_before)

    # Insert observations before and after swap
    obs_before = _insert_observation_and_value(conn, channel_id, t_before, 20.0)
    obs_after = _insert_observation_and_value(conn, channel_id, t_after, 25.0)

    # Swap to Probe-B (close A, open B on same interface)
    _close_wiring(conn, seed["equip_a_id"], t_swap)
    _open_wiring(conn, seed["equip_b_id"], si_id, None, t_swap)

    # Channel_ID must not have changed
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Stream_ID] FROM [dbo].[Channel] WHERE [Stream_ID] = ?", channel_id
    )
    assert cursor.fetchone() is not None

    # AC-EQ2: point-in-time — T_before → Probe-A
    eq_before = _get_equipment_for_observation(conn, obs_before)
    assert eq_before is not None
    assert eq_before["equipment_id"] == seed["equip_a_id"]

    # AC-EQ2: point-in-time — T_after → Probe-B
    eq_after = _get_equipment_for_observation(conn, obs_after)
    assert eq_after is not None
    assert eq_after["equipment_id"] == seed["equip_b_id"]


# ---------------------------------------------------------------------------
# AC-EQ3: Second active equipment row raises a constraint error
# ---------------------------------------------------------------------------


def test_second_active_equipment_row_raises_constraint_error(db):
    conn, _, seed = db
    si_id, _ = _create_interface_and_channel(conn, seed)

    t_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    temporal_history_repository.register_equipment_at_interface(
        conn, seed["equip_a_id"], si_id, None, start_time=t_start
    )

    # Attempting to register a second active row must raise ValueError (app guard)
    with pytest.raises(ValueError, match="already has an active wiring history row"):
        temporal_history_repository.register_equipment_at_interface(
            conn, seed["equip_a_id"], si_id, None, start_time=t_start
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

    result = equip_repo.commission_equipment(
        conn, equip_id, notes="Commissioning Probe-A"
    )
    assert result["is_active"] is True
    assert result["equipment_id"] == equip_id
    assert isinstance(result["equipment_event_id"], int)

    # Confirm DB state
    assert _get_is_active(conn, equip_id)

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT eet.[Name]
        FROM [dbo].[EquipmentEvent] ee
        JOIN [dbo].[EquipmentEventKind] eet ON eet.[EquipmentEventKind_ID] = ee.[EquipmentEventKind_ID]
        WHERE ee.[EquipmentEvent_ID] = ?
        """,
        result["equipment_event_id"],
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "Commissioning"


# ---------------------------------------------------------------------------
# AC-EQ5: Decommission sets IsActive=0; SignalInterface + Channel unaffected
# ---------------------------------------------------------------------------


def test_decommission_sets_is_active_and_channel_unaffected(db):
    conn, _, seed = db
    si_id, channel_id = _create_interface_and_channel(conn, seed)
    equip_id = seed["equip_a_id"]

    # Wire equipment so it has an active association
    temporal_history_repository.register_equipment_at_interface(
        conn,
        equip_id,
        si_id,
        None,
        start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    result = equip_repo.decommission_equipment(conn, equip_id, notes="Retiring Probe-A")
    assert result["is_active"] is False
    assert result["equipment_id"] == equip_id
    assert isinstance(result["equipment_event_id"], int)

    # DB state
    assert not _get_is_active(conn, equip_id)

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT eet.[Name]
        FROM [dbo].[EquipmentEvent] ee
        JOIN [dbo].[EquipmentEventKind] eet ON eet.[EquipmentEventKind_ID] = ee.[EquipmentEventKind_ID]
        WHERE ee.[EquipmentEvent_ID] = ?
        """,
        result["equipment_event_id"],
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "Decommissioning"

    # SignalInterface must still be active (IsActive=1)
    cursor.execute(
        "SELECT [IsActive] FROM [dbo].[SignalInterface] WHERE [SignalInterface_ID] = ?",
        si_id,
    )
    assert bool(cursor.fetchone()[0]) is True

    # Channel must still exist
    cursor.execute(
        "SELECT [Stream_ID] FROM [dbo].[Channel] WHERE [Stream_ID] = ?", channel_id
    )
    assert cursor.fetchone() is not None


# ---------------------------------------------------------------------------
# AC-LO1, AC-LO2: Sensor relocation — Channel_ID unchanged; point-in-time
# ---------------------------------------------------------------------------


def test_sensor_relocation_channel_id_unchanged(db):
    conn, _, seed = db
    si_id, channel_id = _create_interface_and_channel(conn, seed)

    t_install = datetime(2024, 1, 1, tzinfo=timezone.utc)
    t_move = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    t_after = datetime(2024, 9, 1, tzinfo=timezone.utc)

    # Wire equipment to the interface
    temporal_history_repository.register_equipment_at_interface(
        conn, seed["equip_a_id"], si_id, None, start_time=t_install
    )

    # Open initial location at Inlet
    _open_location(conn, seed["equip_a_id"], seed["sp_inlet_id"], t_install)

    # Insert observations before and after move
    obs_before = _insert_observation_and_value(conn, channel_id, t_install, 20.0)
    obs_after = _insert_observation_and_value(conn, channel_id, t_after, 25.0)

    # Relocate to Outlet
    temporal_history_repository.relocate_equipment(
        conn, seed["equip_a_id"], seed["sp_outlet_id"], t_move
    )

    # Channel_ID must be unchanged
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Stream_ID] FROM [dbo].[Channel] WHERE [Stream_ID] = ?", channel_id
    )
    assert cursor.fetchone() is not None

    # AC-LO2: point-in-time T_before → Inlet
    loc_before = _get_location_for_observation(conn, obs_before)
    assert loc_before is not None
    assert loc_before["sampling_point_id"] == seed["sp_inlet_id"]

    # AC-LO2: point-in-time T_after → Outlet
    loc_after = _get_location_for_observation(conn, obs_after)
    assert loc_after is not None
    assert loc_after["sampling_point_id"] == seed["sp_outlet_id"]


# ---------------------------------------------------------------------------
# AC-LO3: Second active location row raises a constraint error
# ---------------------------------------------------------------------------


def test_second_active_location_row_raises_constraint_error(db):
    conn, _, seed = db
    si_id, _ = _create_interface_and_channel(conn, seed)

    t_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _open_location(conn, seed["equip_a_id"], seed["sp_inlet_id"], t_start)

    # The DB has a filtered unique index on (Equipment_ID) WHERE ValidTo IS NULL.
    # Attempting a direct INSERT of a second active row must raise IntegrityError.
    with pytest.raises(pyodbc.IntegrityError):
        _open_location(conn, seed["equip_a_id"], seed["sp_outlet_id"], t_start)


# ---------------------------------------------------------------------------
# AC-LO5: valid_from required on relocation (schema-level validation)
# ---------------------------------------------------------------------------


def test_relocation_valid_from_required():
    """The EquipmentRelocateRequest Pydantic model must require valid_from."""
    from api.v1.schemas.equipment_move import EquipmentRelocateRequest
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        EquipmentRelocateRequest(sampling_point_id=1)  # type: ignore[call-arg]  # missing valid_from


# ---------------------------------------------------------------------------
# Late registration: register_equipment_at_interface
# ---------------------------------------------------------------------------


def test_late_equipment_registration(db):
    conn, _, seed = db
    si_id, _ = _create_interface_and_channel(conn, seed)

    # No active row initially
    active = temporal_history_repository.get_active_wiring_for_equipment(
        conn, seed["equip_a_id"]
    )
    assert active is None

    t_start = datetime(2024, 3, 15, 8, 0, tzinfo=timezone.utc)
    history_id = temporal_history_repository.register_equipment_at_interface(
        conn, seed["equip_a_id"], si_id, None, start_time=t_start
    )
    assert isinstance(history_id, int)

    active = temporal_history_repository.get_active_wiring_for_equipment(
        conn, seed["equip_a_id"]
    )
    assert active is not None
    assert active["equipment_id"] == seed["equip_a_id"]
    assert active["signal_interface_id"] == si_id
    assert active["valid_from"] == t_start.replace(tzinfo=None)
    assert active["valid_to"] is None
