"""Unit tests for the equipment lookup's model-kind columns.

Runs without a database — the pyodbc connection is a MagicMock, so the
assertions are on the SQL emitted and the dicts returned.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.v1.repositories import equipment_repository as er


def test_equipment_lookup_returns_the_model_kind():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [(7, "SAMPLER_001", 3, 3, "Sampler")]
    conn.cursor.return_value = cursor

    rows = er.get_equipment_lookup(conn)

    assert rows == [
        {
            "equipment_id": 7,
            "identifier": "SAMPLER_001",
            "model_id": 3,
            "equipment_kind_id": 3,
            "kind_name": "Sampler",
        }
    ]
    sql = cursor.execute.call_args_list[0].args[0]
    assert "[dbo].[EquipmentKind]" in sql
    assert "LEFT JOIN" in sql


def test_equipment_lookup_tolerates_an_unclassified_model():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [(1, "datamart", None, None, None)]
    conn.cursor.return_value = cursor

    assert er.get_equipment_lookup(conn) == [
        {
            "equipment_id": 1,
            "identifier": "datamart",
            "model_id": None,
            "equipment_kind_id": None,
            "kind_name": None,
        }
    ]
