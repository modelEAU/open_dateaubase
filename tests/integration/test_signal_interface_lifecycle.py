"""Integration tests for SignalInterface lifecycle (Issue #24, v4.0.0).

Tests run against a live MSSQL container at the v4.0.0 schema.
Skipped automatically when the container is unavailable.

Covers the five scenarios from the parent plan §Tests:
  (a) Unknown-port, unknown-equipment ingest
  (b) Port + equipment wired
  (c) TresCON mux (ChannelPortHistory gating)
  (d) Backfill previously-blank port
  (e) Swap equipment, historical resolution
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from api.v1.repositories.channel_repository import update_channel
from api.v1.repositories.ingestion_repository import find_or_create_sensor_metadata
from api.v1.repositories.signal_interface_repository import (
    find_or_create_das,
    find_or_create_signal_interface,
    find_or_create_signal_interface_port,
    find_parameter_by_name,
    find_unit_by_name,
)

pytestmark = pytest.mark.db


def _open_wiring(
    conn,
    equipment_id: int,
    si_id: int,
    port_id: int | None = None,
    valid_from=None,
):
    """Open an EquipmentWiringHistory row. Returns EquipmentWiringHistory_ID."""
    if valid_from is None:
        valid_from = datetime.now(timezone.utc)
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


def _open_location(
    conn,
    equipment_id: int,
    sampling_point_id: int,
    valid_from=None,
):
    """Open an EquipmentLocationHistory row. Returns EquipmentLocationHistory_ID."""
    if valid_from is None:
        valid_from = datetime.now(timezone.utc)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[EquipmentLocationHistory]"
        "    ([Equipment_ID], [SamplingPoint_ID], [ValidFrom])"
        " OUTPUT INSERTED.[EquipmentLocationHistory_ID]"
        " VALUES (?, ?, ?)",
        equipment_id,
        sampling_point_id,
        valid_from,
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    return new_id


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(db_at_v400):
    """Database at v4.0.0 with equipment and sampling points for lifecycle tests."""
    conn, db_name = db_at_v400
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
    conn, seed: dict, tag_name: str = "TIT-101", port_id: int | None = None
) -> tuple[int, int]:
    """Create a DAS + SignalInterface + Channel; return (signal_interface_id, channel_id)."""
    das_id, _ = find_or_create_das(conn, "TestDAS")
    si_id, _ = find_or_create_signal_interface(
        conn, das_id, tag_name, 5
    )  # DirectConnect
    param_id = find_parameter_by_name(conn, "Temperature")
    unit_id = find_unit_by_name(conn, "degC")
    assert param_id is not None
    assert unit_id is not None
    channel_id = find_or_create_sensor_metadata(
        conn,
        signal_interface_id=si_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=1,
        processing_degree_id=1,
    )
    if port_id is not None:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE [dbo].[Channel] SET [SignalInterfacePort_ID] = ? WHERE [Channel_ID] = ?",
            port_id,
            channel_id,
        )
        conn.commit()
    return si_id, channel_id


def _insert_observation_and_value(
    conn, channel_id: int, timestamp: datetime, value: float
) -> int:
    """Insert an Observation + Value and return the Observation_ID.

    Uses direct SQL (not insert_scalar_values) because the db_at_v400
    fixture does not apply the v3.0.1 QualityCode migration, so dbo.Value
    lacks the QualityCode column.
    """
    cursor = conn.cursor()
    ts_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp
    cursor.execute(
        "INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])"
        " OUTPUT INSERTED.[Observation_ID] VALUES (?, ?, 'Scalar')",
        channel_id,
        ts_naive,
    )
    obs_id = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO [dbo].[Value] ([Observation_ID], [Value]) VALUES (?, ?)",
        obs_id,
        value,
    )
    conn.commit()
    return obs_id


def _get_equipment_resolution(conn, obs_id: int) -> dict | None:
    """Return {equipment_id, resolution} from vw_ChannelEquipmentAtTime."""
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
    """Return {sampling_point_id, sampling_point_name} from vw_ChannelLocationAtTime."""
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


def _open_channel_port_history(
    conn,
    channel_id: int,
    port_id: int | None,
    valid_from: datetime,
    gating_note: str | None = None,
) -> int:
    """Open a ChannelPortHistory row. Returns ChannelPortHistory_ID."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[ChannelPortHistory]"
        "    ([Channel_ID], [SignalInterfacePort_ID], [ValidFrom], [GatingNote])"
        " OUTPUT INSERTED.[ChannelPortHistory_ID]"
        " VALUES (?, ?, ?, ?)",
        channel_id,
        port_id,
        valid_from,
        gating_note,
    )
    new_id = cursor.fetchone()[0]
    conn.commit()
    return new_id


# ---------------------------------------------------------------------------
# Scenario (a): Unknown-port, unknown-equipment ingest
# ---------------------------------------------------------------------------


class TestUnknownPortUnknownEquipment:
    def test_data_lands_without_port_or_wiring(self, db):
        conn, _, seed = db
        si_id, channel_id = _create_interface_and_channel(
            conn, seed, tag_name="TIT-A01", port_id=None
        )

        t = datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
        obs_id = _insert_observation_and_value(conn, channel_id, t, 22.5)

        # Observation must exist
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Observation_ID] FROM [dbo].[Observation] WHERE [Observation_ID] = ?",
            obs_id,
        )
        assert cursor.fetchone() is not None

    def test_vw_channel_equipment_returns_null_equipment(self, db):
        conn, _, seed = db
        si_id, channel_id = _create_interface_and_channel(
            conn, seed, tag_name="TIT-A02", port_id=None
        )

        t = datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
        obs_id = _insert_observation_and_value(conn, channel_id, t, 22.5)

        result = _get_equipment_resolution(conn, obs_id)
        assert result is not None
        assert result["equipment_id"] is None
        # No wiring exists → the view has one LEFT JOIN row (match_count=1)
        # so resolution falls through to 'resolved' with NULL EquipmentID.
        assert result["resolution"] == "resolved"


# ---------------------------------------------------------------------------
# Scenario (b): Port + equipment wired
# ---------------------------------------------------------------------------


class TestPortAndEquipmentWired:
    def test_traversal_resolves_cleanly(self, db):
        conn, _, seed = db
        si_id, channel_id = _create_interface_and_channel(
            conn, seed, tag_name="TIT-B01", port_id=None
        )

        # Create a port and wire it to the channel
        port_id, _ = find_or_create_signal_interface_port(
            conn, si_id, "AI-1", 1
        )  # AnalogIn

        # Update channel to have the port
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE [dbo].[Channel] SET [SignalInterfacePort_ID] = ? WHERE [Channel_ID] = ?",
            port_id,
            channel_id,
        )
        conn.commit()

        # Wire equipment to the interface+port
        t_wire = datetime(2024, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        t_obs = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        _open_wiring(conn, seed["equip_a_id"], si_id, port_id, t_wire)
        _open_location(conn, seed["equip_a_id"], seed["sp_inlet_id"], t_wire)

        obs_id = _insert_observation_and_value(conn, channel_id, t_obs, 20.0)

        eq = _get_equipment_resolution(conn, obs_id)
        assert eq is not None
        assert eq["equipment_id"] == seed["equip_a_id"]
        assert eq["resolution"] == "resolved"

        loc = _get_location_for_observation(conn, obs_id)
        assert loc is not None
        assert loc["sampling_point_id"] == seed["sp_inlet_id"]


# ---------------------------------------------------------------------------
# Scenario (c): TresCON mux
# ---------------------------------------------------------------------------


class TestTresCONMux:
    def test_two_channels_on_same_port_with_gating_note(self, db):
        conn, _, seed = db
        das_id, _ = find_or_create_das(conn, "MuxDAS")
        si_id, _ = find_or_create_signal_interface(
            conn, das_id, "TresCON-01", 6
        )  # Multiplexer
        port_id, _ = find_or_create_signal_interface_port(
            conn, si_id, "MUX-PORT-1", 7
        )  # Virtual

        param_id = find_parameter_by_name(conn, "Temperature")
        assert param_id is not None

        # Two channels on the same port, differentiated by TagName
        ch1_id = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name="TIT-MUX-01",
            parameter_id=param_id,
            unit_id=1,
            data_provenance_id=1,
            processing_degree_id=1,
        )
        ch2_id = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name="TIT-MUX-02",
            parameter_id=param_id,
            unit_id=1,
            data_provenance_id=1,
            processing_degree_id=1,
        )
        # Assign the same port to both channels
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE [dbo].[Channel] SET [SignalInterfacePort_ID] = ? WHERE [Channel_ID] IN (?, ?)",
            port_id,
            ch1_id,
            ch2_id,
        )
        conn.commit()

        # Gating notes differentiate which channel is active when
        t_gate1 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        t_gate2 = datetime(2024, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
        _open_channel_port_history(conn, ch1_id, port_id, t_gate1, gating_note="Gate-A")
        _open_channel_port_history(conn, ch2_id, port_id, t_gate2, gating_note="Gate-B")

        # Ingest values for each channel
        t1 = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2024, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
        obs1_id = _insert_observation_and_value(conn, ch1_id, t1, 10.0)
        obs2_id = _insert_observation_and_value(conn, ch2_id, t2, 20.0)

        # Verify observations exist and are distinct
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Channel_ID] FROM [dbo].[Observation] WHERE [Observation_ID] = ?",
            obs1_id,
        )
        assert cursor.fetchone()[0] == ch1_id

        cursor.execute(
            "SELECT [Channel_ID] FROM [dbo].[Observation] WHERE [Observation_ID] = ?",
            obs2_id,
        )
        assert cursor.fetchone()[0] == ch2_id

    def test_vw_channel_status_links_status_to_measurement(self, db):
        conn, _, seed = db
        das_id, _ = find_or_create_das(conn, "MuxDAS-Status")
        si_id, _ = find_or_create_signal_interface(
            conn, das_id, "TresCON-02", 6
        )  # Multiplexer
        port_id, _ = find_or_create_signal_interface_port(
            conn, si_id, "MUX-PORT-2", 7
        )  # Virtual

        param_id = find_parameter_by_name(conn, "Temperature")
        assert param_id is not None

        # Parent measurement channel
        parent_id = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name="TIT-MUX-03",
            parameter_id=param_id,
            unit_id=1,
            data_provenance_id=1,
            processing_degree_id=1,
        )

        # Status child channel
        from api.v1.repositories.signal_interface_repository import (
            find_channel_role_by_name,
        )

        status_role_id = find_channel_role_by_name(conn, "Status")
        assert status_role_id is not None

        child_id = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name="TIT-MUX-03.Status",
            parameter_id=param_id,
            unit_id=1,
            data_provenance_id=1,
            processing_degree_id=1,
            parent_channel_id=parent_id,
            channel_role_id=status_role_id,
        )

        # Assign port to both channels
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE [dbo].[Channel] SET [SignalInterfacePort_ID] = ? WHERE [Channel_ID] IN (?, ?)",
            port_id,
            parent_id,
            child_id,
        )
        conn.commit()

        # Ingest a status value
        t = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        _insert_observation_and_value(conn, child_id, t, 1.0)

        # vw_ChannelStatus should show the link
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MeasurementChannelID, StatusChannelID FROM [dbo].[vw_ChannelStatus]"
            " WHERE StatusChannelID = ?",
            child_id,
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == parent_id
        assert row[1] == child_id


# ---------------------------------------------------------------------------
# Scenario (d): Backfill previously-blank port
# ---------------------------------------------------------------------------


class TestBackfillBlankPort:
    def test_prior_observations_resolve_via_channel_id(self, db):
        conn, _, seed = db
        si_id, channel_id = _create_interface_and_channel(
            conn, seed, tag_name="TIT-D01", port_id=None
        )

        # Create a port but don't assign it yet
        port_id, _ = find_or_create_signal_interface_port(
            conn, si_id, "AI-2", 1
        )  # AnalogIn

        # Ingest observations while port is NULL
        t_before = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        obs_before = _insert_observation_and_value(conn, channel_id, t_before, 15.0)

        # Wire equipment (without port, since channel port is NULL)
        t_wire = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        _open_wiring(conn, seed["equip_a_id"], si_id, None, t_wire)

        # Prior observation should still resolve
        eq_before = _get_equipment_resolution(conn, obs_before)
        assert eq_before is not None
        assert eq_before["equipment_id"] == seed["equip_a_id"]

    def test_new_observations_use_populated_port(self, db):
        conn, _, seed = db
        si_id, channel_id = _create_interface_and_channel(
            conn, seed, tag_name="TIT-D02", port_id=None
        )

        port_id, _ = find_or_create_signal_interface_port(
            conn, si_id, "AI-3", 1
        )  # AnalogIn

        # Ingest before backfill
        t_before = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        obs_before = _insert_observation_and_value(conn, channel_id, t_before, 15.0)

        # Wire equipment with specific port
        t_wire = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        _open_wiring(conn, seed["equip_a_id"], si_id, port_id, t_wire)

        # Backfill: set port on channel via direct update
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE [dbo].[Channel] SET [SignalInterfacePort_ID] = ? WHERE [Channel_ID] = ?",
            port_id,
            channel_id,
        )
        conn.commit()

        # Ingest after backfill
        t_after = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        obs_after = _insert_observation_and_value(conn, channel_id, t_after, 25.0)

        # Both observations should resolve to the same equipment
        eq_before = _get_equipment_resolution(conn, obs_before)
        eq_after = _get_equipment_resolution(conn, obs_after)

        assert eq_before is not None
        assert eq_before["equipment_id"] == seed["equip_a_id"]
        assert eq_before["resolution"] == "resolved"

        assert eq_after is not None
        assert eq_after["equipment_id"] == seed["equip_a_id"]
        assert eq_after["resolution"] == "resolved"


# ---------------------------------------------------------------------------
# Scenario (e): Swap equipment, historical resolution
# ---------------------------------------------------------------------------


class TestEquipmentSwapHistoricalResolution:
    def test_observations_before_swap_resolve_to_old_equipment(self, db):
        conn, _, seed = db
        si_id, channel_id = _create_interface_and_channel(
            conn, seed, tag_name="TIT-E01", port_id=None
        )

        t_start = datetime(2024, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        t_swap = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        t_before = datetime(2024, 3, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Wire Probe-A
        _open_wiring(conn, seed["equip_a_id"], si_id, None, t_start)
        obs_before = _insert_observation_and_value(conn, channel_id, t_before, 18.0)

        # Swap to Probe-B
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE [dbo].[EquipmentWiringHistory] SET [ValidTo] = ?"
            " WHERE [Equipment_ID] = ? AND [ValidTo] IS NULL",
            t_swap,
            seed["equip_a_id"],
        )
        conn.commit()
        _open_wiring(conn, seed["equip_b_id"], si_id, None, t_swap)

        eq_before = _get_equipment_resolution(conn, obs_before)
        assert eq_before is not None
        assert eq_before["equipment_id"] == seed["equip_a_id"]

    def test_observations_after_swap_resolve_to_new_equipment(self, db):
        conn, _, seed = db
        si_id, channel_id = _create_interface_and_channel(
            conn, seed, tag_name="TIT-E02", port_id=None
        )

        t_start = datetime(2024, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        t_swap = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        t_after = datetime(2024, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Wire Probe-A then swap to Probe-B
        _open_wiring(conn, seed["equip_a_id"], si_id, None, t_start)

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE [dbo].[EquipmentWiringHistory] SET [ValidTo] = ?"
            " WHERE [Equipment_ID] = ? AND [ValidTo] IS NULL",
            t_swap,
            seed["equip_a_id"],
        )
        conn.commit()
        _open_wiring(conn, seed["equip_b_id"], si_id, None, t_swap)

        obs_after = _insert_observation_and_value(conn, channel_id, t_after, 22.0)

        eq_after = _get_equipment_resolution(conn, obs_after)
        assert eq_after is not None
        assert eq_after["equipment_id"] == seed["equip_b_id"]

    def test_swap_with_port_preserves_historical_resolution(self, db):
        conn, _, seed = db
        si_id, channel_id = _create_interface_and_channel(
            conn, seed, tag_name="TIT-E03", port_id=None
        )

        port_id, _ = find_or_create_signal_interface_port(
            conn, si_id, "AI-4", 1
        )  # AnalogIn

        # Update channel to have the port
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE [dbo].[Channel] SET [SignalInterfacePort_ID] = ? WHERE [Channel_ID] = ?",
            port_id,
            channel_id,
        )
        conn.commit()

        t_start = datetime(2024, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        t_swap = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        t_before = datetime(2024, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
        t_after = datetime(2024, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Wire Probe-A to interface+port
        _open_wiring(conn, seed["equip_a_id"], si_id, port_id, t_start)
        obs_before = _insert_observation_and_value(conn, channel_id, t_before, 19.0)

        # Swap to Probe-B on same interface+port
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE [dbo].[EquipmentWiringHistory] SET [ValidTo] = ?"
            " WHERE [Equipment_ID] = ? AND [ValidTo] IS NULL",
            t_swap,
            seed["equip_a_id"],
        )
        conn.commit()
        _open_wiring(conn, seed["equip_b_id"], si_id, port_id, t_swap)

        obs_after = _insert_observation_and_value(conn, channel_id, t_after, 23.0)

        eq_before = _get_equipment_resolution(conn, obs_before)
        eq_after = _get_equipment_resolution(conn, obs_after)

        assert eq_before is not None
        assert eq_before["equipment_id"] == seed["equip_a_id"]
        assert eq_before["resolution"] == "resolved"

        assert eq_after is not None
        assert eq_after["equipment_id"] == seed["equip_b_id"]
        assert eq_after["resolution"] == "resolved"
