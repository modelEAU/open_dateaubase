"""PRD 7 slice 1 — field replicate on Sample, laboratory in AnalysisSeries identity.

Two identity changes, pinned from the YAML dictionary through the generated DDL
to the repository/endpoint layer:

* ``Sample.Replicate`` (the FIELD replicate, distinct from the ANALYTICAL
  ``LabAnalysis.Replicate``) plus ``UQ_Sample_Identity`` over
  (SamplingPoint_ID, SampleDateTimeStart, SampleKind_ID, Replicate,
  ParentSample_ID). MSSQL UNIQUE treats NULLs as equal, so a re-import of one
  field sample collides while aliquots / blanks / genuine replicates do not.
* ``AnalysisSeries.Laboratory_ID`` joining ``UQ_AnalysisSeries_Identity``, so
  two laboratories measuring one parameter at one sampling point resolve to two
  series rather than one.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from api.v1.repositories import ingestion_repository
from tools.schema_migrate.loader import load_schema
from tools.schema_migrate.render import render_create_script

_ROOT = Path(__file__).parent.parent.parent
_TABLES_DIR = _ROOT / "schema_dictionary" / "tables"


@pytest.fixture(scope="module")
def schema():
    return load_schema(_TABLES_DIR)


@pytest.fixture(scope="module")
def ddl(schema):
    return render_create_script(schema, "2.4.0", "mssql")


def _columns(table: dict) -> dict[str, dict]:
    return {c["name"]: c for c in table["columns"]}


def _unique(table: dict, name: str) -> list[str]:
    for uq in table.get("unique_constraints", []):
        if uq["name"] == name:
            return uq["columns"]
    raise AssertionError(f"{name} not declared in the dictionary")


class TestSampleReplicateDictionary:
    def test_replicate_is_a_non_null_integer_defaulting_to_one(self, schema):
        col = _columns(schema["Sample"]["table"])["Replicate"]
        assert col["logical_type"] == "integer"
        assert col["nullable"] is False
        assert col["default"] == 1

    def test_sample_identity_constraint_columns(self, schema):
        assert _unique(schema["Sample"]["table"], "UQ_Sample_Identity") == [
            "SamplingPoint_ID",
            "SampleDateTimeStart",
            "SampleKind_ID",
            "Replicate",
            "ParentSample_ID",
        ]

    def test_field_replicate_is_distinct_from_the_analytical_one(self, schema):
        """Both tables carry a Replicate; they count different things."""
        assert "Replicate" in _columns(schema["LabAnalysis"]["table"])
        lab_uq = _unique(schema["LabAnalysis"]["table"], "UQ_LabAnalysis_Identity")
        assert "Replicate" in lab_uq
        assert "Sample_ID" in lab_uq


class TestAnalysisSeriesLaboratoryDictionary:
    def test_laboratory_id_is_a_nullable_fk(self, schema):
        col = _columns(schema["AnalysisSeries"]["table"])["Laboratory_ID"]
        assert col["logical_type"] == "integer"
        assert col.get("nullable", True) is True
        assert col["foreign_key"] == {
            "table": "Laboratory",
            "column": "Laboratory_ID",
        }

    def test_laboratory_joins_series_identity(self, schema):
        assert _unique(
            schema["AnalysisSeries"]["table"], "UQ_AnalysisSeries_Identity"
        ) == ["Parameter_ID", "SamplingPoint_ID", "ValueKind_ID", "Laboratory_ID"]


class TestGeneratedDDL:
    def test_sample_replicate_column_and_constraint_are_emitted(self, ddl):
        assert "[Replicate] INT NOT NULL DEFAULT 1" in ddl
        assert (
            "CONSTRAINT [UQ_Sample_Identity] UNIQUE ([SamplingPoint_ID], "
            "[SampleDateTimeStart], [SampleKind_ID], [Replicate], "
            "[ParentSample_ID])" in ddl
        )

    def test_analysis_series_identity_includes_laboratory(self, ddl):
        assert (
            "CONSTRAINT [UQ_AnalysisSeries_Identity] UNIQUE ([Parameter_ID], "
            "[SamplingPoint_ID], [ValueKind_ID], [Laboratory_ID])" in ddl
        )

    def test_laboratory_fk_is_emitted(self, ddl):
        assert (
            "ALTER TABLE [dbo].[AnalysisSeries] ADD CONSTRAINT "
            "[FK_AnalysisSeries_Laboratory_ID] FOREIGN KEY ([Laboratory_ID]) "
            "REFERENCES [dbo].[Laboratory] ([Laboratory_ID]);" in ddl
        )


class TestVersionAndMigration:
    """A dictionary edit only reaches a deployed database via a version bump."""

    def test_version_is_bumped(self):
        version = yaml.safe_load(
            (_ROOT / "schema_dictionary" / "version.yaml").read_text()
        )
        assert version["schema_version"] == "2.4.0"

    def test_generated_scripts_exist_and_init_points_at_them(self):
        gen = _ROOT / "sql_generation_scripts"
        assert (gen / "v2.4.0_create_mssql.sql").exists()
        assert (gen / "v2.4.0_seed_mssql.sql").exists()
        init = (_ROOT / "sql" / "init.sql").read_text()
        assert "v2.4.0_create_mssql.sql" in init
        assert "v2.4.0_seed_mssql.sql" in init
        assert "v2.3.0_" not in init

    def test_migration_and_rollback_exist(self):
        mig = _ROOT / "migrations" / "v2.3.0_to_v2.4.0_mssql.sql"
        rb = _ROOT / "migrations" / "v2.3.0_to_v2.4.0_mssql_rollback.sql"
        assert mig.exists() and rb.exists()

        mig_sql = mig.read_text()
        # Guarded so a re-run on an already-migrated database is a no-op.
        assert "IF COL_LENGTH('dbo.Sample', 'Replicate') IS NULL" in mig_sql
        assert "IF COL_LENGTH('dbo.AnalysisSeries', 'Laboratory_ID') IS NULL" in mig_sql
        assert "UQ_Sample_Identity" in mig_sql
        assert "N'2.4.0'" in mig_sql
        # Ambiguous series are reported, never guessed at.
        assert "COUNT(DISTINCT [Laboratory_ID]) = 1" in mig_sql
        assert "COUNT(DISTINCT [Laboratory_ID]) > 1" in mig_sql

        rb_sql = rb.read_text()
        assert "DROP COLUMN [Replicate]" in rb_sql
        assert "DROP COLUMN [Laboratory_ID]" in rb_sql
        assert "DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.4.0'" in rb_sql


# ---------------------------------------------------------------------------
# Repository behaviour
# ---------------------------------------------------------------------------


class _FakeCursor:
    """Just enough of pyodbc to exercise find-or-create against a dict "table"."""

    def __init__(self) -> None:
        self.series: dict[tuple, int] = {}  # identity tuple -> Stream_ID
        self.inserts: list[tuple] = []
        self._next_stream = 100
        self._row: tuple | None = None

    def execute(self, sql: str, *params):
        flat = " ".join(sql.split())
        if flat.startswith("SELECT [Stream_ID] FROM [dbo].[AnalysisSeries]"):
            parameter_id, sampling_point_id, value_kind_id, lab, _lab_again = params
            key = (parameter_id, sampling_point_id, value_kind_id, lab)
            found = self.series.get(key)
            self._row = (found,) if found is not None else None
        elif flat.startswith("INSERT INTO [dbo].[Stream]"):
            self._next_stream += 1
            self._row = (self._next_stream,)
        elif flat.startswith("INSERT INTO [dbo].[AnalysisSeries]"):
            stream_id, _name, parameter_id, sampling_point_id, value_kind_id = params[
                :5
            ]
            lab = params[6]
            self.series[(parameter_id, sampling_point_id, value_kind_id, lab)] = (
                stream_id
            )
            self.inserts.append(params)
            self._row = None
        else:  # pragma: no cover - the tested paths issue nothing else
            raise AssertionError(f"unexpected SQL: {flat}")
        return self

    def fetchone(self):
        return self._row


class _FakeConn:
    def __init__(self) -> None:
        self._cursor = _FakeCursor()

    def cursor(self):
        return self._cursor

    def commit(self):
        pass


def _tss_at_effluent(conn: _FakeConn, laboratory_id: int | None = None) -> int:
    """One fixed series identity, varying only the laboratory."""
    return ingestion_repository.find_or_create_analysis_series(
        conn,  # type: ignore[arg-type]  # _FakeConn stands in for pyodbc.Connection
        parameter_id=1,
        sampling_point_id=2,
        value_kind_id=1,
        unit_id=3,
        name="TSS at Effluent",
        laboratory_id=laboratory_id,
    )


class TestFindOrCreateAnalysisSeriesKeysOnLaboratory:
    def test_two_laboratories_give_two_series(self):
        conn = _FakeConn()
        assert _tss_at_effluent(conn, 10) != _tss_at_effluent(conn, 20)
        assert len(conn._cursor.inserts) == 2

    def test_same_laboratory_reuses_the_series(self):
        conn = _FakeConn()
        assert _tss_at_effluent(conn, 10) == _tss_at_effluent(conn, 10)
        assert len(conn._cursor.inserts) == 1

    def test_unrecorded_laboratory_is_its_own_identity(self):
        """NULL is a distinct identity value, and SQL '=' never matches NULL."""
        conn = _FakeConn()
        none_1 = _tss_at_effluent(conn)
        none_2 = _tss_at_effluent(conn)
        with_lab = _tss_at_effluent(conn, 10)
        assert none_1 == none_2
        assert with_lab != none_1


def test_lab_ingest_passes_the_measurement_laboratory_into_series_lookup(monkeypatch):
    from api.v1.endpoints import ingest as ingest_module
    from api.v1.schemas.ingestion import LabIngestRequest, LabMeasurementItem

    repo = MagicMock()
    repo.insert_lab_experiment.return_value = 11
    repo.find_or_create_analysis_series.side_effect = [41, 42]
    repo.insert_lab_analysis.return_value = 55
    repo.get_sample_collection_time.return_value = datetime(
        2026, 5, 18, 8, 15, tzinfo=timezone.utc
    )
    monkeypatch.setattr(ingest_module, "ingestion_repository", repo)

    def measurement(laboratory_id: int) -> LabMeasurementItem:
        return LabMeasurementItem(
            parameter_id=1,
            sampling_point_id=2,
            unit_id=3,
            series_name="TSS at Effluent",
            sample_id=7,
            value=12.4,
            laboratory_id=laboratory_id,
        )

    ingest_module.ingest_lab(
        LabIngestRequest(
            name="Split sample",
            experiment_datetime=datetime(2026, 5, 21, tzinfo=timezone.utc),
            measurements=[measurement(10), measurement(20)],
        ),
        conn=MagicMock(),
    )

    labs = [
        call.kwargs["laboratory_id"]
        for call in repo.find_or_create_analysis_series.call_args_list
    ]
    assert labs == [10, 20]
    # Two series -> the two LabAnalysis rows point at different streams.
    series = [
        call.kwargs["analysis_series_id"]
        for call in repo.insert_lab_analysis.call_args_list
    ]
    assert series == [41, 42]


# ---------------------------------------------------------------------------
# Sample creation
# ---------------------------------------------------------------------------


def test_create_sample_round_trips_a_non_default_replicate(monkeypatch):
    from api.v1.endpoints import ingest as ingest_module
    from api.v1.schemas.ingestion import SampleCreateRequest

    repo = MagicMock()
    repo.insert_sample.return_value = 99
    monkeypatch.setattr(ingest_module, "ingestion_repository", repo)

    response = ingest_module.create_sample(
        SampleCreateRequest(
            sampling_point_id=2,
            sample_datetime_start=datetime(2026, 5, 18, 8, 15, tzinfo=timezone.utc),
            replicate=2,
        ),
        conn=MagicMock(),
    )

    assert response.sample_id == 99
    assert repo.insert_sample.call_args.kwargs["replicate"] == 2


def test_create_sample_defaults_the_replicate_to_one(monkeypatch):
    from api.v1.endpoints import ingest as ingest_module
    from api.v1.schemas.ingestion import SampleCreateRequest

    repo = MagicMock()
    repo.insert_sample.return_value = 99
    monkeypatch.setattr(ingest_module, "ingestion_repository", repo)

    ingest_module.create_sample(
        SampleCreateRequest(
            sampling_point_id=2,
            sample_datetime_start=datetime(2026, 5, 18, 8, 15, tzinfo=timezone.utc),
        ),
        conn=MagicMock(),
    )

    assert repo.insert_sample.call_args.kwargs["replicate"] == 1
