"""Regression: channel_repository must target the Channel PK column Stream_ID.

ADR 0004 made Stream_ID the Channel primary key (the Channel_ID column no longer
exists). The read/update/delete SQL in channel_repository still referenced
[Channel_ID], raising 'Invalid column name Channel_ID' against the v2 schema and
breaking get_channel / list_channels (and the Provenance panel that reuses them).

These pin the rename: the Channel-table PK references are Stream_ID, while the
external dict contract keeps the ``channel_id`` key.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.v1.repositories import channel_repository


def test_channel_select_uses_stream_id_not_channel_id():
    sql = channel_repository._CHANNEL_SELECT
    assert "c.[Stream_ID]" in sql
    assert "[Channel_ID]" not in sql
    # Parent self-join also keys on the PK.
    assert "parent.[Stream_ID] = c.[ParentChannel_ID]" in sql


def test_get_channel_by_id_queries_stream_id():
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    channel_repository.get_channel_by_id(conn, 20)

    executed = cursor.execute.call_args.args[0]
    assert "c.[Stream_ID] = ?" in executed
    assert "[Channel_ID]" not in executed


def test_delete_channel_targets_stream_id():
    cursor = MagicMock()
    cursor.rowcount = 1
    conn = MagicMock()
    conn.cursor.return_value = cursor

    channel_repository.delete_channel(conn, 20)

    executed = cursor.execute.call_args.args[0]
    assert "WHERE [Stream_ID]=?" in executed
    assert "[Channel_ID]" not in executed


def test_insert_channel_mints_stream_then_inserts_with_stream_id():
    cursor = MagicMock()
    # 1) Stream mint OUTPUT returns the new Stream_ID; 2) get_channel_by_id SELECT
    cursor.fetchone.side_effect = [(42,), None]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    channel_repository.insert_channel(conn, {"tag_name": "t", "parameter_id": 9})

    statements = [c.args[0] for c in cursor.execute.call_args_list]
    joined = " ".join(statements)
    # Stream supertype is minted first (no reliance on the invalid @@IDENTITY).
    assert "INSERT INTO [dbo].[Stream] ([StreamKind_ID])" in joined
    assert "@@IDENTITY" not in joined
    # Channel INSERT carries the explicit shared Stream_ID primary key...
    channel_insert = next(s for s in statements if "INSERT INTO [dbo].[Channel]" in s)
    assert "[Stream_ID]" in channel_insert
    # ...bound to the minted id.
    channel_call = next(
        c for c in cursor.execute.call_args_list
        if "INSERT INTO [dbo].[Channel]" in c.args[0]
    )
    assert channel_call.args[1] == 42
    conn.commit.assert_called_once()


def test_provision_contract_uses_channel_kind_not_role():
    """Guard the Channel role->kind rename on the L5X provision path: the schema
    field is channel_kind and the resolver is find_channel_kind_by_name (the stale
    channel_role / find_channel_role_by_name references 500'd /channels/provision)."""
    from api.v1.schemas.channel import ChannelProvisionIn
    from api.v1.repositories import signal_interface_repository

    assert "channel_kind" in ChannelProvisionIn.model_fields
    assert "channel_role" not in ChannelProvisionIn.model_fields
    assert hasattr(signal_interface_repository, "find_channel_kind_by_name")
    assert not hasattr(signal_interface_repository, "find_channel_role_by_name")


def test_get_channel_ids_for_equipment_selects_stream_id():
    cursor = MagicMock()
    cursor.fetchall.return_value = [(16,), (17,)]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    ids = channel_repository.get_channel_ids_for_equipment(conn, 5)

    executed = cursor.execute.call_args.args[0]
    assert "c.[Stream_ID]" in executed
    assert "[Channel_ID]" not in executed
    assert ids == [16, 17]
