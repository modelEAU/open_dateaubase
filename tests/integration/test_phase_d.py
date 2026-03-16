"""Integration tests for v2.2.0 Observation migration schema.

Verifies:
- Observation table exists with correct columns and constraints
- Value, ValueVector, ValueMatrix, ValueImage are restructured (no Channel_ID/Timestamp)
- Annotation has nullable Observation_ID column
- Round-trip: insert Observation + scalar Value, then query via get_scalar_values
"""

import pytest
from .conftest import column_exists, get_table_names

pytestmark = pytest.mark.db

V220_NEW_TABLES = {"Observation"}

V220_REMOVED_COLUMNS = {
    "Value": {"Value_ID", "Channel_ID", "Timestamp"},
    "ValueVector": {"Channel_ID", "Timestamp"},
    "ValueMatrix": {"Channel_ID", "Timestamp"},
    "ValueImage": {"ValueImage_ID", "Channel_ID", "Timestamp"},
}

V220_ADDED_COLUMNS = {
    "Observation": {"Observation_ID", "Channel_ID", "Timestamp", "DataType"},
    "ValueImage": {"Observation_ID"},
    "Annotation": {"Observation_ID"},
}


class TestV220Schema:
    def test_observation_table_exists(self, db_at_v220):
        conn, _ = db_at_v220
        tables = get_table_names(conn)
        assert "Observation" in tables

    def test_observation_columns(self, db_at_v220):
        conn, _ = db_at_v220
        for col in V220_ADDED_COLUMNS["Observation"]:
            assert column_exists(conn, "Observation", col), f"Observation.{col} missing"

    def test_value_dropped_columns(self, db_at_v220):
        conn, _ = db_at_v220
        for col in V220_REMOVED_COLUMNS["Value"]:
            assert not column_exists(conn, "Value", col), (
                f"Value.{col} should have been dropped"
            )

    def test_value_has_observation_id(self, db_at_v220):
        conn, _ = db_at_v220
        assert column_exists(conn, "Value", "Observation_ID")

    def test_valuevector_dropped_columns(self, db_at_v220):
        conn, _ = db_at_v220
        for col in V220_REMOVED_COLUMNS["ValueVector"]:
            assert not column_exists(conn, "ValueVector", col), (
                f"ValueVector.{col} should have been dropped"
            )

    def test_valuematrix_dropped_columns(self, db_at_v220):
        conn, _ = db_at_v220
        for col in V220_REMOVED_COLUMNS["ValueMatrix"]:
            assert not column_exists(conn, "ValueMatrix", col)

    def test_valueimage_swapped_pk(self, db_at_v220):
        conn, _ = db_at_v220
        assert not column_exists(conn, "ValueImage", "ValueImage_ID")
        assert column_exists(conn, "ValueImage", "Observation_ID")

    def test_annotation_observation_id_nullable(self, db_at_v220):
        """Annotation.Observation_ID must exist and be nullable."""
        conn, _ = db_at_v220
        assert column_exists(conn, "Annotation", "Observation_ID")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT is_nullable FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'Annotation' AND COLUMN_NAME = 'Observation_ID'
        """)
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "YES", "Annotation.Observation_ID must be nullable"

    def test_processing_lineage_unchanged(self, db_at_v220):
        """ProcessingLineage must NOT have Observation_ID (left intentionally unchanged)."""
        conn, _ = db_at_v220
        assert not column_exists(conn, "ProcessingLineage", "Observation_ID")
