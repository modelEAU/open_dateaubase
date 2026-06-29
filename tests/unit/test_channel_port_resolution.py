"""F3 regression: Channel.SignalInterfacePort_ID denorm column is dropped.

The current port is resolved from the active ChannelPortHistory row via the
vw_ChannelResolved view, and writes go through set_channel_active_port (the
single writer of the CPH active-row invariant). These pin:
  * reads come FROM the view, not the base Channel table;
  * the Channel INSERT no longer carries the dropped column;
  * set_channel_active_port closes-then-opens, no-ops when unchanged, and
    closes-only when cleared.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.v1.repositories import channel_repository


def test_channel_select_reads_from_resolved_view_not_base_table():
    sql = channel_repository._CHANNEL_SELECT
    assert "[dbo].[vw_ChannelResolved] c" in sql
    assert "FROM [dbo].[Channel] c" not in sql


def test_insert_channel_does_not_write_dropped_port_column():
    cursor = MagicMock()
    # stream mint -> 42; set_channel_active_port SELECT active -> None;
    # CPH INSERT -> 77; get_channel_by_id SELECT -> None
    cursor.fetchone.side_effect = [(42,), None, (77,), None]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    channel_repository.insert_channel(
        conn, {"signal_interface_id": 3, "tag_name": "t", "signal_interface_port_id": 5}
    )

    statements = [c.args[0] for c in cursor.execute.call_args_list]
    channel_insert = next(s for s in statements if "INSERT INTO [dbo].[Channel]" in s)
    assert "SignalInterfacePort_ID" not in channel_insert
    # The port is recorded as a ChannelPortHistory row instead.
    assert any("INSERT INTO [dbo].[ChannelPortHistory]" in s for s in statements)


def test_insert_channel_without_port_opens_no_cph_row():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [(42,), None]  # stream mint, get_channel_by_id
    conn = MagicMock()
    conn.cursor.return_value = cursor

    channel_repository.insert_channel(conn, {"signal_interface_id": 3, "tag_name": "t"})

    statements = [c.args[0] for c in cursor.execute.call_args_list]
    assert not any("ChannelPortHistory" in s for s in statements)


def test_set_active_port_unchanged_is_noop():
    cursor = MagicMock()
    cursor.fetchone.return_value = (10, 5)  # active row id=10, port=5
    new_id, closed_id = channel_repository.set_channel_active_port(cursor, 1, 5)
    assert (new_id, closed_id) == (None, 10)
    # Only the SELECT ran — no close, no open.
    assert cursor.execute.call_count == 1


def test_set_active_port_change_closes_then_opens():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [(10, 5), (10,), (11,)]  # active, closed id, new id
    new_id, closed_id = channel_repository.set_channel_active_port(cursor, 1, 7)
    assert (new_id, closed_id) == (11, 10)
    stmts = " ".join(c.args[0] for c in cursor.execute.call_args_list)
    assert "UPDATE [dbo].[ChannelPortHistory]" in stmts
    assert "INSERT INTO [dbo].[ChannelPortHistory]" in stmts


def test_set_active_port_clear_closes_without_opening():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [(10, 5), (10,)]  # active row, then closed id
    new_id, closed_id = channel_repository.set_channel_active_port(cursor, 1, None)
    assert (new_id, closed_id) == (None, 10)
    stmts = [c.args[0] for c in cursor.execute.call_args_list]
    assert any("UPDATE [dbo].[ChannelPortHistory]" in s for s in stmts)
    assert not any("INSERT INTO [dbo].[ChannelPortHistory]" in s for s in stmts)
