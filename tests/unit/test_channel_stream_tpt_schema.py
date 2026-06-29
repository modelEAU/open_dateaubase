"""Unit tests for Channel as a shared-PK subtype of Stream (ADR 0004, Slice 2).

Slice 2 converts ``Channel`` into a table-per-type (TPT) subtype of the
``Stream`` supertype using a shared primary key: ``Channel.Stream_ID`` is
both the PRIMARY KEY of ``Channel`` and a FOREIGN KEY to ``Stream.Stream_ID``.
The old identity surrogate ``Channel_ID`` is removed, and the self-FK
``ParentChannel_ID`` is retargeted from ``Channel.Channel_ID`` to the new
``Channel.Stream_ID`` PK.

These tests pin the dictionary (YAML) shape and assert the DDL generator
emits BOTH the PRIMARY KEY and the FOREIGN KEY on ``Stream_ID`` (guarding the
known generator caveat where some constraint YAML patterns were silently
dropped), and that the ``UQ_Channel_SignalStream`` unique index survives.
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
def channel(schema):
    return schema["Channel"]["table"]


class TestChannelSharedPKDictionary:
    """Channel's identity is now Stream_ID, shared with the Stream supertype."""

    def test_channel_id_column_is_gone(self, channel):
        names = {c["name"] for c in channel["columns"]}
        assert "Channel_ID" not in names

    def test_stream_id_is_the_primary_key(self, channel):
        cols = {c["name"]: c for c in channel["columns"]}
        assert "Stream_ID" in cols
        assert cols["Stream_ID"]["logical_type"] == "integer"
        assert cols["Stream_ID"].get("nullable", True) is False
        # Shared PK: NOT an identity column — the value comes from Stream.
        assert cols["Stream_ID"].get("identity", False) is False
        assert channel["primary_key"] == ["Stream_ID"]

    def test_stream_id_is_simultaneously_a_fk_to_stream(self, channel):
        cols = {c["name"]: c for c in channel["columns"]}
        fk = cols["Stream_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "Stream"
        assert fk["column"] == "Stream_ID"

    def test_parent_channel_id_targets_channel_stream_id(self, channel):
        cols = {c["name"]: c for c in channel["columns"]}
        fk = cols["ParentChannel_ID"].get("foreign_key")
        assert fk is not None
        assert fk["table"] == "Channel"
        assert fk["column"] == "Stream_ID"

    def test_subtype_columns_still_present(self, channel):
        names = {c["name"] for c in channel["columns"]}
        for col in (
            "SignalInterface_ID",
            "TagName",
            "ChannelKind_ID",
            "Parameter_ID",
            "DataProvenanceKind_ID",
            "ProducedByStep_ID",
            "ValueKind_ID",
            "Unit_ID",
        ):
            assert col in names

    def test_denormalised_port_column_dropped(self, channel):
        # F3: the denormalised port column is gone; the current port is resolved
        # from the active ChannelPortHistory row via vw_ChannelResolved.
        names = {c["name"] for c in channel["columns"]}
        assert "SignalInterfacePort_ID" not in names

    def test_uq_signal_stream_index_unchanged(self, channel):
        idx = {i["name"]: i for i in channel.get("indexes", [])}
        assert "UQ_Channel_SignalStream" in idx
        uq = idx["UQ_Channel_SignalStream"]
        assert uq["unique"] is True
        assert uq["columns"] == [
            "SignalInterface_ID",
            "TagName",
            "Parameter_ID",
            "DataProvenanceKind_ID",
            "ProducedByStep_ID",
        ]


class TestChannelSharedPKDDL:
    """The DDL generator emits Stream_ID as both PK and FK on Channel."""

    def test_generated_ddl_emits_pk_and_fk_on_stream_id(self, schema):
        sql = render_create_script(schema, version="0.0.0", platform="mssql")

        assert "CREATE TABLE [dbo].[Channel] (" in sql

        # PRIMARY KEY on Stream_ID — the shared TPT key
        assert "CONSTRAINT [PK_Channel] PRIMARY KEY ([Stream_ID])" in sql

        # FK from Stream_ID to Stream — guards the generator caveat that a
        # column carrying BOTH a PK and an FK still emits the FK.
        assert (
            "ALTER TABLE [dbo].[Channel] ADD CONSTRAINT "
            "[FK_Channel_Stream_ID] FOREIGN KEY ([Stream_ID]) "
            "REFERENCES [dbo].[Stream] ([Stream_ID]);"
        ) in sql

        # The descriptor uniqueness constraint still survives the rewrite.
        assert (
            "CREATE UNIQUE INDEX [UQ_Channel_SignalStream] ON [dbo].[Channel] "
            "([SignalInterface_ID], [TagName], [Parameter_ID], "
            "[DataProvenanceKind_ID], [ProducedByStep_ID]);"
        ) in sql
