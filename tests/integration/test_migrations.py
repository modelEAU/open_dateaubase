"""Integration tests for database schema migrations.

Each test class targets a specific schema version and verifies:
- Schema structure is correct
- Sample data was loaded successfully
- Data from previous versions survives the migration intact
"""

import pytest

from .conftest import (
    SQL_FILES,
    column_exists,
    get_column_type,
    get_table_names,
    get_table_row_count,
    run_sql_file,
)

pytestmark = pytest.mark.db


# Expected tables at v1.0.0 (22 tables)
V100_TABLES = {
    "Comments",
    "Contact",
    "Equipment",
    "EquipmentModel",
    "EquipmentModelHasParameter",
    "EquipmentModelHasProcedures",
    "HydrologicalCharacteristics",
    "MetaData",
    "Parameter",
    "ParameterHasProcedures",
    "Procedures",
    "Project",
    "ProjectHasContact",
    "ProjectHasEquipment",
    "ProjectHasSamplingPoints",
    "Purpose",
    "SamplingPoints",
    "Site",
    "Unit",
    "UrbanCharacteristics",
    "Value",
    "Watershed",
    "WeatherCondition",
}

# Expected row counts after seed_v1.0.0.sql
V100_ROW_COUNTS = {
    "Unit": 5,
    "Watershed": 2,
    "WeatherCondition": 3,
    "EquipmentModel": 3,
    "Procedures": 3,
    "Project": 2,
    "Purpose": 2,
    "Comments": 4,
    "HydrologicalCharacteristics": 2,
    "UrbanCharacteristics": 2,
    "Contact": 2,
    "Equipment": 3,
    "Parameter": 5,
    "Site": 2,
    "SamplingPoints": 3,
    "EquipmentModelHasParameter": 5,
    "EquipmentModelHasProcedures": 3,
    "ParameterHasProcedures": 4,
    "MetaData": 6,
    "ProjectHasContact": 3,
    "ProjectHasEquipment": 4,
    "ProjectHasSamplingPoints": 3,
    "Value": 18,
}


# ============================================================================
# v1.0.0 Baseline
# ============================================================================


class TestV100Baseline:
    """Tests for the v1.0.0 baseline schema with sample data."""

    def test_all_v100_tables_exist(self, db_at_v100):
        conn, _ = db_at_v100
        tables = get_table_names(conn)
        assert V100_TABLES.issubset(tables), (
            f"Missing tables: {V100_TABLES - tables}"
        )

    def test_sample_data_row_counts(self, db_at_v100):
        conn, _ = db_at_v100
        for table, expected_count in V100_ROW_COUNTS.items():
            actual = get_table_row_count(conn, table)
            assert actual == expected_count, (
                f"{table}: expected {expected_count} rows, got {actual}"
            )

    def test_value_timestamps_are_int(self, db_at_v100):
        conn, _ = db_at_v100
        col_type = get_column_type(conn, "Value", "Timestamp")
        assert col_type == "int"

    def test_value_timestamps_are_valid_epochs(self, db_at_v100):
        conn, _ = db_at_v100
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Timestamp] FROM [dbo].[Value] WHERE [Timestamp] IS NOT NULL"
        )
        for (ts,) in cursor.fetchall():
            # Unix epochs should be between 2024-01-01 and 2025-12-31
            assert 1704067200 <= ts <= 1735689600, f"Unexpected epoch: {ts}"

    def test_null_timestamp_exists(self, db_at_v100):
        conn, _ = db_at_v100
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[Value] WHERE [Timestamp] IS NULL"
        )
        assert cursor.fetchone()[0] >= 1

    def test_foreign_keys_hold(self, db_at_v100):
        """Verify no orphaned FK references in MetaData."""
        conn, _ = db_at_v100
        cursor = conn.cursor()
        # Check MetaData -> Project (non-NULL FK values should have matching parent)
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] m "
            "WHERE m.[Project_ID] IS NOT NULL "
            "AND m.[Project_ID] NOT IN (SELECT [Project_ID] FROM [dbo].[Project])"
        )
        assert cursor.fetchone()[0] == 0, "Orphaned MetaData.Project_ID found"

        # Check Value -> MetaData
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[Value] v "
            "WHERE v.[Metadata_ID] IS NOT NULL "
            "AND v.[Metadata_ID] NOT IN (SELECT [Metadata_ID] FROM [dbo].[MetaData])"
        )
        assert cursor.fetchone()[0] == 0, "Orphaned Value.Metadata_ID found"


# ============================================================================
# v1.0.1 Migration (adds SchemaVersion table)
# ============================================================================


class TestMigrationV101:
    """Tests after migrating from v1.0.0 to v1.0.1."""

    def test_schema_version_table_exists(self, db_at_v101):
        conn, _ = db_at_v101
        tables = get_table_names(conn)
        assert "SchemaVersion" in tables

    def test_schema_version_has_records(self, db_at_v101):
        conn, _ = db_at_v101
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Version] FROM [dbo].[SchemaVersion] ORDER BY [VersionID]"
        )
        versions = [row[0] for row in cursor.fetchall()]
        assert "1.0.0" in versions
        assert "1.0.1" in versions

    def test_original_data_unchanged(self, db_at_v101):
        conn, _ = db_at_v101
        for table, expected_count in V100_ROW_COUNTS.items():
            actual = get_table_row_count(conn, table)
            assert actual == expected_count, (
                f"{table}: expected {expected_count} rows after v1.0.1 migration, got {actual}"
            )

    def test_value_data_intact(self, db_at_v101):
        """Spot-check specific Value rows survived the migration."""
        conn, _ = db_at_v101
        cursor = conn.cursor()
        # Value ID 1: TSS=185.0 at WWTP inlet
        cursor.execute(
            "SELECT [Value], [Timestamp] FROM [dbo].[Value] WHERE [Value_ID] = 1"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == pytest.approx(185.0)
        assert row[1] == 1705320000


# ============================================================================
# v1.0.2 Migration (INT timestamps -> DATETIMEOFFSET)
# ============================================================================


class TestMigrationV102:
    """Tests after migrating from v1.0.1 to v1.0.2."""

    def test_timestamp_column_is_datetimeoffset(self, db_at_v102):
        conn, _ = db_at_v102
        col_type = get_column_type(conn, "Value", "Timestamp")
        assert col_type == "datetimeoffset"

    def test_unix_timestamps_converted_correctly(self, db_at_v102):
        """Known epoch values should convert to correct DATETIMEOFFSET."""
        conn, _ = db_at_v102
        cursor = conn.cursor()
        # Value ID 1: epoch 1705320000 = 2024-01-15T13:00:00+00:00
        cursor.execute(
            "SELECT [Timestamp] FROM [dbo].[Value] WHERE [Value_ID] = 1"
        )
        ts = cursor.fetchone()[0]
        assert ts is not None
        # Check year/month/day at UTC
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15

    def test_null_timestamps_preserved(self, db_at_v102):
        conn, _ = db_at_v102
        cursor = conn.cursor()
        # Value ID 18 had NULL timestamp
        cursor.execute(
            "SELECT [Timestamp] FROM [dbo].[Value] WHERE [Value_ID] = 18"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] is None

    def test_new_datetimeoffset_values_inserted(self, db_at_v102):
        """seed_v1.0.2.sql inserts new rows with DATETIMEOFFSET timestamps."""
        conn, _ = db_at_v102
        cursor = conn.cursor()
        # 4 new rows from seed_v1.0.2 (IDs 19-22)
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[Value] WHERE [Value_ID] >= 19"
        )
        assert cursor.fetchone()[0] == 4

    def test_schema_version_recorded(self, db_at_v102):
        conn, _ = db_at_v102
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[SchemaVersion] WHERE [Version] = '1.0.2'"
        )
        assert cursor.fetchone()[0] == 1

    def test_applied_at_is_datetimeoffset(self, db_at_v102):
        conn, _ = db_at_v102
        col_type = get_column_type(conn, "SchemaVersion", "AppliedAt")
        assert col_type == "datetimeoffset"

    def test_original_row_counts_preserved(self, db_at_v102):
        conn, _ = db_at_v102
        # Original v1.0.0 tables should keep their row counts
        # (Value has 18 + 4 new = 22 total)
        for table, expected_count in V100_ROW_COUNTS.items():
            actual = get_table_row_count(conn, table)
            if table == "Value":
                assert actual == expected_count + 4, (
                    f"Value: expected {expected_count + 4} rows, got {actual}"
                )
            else:
                assert actual == expected_count, (
                    f"{table}: expected {expected_count} rows, got {actual}"
                )

    def test_value_magnitudes_preserved(self, db_at_v102):
        """Verify that measurement values were not corrupted by timestamp migration."""
        conn, _ = db_at_v102
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Value_ID], [Value] FROM [dbo].[Value] "
            "WHERE [Value_ID] IN (1, 4, 10) ORDER BY [Value_ID]"
        )
        rows = {r[0]: r[1] for r in cursor.fetchall()}
        assert rows[1] == pytest.approx(185.0)   # TSS
        assert rows[4] == pytest.approx(450.0)   # COD
        assert rows[10] == pytest.approx(350.0)  # CSO TSS


# ============================================================================
# v1.1.0 Migration (polymorphic value types)
# ============================================================================


V110_NEW_TABLES = {
    "ValueType",
    "ValueBinningAxis",
    "ValueBin",
    "MetaDataAxis",
    "ValueVector",
    "ValueMatrix",
    "ValueImage",
}


class TestMigrationV110:
    """Tests after migrating from v1.0.2 to v1.1.0."""

    def test_new_tables_exist(self, db_at_v110):
        conn, _ = db_at_v110
        tables = get_table_names(conn)
        assert V110_NEW_TABLES.issubset(tables), (
            f"Missing tables: {V110_NEW_TABLES - tables}"
        )

    def test_value_type_seed_data(self, db_at_v110):
        conn, _ = db_at_v110
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [ValueType_ID], [ValueType_Name] FROM [dbo].[ValueType] "
            "ORDER BY [ValueType_ID]"
        )
        rows = {r[0]: r[1] for r in cursor.fetchall()}
        assert rows == {1: "Scalar", 2: "Vector", 3: "Matrix", 4: "Image"}

    def test_metadata_has_new_column(self, db_at_v110):
        conn, _ = db_at_v110
        assert column_exists(conn, "MetaData", "ValueType_ID")

    def test_existing_metadata_defaulted_to_scalar(self, db_at_v110):
        """Pre-existing MetaData rows (IDs 1-6) should have ValueType_ID=1 (Scalar)."""
        conn, _ = db_at_v110
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] "
            "WHERE [Metadata_ID] <= 6 AND [ValueType_ID] != 1"
        )
        assert cursor.fetchone()[0] == 0

    def test_vector_data_inserted(self, db_at_v110):
        conn, _ = db_at_v110
        count = get_table_row_count(conn, "ValueVector")
        assert count == 18  # 10 UV-Vis bins (7+3) + 8 PSD bins (4+4)

    def test_matrix_data_inserted(self, db_at_v110):
        conn, _ = db_at_v110
        count = get_table_row_count(conn, "ValueMatrix")
        assert count == 6  # 3 size bins x 2 velocity bins at 1 timestamp

    def test_image_data_inserted(self, db_at_v110):
        conn, _ = db_at_v110
        count = get_table_row_count(conn, "ValueImage")
        assert count == 2

    def test_value_bins_inserted(self, db_at_v110):
        conn, _ = db_at_v110
        count = get_table_row_count(conn, "ValueBin")
        assert count == 13  # 7 UV-Vis + 4 size + 2 velocity bins

    def test_original_data_intact(self, db_at_v110):
        """All original v1.0.0 table row counts should be unchanged."""
        conn, _ = db_at_v110
        for table, expected_count in V100_ROW_COUNTS.items():
            actual = get_table_row_count(conn, table)
            if table == "Value":
                # 18 original + 4 from v1.0.2 seed
                assert actual == expected_count + 4
            elif table == "MetaData":
                # 6 original + 4 new (vector UV-Vis, image, vector PSD, matrix)
                assert actual == expected_count + 4
            elif table == "Unit":
                # 5 original + 3 new axis units (nm, µm, m/s) from seed_v1.1.0
                assert actual == expected_count + 3, (
                    f"{table}: expected {expected_count + 3} rows, got {actual}"
                )
            else:
                assert actual == expected_count, (
                    f"{table}: expected {expected_count} rows, got {actual}"
                )

    def test_schema_version_recorded(self, db_at_v110):
        conn, _ = db_at_v110
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[SchemaVersion] WHERE [Version] = '1.1.0'"
        )
        assert cursor.fetchone()[0] == 1

    def test_new_metadata_value_types_correct(self, db_at_v110):
        """New MetaData rows should have the correct ValueType_ID."""
        conn, _ = db_at_v110
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Metadata_ID], [ValueType_ID] FROM [dbo].[MetaData] "
            "WHERE [Metadata_ID] > 6 ORDER BY [Metadata_ID]"
        )
        rows = {r[0]: r[1] for r in cursor.fetchall()}
        assert rows[7] == 2   # Vector (UV-Vis spectrum)
        assert rows[8] == 4   # Image
        assert rows[9] == 2   # Vector (particle size distribution)
        assert rows[10] == 3  # Matrix (size-velocity distribution)


# ============================================================================
# Rollback Tests
# ============================================================================


class TestRollbacks:
    """Test that rollback scripts revert migrations without data loss."""

    def test_rollback_v101(self, fresh_db):
        """Apply v1.0.1 then rollback: SchemaVersion should be gone, data intact."""
        conn, _ = fresh_db
        run_sql_file(conn, SQL_FILES["v1.0.0_create"])
        run_sql_file(conn, SQL_FILES["seed_v1.0.0"])
        run_sql_file(conn, SQL_FILES["v1.0.0_to_v1.0.1"])

        # Verify SchemaVersion exists before rollback
        assert "SchemaVersion" in get_table_names(conn)

        # Rollback
        run_sql_file(conn, SQL_FILES["rollback_v1.0.1"])

        # SchemaVersion should be gone
        assert "SchemaVersion" not in get_table_names(conn)

        # Original data should be intact
        for table, expected_count in V100_ROW_COUNTS.items():
            actual = get_table_row_count(conn, table)
            assert actual == expected_count, (
                f"{table}: expected {expected_count} after rollback, got {actual}"
            )

    def test_rollback_v102(self, fresh_db):
        """Apply through v1.0.2 then rollback: timestamps back to INT."""
        conn, _ = fresh_db
        run_sql_file(conn, SQL_FILES["v1.0.0_create"])
        run_sql_file(conn, SQL_FILES["seed_v1.0.0"])
        run_sql_file(conn, SQL_FILES["v1.0.0_to_v1.0.1"])
        run_sql_file(conn, SQL_FILES["seed_v1.0.1"])
        run_sql_file(conn, SQL_FILES["v1.0.1_to_v1.0.2"])

        # Verify timestamp is DATETIMEOFFSET before rollback
        assert get_column_type(conn, "Value", "Timestamp") == "datetimeoffset"

        # Rollback v1.0.2
        run_sql_file(conn, SQL_FILES["rollback_v1.0.2"])

        # Timestamp should be back to INT
        assert get_column_type(conn, "Value", "Timestamp") == "int"

        # Original epoch values should be restored
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Timestamp] FROM [dbo].[Value] WHERE [Value_ID] = 1"
        )
        ts = cursor.fetchone()[0]
        assert ts == 1705320000

        # NULL timestamps should remain NULL
        cursor.execute(
            "SELECT [Timestamp] FROM [dbo].[Value] WHERE [Value_ID] = 18"
        )
        assert cursor.fetchone()[0] is None

        # Version record should be removed
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[SchemaVersion] WHERE [Version] = '1.0.2'"
        )
        assert cursor.fetchone()[0] == 0

    def test_rollback_v110(self, fresh_db):
        """Apply through v1.1.0 then rollback: new tables gone, MetaData columns removed."""
        conn, _ = fresh_db
        run_sql_file(conn, SQL_FILES["v1.0.0_create"])
        run_sql_file(conn, SQL_FILES["seed_v1.0.0"])
        run_sql_file(conn, SQL_FILES["v1.0.0_to_v1.0.1"])
        run_sql_file(conn, SQL_FILES["seed_v1.0.1"])
        run_sql_file(conn, SQL_FILES["v1.0.1_to_v1.0.2"])
        run_sql_file(conn, SQL_FILES["seed_v1.0.2"])
        run_sql_file(conn, SQL_FILES["v1.0.2_to_v1.1.0"])

        # Verify new tables exist before rollback
        tables_before = get_table_names(conn)
        assert V110_NEW_TABLES.issubset(tables_before)

        # Rollback v1.1.0
        run_sql_file(conn, SQL_FILES["rollback_v1.1.0"])

        # New tables should be gone
        tables_after = get_table_names(conn)
        for table in V110_NEW_TABLES:
            assert table not in tables_after, f"{table} still exists after rollback"

        # MetaData column should be gone
        assert not column_exists(conn, "MetaData", "ValueType_ID")

        # Original data should be intact (only v1.0.0 + v1.0.2 seed data)
        assert get_table_row_count(conn, "Value") == 22  # 18 + 4 from v1.0.2
        assert get_table_row_count(conn, "MetaData") == 6  # only original 6

        # Version record should be removed
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[SchemaVersion] WHERE [Version] = '1.1.0'"
        )
        assert cursor.fetchone()[0] == 0


# ============================================================================
# Full Migration Chain
# ============================================================================


class TestFullMigrationChain:
    """Test the complete migration path from v1.0.0 to v1.1.0."""

    def test_sequential_full_migration(self, db_at_v110):
        """All migrations applied in order produce a valid v1.1.0 database."""
        conn, _ = db_at_v110
        tables = get_table_names(conn)

        # All original + new tables should exist (V110_NEW_TABLES is the v1.1.0 set)
        all_expected = V100_TABLES | V110_NEW_TABLES | {"SchemaVersion"}
        assert all_expected.issubset(tables), (
            f"Missing tables: {all_expected - tables}"
        )

    def test_data_survives_full_migration_chain(self, db_at_v110):
        """Original v1.0.0 sample data is fully queryable after all migrations."""
        conn, _ = db_at_v110
        cursor = conn.cursor()

        # Verify original measurement values are accessible
        cursor.execute(
            "SELECT v.[Value], m.[Metadata_ID], p.[Parameter] "
            "FROM [dbo].[Value] v "
            "JOIN [dbo].[MetaData] m ON v.[Metadata_ID] = m.[Metadata_ID] "
            "JOIN [dbo].[Parameter] p ON m.[Parameter_ID] = p.[Parameter_ID] "
            "WHERE v.[Value_ID] = 1"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == pytest.approx(185.0)
        assert row[2] == "TSS"

        # Verify new value types are also queryable alongside old data
        cursor.execute(
            "SELECT vt.[ValueType_Name], COUNT(*) "
            "FROM [dbo].[MetaData] m "
            "JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID] "
            "GROUP BY vt.[ValueType_Name] "
            "ORDER BY vt.[ValueType_Name]"
        )
        type_counts = {r[0]: r[1] for r in cursor.fetchall()}
        assert type_counts["Scalar"] == 6
        assert type_counts["Vector"] == 2   # UV-Vis + PSD
        assert type_counts["Image"] == 1
        assert type_counts["Matrix"] == 1

    def test_schema_version_history_complete(self, db_at_v110):
        """SchemaVersion should have a complete history."""
        conn, _ = db_at_v110
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Version] FROM [dbo].[SchemaVersion] ORDER BY [VersionID]"
        )
        versions = [row[0] for row in cursor.fetchall()]
        assert "1.0.0" in versions
        assert "1.0.1" in versions
        assert "1.0.2" in versions
        assert "1.1.0" in versions
