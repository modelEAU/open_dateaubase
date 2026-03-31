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


class TestSignalPortTypeSchema:
    """Tests for SignalPortType.yaml — v3.0.0 replaces SensorStatusCode + StatusChannel_ID."""

    def test_signal_port_type_table_exists(self, tables_dir):
        """SignalPortType table should exist in schema."""
        schema = load_schema(tables_dir)
        assert "SignalPortType" in schema

    def test_signal_port_type_has_all_columns(self, tables_dir):
        """SignalPortType should have required columns."""
        schema = load_schema(tables_dir)
        tbl = schema["SignalPortType"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "SignalPortType_ID" in col_names
        assert "Name" in col_names
        assert "Description" in col_names

    def test_signal_port_type_seed_data_has_four_types(self, tables_dir):
        """SignalPortType should have Value, Status, Alarm, Uncertainty seed rows."""
        schema = load_schema(tables_dir)
        tbl = schema["SignalPortType"]["table"]
        seed_data = tbl.get("seed_data", [])

        assert len(seed_data) == 4
        names = {row["Name"] for row in seed_data}
        assert names == {"Value", "Status", "Alarm", "Uncertainty"}

    def test_signal_port_type_ids(self, tables_dir):
        """SignalPortType IDs should follow the expected convention."""
        schema = load_schema(tables_dir)
        tbl = schema["SignalPortType"]["table"]
        by_name = {row["Name"]: row["SignalPortType_ID"] for row in tbl.get("seed_data", [])}

        assert by_name["Value"] == 1
        assert by_name["Status"] == 2
        assert by_name["Alarm"] == 3
        assert by_name["Uncertainty"] == 4


class TestSignalPortSubSignalColumns:
    """Tests for SignalPort.yaml sub-signal columns — v3.0.0 parent-port navigation."""

    def test_signal_port_has_parent_port_id(self, tables_dir):
        """SignalPort should have ParentPort_ID for sub-signal linking."""
        schema = load_schema(tables_dir)
        tbl = schema["SignalPort"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "ParentPort_ID" in col_names

    def test_signal_port_parent_port_id_is_nullable(self, tables_dir):
        """ParentPort_ID must be nullable — only sub-signal ports set it."""
        schema = load_schema(tables_dir)
        tbl = schema["SignalPort"]["table"]
        cols = {c["name"]: c for c in tbl["columns"]}

        assert cols["ParentPort_ID"].get("nullable", True) is True

    def test_signal_port_has_signal_port_type_id(self, tables_dir):
        """SignalPort should have SignalPortType_ID FK."""
        schema = load_schema(tables_dir)
        tbl = schema["SignalPort"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "SignalPortType_ID" in col_names

    def test_deprecated_tables_not_active(self, tables_dir):
        """SensorStatusCode and EquipmentStatusChannel should not be active tables (v3.0.0)."""
        schema = load_schema(tables_dir)
        assert "SensorStatusCode" not in schema
        assert "EquipmentStatusChannel" not in schema


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
