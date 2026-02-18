"""Integration tests for Phase 2d: Ingestion Routing (schema v1.5.0).

Tests cover:
  - Task 2d.1: IngestionRoute table structure and FK constraints
  - Task 2d.2: Route resolution logic (happy path, no route, expired,
                route transitions, ambiguous routes)
  - Task 2d.3: Backfill script idempotency
  - Schema version 1.5.0 registered
  - Rollback from v1.5.0 → v1.4.0

Requires a running MSSQL container. Skipped automatically if unavailable.
"""

import pytest

from .conftest import (
    SQL_FILES,
    column_exists,
    get_column_type,
    get_table_names,
    run_sql_file,
)

# ---------------------------------------------------------------------------
# Helper: resolve the active route for a given key at a given timestamp.
# Returns the Metadata_ID or raises if 0 or >1 routes match.
# ---------------------------------------------------------------------------

RESOLVE_ROUTE_SQL = """
SELECT [Metadata_ID]
FROM [dbo].[IngestionRoute]
WHERE [Equipment_ID]      = ?
  AND [Parameter_ID]      = ?
  AND [DataProvenance_ID] = ?
  AND [ProcessingDegree]  = ?
  AND [ValidFrom]        <= ?
  AND ([ValidTo] IS NULL OR [ValidTo] > ?)
"""


def resolve_route(conn, equipment_id, parameter_id, data_provenance_id,
                  processing_degree, timestamp):
    """Python implementation of route resolution (Task 2d.2)."""
    cursor = conn.cursor()
    cursor.execute(
        RESOLVE_ROUTE_SQL,
        equipment_id, parameter_id, data_provenance_id,
        processing_degree, timestamp, timestamp,
    )
    rows = cursor.fetchall()
    if len(rows) == 0:
        raise LookupError(
            f"No active IngestionRoute for Equipment={equipment_id}, "
            f"Parameter={parameter_id}, DataProvenance={data_provenance_id}, "
            f"ProcessingDegree='{processing_degree}' at {timestamp}."
        )
    if len(rows) > 1:
        ids = [r[0] for r in rows]
        raise ValueError(
            f"Ambiguous IngestionRoute: {len(rows)} routes match for "
            f"Equipment={equipment_id}, Parameter={parameter_id} at {timestamp}. "
            f"Matching Metadata_IDs: {ids}"
        )
    return rows[0][0]


# ===========================================================================
# TestIngestionRouteTable
# ===========================================================================


class TestIngestionRouteTable:
    """IngestionRoute table exists with correct structure."""

    def test_table_exists(self, db_at_v150):
        conn, _ = db_at_v150
        assert "IngestionRoute" in get_table_names(conn)

    def test_required_columns_exist(self, db_at_v150):
        conn, _ = db_at_v150
        expected = [
            "IngestionRoute_ID",
            "Equipment_ID",
            "Parameter_ID",
            "DataProvenance_ID",
            "ProcessingDegree",
            "ValidFrom",
            "ValidTo",
            "CreatedAt",
            "Metadata_ID",
            "Notes",
        ]
        for col in expected:
            assert column_exists(conn, "IngestionRoute", col), f"Missing column: {col}"

    def test_valid_from_type_is_datetime2(self, db_at_v150):
        conn, _ = db_at_v150
        assert get_column_type(conn, "IngestionRoute", "ValidFrom") == "datetime2"

    def test_valid_to_is_nullable(self, db_at_v150):
        conn, _ = db_at_v150
        cursor = conn.cursor()
        cursor.execute(
            "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='IngestionRoute' "
            "AND COLUMN_NAME='ValidTo'"
        )
        assert cursor.fetchone()[0] == "YES"

    def test_equipment_id_is_nullable(self, db_at_v150):
        conn, _ = db_at_v150
        cursor = conn.cursor()
        cursor.execute(
            "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='IngestionRoute' "
            "AND COLUMN_NAME='Equipment_ID'"
        )
        assert cursor.fetchone()[0] == "YES"

    def test_processing_degree_default_is_raw(self, db_at_v150):
        """Default value for ProcessingDegree column is 'Raw'."""
        conn, _ = db_at_v150
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [COLUMN_DEFAULT] FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='IngestionRoute' "
            "AND COLUMN_NAME='ProcessingDegree'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert "Raw" in row[0]

    def test_fk_to_invalid_parameter_rejected(self, db_at_v150):
        conn, _ = db_at_v150
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Metadata_ID] FROM [dbo].[MetaData]")
        md_id = cursor.fetchone()[0]
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[IngestionRoute] "
                "([Parameter_ID], [DataProvenance_ID], [ValidFrom], [Metadata_ID]) "
                "VALUES (99999, 1, '2025-01-01', ?)",
                md_id,
            )
            conn.commit()

    def test_fk_to_invalid_metadata_rejected(self, db_at_v150):
        conn, _ = db_at_v150
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Parameter_ID] FROM [dbo].[Parameter]")
        param_id = cursor.fetchone()[0]
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[IngestionRoute] "
                "([Parameter_ID], [DataProvenance_ID], [ValidFrom], [Metadata_ID]) "
                "VALUES (?, 1, '2025-01-01', 99999999)",
                param_id,
            )
            conn.commit()


# ===========================================================================
# TestSeedRoute
# ===========================================================================


class TestSeedRoute:
    """seed_v1.5.0.sql creates at least one route for existing MetaData."""

    def test_at_least_one_route_exists(self, db_at_v150):
        conn, _ = db_at_v150
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM [dbo].[IngestionRoute]")
        assert cursor.fetchone()[0] >= 1

    def test_seed_route_has_raw_processing_degree(self, db_at_v150):
        conn, _ = db_at_v150
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[IngestionRoute] "
            "WHERE [ProcessingDegree] = 'Raw'"
        )
        assert cursor.fetchone()[0] >= 1

    def test_seed_route_has_null_valid_to(self, db_at_v150):
        """A seed route is still active (ValidTo IS NULL)."""
        conn, _ = db_at_v150
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[IngestionRoute] WHERE [ValidTo] IS NULL"
        )
        assert cursor.fetchone()[0] >= 1


# ===========================================================================
# TestRouteResolution  (Task 2d.2)
# ===========================================================================


class TestRouteResolution:
    """Route resolution logic: correct MetaDataID returned for various scenarios."""

    # ------------------------------------------------------------------
    # Shared setup: insert a fresh equipment, parameter, provenance, and
    # metadata row, then register routes for the tests below.
    # ------------------------------------------------------------------

    def _setup_base(self, conn):
        """Return (equipment_id, parameter_id, metadata_id) for a fresh scenario.

        Inserts a brand-new Equipment row so the returned equipment_id has
        absolutely no pre-existing IngestionRoute entries — keeping every
        resolution test fully isolated from seed data.
        """
        cursor = conn.cursor()

        # Fresh Equipment — all non-PK columns are nullable
        cursor.execute(
            "INSERT INTO [dbo].[Equipment] ([identifier]) "
            "OUTPUT INSERTED.Equipment_ID "
            "VALUES ('TestEquip_RouteResolution')"
        )
        equip_id = cursor.fetchone()[0]

        # Reuse seed Parameter and SamplingPoints (no routes exist for the new equip_id)
        cursor.execute("SELECT TOP 1 [Parameter_ID] FROM [dbo].[Parameter]")
        param_id = cursor.fetchone()[0]

        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]

        # Fresh MetaData pointing to the new equipment
        cursor.execute(
            "INSERT INTO [dbo].[MetaData] "
            "([Equipment_ID], [Parameter_ID], [Sampling_point_ID], [DataProvenance_ID]) "
            "OUTPUT INSERTED.Metadata_ID "
            "VALUES (?, ?, ?, 1)",
            equip_id, param_id, sp_id,
        )
        md_id = cursor.fetchone()[0]

        return equip_id, param_id, md_id

    def test_happy_path_single_active_route(self, db_at_v150):
        """One active route → correct MetaDataID returned."""
        conn, _ = db_at_v150
        equip_id, param_id, md_id = self._setup_base(conn)

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[IngestionRoute] "
            "([Equipment_ID], [Parameter_ID], [DataProvenance_ID], "
            "[ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID]) "
            "VALUES (?, ?, 1, 'Raw', '2025-01-01', NULL, ?)",
            equip_id, param_id, md_id,
        )

        result = resolve_route(
            conn, equip_id, param_id, 1, "Raw", "2025-06-01T12:00:00"
        )
        assert result == md_id

    def test_no_route_raises_error(self, db_at_v150):
        """No matching route → LookupError with a helpful message."""
        conn, _ = db_at_v150
        # Use IDs that are unlikely to exist as routes
        with pytest.raises(LookupError, match="No active IngestionRoute"):
            resolve_route(conn, 999999, 999999, 1, "Raw", "2025-06-01")

    def test_expired_route_not_returned(self, db_at_v150):
        """Route whose ValidTo is in the past is not matched."""
        conn, _ = db_at_v150
        equip_id, param_id, md_id = self._setup_base(conn)

        cursor = conn.cursor()
        # Insert an expired route (ValidTo = March 15)
        cursor.execute(
            "INSERT INTO [dbo].[IngestionRoute] "
            "([Equipment_ID], [Parameter_ID], [DataProvenance_ID], "
            "[ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID]) "
            "VALUES (?, ?, 1, 'Raw', '2025-01-01', '2025-03-15T00:00:00', ?)",
            equip_id, param_id, md_id,
        )

        # Query after the expiry date → no route
        with pytest.raises(LookupError):
            resolve_route(conn, equip_id, param_id, 1, "Raw", "2025-04-01T00:00:00")

    def test_route_transition_boundary(self, db_at_v150):
        """Route A expires, route B begins at the same timestamp → correct resolution."""
        conn, _ = db_at_v150
        equip_id, param_id, md_id = self._setup_base(conn)

        # Create a second MetaData entry for route B
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO [dbo].[MetaData] "
            "([Equipment_ID], [Parameter_ID], [Sampling_point_ID], [DataProvenance_ID]) "
            "OUTPUT INSERTED.Metadata_ID "
            "VALUES (?, ?, ?, 1)",
            equip_id, param_id, sp_id,
        )
        md_id_b = cursor.fetchone()[0]

        boundary = "2025-03-16T00:00:00"

        # Route A: valid until the boundary
        cursor.execute(
            "INSERT INTO [dbo].[IngestionRoute] "
            "([Equipment_ID], [Parameter_ID], [DataProvenance_ID], "
            "[ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID]) "
            "VALUES (?, ?, 1, 'Raw', '2025-01-01', ?, ?)",
            equip_id, param_id, boundary, md_id,
        )

        # Route B: starts at the boundary (ValidFrom=boundary, ValidTo=NULL)
        cursor.execute(
            "INSERT INTO [dbo].[IngestionRoute] "
            "([Equipment_ID], [Parameter_ID], [DataProvenance_ID], "
            "[ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID]) "
            "VALUES (?, ?, 1, 'Raw', ?, NULL, ?)",
            equip_id, param_id, boundary, md_id_b,
        )

        # Before boundary → route A
        result_before = resolve_route(
            conn, equip_id, param_id, 1, "Raw", "2025-02-01T00:00:00"
        )
        assert result_before == md_id

        # At or after boundary → route B
        result_after = resolve_route(
            conn, equip_id, param_id, 1, "Raw", "2025-04-01T00:00:00"
        )
        assert result_after == md_id_b

    def test_ambiguous_routes_raises_error(self, db_at_v150):
        """Two active routes for the same key → ValueError."""
        conn, _ = db_at_v150
        equip_id, param_id, md_id = self._setup_base(conn)

        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO [dbo].[MetaData] "
            "([Equipment_ID], [Parameter_ID], [Sampling_point_ID], [DataProvenance_ID]) "
            "OUTPUT INSERTED.Metadata_ID "
            "VALUES (?, ?, ?, 1)",
            equip_id, param_id, sp_id,
        )
        md_id_dup = cursor.fetchone()[0]

        # Two overlapping active routes for the same key
        cursor.execute(
            "INSERT INTO [dbo].[IngestionRoute] "
            "([Equipment_ID], [Parameter_ID], [DataProvenance_ID], "
            "[ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID]) "
            "VALUES (?, ?, 1, 'Raw', '2025-01-01', NULL, ?)",
            equip_id, param_id, md_id,
        )
        cursor.execute(
            "INSERT INTO [dbo].[IngestionRoute] "
            "([Equipment_ID], [Parameter_ID], [DataProvenance_ID], "
            "[ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID]) "
            "VALUES (?, ?, 1, 'Raw', '2025-02-01', NULL, ?)",
            equip_id, param_id, md_id_dup,
        )

        with pytest.raises(ValueError, match="Ambiguous"):
            resolve_route(conn, equip_id, param_id, 1, "Raw", "2025-06-01T00:00:00")

    def test_route_before_valid_from_not_returned(self, db_at_v150):
        """Querying before ValidFrom → no route matched."""
        conn, _ = db_at_v150
        equip_id, param_id, md_id = self._setup_base(conn)

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[IngestionRoute] "
            "([Equipment_ID], [Parameter_ID], [DataProvenance_ID], "
            "[ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID]) "
            "VALUES (?, ?, 1, 'Raw', '2025-06-01', NULL, ?)",
            equip_id, param_id, md_id,
        )

        with pytest.raises(LookupError):
            resolve_route(conn, equip_id, param_id, 1, "Raw", "2025-01-01T00:00:00")

    def test_different_processing_degree_not_matched(self, db_at_v150):
        """A 'Cleaned' route is not matched when querying for 'Raw'."""
        conn, _ = db_at_v150
        equip_id, param_id, md_id = self._setup_base(conn)

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[IngestionRoute] "
            "([Equipment_ID], [Parameter_ID], [DataProvenance_ID], "
            "[ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID]) "
            "VALUES (?, ?, 1, 'Cleaned', '2025-01-01', NULL, ?)",
            equip_id, param_id, md_id,
        )

        with pytest.raises(LookupError):
            resolve_route(conn, equip_id, param_id, 1, "Raw", "2025-06-01T00:00:00")


# ===========================================================================
# TestBackfillIdempotency  (Task 2d.3)
# ===========================================================================


class TestBackfillIdempotency:
    """Backfill script can be run multiple times without creating duplicates."""

    def test_backfill_runs_without_error(self, db_at_v150):
        conn, _ = db_at_v150
        backfill_path = (
            __file__
            .replace("tests/integration/test_phase2d.py", "")
            .replace("test_phase2d.py", "")
        )
        from pathlib import Path
        backfill_sql = (
            Path(__file__).parent.parent.parent
            / "migrations" / "data" / "backfill_ingestion_routes.sql"
        )
        run_sql_file(conn, backfill_sql)  # Should not raise

    def test_backfill_twice_no_duplicates(self, db_at_v150):
        """Running the backfill twice must not create duplicate routes."""
        conn, _ = db_at_v150
        from pathlib import Path
        backfill_sql = (
            Path(__file__).parent.parent.parent
            / "migrations" / "data" / "backfill_ingestion_routes.sql"
        )

        run_sql_file(conn, backfill_sql)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM [dbo].[IngestionRoute]")
        count_after_first = cursor.fetchone()[0]

        run_sql_file(conn, backfill_sql)
        cursor.execute("SELECT COUNT(*) FROM [dbo].[IngestionRoute]")
        count_after_second = cursor.fetchone()[0]

        assert count_after_first == count_after_second, (
            "Backfill created duplicate routes on second run"
        )


# ===========================================================================
# TestSchemaVersionV150
# ===========================================================================


class TestSchemaVersionV150:
    def test_schema_version_is_150(self, db_at_v150):
        conn, _ = db_at_v150
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Version] FROM [dbo].[SchemaVersion] WHERE [Version] = '1.5.0'"
        )
        assert cursor.fetchone() is not None


# ===========================================================================
# TestRollbackV150
# ===========================================================================


class TestRollbackV150:
    """Rolling back v1.5.0 removes IngestionRoute and leaves v1.4.0 intact."""

    def test_rollback_removes_ingestion_route_table(self, db_at_v150):
        conn, _ = db_at_v150
        run_sql_file(conn, SQL_FILES["rollback_v1.5.0"])
        assert "IngestionRoute" not in get_table_names(conn)

    def test_rollback_removes_version_entry(self, db_at_v150):
        conn, _ = db_at_v150
        run_sql_file(conn, SQL_FILES["rollback_v1.5.0"])
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[SchemaVersion] WHERE [Version] = '1.5.0'"
        )
        assert cursor.fetchone()[0] == 0

    def test_rollback_preserves_v140_tables(self, db_at_v150):
        conn, _ = db_at_v150
        run_sql_file(conn, SQL_FILES["rollback_v1.5.0"])
        tables = get_table_names(conn)
        for t in ["EquipmentEvent", "EquipmentInstallation", "EquipmentEventType",
                  "Campaign", "Sample", "Laboratory"]:
            assert t in tables, f"v1.4.0 table {t} should still exist after rollback"
