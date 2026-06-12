"""Unit tests for the Stream supertype schema (ADR 0004, Slice 1).

ADR 0004 materializes ``Stream`` as a stored supertype: a ``Stream`` row is
the universal identity of any measurement stream (sensor Channel or lab
AnalysisSeries). This slice is purely additive — it introduces two new
dictionary tables and nothing references them yet:

- ``StreamKind`` — a controlled-vocabulary lookup (Sensor / Lab) used as the
  discriminator on ``Stream``.
- ``Stream`` — the stored supertype, with an identity surrogate PK
  (``Stream_ID``) and a non-NULL ``StreamKind_ID`` FK to ``StreamKind``.

These tests pin the dictionary (YAML) shape and assert the DDL generator
emits the PRIMARY KEY and the FOREIGN KEY, guarding against the known
generator caveat where some constraint YAML patterns were silently dropped.
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
def stream(schema):
    return schema["Stream"]["table"]


@pytest.fixture
def stream_kind(schema):
    return schema["StreamKind"]["table"]


class TestStreamKindDictionary:
    """The StreamKind lookup table carries the discriminator vocabulary."""

    def test_stream_kind_table_exists(self, schema):
        assert "StreamKind" in schema

    def test_stream_kind_id_is_non_identity_pk(self, stream_kind):
        cols = {c["name"]: c for c in stream_kind["columns"]}
        assert "StreamKind_ID" in cols
        assert cols["StreamKind_ID"]["logical_type"] == "integer"
        assert cols["StreamKind_ID"].get("nullable", True) is False
        # Lookups use manually-assigned IDs, not identity (mirrors QualityCode)
        assert cols["StreamKind_ID"].get("identity", False) is False
        assert stream_kind["primary_key"] == ["StreamKind_ID"]

    def test_stream_kind_name_column(self, stream_kind):
        cols = {c["name"]: c for c in stream_kind["columns"]}
        assert cols["Name"]["logical_type"] == "string"
        assert cols["Name"]["max_length"] == 50
        assert cols["Name"].get("nullable", True) is False

    def test_stream_kind_description_column(self, stream_kind):
        cols = {c["name"]: c for c in stream_kind["columns"]}
        assert cols["Description"]["logical_type"] == "string"
        assert cols["Description"]["max_length"] == 200
        assert cols["Description"].get("nullable", True) is True

    def test_stream_kind_seed_has_exactly_two_entries(self, stream_kind):
        seed = stream_kind.get("seed_data") or []
        assert len(seed) == 2
        by_id = {row["StreamKind_ID"]: row for row in seed}
        assert by_id[1]["Name"] == "Sensor"
        assert by_id[2]["Name"] == "Lab"


class TestStreamDictionary:
    """The Stream supertype carries an identity PK and the StreamKind FK."""

    def test_stream_table_exists(self, schema):
        assert "Stream" in schema

    def test_stream_id_is_identity_pk(self, stream):
        cols = {c["name"]: c for c in stream["columns"]}
        assert "Stream_ID" in cols
        assert cols["Stream_ID"]["logical_type"] == "integer"
        assert cols["Stream_ID"].get("identity", False) is True
        assert cols["Stream_ID"].get("nullable", True) is False
        assert stream["primary_key"] == ["Stream_ID"]

    def test_stream_kind_id_is_non_null_fk(self, stream):
        cols = {c["name"]: c for c in stream["columns"]}
        assert "StreamKind_ID" in cols
        assert cols["StreamKind_ID"]["logical_type"] == "integer"
        assert cols["StreamKind_ID"].get("nullable", True) is False
        fk = cols["StreamKind_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "StreamKind"
        assert fk["column"] == "StreamKind_ID"

    def test_stream_is_minimal(self, stream):
        # Supertype stays minimal — only the surrogate PK and discriminator.
        names = {c["name"] for c in stream["columns"]}
        assert names == {"Stream_ID", "StreamKind_ID"}


class TestStreamDDL:
    """The DDL generator emits the Stream table, its PK, and the FK."""

    def test_generated_ddl_emits_stream_table_pk_and_fk(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")

        # The Stream table is created
        assert "CREATE TABLE [dbo].[Stream] (" in sql

        # PRIMARY KEY on Stream_ID
        assert "CONSTRAINT [PK_Stream] PRIMARY KEY ([Stream_ID])" in sql

        # FK from StreamKind_ID to StreamKind — guards the generator caveat
        assert (
            "ALTER TABLE [dbo].[Stream] ADD CONSTRAINT "
            "[FK_Stream_StreamKind_ID] FOREIGN KEY ([StreamKind_ID]) "
            "REFERENCES [dbo].[StreamKind] ([StreamKind_ID]);"
        ) in sql
