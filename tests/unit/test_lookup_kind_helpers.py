"""Unit tests for the generic (ID, Name, Description) "kind" CRUD helpers in
api.v1.repositories.lookup_repository.

These run without a database — they patch the pyodbc connection with MagicMock
and assert on the SQL emitted and the dicts returned. They lock the behavior of
``_list_kinds``/``_insert_kind``/``_update_kind``/``_delete_kind`` and the named
wrappers that delegate to them (Phase 4a de-duplication).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.v1.repositories import lookup_repository as lr


def _conn(fetchall=None, fetchone=None, rowcount=1):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall or []
    cursor.fetchone.return_value = fetchone
    cursor.rowcount = rowcount
    conn.cursor.return_value = cursor
    return conn, cursor


def _sql(cursor):
    return "\n".join(call.args[0] for call in cursor.execute.call_args_list)


def test_list_kinds_maps_rows_to_id_key():
    conn, cursor = _conn(fetchall=[(1, "A", "desc-a"), (2, "B", None)])
    rows = lr._list_kinds(conn, "BinKind", "BinKind_ID", "bin_kind_id")
    assert rows == [
        {"bin_kind_id": 1, "name": "A", "description": "desc-a"},
        {"bin_kind_id": 2, "name": "B", "description": None},
    ]
    sql = _sql(cursor)
    assert "FROM [dbo].[BinKind]" in sql and "ORDER BY [BinKind_ID]" in sql


def test_insert_kind_parameterizes_values_and_commits():
    conn, cursor = _conn(fetchone=(7, "New", "d"))
    out = lr._insert_kind(conn, "CampaignKind", "CampaignKind_ID", "campaign_kind_id", "New", "d")
    assert out == {"campaign_kind_id": 7, "name": "New", "description": "d"}
    # name/description go through ? placeholders, not string-formatted into SQL
    assert cursor.execute.call_args.args[1:] == ("New", "d")
    assert "INSERT INTO [dbo].[CampaignKind]" in _sql(cursor)
    conn.commit.assert_called_once()


def test_update_kind_returns_none_when_row_missing():
    conn, cursor = _conn(fetchone=None)
    out = lr._update_kind(
        conn, "ProcedureKind", "ProcedureKind_ID", "procedure_kind_id", 99, "x", None
    )
    assert out is None
    assert cursor.execute.call_args.args[1:] == ("x", None, 99)


def test_delete_kind_reports_rows_affected():
    conn, cursor = _conn(rowcount=0)
    assert lr._delete_kind(conn, "ControllerKind", "ControllerKind_ID", 3) is False
    conn, cursor = _conn(rowcount=1)
    assert lr._delete_kind(conn, "ControllerKind", "ControllerKind_ID", 3) is True


def test_insert_rolls_back_on_error():
    conn, cursor = _conn()
    cursor.execute.side_effect = RuntimeError("boom")
    try:
        lr._insert_kind(conn, "CampaignKind", "CampaignKind_ID", "campaign_kind_id", "x")
    except RuntimeError:
        pass
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()


def test_named_wrapper_targets_correct_table_and_key():
    # get_das_kinds must hit DataAcquisitionSystemKind and emit das_kind_id.
    conn, cursor = _conn(fetchall=[(5, "SCADA", None)])
    rows = lr.get_das_kinds(conn)
    assert rows == [{"das_kind_id": 5, "name": "SCADA", "description": None}]
    assert "FROM [dbo].[DataAcquisitionSystemKind]" in _sql(cursor)


def test_sample_material_kind_wrappers_target_table_and_key():
    conn, cursor = _conn(fetchall=[(10, "mixed liquor", "desc")])
    rows = lr.get_sample_material_kinds(conn)
    assert rows == [{"sample_material_kind_id": 10, "name": "mixed liquor", "description": "desc"}]
    assert "FROM [dbo].[SampleMaterialKind]" in _sql(cursor)

    conn, cursor = _conn(fetchone=(11, "digestate", None))
    out = lr.insert_sample_material_kind(conn, "digestate")
    assert out == {"sample_material_kind_id": 11, "name": "digestate", "description": None}
    assert "INSERT INTO [dbo].[SampleMaterialKind]" in _sql(cursor)
