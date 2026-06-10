"""Unit tests for the Annotation exclusive-arc schema (ADR 0003).

Slice 0 of the lab AnalysisSeries annotation plan mirrors the Observation
exclusive arc onto Annotation: Channel_ID becomes nullable, a new nullable
AnalysisSeries_ID FK is added, and an XOR CHECK constraint
(CK_Annotation_Source) enforces exactly one anchor is set per row.

These tests pin the dictionary (YAML) shape and assert the DDL generator
emits the CHECK + FK + index, guarding against the known generator caveat
where some constraint YAML patterns were silently dropped.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.schema_migrate.loader import load_schema
from tools.schema_migrate.render import render_create_script

_TABLES_DIR = Path(__file__).parent.parent.parent / "schema_dictionary" / "tables"


@pytest.fixture
def schema():
    return load_schema(_TABLES_DIR)


@pytest.fixture
def annotation(schema):
    return schema["Annotation"]["table"]


class TestAnnotationExclusiveArcDictionary:
    """The Annotation YAML now carries the exclusive arc."""

    def test_channel_id_is_nullable(self, annotation):
        cols = {c["name"]: c for c in annotation["columns"]}
        assert "Channel_ID" in cols
        # nullable defaults to True if omitted; here it must be explicitly true
        assert cols["Channel_ID"].get("nullable", True) is True

    def test_analysis_series_id_column_exists_and_is_nullable(self, annotation):
        cols = {c["name"]: c for c in annotation["columns"]}
        assert "AnalysisSeries_ID" in cols
        assert cols["AnalysisSeries_ID"].get("nullable", True) is True

    def test_analysis_series_id_fk_targets_analysis_series(self, annotation):
        cols = {c["name"]: c for c in annotation["columns"]}
        fk = cols["AnalysisSeries_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "AnalysisSeries"
        assert fk["column"] == "AnalysisSeries_ID"

    def test_check_constraint_ck_annotation_source_present(self, annotation):
        checks = annotation.get("check_constraints") or []
        names = {c.get("name") for c in checks}
        assert "CK_Annotation_Source" in names

    def test_check_constraint_is_an_xor(self, annotation):
        checks = {c["name"]: c for c in (annotation.get("check_constraints") or [])}
        expr = checks["CK_Annotation_Source"]["expression"]
        # exactly-one-non-NULL XOR over the two anchors
        assert "Channel_ID IS NOT NULL AND AnalysisSeries_ID IS NULL" in expr
        assert "Channel_ID IS NULL AND AnalysisSeries_ID IS NOT NULL" in expr

    def test_series_time_index_present(self, annotation):
        idx = {i["name"]: i for i in annotation.get("indexes", [])}
        assert "IX_Annotation_Series_Time" in idx
        assert idx["IX_Annotation_Series_Time"]["columns"] == [
            "AnalysisSeries_ID",
            "StartTime",
            "EndTime",
        ]


class TestAnnotationExclusiveArcDDL:
    """The DDL generator emits the CHECK, FK, and index for Annotation."""

    def test_generated_ddl_emits_check_fk_and_index(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")

        # XOR CHECK constraint — guards the known generator caveat
        assert (
            "CONSTRAINT [CK_Annotation_Source] CHECK "
            "((Channel_ID IS NOT NULL AND AnalysisSeries_ID IS NULL) "
            "OR (Channel_ID IS NULL AND AnalysisSeries_ID IS NOT NULL))"
        ) in sql

        # FK on the new lab arm
        assert (
            "ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT "
            "[FK_Annotation_AnalysisSeries_ID] FOREIGN KEY ([AnalysisSeries_ID]) "
            "REFERENCES [dbo].[AnalysisSeries] ([AnalysisSeries_ID]);"
        ) in sql

        # Series-time interval index
        assert (
            "CREATE INDEX [IX_Annotation_Series_Time] ON [dbo].[Annotation] "
            "([AnalysisSeries_ID], [StartTime], [EndTime]);"
        ) in sql
