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


# NOTE: SignalInterfacePortKind table was removed from the schema. The
# corresponding TestSignalInterfacePortKindSchema class was deleted.


class TestChannelKindSchema:
    """Tests for ChannelKind.yaml — Value, Status, Alarm, Uncertainty."""

    def test_channel_kind_table_exists(self, tables_dir):
        """ChannelKind table should exist in schema."""
        schema = load_schema(tables_dir)
        assert "ChannelKind" in schema

    def test_channel_kind_has_all_columns(self, tables_dir):
        """ChannelKind should have required columns."""
        schema = load_schema(tables_dir)
        tbl = schema["ChannelKind"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "ChannelKind_ID" in col_names
        assert "Name" in col_names
        assert "Description" in col_names

    def test_channel_kind_seed_data_has_four_types(self, tables_dir):
        """ChannelKind should have Value, Status, Alarm, Uncertainty seed rows."""
        schema = load_schema(tables_dir)
        tbl = schema["ChannelKind"]["table"]
        seed_data = tbl.get("seed_data", [])

        assert len(seed_data) == 4
        names = {row["Name"] for row in seed_data}
        assert names == {"Value", "Status", "Alarm", "Uncertainty"}

    def test_channel_kind_ids(self, tables_dir):
        """ChannelKind IDs should follow the expected convention."""
        schema = load_schema(tables_dir)
        tbl = schema["ChannelKind"]["table"]
        by_name = {
            row["Name"]: row["ChannelKind_ID"] for row in tbl.get("seed_data", [])
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

    def test_channel_has_channel_kind_id(self, tables_dir):
        """Channel should have ChannelKind_ID FK."""
        schema = load_schema(tables_dir)
        tbl = schema["Channel"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "ChannelKind_ID" in col_names

    def test_deprecated_tables_not_active(self, tables_dir):
        """Deprecated v3 tables should not be active in v4.0.0 schema."""
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
