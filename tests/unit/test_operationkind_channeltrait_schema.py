"""Unit tests for the ProcessingKind retirement (ADR 0005, Slice 4).

Slice 4 retires the conflated ``ProcessingKind`` lookup and replaces it with:

* ``OperationKind`` — a lookup table classifying what a single
  ``ProcessingStep`` does (one step = one OperationKind). The accumulated set
  of OperationKinds over a Channel's lineage forms its trait set.
* ``ChannelTrait`` — a (Stream_ID, OperationKind_ID) junction recording that
  accumulated set per Channel.

``ProcessingStep.ProcessingKind_ID`` is renamed/retargeted to
``OperationKind_ID`` (FK → OperationKind), and the ``ProcessingKind`` table is
deleted outright.

These tests pin the dictionary (YAML) shape and assert the DDL generator emits
ChannelTrait's composite PRIMARY KEY plus both FOREIGN KEYs, and ProcessingStep's
FK to OperationKind (guarding the known generator constraint-drop caveat).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.schema_migrate.loader import load_schema
from tools.schema_migrate.render import render_create_script

_TABLES_DIR = Path(__file__).parent.parent.parent / "schema_dictionary" / "tables"

# (ID, Name) the seed order/IDs are load-bearing — code references these IDs.
_EXPECTED_OPERATION_KINDS = [
    (1, "Unprocessed"),
    (2, "OutlierRemoval"),
    (3, "DriftCorrection"),
    (4, "FaultRemoval"),
    (5, "Smoothing"),
    (6, "Interpolation"),
    (7, "Reconstruction"),
]


@pytest.fixture
def schema():
    return load_schema(_TABLES_DIR)


class TestProcessingKindRetired:
    def test_processing_kind_table_is_gone(self, schema):
        assert "ProcessingKind" not in schema


class TestOperationKindDictionary:
    def test_operation_kind_table_exists(self, schema):
        assert "OperationKind" in schema

    def test_operation_kind_pk_is_non_identity_integer(self, schema):
        tbl = schema["OperationKind"]["table"]
        cols = {c["name"]: c for c in tbl["columns"]}
        assert tbl["primary_key"] == ["OperationKind_ID"]
        pk = cols["OperationKind_ID"]
        assert pk["logical_type"] == "integer"
        assert pk.get("nullable", True) is False
        # Manually-assigned lookup PK — values are referenced by code.
        assert pk.get("identity", False) is False

    def test_operation_kind_name_and_description_columns(self, schema):
        cols = {c["name"]: c for c in schema["OperationKind"]["table"]["columns"]}
        assert cols["Name"]["logical_type"] == "string"
        assert cols["Name"]["max_length"] == 50
        assert cols["Name"].get("nullable", True) is False
        assert cols["Description"]["logical_type"] == "string"
        assert cols["Description"]["max_length"] == 200
        assert cols["Description"].get("nullable", True) is True

    def test_operation_kind_seed_data_exact(self, schema):
        seed = schema["OperationKind"]["table"]["seed_data"]
        got = [(row["OperationKind_ID"], row["Name"]) for row in seed]
        assert got == _EXPECTED_OPERATION_KINDS


class TestProcessingStepRetargeted:
    def test_processing_step_has_operation_kind_fk(self, schema):
        cols = {c["name"]: c for c in schema["ProcessingStep"]["table"]["columns"]}
        assert "ProcessingKind_ID" not in cols
        assert "OperationKind_ID" in cols
        fk = cols["OperationKind_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "OperationKind"
        assert fk["column"] == "OperationKind_ID"


class TestChannelTraitDictionary:
    def test_channel_trait_table_exists(self, schema):
        assert "ChannelTrait" in schema

    def test_channel_trait_composite_pk(self, schema):
        tbl = schema["ChannelTrait"]["table"]
        assert tbl["primary_key"] == ["Stream_ID", "OperationKind_ID"]

    def test_channel_trait_both_fks(self, schema):
        cols = {c["name"]: c for c in schema["ChannelTrait"]["table"]["columns"]}
        stream_fk = cols["Stream_ID"].get("foreign_key")
        assert stream_fk == {"table": "Stream", "column": "Stream_ID"}
        op_fk = cols["OperationKind_ID"].get("foreign_key")
        assert op_fk == {"table": "OperationKind", "column": "OperationKind_ID"}
        assert cols["Stream_ID"].get("nullable", True) is False
        assert cols["OperationKind_ID"].get("nullable", True) is False

    def test_channel_trait_has_stream_lookup_index(self, schema):
        idx = {i["name"]: i for i in schema["ChannelTrait"]["table"].get("indexes", [])}
        # An index on [Stream_ID] supports the "traits of this channel" lookup.
        assert any(i["columns"] == ["Stream_ID"] for i in idx.values())


class TestRenderedDDL:
    """Guard the generator constraint-drop caveat: assert the rendered string."""

    @pytest.fixture
    def sql(self, schema):
        return render_create_script(schema, version="0.0.0", platform="mssql")

    def test_channel_trait_composite_pk_rendered(self, sql):
        assert (
            "CONSTRAINT [PK_ChannelTrait] PRIMARY KEY "
            "([Stream_ID], [OperationKind_ID])"
        ) in sql

    def test_channel_trait_both_fks_rendered(self, sql):
        assert (
            "ALTER TABLE [dbo].[ChannelTrait] ADD CONSTRAINT "
            "[FK_ChannelTrait_Stream_ID] FOREIGN KEY ([Stream_ID]) "
            "REFERENCES [dbo].[Stream] ([Stream_ID]);"
        ) in sql
        assert (
            "ALTER TABLE [dbo].[ChannelTrait] ADD CONSTRAINT "
            "[FK_ChannelTrait_OperationKind_ID] FOREIGN KEY ([OperationKind_ID]) "
            "REFERENCES [dbo].[OperationKind] ([OperationKind_ID]);"
        ) in sql

    def test_processing_step_fk_to_operation_kind_rendered(self, sql):
        assert (
            "ALTER TABLE [dbo].[ProcessingStep] ADD CONSTRAINT "
            "[FK_ProcessingStep_OperationKind_ID] FOREIGN KEY ([OperationKind_ID]) "
            "REFERENCES [dbo].[OperationKind] ([OperationKind_ID]);"
        ) in sql
