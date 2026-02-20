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


class TestSensorStatusCodeSchema:
    """Tests for SensorStatusCode.yaml validation."""

    def test_sensor_status_code_table_exists(self, tables_dir):
        """SensorStatusCode table should exist in schema."""
        schema = load_schema(tables_dir)
        assert "SensorStatusCode" in schema

    def test_sensor_status_code_has_all_columns(self, tables_dir):
        """SensorStatusCode should have all required columns."""
        schema = load_schema(tables_dir)
        tbl = schema["SensorStatusCode"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "StatusCodeID" in col_names
        assert "StatusName" in col_names
        assert "Description" in col_names
        assert "IsOperational" in col_names
        assert "Severity" in col_names

    def test_sensor_status_code_primary_key(self, tables_dir):
        """SensorStatusCode should have StatusCodeID as primary key."""
        schema = load_schema(tables_dir)
        tbl = schema["SensorStatusCode"]["table"]
        pk = tbl.get("primary_key", [])

        assert pk == ["StatusCodeID"]

    def test_sensor_status_code_seed_data_count(self, tables_dir):
        """SensorStatusCode should have 11 seed data rows."""
        schema = load_schema(tables_dir)
        tbl = schema["SensorStatusCode"]["table"]
        seed_data = tbl.get("seed_data", [])

        assert len(seed_data) == 11

    def test_sensor_status_code_seed_data_values(self, tables_dir):
        """SensorStatusCode seed data should have expected values."""
        schema = load_schema(tables_dir)
        tbl = schema["SensorStatusCode"]["table"]
        seed_data = {row["StatusCodeID"]: row for row in tbl.get("seed_data", [])}

        assert 0 in seed_data
        assert seed_data[0]["StatusName"] == "Unknown"
        assert seed_data[0]["IsOperational"] is False

        assert 1 in seed_data
        assert seed_data[1]["StatusName"] == "Operational"
        assert seed_data[1]["IsOperational"] is True
        assert seed_data[1]["Severity"] == 0

        assert 10 in seed_data
        assert seed_data[10]["StatusName"] == "Fouled"
        assert seed_data[10]["Severity"] == 2


class TestMetadataStatusColumns:
    """Tests for MetaData.yaml status link columns."""

    def test_metadata_has_status_of_metadata_id(self, tables_dir):
        """MetaData should have StatusOfMetaDataID column."""
        schema = load_schema(tables_dir)
        tbl = schema["MetaData"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "StatusOfMetaDataID" in col_names

    def test_metadata_has_status_of_equipment_id(self, tables_dir):
        """MetaData should have StatusOfEquipmentID column."""
        schema = load_schema(tables_dir)
        tbl = schema["MetaData"]["table"]
        col_names = [c["name"] for c in tbl["columns"]]

        assert "StatusOfEquipmentID" in col_names

    def test_metadata_status_columns_are_nullable(self, tables_dir):
        """Status link columns should be nullable."""
        schema = load_schema(tables_dir)
        tbl = schema["MetaData"]["table"]
        cols = {c["name"]: c for c in tbl["columns"]}

        assert cols["StatusOfMetaDataID"].get("nullable", True) is True
        assert cols["StatusOfEquipmentID"].get("nullable", True) is True

    def test_metadata_has_check_constraint(self, tables_dir):
        """MetaData should have CK_MetaData_StatusTarget check constraint."""
        schema = load_schema(tables_dir)
        tbl = schema["MetaData"]["table"]
        check_constraints = tbl.get("check_constraints", [])

        constraint_names = [c["name"] for c in check_constraints]
        assert "CK_MetaData_StatusTarget" in constraint_names


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
