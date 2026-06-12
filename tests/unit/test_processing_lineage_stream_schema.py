"""Unit tests for the ProcessingLineage Stream-FK schema (ADR 0004, Slice 6).

ADR 0004 generalizes ProcessingLineage *input* edges from a Channel to any
measurement Stream. The input-edge column is renamed Channel_ID -> Stream_ID
(non-NULL FK -> Stream), so a lab AnalysisSeries can feed a derived Channel.
The supporting backward-lineage index is renamed accordingly. The OUTPUT of a
step is unchanged: it is still identified by Channel.ProducedByStep_ID.

These tests pin the dictionary (YAML) shape and assert the DDL generator emits
the Stream FK + renamed index. They are red against the pre-Slice-6 YAML (which
had a Channel_ID column and IX_ProcessingLineage_Channel index) and green
against the new Stream-anchored YAML.
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
def lineage(schema):
    return schema["ProcessingLineage"]["table"]


class TestProcessingLineageStreamDictionary:
    """The ProcessingLineage YAML now carries a Stream_ID input anchor."""

    def test_channel_id_column_is_gone(self, lineage):
        cols = {c["name"] for c in lineage["columns"]}
        assert "Channel_ID" not in cols

    def test_stream_id_column_exists_and_is_not_null(self, lineage):
        cols = {c["name"]: c for c in lineage["columns"]}
        assert "Stream_ID" in cols
        # nullable must be explicitly false — the input anchor is mandatory.
        assert cols["Stream_ID"].get("nullable", True) is False

    def test_stream_id_fk_targets_stream(self, lineage):
        cols = {c["name"]: c for c in lineage["columns"]}
        fk = cols["Stream_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "Stream"
        assert fk["column"] == "Stream_ID"

    def test_processing_step_id_column_preserved(self, lineage):
        cols = {c["name"]: c for c in lineage["columns"]}
        assert "ProcessingStep_ID" in cols
        fk = cols["ProcessingStep_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "ProcessingStep"

    def test_slice_time_columns_preserved(self, lineage):
        cols = {c["name"] for c in lineage["columns"]}
        assert "StartTime" in cols
        assert "EndTime" in cols

    def test_stream_index_present(self, lineage):
        idx = {i["name"]: i for i in lineage.get("indexes", [])}
        assert "IX_ProcessingLineage_Stream" in idx
        assert idx["IX_ProcessingLineage_Stream"]["columns"] == ["Stream_ID"]

    def test_old_channel_index_is_gone(self, lineage):
        idx = {i["name"] for i in lineage.get("indexes", [])}
        assert "IX_ProcessingLineage_Channel" not in idx
        # the step traversal index is untouched
        assert "IX_Lineage_Step" in idx


class TestProcessingLineageStreamDDL:
    """The DDL generator emits the Stream FK + renamed index."""

    def test_generated_ddl_emits_stream_fk(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")
        assert (
            "ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT "
            "[FK_ProcessingLineage_Stream_ID] FOREIGN KEY ([Stream_ID]) "
            "REFERENCES [dbo].[Stream] ([Stream_ID]);"
        ) in sql

    def test_generated_ddl_emits_stream_index(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")
        assert (
            "CREATE INDEX [IX_ProcessingLineage_Stream] ON "
            "[dbo].[ProcessingLineage] ([Stream_ID]);"
        ) in sql

    def test_generated_ddl_drops_old_channel_index(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")
        assert "IX_ProcessingLineage_Channel" not in sql

    def test_generated_ddl_has_no_channel_fk_on_lineage(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")
        assert "FK_ProcessingLineage_Channel_ID" not in sql
