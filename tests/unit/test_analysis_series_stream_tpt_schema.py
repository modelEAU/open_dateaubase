"""Unit tests for AnalysisSeries as a shared-PK subtype of Stream (ADR 0004/0005, Slice 3).

Slice 3 converts ``AnalysisSeries`` into a table-per-type (TPT) subtype of the
``Stream`` supertype using a shared primary key: ``AnalysisSeries.Stream_ID`` is
both the PRIMARY KEY of ``AnalysisSeries`` and a FOREIGN KEY to
``Stream.Stream_ID``. The old identity surrogate ``AnalysisSeries_ID`` is
removed. This slice also removes the ``ProcessingKind_ID`` column entirely and
narrows the identity uniqueness constraint accordingly.

These tests pin the dictionary (YAML) shape and assert the DDL generator emits
BOTH the PRIMARY KEY and the FOREIGN KEY on ``Stream_ID`` (guarding the known
generator caveat where some constraint YAML patterns were silently dropped),
and that the narrowed ``UQ_AnalysisSeries_Identity`` constraint survives.
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
def analysis_series(schema):
    return schema["AnalysisSeries"]["table"]


class TestAnalysisSeriesSharedPKDictionary:
    """AnalysisSeries' identity is now Stream_ID, shared with the Stream supertype."""

    def test_analysis_series_id_column_is_gone(self, analysis_series):
        names = {c["name"] for c in analysis_series["columns"]}
        assert "AnalysisSeries_ID" not in names

    def test_stream_id_is_the_primary_key(self, analysis_series):
        cols = {c["name"]: c for c in analysis_series["columns"]}
        assert "Stream_ID" in cols
        assert cols["Stream_ID"]["logical_type"] == "integer"
        assert cols["Stream_ID"].get("nullable", True) is False
        # Shared PK: NOT an identity column — the value comes from Stream.
        assert cols["Stream_ID"].get("identity", False) is False
        assert analysis_series["primary_key"] == ["Stream_ID"]

    def test_stream_id_is_simultaneously_a_fk_to_stream(self, analysis_series):
        cols = {c["name"]: c for c in analysis_series["columns"]}
        fk = cols["Stream_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "Stream"
        assert fk["column"] == "Stream_ID"

    def test_processing_kind_id_column_is_gone(self, analysis_series):
        names = {c["name"] for c in analysis_series["columns"]}
        assert "ProcessingKind_ID" not in names

    def test_identity_unique_constraint_narrowed_to_three_columns(self, analysis_series):
        uqs = {u["name"]: u for u in analysis_series.get("unique_constraints", [])}
        assert "UQ_AnalysisSeries_Identity" in uqs
        assert uqs["UQ_AnalysisSeries_Identity"]["columns"] == [
            "Parameter_ID",
            "SamplingPoint_ID",
            "ValueKind_ID",
        ]

    def test_subtype_columns_still_present(self, analysis_series):
        names = {c["name"] for c in analysis_series["columns"]}
        for col in ("Name", "Parameter_ID", "SamplingPoint_ID", "ValueKind_ID", "Unit_ID"):
            assert col in names


class TestAnalysisSeriesSharedPKDDL:
    """The DDL generator emits Stream_ID as both PK and FK on AnalysisSeries."""

    def test_generated_ddl_emits_pk_fk_and_narrowed_unique(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")

        assert "CREATE TABLE [dbo].[AnalysisSeries] (" in sql

        # PRIMARY KEY on Stream_ID — the shared TPT key.
        assert "CONSTRAINT [PK_AnalysisSeries] PRIMARY KEY ([Stream_ID])" in sql

        # FK from Stream_ID to Stream — guards the generator caveat that a
        # column carrying BOTH a PK and an FK still emits the FK.
        assert (
            "ALTER TABLE [dbo].[AnalysisSeries] ADD CONSTRAINT "
            "[FK_AnalysisSeries_Stream_ID] FOREIGN KEY ([Stream_ID]) "
            "REFERENCES [dbo].[Stream] ([Stream_ID]);"
        ) in sql

        # The narrowed 3-column identity uniqueness constraint survives.
        assert (
            "CONSTRAINT [UQ_AnalysisSeries_Identity] UNIQUE "
            "([Parameter_ID], [SamplingPoint_ID], [ValueKind_ID])"
        ) in sql

        # ProcessingKind_ID is gone from the AnalysisSeries DDL entirely.
        assert "[FK_AnalysisSeries_ProcessingKind_ID]" not in sql
