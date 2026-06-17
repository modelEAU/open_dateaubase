"""Integration tests for sub-signal grouping (Issue #8, v4.0.0).

Tests run against a live MSSQL container at the v4.0.0 schema.
Skipped automatically when the container is unavailable.

Covers all issue #8 acceptance criteria:

  AC-SS1  ParentChannel_ID correctly links a child Channel to its parent
  AC-SS2  Sub-signal Channel is created with the correct ChannelRole
          (Value/Status/Alarm/Uncertainty)
  AC-SS3  Querying sub-signals by ParentChannel_ID returns all children
  AC-SS4  Status-channel auto-selection works via ParentChannel_ID +
          ChannelRole.Name = 'Status'
  AC-SS5  Parent/child links survive independent of Equipment wiring/location
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.db

from api.v1.repositories.ingestion_repository import find_or_create_sensor_metadata
from api.v1.repositories.signal_interface_repository import (
    find_channel_kind_by_name,
    find_or_create_das,
    find_or_create_signal_interface,
    find_parameter_by_name,
    find_unit_by_name,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parent_channel(conn, das_name: str, tag: str) -> int:
    """Create a parent (measurement) Channel with Value role. Returns Channel_ID."""
    das_id, _ = find_or_create_das(conn, das_name)
    si_id, _ = find_or_create_signal_interface(conn, das_id, tag)
    param_id = find_parameter_by_name(conn, "Temperature")
    unit_id = find_unit_by_name(conn, "°C")
    assert param_id is not None
    assert unit_id is not None
    return find_or_create_sensor_metadata(
        conn,
        signal_interface_id=si_id,
        tag_name=tag,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=1,
        value_kind_id=1,
        channel_kind_id=1,  # Value
    )


def _make_child_channel(conn, parent_channel_id: int, tag: str, role_name: str) -> int:
    """Create a child Channel with a specific role linked to a parent. Returns Channel_ID."""
    param_id = find_parameter_by_name(conn, "Temperature")
    unit_id = find_unit_by_name(conn, "°C")
    assert param_id is not None
    assert unit_id is not None
    role_id = find_channel_kind_by_name(conn, role_name)
    assert role_id is not None, f"Unknown channel role: {role_name}"
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterface_ID] FROM [dbo].[Channel] WHERE [Stream_ID] = ?",
        parent_channel_id,
    )
    row = cursor.fetchone()
    assert row is not None
    si_id = row[0]
    return find_or_create_sensor_metadata(
        conn,
        signal_interface_id=si_id,
        tag_name=tag,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=1,
        value_kind_id=1,
        parent_channel_id=parent_channel_id,
        channel_kind_id=role_id,
    )


def _get_sub_signal_channel_ids(conn, parent_channel_id: int) -> list[int]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Stream_ID] FROM [dbo].[Channel]"
        " WHERE [ParentChannel_ID] = ?"
        " ORDER BY [Stream_ID]",
        parent_channel_id,
    )
    return [row[0] for row in cursor.fetchall()]


def _get_channel_role_name(conn, channel_id: int) -> str:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT cr.[Name]
        FROM [dbo].[Channel] c
        JOIN [dbo].[ChannelKind] cr ON cr.[ChannelKind_ID] = c.[ChannelKind_ID]
        WHERE c.[Stream_ID] = ?
        """,
        channel_id,
    )
    row = cursor.fetchone()
    assert row is not None
    return row[0]


def _get_status_channel_for_measurement(
    conn, measurement_channel_id: int
) -> int | None:
    """Raw SQL matching _STATUS_CHANNEL_FOR_MEASUREMENT pattern."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sc.[Stream_ID]
        FROM [dbo].[Channel] sc
        JOIN [dbo].[ChannelKind] cr ON cr.[ChannelKind_ID] = sc.[ChannelKind_ID]
        WHERE sc.[ParentChannel_ID] = ?
          AND cr.[Name] = N'Status'
        """,
        measurement_channel_id,
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _insert_observation_and_value(
    conn, channel_id: int, timestamp: datetime, value: float
) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [ValueKind_ID])"
        " OUTPUT INSERTED.[Observation_ID]"
        " VALUES (?, ?, 1)",
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


# ---------------------------------------------------------------------------
# AC-SS1: ParentChannel_ID links child Channel correctly
# ---------------------------------------------------------------------------


class TestParentChildLink:
    def test_parent_channel_links_sub_signal(self, db_at_v200):
        conn, _ = db_at_v200
        parent_id = _make_parent_channel(conn, "DAS1", "TIT-101")
        child_id = _make_child_channel(conn, parent_id, "TIT-101.status", "Status")

        cursor = conn.cursor()
        cursor.execute(
            "SELECT [ParentChannel_ID] FROM [dbo].[Channel] WHERE [Stream_ID] = ?",
            child_id,
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == parent_id

    def test_parent_channel_link_idempotent(self, db_at_v200):
        conn, _ = db_at_v200
        parent_id = _make_parent_channel(conn, "DAS1", "TIT-202")
        child_id_1 = _make_child_channel(conn, parent_id, "TIT-202.alarm", "Alarm")
        child_id_2 = _make_child_channel(conn, parent_id, "TIT-202.alarm", "Alarm")

        assert child_id_1 == child_id_2

    def test_child_channels_differentiated_by_role(self, db_at_v200):
        conn, _ = db_at_v200
        parent_id = _make_parent_channel(conn, "DAS1", "TIT-303")
        status_id = _make_child_channel(conn, parent_id, "TIT-303.status", "Status")
        alarm_id = _make_child_channel(conn, parent_id, "TIT-303.alarm", "Alarm")

        assert status_id != alarm_id


# ---------------------------------------------------------------------------
# AC-SS2: ChannelRole is stored correctly
# ---------------------------------------------------------------------------


class TestChannelRole:
    def test_sub_signal_has_correct_channel_role(self, db_at_v200):
        conn, _ = db_at_v200
        parent_id = _make_parent_channel(conn, "DAS1", "TIT-404")
        status_id = _make_child_channel(conn, parent_id, "TIT-404.status", "Status")
        alarm_id = _make_child_channel(conn, parent_id, "TIT-404.alarm", "Alarm")
        unc_id = _make_child_channel(
            conn, parent_id, "TIT-404.uncertainty", "Uncertainty"
        )

        assert _get_channel_role_name(conn, parent_id) == "Value"
        assert _get_channel_role_name(conn, status_id) == "Status"
        assert _get_channel_role_name(conn, alarm_id) == "Alarm"
        assert _get_channel_role_name(conn, unc_id) == "Uncertainty"


# ---------------------------------------------------------------------------
# AC-SS3: Querying sub-signals by ParentChannel_ID
# ---------------------------------------------------------------------------


class TestGetSubSignals:
    def test_get_sub_signals_returns_all_children(self, db_at_v200):
        conn, _ = db_at_v200
        parent_id = _make_parent_channel(conn, "DAS1", "TIT-505")
        status_id = _make_child_channel(conn, parent_id, "TIT-505.status", "Status")
        alarm_id = _make_child_channel(conn, parent_id, "TIT-505.alarm", "Alarm")
        unc_id = _make_child_channel(
            conn, parent_id, "TIT-505.uncertainty", "Uncertainty"
        )

        children = _get_sub_signal_channel_ids(conn, parent_id)
        assert set(children) == {status_id, alarm_id, unc_id}

    def test_get_sub_signals_empty_for_root_channel(self, db_at_v200):
        conn, _ = db_at_v200
        parent_id = _make_parent_channel(conn, "DAS1", "TIT-606")
        children = _get_sub_signal_channel_ids(conn, parent_id)
        assert children == []


# ---------------------------------------------------------------------------
# AC-SS4: Status-channel auto-selection
# ---------------------------------------------------------------------------


class TestStatusChannelAutoSelection:
    def test_status_channel_for_measurement_query(self, db_at_v200):
        conn, _ = db_at_v200
        parent_id = _make_parent_channel(conn, "DAS1", "TIT-707")
        status_id = _make_child_channel(conn, parent_id, "TIT-707.status", "Status")

        resolved = _get_status_channel_for_measurement(conn, parent_id)
        assert resolved == status_id

    def test_status_channel_returns_none_when_missing(self, db_at_v200):
        conn, _ = db_at_v200
        parent_id = _make_parent_channel(conn, "DAS1", "TIT-808")

        resolved = _get_status_channel_for_measurement(conn, parent_id)
        assert resolved is None

    def test_status_channel_resolves_with_observation(self, db_at_v200):
        conn, _ = db_at_v200
        parent_id = _make_parent_channel(conn, "DAS1", "TIT-909")
        status_id = _make_child_channel(conn, parent_id, "TIT-909.status", "Status")

        # Insert an observation on the status channel
        t = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        _insert_observation_and_value(conn, status_id, t, 1.0)

        # Verify the status channel still resolves correctly
        resolved = _get_status_channel_for_measurement(conn, parent_id)
        assert resolved == status_id


# ---------------------------------------------------------------------------
# AC-SS5: Parent/child links are independent of Equipment wiring/location
# ---------------------------------------------------------------------------


def test_parent_child_link_survives_equipment_wiring(db_at_v200):
    """Opening an EquipmentWiringHistory row does not affect Channel.ParentChannel_ID."""
    from api.v1.repositories.signal_interface_repository import (
        find_or_create_equipment_by_identifier,
        open_equipment_wiring_history,
    )

    conn, _ = db_at_v200
    parent_id = _make_parent_channel(conn, "DAS1", "TIT-WIRE")
    child_id = _make_child_channel(conn, parent_id, "TIT-WIRE.status", "Status")

    equip_id, _ = find_or_create_equipment_by_identifier(conn, "Probe_Wire")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterface_ID] FROM [dbo].[Channel] WHERE [Stream_ID] = ?",
        parent_id,
    )
    si_id = cursor.fetchone()[0]
    open_equipment_wiring_history(conn, equip_id, si_id, None)

    # Parent/child link must be unchanged
    children = _get_sub_signal_channel_ids(conn, parent_id)
    assert children == [child_id]
