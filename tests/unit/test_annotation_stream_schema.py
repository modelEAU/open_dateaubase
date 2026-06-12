"""Unit tests for the Annotation Stream-FK schema (ADR 0004, Slice 5).

ADR 0004 retires the stream-level XOR arc (Channel_ID xor AnalysisSeries_ID)
in favour of the materialized Stream supertype. Annotation now anchors to a
single non-NULL Stream_ID FK -> Stream, covering sensor Channels and lab
AnalysisSeries uniformly. The XOR CHECK (CK_Annotation_Source) and the two
per-arm interval indexes are gone, replaced by one Stream-keyed index.

These tests pin the dictionary (YAML) shape and assert the DDL generator emits
the Stream FK + index and no longer emits the retired CHECK. They are red
against the pre-Slice-5 YAML (which had the two arm columns + XOR + two indexes)
and green against the new single-anchor YAML.
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


class TestAnnotationStreamDictionary:
    """The Annotation YAML now carries a single Stream_ID anchor."""

    def test_channel_id_column_is_gone(self, annotation):
        cols = {c["name"] for c in annotation["columns"]}
        assert "Channel_ID" not in cols

    def test_analysis_series_id_column_is_gone(self, annotation):
        cols = {c["name"] for c in annotation["columns"]}
        assert "AnalysisSeries_ID" not in cols

    def test_stream_id_column_exists_and_is_not_null(self, annotation):
        cols = {c["name"]: c for c in annotation["columns"]}
        assert "Stream_ID" in cols
        # nullable must be explicitly false — the single anchor is mandatory.
        assert cols["Stream_ID"].get("nullable", True) is False

    def test_stream_id_fk_targets_stream(self, annotation):
        cols = {c["name"]: c for c in annotation["columns"]}
        fk = cols["Stream_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "Stream"
        assert fk["column"] == "Stream_ID"

    def test_observation_id_point_link_preserved(self, annotation):
        cols = {c["name"]: c for c in annotation["columns"]}
        assert "Observation_ID" in cols
        fk = cols["Observation_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "Observation"

    def test_xor_check_constraint_is_gone(self, annotation):
        checks = annotation.get("check_constraints") or []
        names = {c.get("name") for c in checks}
        assert "CK_Annotation_Source" not in names

    def test_single_stream_time_index_present(self, annotation):
        idx = {i["name"]: i for i in annotation.get("indexes", [])}
        assert "IX_Annotation_Stream_Time" in idx
        assert idx["IX_Annotation_Stream_Time"]["columns"] == [
            "Stream_ID",
            "StartTime",
            "EndTime",
        ]

    def test_old_per_arm_indexes_are_gone(self, annotation):
        idx = {i["name"] for i in annotation.get("indexes", [])}
        assert "IX_Annotation_Channel_Time" not in idx
        assert "IX_Annotation_Series_Time" not in idx
        # the author index is untouched
        assert "IX_Annotation_Author" in idx


class TestAnnotationStreamDDL:
    """The DDL generator emits the Stream FK + index and drops the XOR CHECK."""

    def test_generated_ddl_emits_stream_fk(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")
        assert (
            "ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT "
            "[FK_Annotation_Stream_ID] FOREIGN KEY ([Stream_ID]) "
            "REFERENCES [dbo].[Stream] ([Stream_ID]);"
        ) in sql

    def test_generated_ddl_emits_stream_time_index(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")
        assert (
            "CREATE INDEX [IX_Annotation_Stream_Time] ON [dbo].[Annotation] "
            "([Stream_ID], [StartTime], [EndTime]);"
        ) in sql

    def test_generated_ddl_drops_xor_check(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")
        assert "CK_Annotation_Source" not in sql

    def test_generated_ddl_drops_old_per_arm_indexes(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")
        assert "IX_Annotation_Channel_Time" not in sql
        assert "IX_Annotation_Series_Time" not in sql
