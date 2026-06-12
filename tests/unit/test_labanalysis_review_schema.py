"""Unit tests for point-level lab review on LabAnalysis (ADR 0005, Slice 7).

Slice 7 adds the institutional review/approval state of an individual lab
measurement to ``LabAnalysis``, parallel to ``QualityCode_ID``:

* ``ReviewStatus`` — a lookup table (Pending / Approved / Rejected), modelled as
  a lookup table per project convention (QualityCode, OperationKind, ...), not a
  constrained string.
* ``LabAnalysis.ReviewStatus_ID`` — NOT NULL, default 1 (Pending), FK → ReviewStatus.
* ``LabAnalysis.ReviewedByPerson_ID`` — nullable FK → Person.
* ``LabAnalysis.ReviewDateTime`` — nullable timestamp(7).

These tests pin the dictionary (YAML) shape and assert the DDL generator emits
the three additions plus the FK to ReviewStatus (guarding the known generator
constraint-drop caveat).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.schema_migrate.loader import load_schema
from tools.schema_migrate.render import render_create_script

_TABLES_DIR = Path(__file__).parent.parent.parent / "schema_dictionary" / "tables"

# (ID, Name) — seed order/IDs are load-bearing: code references these IDs.
_EXPECTED_REVIEW_STATUSES = [
    (1, "Pending"),
    (2, "Approved"),
    (3, "Rejected"),
]


@pytest.fixture
def schema():
    return load_schema(_TABLES_DIR)


class TestReviewStatusDictionary:
    def test_review_status_table_exists(self, schema):
        assert "ReviewStatus" in schema

    def test_review_status_pk_is_non_identity_integer(self, schema):
        tbl = schema["ReviewStatus"]["table"]
        cols = {c["name"]: c for c in tbl["columns"]}
        assert tbl["primary_key"] == ["ReviewStatus_ID"]
        pk = cols["ReviewStatus_ID"]
        assert pk["logical_type"] == "integer"
        assert pk.get("nullable", True) is False
        # Manually-assigned lookup PK — values are referenced by code.
        assert pk.get("identity", False) is False

    def test_review_status_name_and_description_columns(self, schema):
        cols = {c["name"]: c for c in schema["ReviewStatus"]["table"]["columns"]}
        assert cols["Name"]["logical_type"] == "string"
        assert cols["Name"]["max_length"] == 50
        assert cols["Name"].get("nullable", True) is False
        assert cols["Description"]["logical_type"] == "string"
        assert cols["Description"]["max_length"] == 200
        assert cols["Description"].get("nullable", True) is True

    def test_review_status_seed_data_exact(self, schema):
        seed = schema["ReviewStatus"]["table"]["seed_data"]
        got = [(row["ReviewStatus_ID"], row["Name"]) for row in seed]
        assert got == _EXPECTED_REVIEW_STATUSES


class TestLabAnalysisReviewColumns:
    @pytest.fixture
    def cols(self, schema):
        return {c["name"]: c for c in schema["LabAnalysis"]["table"]["columns"]}

    def test_review_status_id_not_null_default_pending_fk(self, cols):
        col = cols["ReviewStatus_ID"]
        assert col["logical_type"] == "integer"
        assert col.get("nullable", True) is False
        assert col["default"] == 1
        assert col.get("foreign_key") == {
            "table": "ReviewStatus",
            "column": "ReviewStatus_ID",
        }

    def test_reviewed_by_person_id_nullable_fk(self, cols):
        col = cols["ReviewedByPerson_ID"]
        assert col["logical_type"] == "integer"
        assert col.get("nullable", True) is True
        assert col.get("foreign_key") == {"table": "Person", "column": "Person_ID"}

    def test_review_datetime_nullable_timestamp(self, cols):
        col = cols["ReviewDateTime"]
        assert col["logical_type"] == "timestamp"
        assert col["precision"] == 7
        assert col.get("nullable", True) is True

    def test_identity_unique_constraint_unchanged(self, schema):
        uqs = {
            u["name"]: u
            for u in schema["LabAnalysis"]["table"].get("unique_constraints", [])
        }
        assert "UQ_LabAnalysis_Identity" in uqs
        assert uqs["UQ_LabAnalysis_Identity"]["columns"] == [
            "LabExperiment_ID",
            "AnalysisSeries_ID",
            "Sample_ID",
            "Replicate",
        ]


class TestRenderedDDL:
    """Guard the generator constraint-drop caveat: assert the rendered string."""

    @pytest.fixture
    def sql(self, schema):
        return render_create_script(schema, version="0.0.0", platform="mssql")

    def test_review_status_id_column_rendered(self, sql):
        assert "[ReviewStatus_ID] INT NOT NULL DEFAULT 1" in sql

    def test_reviewed_by_person_id_column_rendered(self, sql):
        assert "[ReviewedByPerson_ID] INT" in sql

    def test_review_datetime_column_rendered(self, sql):
        assert "[ReviewDateTime] DATETIME2(7)" in sql

    def test_review_status_fk_rendered(self, sql):
        assert (
            "ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT "
            "[FK_LabAnalysis_ReviewStatus_ID] FOREIGN KEY ([ReviewStatus_ID]) "
            "REFERENCES [dbo].[ReviewStatus] ([ReviewStatus_ID]);"
        ) in sql

    def test_reviewed_by_person_fk_rendered(self, sql):
        assert (
            "ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT "
            "[FK_LabAnalysis_ReviewedByPerson_ID] FOREIGN KEY ([ReviewedByPerson_ID]) "
            "REFERENCES [dbo].[Person] ([Person_ID]);"
        ) in sql
