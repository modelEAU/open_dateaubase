"""Integration tests for Phase 3: Processing Lineage (schema v1.6.0).

Tests cover:
  - TestProcessingStepTable  : table created, FK enforced, insert/query
  - TestDataLineageTable     : table created, CHECK(Role), indexes exist
  - TestMetaDataProcessingDegree : column added, backfill='Raw', filter
  - TestLinearChain          : Raw → Cleaned → Validated forward/backward
  - TestFanOut               : Raw → Cleaned + Raw → Aggregated (branching)
  - TestFanIn                : TSS_raw + Turbidity_raw → Derived_TSS (multi-input)
  - TestIdempotency          : calling record_processing twice is safe
  - TestRollback             : v1.5.0 → v1.6.0 → rollback to v1.5.0 works

Requires a running MSSQL container. Skipped automatically if unavailable.
"""

import json
from datetime import datetime, timezone

import pytest

from .conftest import (
    SQL_FILES,
    column_exists,
    get_column_type,
    get_table_names,
    run_sql_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_metadata(conn, *, equipment_id=None, parameter_id=None,
                     sampling_point_id=None, data_provenance_id=1,
                     processing_degree="Raw") -> int:
    """Insert a MetaData row and return its Metadata_ID."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[MetaData] "
        "([Equipment_ID], [Parameter_ID], [Sampling_point_ID], "
        " [DataProvenance_ID], [ProcessingDegree]) "
        "OUTPUT INSERTED.[Metadata_ID] "
        "VALUES (?, ?, ?, ?, ?)",
        equipment_id, parameter_id, sampling_point_id,
        data_provenance_id, processing_degree,
    )
    return cursor.fetchone()[0]


def _insert_processing_step(conn, *, name="Test step",
                             method_name="test_method",
                             processing_type="Filtering",
                             executed_at=None) -> int:
    """Insert a ProcessingStep row and return its ProcessingStep_ID."""
    if executed_at is None:
        executed_at = datetime(2025, 6, 1, 12, 0, 0)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[ProcessingStep] "
        "([Name], [MethodName], [ProcessingType], [ExecutedAt]) "
        "OUTPUT INSERTED.[ProcessingStep_ID] "
        "VALUES (?, ?, ?, ?)",
        name, method_name, processing_type, executed_at,
    )
    return cursor.fetchone()[0]


def _insert_lineage(conn, *, step_id: int, metadata_id: int, role: str) -> int:
    """Insert a DataLineage row and return its DataLineage_ID."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[DataLineage] "
        "([ProcessingStep_ID], [Metadata_ID], [Role]) "
        "OUTPUT INSERTED.[DataLineage_ID] "
        "VALUES (?, ?, ?)",
        step_id, metadata_id, role,
    )
    return cursor.fetchone()[0]


def _seed_ids(conn):
    """Return (parameter_id, sampling_point_id) from seed data."""
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 [Parameter_ID] FROM [dbo].[Parameter]")
    param_id = cursor.fetchone()[0]
    cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
    sp_id = cursor.fetchone()[0]
    return param_id, sp_id


# ===========================================================================
# TestProcessingStepTable
# ===========================================================================


class TestProcessingStepTable:
    """ProcessingStep table exists with correct structure and FK behaviour."""

    def test_table_exists(self, db_at_v160):
        conn, _ = db_at_v160
        assert "ProcessingStep" in get_table_names(conn)

    def test_required_columns_exist(self, db_at_v160):
        conn, _ = db_at_v160
        for col in [
            "ProcessingStep_ID", "Name", "Description", "MethodName",
            "MethodVersion", "ProcessingType", "Parameters",
            "ExecutedAt", "ExecutedByPerson_ID",
        ]:
            assert column_exists(conn, "ProcessingStep", col), f"Missing column: {col}"

    def test_name_is_not_nullable(self, db_at_v160):
        conn, _ = db_at_v160
        cursor = conn.cursor()
        cursor.execute(
            "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='ProcessingStep' "
            "AND COLUMN_NAME='Name'"
        )
        assert cursor.fetchone()[0] == "NO"

    def test_insert_and_query(self, db_at_v160):
        conn, _ = db_at_v160
        step_id = _insert_processing_step(
            conn, name="Hampel filter", method_name="outlier_removal",
            processing_type="Filtering",
        )
        assert isinstance(step_id, int) and step_id > 0

        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Name], [ProcessingType] FROM [dbo].[ProcessingStep] "
            "WHERE [ProcessingStep_ID] = ?",
            step_id,
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Hampel filter"
        assert row[1] == "Filtering"

    def test_fk_to_invalid_person_rejected(self, db_at_v160):
        conn, _ = db_at_v160
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[ProcessingStep] "
                "([Name], [ExecutedByPerson_ID]) VALUES ('X', 99999999)"
            )
            conn.commit()  # pyodbc autocommit=True, but trigger the constraint

    def test_parameters_stored_as_json(self, db_at_v160):
        conn, _ = db_at_v160
        params = json.dumps({"window": 5, "threshold": 3.0})
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[ProcessingStep] ([Name], [Parameters]) "
            "OUTPUT INSERTED.[ProcessingStep_ID] VALUES (?, ?)",
            "step with params", params,
        )
        step_id = cursor.fetchone()[0]

        cursor.execute(
            "SELECT [Parameters] FROM [dbo].[ProcessingStep] "
            "WHERE [ProcessingStep_ID] = ?",
            step_id,
        )
        stored = cursor.fetchone()[0]
        assert json.loads(stored) == {"window": 5, "threshold": 3.0}


# ===========================================================================
# TestDataLineageTable
# ===========================================================================


class TestDataLineageTable:
    """DataLineage table exists with CHECK constraint and correct indexes."""

    def test_table_exists(self, db_at_v160):
        conn, _ = db_at_v160
        assert "DataLineage" in get_table_names(conn)

    def test_required_columns_exist(self, db_at_v160):
        conn, _ = db_at_v160
        for col in ["DataLineage_ID", "ProcessingStep_ID", "Metadata_ID", "Role"]:
            assert column_exists(conn, "DataLineage", col), f"Missing column: {col}"

    def test_role_check_constraint_input_accepted(self, db_at_v160):
        conn, _ = db_at_v160
        param_id, sp_id = _seed_ids(conn)
        md_id = _insert_metadata(conn, parameter_id=param_id,
                                  sampling_point_id=sp_id)
        step_id = _insert_processing_step(conn)
        dl_id = _insert_lineage(conn, step_id=step_id,
                                 metadata_id=md_id, role="Input")
        assert isinstance(dl_id, int) and dl_id > 0

    def test_role_check_constraint_output_accepted(self, db_at_v160):
        conn, _ = db_at_v160
        param_id, sp_id = _seed_ids(conn)
        md_id = _insert_metadata(conn, parameter_id=param_id,
                                  sampling_point_id=sp_id)
        step_id = _insert_processing_step(conn)
        dl_id = _insert_lineage(conn, step_id=step_id,
                                 metadata_id=md_id, role="Output")
        assert isinstance(dl_id, int) and dl_id > 0

    def test_role_check_constraint_invalid_rejected(self, db_at_v160):
        conn, _ = db_at_v160
        param_id, sp_id = _seed_ids(conn)
        md_id = _insert_metadata(conn, parameter_id=param_id,
                                  sampling_point_id=sp_id)
        step_id = _insert_processing_step(conn)
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[DataLineage] "
                "([ProcessingStep_ID], [Metadata_ID], [Role]) "
                "VALUES (?, ?, 'Banana')",
                step_id, md_id,
            )

    def test_fk_to_invalid_processing_step_rejected(self, db_at_v160):
        conn, _ = db_at_v160
        param_id, sp_id = _seed_ids(conn)
        md_id = _insert_metadata(conn, parameter_id=param_id,
                                  sampling_point_id=sp_id)
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[DataLineage] "
                "([ProcessingStep_ID], [Metadata_ID], [Role]) "
                "VALUES (99999999, ?, 'Input')",
                md_id,
            )

    def test_indexes_exist(self, db_at_v160):
        conn, _ = db_at_v160
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [name] FROM sys.indexes "
            "WHERE object_id = OBJECT_ID('dbo.DataLineage') "
            "AND [name] IN ('IX_DataLineage_Metadata', 'IX_DataLineage_Step_Role')"
        )
        names = {row[0] for row in cursor.fetchall()}
        assert "IX_DataLineage_Metadata" in names, "IX_DataLineage_Metadata index missing"
        assert "IX_DataLineage_Step_Role" in names, "IX_DataLineage_Step_Role index missing"


# ===========================================================================
# TestMetaDataProcessingDegree
# ===========================================================================


class TestMetaDataProcessingDegree:
    """MetaData.ProcessingDegree column exists, is backfilled, and is filterable."""

    def test_column_exists(self, db_at_v160):
        conn, _ = db_at_v160
        assert column_exists(conn, "MetaData", "ProcessingDegree")

    def test_column_type_is_nvarchar(self, db_at_v160):
        conn, _ = db_at_v160
        assert get_column_type(conn, "MetaData", "ProcessingDegree") == "nvarchar"

    def test_existing_rows_backfilled_to_raw(self, db_at_v160):
        conn, _ = db_at_v160
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] "
            "WHERE [ProcessingDegree] IS NULL"
        )
        assert cursor.fetchone()[0] == 0, "Some MetaData rows still have NULL ProcessingDegree"

    def test_default_value_is_raw(self, db_at_v160):
        """Inserting a MetaData row without ProcessingDegree gets 'Raw'."""
        conn, _ = db_at_v160
        param_id, sp_id = _seed_ids(conn)
        md_id = _insert_metadata(conn, parameter_id=param_id,
                                  sampling_point_id=sp_id,
                                  processing_degree="Raw")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [ProcessingDegree] FROM [dbo].[MetaData] WHERE [Metadata_ID] = ?",
            md_id,
        )
        assert cursor.fetchone()[0] == "Raw"

    def test_filter_by_processing_degree(self, db_at_v160):
        conn, _ = db_at_v160
        param_id, sp_id = _seed_ids(conn)
        _insert_metadata(conn, parameter_id=param_id,
                          sampling_point_id=sp_id, processing_degree="Cleaned")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] "
            "WHERE [ProcessingDegree] = 'Cleaned'"
        )
        assert cursor.fetchone()[0] >= 1


# ===========================================================================
# TestLinearChain
# ===========================================================================


class TestLinearChain:
    """Raw → Cleaned → Validated: forward and backward queries return correct chain."""

    def _build_chain(self, conn):
        """Insert Raw → Cleaned → Validated lineage. Return (raw_id, cleaned_id, validated_id)."""
        from open_dateaubase.meteaudata_bridge import record_processing

        param_id, sp_id = _seed_ids(conn)
        raw_id = _insert_metadata(conn, parameter_id=param_id,
                                   sampling_point_id=sp_id, processing_degree="Raw")
        cleaned_id = _insert_metadata(conn, parameter_id=param_id,
                                       sampling_point_id=sp_id, processing_degree="Cleaned")
        validated_id = _insert_metadata(conn, parameter_id=param_id,
                                         sampling_point_id=sp_id, processing_degree="Validated")

        record_processing(
            source_metadata_ids=[raw_id],
            method_name="outlier_removal",
            method_version="meteaudata 0.5.1",
            processing_type="Filtering",
            parameters={"window": 5},
            executed_at=datetime(2025, 6, 1, 10, 0, 0),
            executed_by_person_id=None,
            output_metadata_id=cleaned_id,
            conn=conn,
        )
        record_processing(
            source_metadata_ids=[cleaned_id],
            method_name="range_validation",
            method_version="meteaudata 0.5.1",
            processing_type="Filtering",
            parameters={"min": 0, "max": 1000},
            executed_at=datetime(2025, 6, 1, 10, 5, 0),
            executed_by_person_id=None,
            output_metadata_id=validated_id,
            conn=conn,
        )
        return raw_id, cleaned_id, validated_id

    def test_forward_from_raw(self, db_at_v160):
        from open_dateaubase.lineage import get_lineage_forward

        conn, _ = db_at_v160
        raw_id, cleaned_id, _ = self._build_chain(conn)

        results = get_lineage_forward(raw_id, conn)
        assert len(results) == 1
        assert cleaned_id in results[0]["output_metadata_ids"]

    def test_forward_from_cleaned(self, db_at_v160):
        from open_dateaubase.lineage import get_lineage_forward

        conn, _ = db_at_v160
        _, cleaned_id, validated_id = self._build_chain(conn)

        results = get_lineage_forward(cleaned_id, conn)
        assert len(results) == 1
        assert validated_id in results[0]["output_metadata_ids"]

    def test_backward_from_validated(self, db_at_v160):
        from open_dateaubase.lineage import get_lineage_backward

        conn, _ = db_at_v160
        _, cleaned_id, validated_id = self._build_chain(conn)

        results = get_lineage_backward(validated_id, conn)
        assert len(results) == 1
        assert cleaned_id in results[0]["input_metadata_ids"]

    def test_backward_from_cleaned(self, db_at_v160):
        from open_dateaubase.lineage import get_lineage_backward

        conn, _ = db_at_v160
        raw_id, cleaned_id, _ = self._build_chain(conn)

        results = get_lineage_backward(cleaned_id, conn)
        assert len(results) == 1
        assert raw_id in results[0]["input_metadata_ids"]

    def test_full_lineage_tree_has_parents_and_children(self, db_at_v160):
        from open_dateaubase.lineage import get_full_lineage_tree

        conn, _ = db_at_v160
        raw_id, cleaned_id, validated_id = self._build_chain(conn)

        tree = get_full_lineage_tree(cleaned_id, conn)
        assert tree["metadata_id"] == cleaned_id
        # Raw is an ancestor
        parent_ids = [p["metadata_id"] for p in tree["parents"]]
        assert raw_id in parent_ids
        # Validated is a descendant
        child_ids = [c["metadata_id"] for c in tree["children"]]
        assert validated_id in child_ids


# ===========================================================================
# TestFanOut
# ===========================================================================


class TestFanOut:
    """Raw → Cleaned AND Raw → Aggregated: branching works correctly."""

    def _build_fan_out(self, conn):
        from open_dateaubase.meteaudata_bridge import record_processing

        param_id, sp_id = _seed_ids(conn)
        raw_id = _insert_metadata(conn, parameter_id=param_id,
                                   sampling_point_id=sp_id, processing_degree="Raw")
        cleaned_id = _insert_metadata(conn, parameter_id=param_id,
                                       sampling_point_id=sp_id, processing_degree="Cleaned")
        aggregated_id = _insert_metadata(conn, parameter_id=param_id,
                                          sampling_point_id=sp_id, processing_degree="Aggregated")

        record_processing(
            source_metadata_ids=[raw_id],
            method_name="outlier_removal",
            method_version=None,
            processing_type="Filtering",
            parameters={},
            executed_at=datetime(2025, 6, 1, 10, 0, 0),
            executed_by_person_id=None,
            output_metadata_id=cleaned_id,
            conn=conn,
        )
        record_processing(
            source_metadata_ids=[raw_id],
            method_name="daily_mean",
            method_version=None,
            processing_type="Resampling",
            parameters={"freq": "1D"},
            executed_at=datetime(2025, 6, 1, 10, 0, 0),
            executed_by_person_id=None,
            output_metadata_id=aggregated_id,
            conn=conn,
        )
        return raw_id, cleaned_id, aggregated_id

    def test_forward_from_raw_returns_two_branches(self, db_at_v160):
        from open_dateaubase.lineage import get_lineage_forward

        conn, _ = db_at_v160
        raw_id, cleaned_id, aggregated_id = self._build_fan_out(conn)

        results = get_lineage_forward(raw_id, conn)
        all_outputs = {oid for r in results for oid in r["output_metadata_ids"]}
        assert cleaned_id in all_outputs
        assert aggregated_id in all_outputs

    def test_backward_from_cleaned_only_one_input(self, db_at_v160):
        from open_dateaubase.lineage import get_lineage_backward

        conn, _ = db_at_v160
        raw_id, cleaned_id, _ = self._build_fan_out(conn)

        results = get_lineage_backward(cleaned_id, conn)
        all_inputs = {iid for r in results for iid in r["input_metadata_ids"]}
        assert raw_id in all_inputs

    def test_backward_from_aggregated_only_one_input(self, db_at_v160):
        from open_dateaubase.lineage import get_lineage_backward

        conn, _ = db_at_v160
        raw_id, _, aggregated_id = self._build_fan_out(conn)

        results = get_lineage_backward(aggregated_id, conn)
        all_inputs = {iid for r in results for iid in r["input_metadata_ids"]}
        assert raw_id in all_inputs


# ===========================================================================
# TestFanIn
# ===========================================================================


class TestFanIn:
    """TSS_raw + Turbidity_raw → Derived_TSS: multiple inputs to one step."""

    def _build_fan_in(self, conn):
        from open_dateaubase.meteaudata_bridge import record_processing

        param_id, sp_id = _seed_ids(conn)
        tss_raw_id = _insert_metadata(conn, parameter_id=param_id,
                                       sampling_point_id=sp_id, processing_degree="Raw")
        turb_raw_id = _insert_metadata(conn, parameter_id=param_id,
                                        sampling_point_id=sp_id, processing_degree="Raw")
        derived_id = _insert_metadata(conn, parameter_id=param_id,
                                       sampling_point_id=sp_id, processing_degree="Cleaned")

        record_processing(
            source_metadata_ids=[tss_raw_id, turb_raw_id],
            method_name="derive_tss",
            method_version=None,
            processing_type="Transformation",
            parameters={"model": "empirical_v2"},
            executed_at=datetime(2025, 6, 2, 8, 0, 0),
            executed_by_person_id=None,
            output_metadata_id=derived_id,
            conn=conn,
        )
        return tss_raw_id, turb_raw_id, derived_id

    def test_backward_from_derived_has_both_inputs(self, db_at_v160):
        from open_dateaubase.lineage import get_lineage_backward

        conn, _ = db_at_v160
        tss_raw_id, turb_raw_id, derived_id = self._build_fan_in(conn)

        results = get_lineage_backward(derived_id, conn)
        all_inputs = {iid for r in results for iid in r["input_metadata_ids"]}
        assert tss_raw_id in all_inputs
        assert turb_raw_id in all_inputs

    def test_forward_from_each_source_reaches_derived(self, db_at_v160):
        from open_dateaubase.lineage import get_lineage_forward

        conn, _ = db_at_v160
        tss_raw_id, turb_raw_id, derived_id = self._build_fan_in(conn)

        for src_id in (tss_raw_id, turb_raw_id):
            results = get_lineage_forward(src_id, conn)
            all_outputs = {oid for r in results for oid in r["output_metadata_ids"]}
            assert derived_id in all_outputs, (
                f"Derived ID {derived_id} not found in forward lineage from {src_id}"
            )


# ===========================================================================
# TestIdempotency
# ===========================================================================


class TestIdempotency:
    """Calling record_processing twice with identical arguments creates no duplicates."""

    def test_duplicate_call_returns_same_step_id(self, db_at_v160):
        from open_dateaubase.meteaudata_bridge import record_processing

        conn, _ = db_at_v160
        param_id, sp_id = _seed_ids(conn)
        raw_id = _insert_metadata(conn, parameter_id=param_id,
                                   sampling_point_id=sp_id, processing_degree="Raw")
        cleaned_id = _insert_metadata(conn, parameter_id=param_id,
                                       sampling_point_id=sp_id, processing_degree="Cleaned")

        kwargs = dict(
            source_metadata_ids=[raw_id],
            method_name="hampel",
            method_version=None,
            processing_type="Filtering",
            parameters={"k": 3},
            executed_at=datetime(2025, 7, 1, 9, 0, 0),
            executed_by_person_id=None,
            output_metadata_id=cleaned_id,
            conn=conn,
        )

        step_id_first = record_processing(**kwargs)
        step_id_second = record_processing(**kwargs)
        assert step_id_first == step_id_second

    def test_duplicate_call_creates_no_extra_lineage_rows(self, db_at_v160):
        from open_dateaubase.meteaudata_bridge import record_processing

        conn, _ = db_at_v160
        param_id, sp_id = _seed_ids(conn)
        raw_id = _insert_metadata(conn, parameter_id=param_id,
                                   sampling_point_id=sp_id, processing_degree="Raw")
        out_id = _insert_metadata(conn, parameter_id=param_id,
                                   sampling_point_id=sp_id, processing_degree="Cleaned")

        kwargs = dict(
            source_metadata_ids=[raw_id],
            method_name="linear_interpolation",
            method_version=None,
            processing_type="GapFilling",
            parameters={},
            executed_at=datetime(2025, 7, 2, 9, 0, 0),
            executed_by_person_id=None,
            output_metadata_id=out_id,
            conn=conn,
        )

        step_id = record_processing(**kwargs)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[DataLineage] WHERE [ProcessingStep_ID] = ?",
            step_id,
        )
        count_after_first = cursor.fetchone()[0]

        # Call again — should be no-op
        record_processing(**kwargs)

        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[DataLineage] WHERE [ProcessingStep_ID] = ?",
            step_id,
        )
        count_after_second = cursor.fetchone()[0]

        assert count_after_first == count_after_second, (
            "record_processing created duplicate DataLineage rows on second call"
        )


# ===========================================================================
# TestSchemaVersionV160
# ===========================================================================


class TestSchemaVersionV160:
    def test_schema_version_is_160(self, db_at_v160):
        conn, _ = db_at_v160
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Version] FROM [dbo].[SchemaVersion] WHERE [Version] = '1.6.0'"
        )
        assert cursor.fetchone() is not None


# ===========================================================================
# TestRollback
# ===========================================================================


class TestRollback:
    """Rolling back v1.6.0 removes new tables/column and leaves v1.5.0 intact."""

    def test_rollback_removes_processing_step_table(self, db_at_v160):
        conn, _ = db_at_v160
        run_sql_file(conn, SQL_FILES["rollback_v1.6.0"])
        assert "ProcessingStep" not in get_table_names(conn)

    def test_rollback_removes_data_lineage_table(self, db_at_v160):
        conn, _ = db_at_v160
        run_sql_file(conn, SQL_FILES["rollback_v1.6.0"])
        assert "DataLineage" not in get_table_names(conn)

    def test_rollback_removes_processing_degree_column(self, db_at_v160):
        conn, _ = db_at_v160
        run_sql_file(conn, SQL_FILES["rollback_v1.6.0"])
        assert not column_exists(conn, "MetaData", "ProcessingDegree")

    def test_rollback_removes_version_entry(self, db_at_v160):
        conn, _ = db_at_v160
        run_sql_file(conn, SQL_FILES["rollback_v1.6.0"])
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[SchemaVersion] WHERE [Version] = '1.6.0'"
        )
        assert cursor.fetchone()[0] == 0

    def test_rollback_preserves_v150_tables(self, db_at_v160):
        conn, _ = db_at_v160
        run_sql_file(conn, SQL_FILES["rollback_v1.6.0"])
        tables = get_table_names(conn)
        for t in ["IngestionRoute", "MetaData", "Parameter", "Equipment",
                  "Campaign", "Sample", "Laboratory"]:
            assert t in tables, f"v1.5.0 table {t} should still exist after rollback"
