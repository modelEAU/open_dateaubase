"""Integration tests for ControlLoop lifecycle (Issue #9).

Tests run against a live MSSQL container at the v4.0.0 schema.
Skipped automatically when the container is unavailable.

Covers all Issue #9 acceptance criteria:

  AC-CL1  ControlLoop created with any supported ControllerType + optional AlgorithmReference
  AC-CL2  ControlLoopPort associates Channel with loop; UQ(ControlLoop_ID, Channel_ID) enforced
  AC-CL3  ControlLoopApplication created with JSON params and StartTime; at most one active per loop
  AC-CL4  Re-tuning closes current Application and opens new one; old tuning preserved with time window
  AC-CL5  Point-in-time query returns correct Application for a given timestamp
  AC-CL6  Cascade: ManipulatedVariable channel on outer loop can be SetPoint channel on inner loop
  AC-CL7  FallbackControlLoop_ID chain is queryable end-to-end
  AC-CL8  Deactivating a cascade loop does not affect the inner loop's Application
  AC-CL9  Integration scenarios: PID with 3 ports, re-tuning, model-based loop, cascade+fallback, point-in-time
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from api.v1.repositories import control_loop_repository


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(db_at_v400):  # noqa: F811
    """Database at v4.0.0 schema with minimal seed data for control loop tests."""
    conn, db_name = db_at_v400

    from api.v1.repositories.ingestion_repository import find_or_create_sensor_metadata
    from api.v1.repositories.signal_interface_repository import find_parameter_by_name

    cursor = conn.cursor()
    # Seed a DAS and SignalInterface for use in tests
    cursor.execute(
        "INSERT INTO [dbo].[DataAcquisitionSystem] ([Name])"
        " OUTPUT INSERTED.[DataAcquisitionSystem_ID] VALUES (?)",
        "TestDAS",
    )
    das_id = cursor.fetchone()[0]

    # SignalInterfaceType_ID 1 = PLC (seeded by v4.0.0 migration)
    cursor.execute(
        "INSERT INTO [dbo].[SignalInterface]"
        "    ([DataAcquisitionSystem_ID], [SignalInterfaceType_ID], [Name])"
        " OUTPUT INSERTED.[SignalInterface_ID]"
        " VALUES (?, ?, ?)",
        das_id,
        1,
        "TestInterface",
    )
    si_id = cursor.fetchone()[0]
    conn.commit()

    param_id = find_parameter_by_name(conn, "temperature")
    assert param_id is not None

    # Create Channels for the test tags
    channel_map = {}
    for tag in ("DO_PV", "DO_MV", "DO_SP", "Turbidity_PV"):
        ch_id = find_or_create_sensor_metadata(
            conn,
            signal_interface_id=si_id,
            tag_name=tag,
            parameter_id=param_id,
            data_provenance_id=1,
            value_kind_id=1,
        )
        channel_map[tag] = ch_id

    yield conn, db_name, channel_map


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _role_id(conn, name: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ControlLoopPortRole_ID] FROM [dbo].[ControlLoopPortRole]"
        " WHERE [Name] = ?",
        name,
    )
    return cursor.fetchone()[0]


def _app_count(conn, loop_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[ControlLoopApplication]"
        " WHERE [ControlLoop_ID] = ?",
        loop_id,
    )
    return cursor.fetchone()[0]


# ===========================================================================
# AC-CL1: ControlLoop creation with supported ControllerTypes
# ===========================================================================


class TestControlLoopCreation:
    """AC-CL1: All supported ControllerTypes can be created."""

    def test_create_pid_loop(self, db):
        conn, _, _ = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name="DO PID", controller_type="PID"
        )
        assert isinstance(loop_id, int) and loop_id > 0

    @pytest.mark.parametrize("ct", ["PI", "P", "BangBang", "Manual"])
    def test_create_all_supported_types(self, db, ct):
        conn, _, _ = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name=f"{ct} loop", controller_type=ct
        )
        row = control_loop_repository.get_control_loop(conn, loop_id)
        assert row["ControllerType"] == ct

    def test_create_custom_loop_with_algorithm_reference(self, db):
        conn, _, _ = db
        loop_id = control_loop_repository.create_control_loop(
            conn,
            name="MPC reactor",
            controller_type="Custom",
            algorithm_reference="https://github.com/example/mpc-controller",
            description="Model predictive control for reactor temperature",
        )
        row = control_loop_repository.get_control_loop(conn, loop_id)
        assert row["AlgorithmReference"] == "https://github.com/example/mpc-controller"
        assert row["Description"] == "Model predictive control for reactor temperature"

    def test_get_nonexistent_loop_returns_none(self, db):
        conn, _, _ = db
        assert control_loop_repository.get_control_loop(conn, 999999) is None


# ===========================================================================
# AC-CL2: ControlLoopPort — association and unique constraint
# ===========================================================================


class TestControlLoopPort:
    """AC-CL2: Ports can be added; UQ(ControlLoop_ID, Channel_ID) enforced."""

    def test_add_three_ports(self, db):
        conn, _, channel_map = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name="DO PID 3port", controller_type="PID"
        )
        mv_id = _role_id(conn, "MeasuredVariable")
        manip_id = _role_id(conn, "ManipulatedVariable")
        sp_id = _role_id(conn, "SetPoint")

        p1 = control_loop_repository.add_loop_port(
            conn, loop_id, channel_map["DO_PV"], mv_id
        )
        p2 = control_loop_repository.add_loop_port(
            conn, loop_id, channel_map["DO_MV"], manip_id
        )
        p3 = control_loop_repository.add_loop_port(
            conn, loop_id, channel_map["DO_SP"], sp_id
        )
        assert len({p1, p2, p3}) == 3  # all distinct IDs

        ports = control_loop_repository.get_loop_ports(conn, loop_id)
        assert len(ports) == 3

    def test_duplicate_port_raises(self, db):
        import pyodbc

        conn, _, channel_map = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name="Dup Port Test", controller_type="P"
        )
        mv_id = _role_id(conn, "MeasuredVariable")

        control_loop_repository.add_loop_port(
            conn, loop_id, channel_map["DO_PV"], mv_id
        )
        with pytest.raises(pyodbc.IntegrityError):
            control_loop_repository.add_loop_port(
                conn, loop_id, channel_map["DO_PV"], mv_id
            )


# ===========================================================================
# AC-CL3 & AC-CL4: ControlLoopApplication — open, at-most-one, re-tuning
# ===========================================================================


class TestControlLoopApplication:
    """AC-CL3 and AC-CL4."""

    def test_open_application_creates_active_row(self, db):
        conn, _, _ = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name="App Test", controller_type="PID"
        )
        app_id = control_loop_repository.open_application(
            conn,
            loop_id=loop_id,
            start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            parameters=json.dumps({"Kp": 1.2, "Ki": 0.05, "Kd": 0.0}),
        )
        active = control_loop_repository.get_active_application(conn, loop_id)
        assert active is not None
        assert active["ControlLoopApplication_ID"] == app_id
        assert active["EndTime"] is None

    def test_second_open_raises_value_error(self, db):
        conn, _, _ = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name="At-most-one", controller_type="PID"
        )
        control_loop_repository.open_application(
            conn, loop_id=loop_id, start_time=datetime(2025, 1, 1)
        )
        with pytest.raises(ValueError, match="already has an active Application"):
            control_loop_repository.open_application(
                conn, loop_id=loop_id, start_time=datetime(2025, 6, 1)
            )

    def test_retune_closes_old_and_opens_new(self, db):
        conn, _, _ = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name="Retune Test", controller_type="PID"
        )
        old_id = control_loop_repository.open_application(
            conn,
            loop_id=loop_id,
            start_time=datetime(2025, 1, 1),
            parameters=json.dumps({"Kp": 1.0}),
        )
        new_id, closed_id = control_loop_repository.retune(
            conn,
            loop_id=loop_id,
            start_time=datetime(2025, 6, 1),
            parameters=json.dumps({"Kp": 2.0}),
        )

        assert closed_id == old_id
        assert new_id != old_id

        # Old Application is closed
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [EndTime] FROM [dbo].[ControlLoopApplication]"
            " WHERE [ControlLoopApplication_ID] = ?",
            old_id,
        )
        end_time = cursor.fetchone()[0]
        assert end_time is not None

        # Only new Application is active
        active = control_loop_repository.get_active_application(conn, loop_id)
        assert active["ControlLoopApplication_ID"] == new_id
        assert json.loads(active["Parameters"]) == {"Kp": 2.0}

    def test_retune_without_active_creates_first_row(self, db):
        conn, _, _ = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name="Retune No Active", controller_type="PI"
        )
        new_id, closed_id = control_loop_repository.retune(
            conn,
            loop_id=loop_id,
            start_time=datetime(2025, 3, 1),
            parameters=json.dumps({"Kp": 0.5, "Ki": 0.02}),
        )
        assert closed_id is None
        assert new_id > 0

    def test_old_tuning_preserved_with_time_window(self, db):
        conn, _, _ = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name="History Preserved", controller_type="PID"
        )
        app1_id = control_loop_repository.open_application(
            conn,
            loop_id=loop_id,
            start_time=datetime(2025, 1, 1),
            parameters=json.dumps({"Kp": 1.0}),
        )
        app2_id, _ = control_loop_repository.retune(
            conn,
            loop_id=loop_id,
            start_time=datetime(2025, 4, 1),
            parameters=json.dumps({"Kp": 1.5}),
        )
        _, _ = control_loop_repository.retune(
            conn,
            loop_id=loop_id,
            start_time=datetime(2025, 7, 1),
            parameters=json.dumps({"Kp": 2.0}),
        )
        total = _app_count(conn, loop_id)
        assert total == 3  # all three applications preserved

        # First row has EndTime set
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [EndTime] FROM [dbo].[ControlLoopApplication]"
            " WHERE [ControlLoopApplication_ID] = ?",
            app1_id,
        )
        assert cursor.fetchone()[0] is not None


# ===========================================================================
# AC-CL5: Point-in-time query
# ===========================================================================


class TestPointInTimeQuery:
    """AC-CL5: get_application_at returns correct row for timestamp."""

    def _build_two_tunings(self, conn):
        loop_id = control_loop_repository.create_control_loop(
            conn, name="Point-in-time", controller_type="PID"
        )
        app1_id = control_loop_repository.open_application(
            conn,
            loop_id=loop_id,
            start_time=datetime(2025, 1, 1),
            parameters=json.dumps({"Kp": 1.0}),
        )
        app2_id, _ = control_loop_repository.retune(
            conn,
            loop_id=loop_id,
            start_time=datetime(2025, 6, 1),
            parameters=json.dumps({"Kp": 2.0}),
        )
        return loop_id, app1_id, app2_id

    def test_query_in_first_window(self, db):
        conn, _, _ = db
        loop_id, app1_id, _ = self._build_two_tunings(conn)
        row = control_loop_repository.get_application_at(
            conn, loop_id, datetime(2025, 3, 1)
        )
        assert row is not None
        assert row["ControlLoopApplication_ID"] == app1_id
        assert json.loads(row["Parameters"]) == {"Kp": 1.0}

    def test_query_in_second_window(self, db):
        conn, _, _ = db
        loop_id, _, app2_id = self._build_two_tunings(conn)
        row = control_loop_repository.get_application_at(
            conn, loop_id, datetime(2025, 8, 1)
        )
        assert row is not None
        assert row["ControlLoopApplication_ID"] == app2_id

    def test_query_before_any_tuning_returns_none(self, db):
        conn, _, _ = db
        loop_id, _, _ = self._build_two_tunings(conn)
        row = control_loop_repository.get_application_at(
            conn, loop_id, datetime(2024, 1, 1)
        )
        assert row is None

    def test_query_at_exact_start_time(self, db):
        conn, _, _ = db
        loop_id, app1_id, _ = self._build_two_tunings(conn)
        row = control_loop_repository.get_application_at(
            conn, loop_id, datetime(2025, 1, 1)
        )
        assert row is not None
        assert row["ControlLoopApplication_ID"] == app1_id


# ===========================================================================
# AC-CL6: Cascade architecture
# ===========================================================================


class TestCascadeArchitecture:
    """AC-CL6: ManipulatedVariable on outer loop can be SetPoint on inner loop
    via the same Channel_ID with different roles.
    """

    def test_shared_port_different_roles(self, db):
        conn, _, channel_map = db
        mv_role = _role_id(conn, "ManipulatedVariable")
        sp_role = _role_id(conn, "SetPoint")

        outer_loop_id = control_loop_repository.create_control_loop(
            conn, name="Outer DO loop", controller_type="PID"
        )
        inner_loop_id = control_loop_repository.create_control_loop(
            conn, name="Inner aeration loop", controller_type="PID"
        )

        # DO_SP is the ManipulatedVariable of the outer loop
        control_loop_repository.add_loop_port(
            conn, outer_loop_id, channel_map["DO_SP"], mv_role
        )
        # DO_SP is the SetPoint of the inner loop
        control_loop_repository.add_loop_port(
            conn, inner_loop_id, channel_map["DO_SP"], sp_role
        )

        outer_ports = control_loop_repository.get_loop_ports(conn, outer_loop_id)
        inner_ports = control_loop_repository.get_loop_ports(conn, inner_loop_id)

        assert outer_ports[0]["Channel_ID"] == channel_map["DO_SP"]
        assert outer_ports[0]["role_name"] == "ManipulatedVariable"
        assert inner_ports[0]["Channel_ID"] == channel_map["DO_SP"]
        assert inner_ports[0]["role_name"] == "SetPoint"


# ===========================================================================
# AC-CL7: Fallback chain
# ===========================================================================


class TestFallbackChain:
    """AC-CL7: FallbackControlLoop_ID chain is queryable end-to-end."""

    def test_three_level_chain(self, db):
        conn, _, _ = db
        manual_id = control_loop_repository.create_control_loop(
            conn, name="Manual fallback", controller_type="Manual"
        )
        pi_id = control_loop_repository.create_control_loop(
            conn,
            name="PI fallback",
            controller_type="PI",
            fallback_control_loop_id=manual_id,
        )
        pid_id = control_loop_repository.create_control_loop(
            conn,
            name="PID outer",
            controller_type="PID",
            fallback_control_loop_id=pi_id,
        )

        chain = control_loop_repository.get_fallback_chain(conn, pid_id)
        assert len(chain) == 3
        assert chain[0]["ControlLoop_ID"] == pid_id
        assert chain[1]["ControlLoop_ID"] == pi_id
        assert chain[2]["ControlLoop_ID"] == manual_id
        assert chain[2]["FallbackControlLoop_ID"] is None

    def test_single_loop_chain(self, db):
        conn, _, _ = db
        loop_id = control_loop_repository.create_control_loop(
            conn, name="Standalone", controller_type="PID"
        )
        chain = control_loop_repository.get_fallback_chain(conn, loop_id)
        assert len(chain) == 1
        assert chain[0]["ControlLoop_ID"] == loop_id


# ===========================================================================
# AC-CL8: Deactivating cascade loop does not affect inner loop
# ===========================================================================


class TestCascadeDeactivation:
    """AC-CL8: Closing an outer loop Application leaves the inner loop's Application open."""

    def test_close_outer_leaves_inner_active(self, db):
        conn, _, _ = db
        outer_id = control_loop_repository.create_control_loop(
            conn, name="Outer", controller_type="PID"
        )
        inner_id = control_loop_repository.create_control_loop(
            conn, name="Inner", controller_type="PID"
        )

        outer_app_id = control_loop_repository.open_application(
            conn, loop_id=outer_id, start_time=datetime(2025, 1, 1)
        )
        inner_app_id = control_loop_repository.open_application(
            conn, loop_id=inner_id, start_time=datetime(2025, 1, 1)
        )

        # Deactivate (close) the outer loop's application
        control_loop_repository.close_application(
            conn, outer_app_id, end_time=datetime(2025, 6, 1)
        )

        # Outer is closed
        outer_active = control_loop_repository.get_active_application(conn, outer_id)
        assert outer_active is None

        # Inner is still active
        inner_active = control_loop_repository.get_active_application(conn, inner_id)
        assert inner_active is not None
        assert inner_active["ControlLoopApplication_ID"] == inner_app_id


# ===========================================================================
# AC-CL9: Full integration scenario — model-based loop with custom params
# ===========================================================================


class TestModelBasedLoop:
    """AC-CL9: Custom controller with arbitrary JSON parameters blob."""

    def test_mpc_loop_with_custom_params(self, db):
        conn, _, channel_map = db
        loop_id = control_loop_repository.create_control_loop(
            conn,
            name="MPC nitrification",
            controller_type="Custom",
            algorithm_reference="git+https://github.com/example/mpc-n@v1.2.0",
        )
        mv_role = _role_id(conn, "MeasuredVariable")
        control_loop_repository.add_loop_port(
            conn, loop_id, channel_map["Turbidity_PV"], mv_role
        )

        params = json.dumps(
            {
                "prediction_horizon": 10,
                "control_horizon": 3,
                "weights": {"Q": 1.0, "R": 0.1},
            }
        )
        app_id = control_loop_repository.open_application(
            conn, loop_id=loop_id, start_time=datetime(2025, 1, 1), parameters=params
        )

        active = control_loop_repository.get_active_application(conn, loop_id)
        stored = json.loads(active["Parameters"])
        assert stored["prediction_horizon"] == 10
        assert stored["weights"]["Q"] == 1.0
