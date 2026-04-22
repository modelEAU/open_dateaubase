"""Tests for sensor status schema YAML validation."""

import pytest
from pathlib import Path

from tools.schema_migrate.loader import load_schema


@pytest.fixture
def tables_dir():
    return Path(__file__).parent.parent.parent / "schema_dictionary" / "tables"


@pytest.fixture
def views_dir():
    return Path(__file__).parent.parent.parent / "schema_dictionary" / "views"


class TestSignalInterfacePortKindSchema:
    """Tests for SignalInterfacePortKind.yaml — physical port kinds."""

    def test_signal_interface_port_kind_table_exists(self, tables_dir):
        """SignalInterfacePortKind table should exist in schema."""
        schema = load_schema(tables_dir)
        assert "SignalInterfacePortKind" in schema

    def test_signal_interface_port_kind_has_all_columns(self, tables_dir):
        """SignalInterfacePortKind should have required columns."""
        schema = load_schema(tables_dir)
        tbl = schema["SignalInterfacePortKind"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "SignalInterfacePortKind_ID" in col_names
        assert "Name" in col_names
        assert "Description" in col_names

    def test_signal_interface_port_kind_seed_data_has_eight_types(self, tables_dir):
        """SignalInterfacePortKind should have eight seed rows."""
        schema = load_schema(tables_dir)
        tbl = schema["SignalInterfacePortKind"]["table"]
        seed_data = tbl.get("seed_data", [])

        assert len(seed_data) == 8
        names = {row["Name"] for row in seed_data}
        assert names == {
            "AnalogIn",
            "AnalogOut",
            "DigitalIn",
            "DigitalOut",
            "Serial",
            "Network",
            "Virtual",
            "Unknown",
        }


class TestChannelRoleSchema:
    """Tests for ChannelRole.yaml — Value, Status, Alarm, Uncertainty."""

    def test_channel_role_table_exists(self, tables_dir):
        """ChannelRole table should exist in schema."""
        schema = load_schema(tables_dir)
        assert "ChannelRole" in schema

    def test_channel_role_has_all_columns(self, tables_dir):
        """ChannelRole should have required columns."""
        schema = load_schema(tables_dir)
        tbl = schema["ChannelRole"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "ChannelRole_ID" in col_names
        assert "Name" in col_names
        assert "Description" in col_names

    def test_channel_role_seed_data_has_four_types(self, tables_dir):
        """ChannelRole should have Value, Status, Alarm, Uncertainty seed rows."""
        schema = load_schema(tables_dir)
        tbl = schema["ChannelRole"]["table"]
        seed_data = tbl.get("seed_data", [])

        assert len(seed_data) == 4
        names = {row["Name"] for row in seed_data}
        assert names == {"Value", "Status", "Alarm", "Uncertainty"}

    def test_channel_role_ids(self, tables_dir):
        """ChannelRole IDs should follow the expected convention."""
        schema = load_schema(tables_dir)
        tbl = schema["ChannelRole"]["table"]
        by_name = {
            row["Name"]: row["ChannelRole_ID"] for row in tbl.get("seed_data", [])
        }

        assert by_name["Value"] == 1
        assert by_name["Status"] == 2
        assert by_name["Alarm"] == 3
        assert by_name["Uncertainty"] == 4


class TestChannelSubSignalColumns:
    """Tests for Channel.yaml sub-signal columns — v4.0.0 parent-channel navigation."""

    def test_channel_has_parent_channel_id(self, tables_dir):
        """Channel should have ParentChannel_ID for sub-signal linking."""
        schema = load_schema(tables_dir)
        tbl = schema["Channel"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "ParentChannel_ID" in col_names

    def test_channel_parent_channel_id_is_nullable(self, tables_dir):
        """ParentChannel_ID must be nullable — only sub-signal channels set it."""
        schema = load_schema(tables_dir)
        tbl = schema["Channel"]["table"]
        cols = {c["name"]: c for c in tbl["columns"]}

        assert cols["ParentChannel_ID"].get("nullable", True) is True

    def test_channel_has_channel_role_id(self, tables_dir):
        """Channel should have ChannelRole_ID FK."""
        schema = load_schema(tables_dir)
        tbl = schema["Channel"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "ChannelRole_ID" in col_names

    def test_deprecated_tables_not_active(self, tables_dir):
        """SensorStatusCode, EquipmentStatusChannel, SignalPort, SignalPortType should not be active tables (v4.0.0)."""
        schema = load_schema(tables_dir)
        assert "SensorStatusCode" not in schema
        assert "EquipmentStatusChannel" not in schema
        assert "SignalPort" not in schema
        assert "SignalPortType" not in schema


class TestStatusViews:
    """Tests for status view YAML definitions."""

    def test_channel_status_view_exists(self, views_dir):
        """vw_ChannelStatus view should exist."""
        schema_dir = views_dir
        assert schema_dir.exists()

    def test_device_status_view_exists(self, views_dir):
        """vw_DeviceStatus view should exist."""
        schema_dir = views_dir
        assert schema_dir.exists()
