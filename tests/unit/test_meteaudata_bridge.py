"""Unit tests for ``meteaudata_bridge.load_signal_context`` (Slice 11).

ADR 0005: a Channel's processing state is no longer a single ProcessingKind
string. It is the accumulated ChannelTrait set — the list of OperationKind
names applied to the Channel, keyed on its Stream_ID.

``load_signal_context`` therefore returns ``trait_names`` (a list[str]) instead
of the old scalar ``processing_kind_name``. These tests mock a pyodbc-style
cursor: the first ``execute`` resolves the single context row (``fetchone``);
the second ``execute`` resolves the trait rows (``fetchall``).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from open_dateaubase.meteaudata_bridge import load_signal_context

# The single context row, matching the SELECT column order:
# Stream_ID, Parameter_ID, ParameterName, Unit_ID, UnitName,
# Equipment_ID, EquipmentName, DataProvenanceName
_CONTEXT_ROW = (
    7,            # Stream_ID
    3, "TSS",     # Parameter_ID, ParameterName
    2, "mg/L",    # Unit_ID, UnitName
    9, "SC1000",  # Equipment_ID, EquipmentName
    "Measured",   # DataProvenanceName
)


def _make_conn(context_row, trait_rows):
    """Build a mock connection whose cursor returns context_row then trait_rows."""
    cursor = MagicMock()
    cursor.fetchone.return_value = context_row
    cursor.fetchall.return_value = trait_rows
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def test_returns_trait_names_list_from_multiple_operationkind_rows():
    """The accumulated ChannelTrait set is returned as a list of names."""
    trait_rows = [("Unprocessed",), ("OutlierRemoval",), ("Smoothing",)]
    conn, _ = _make_conn(_CONTEXT_ROW, trait_rows)

    out = load_signal_context(7, conn)

    assert out["trait_names"] == ["Unprocessed", "OutlierRemoval", "Smoothing"]
    # The scalar processing_kind_name contract is gone.
    assert "processing_kind_name" not in out


def test_trait_names_empty_when_no_traits():
    """A channel with no ChannelTrait rows yields an empty list, not None."""
    conn, _ = _make_conn(_CONTEXT_ROW, [])

    out = load_signal_context(7, conn)

    assert out["trait_names"] == []


def test_context_fields_resolved():
    """Parameter / unit / equipment / provenance are still resolved."""
    conn, _ = _make_conn(_CONTEXT_ROW, [("Unprocessed",)])

    out = load_signal_context(7, conn)

    assert out["channel_id"] == 7
    assert out["parameter"] == {"id": 3, "name": "TSS"}
    assert out["unit"] == "mg/L"
    assert out["equipment"] == {"id": 9, "name": "SC1000"}
    assert out["data_provenance"] == "Measured"


def test_trait_query_keyed_on_stream_id_against_channeltrait_operationkind():
    """The trait query joins ChannelTrait -> OperationKind, keyed on Stream_ID."""
    conn, cursor = _make_conn(_CONTEXT_ROW, [("Smoothing",)])

    load_signal_context(7, conn)

    # Second execute is the trait query.
    trait_call = cursor.execute.call_args_list[1]
    sql = trait_call.args[0]
    assert "[ChannelTrait]" in sql
    assert "[OperationKind]" in sql
    assert "ct.[Stream_ID] = ?" in sql
    # Bound to the requested channel (its Stream_ID).
    assert trait_call.args[1] == 7
    # No remnant of the removed ProcessingKind join.
    assert "ProcessingKind" not in sql


def test_missing_channel_raises_keyerror():
    conn, _ = _make_conn(None, [])

    with pytest.raises(KeyError):
        load_signal_context(999, conn)
