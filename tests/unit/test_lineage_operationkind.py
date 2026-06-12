"""Unit tests for the processing-kind -> operation-kind rename (Slice 12, ADR 0005).

These pin the new contract end-to-end through the lineage write path and the
raw-SQL lineage module:

* ``lineage_service.persist_processing`` accepts ``operation_kind_id`` and
  forwards it (same name) to ``meteaudata_bridge.record_processing``.
* ``meteaudata_bridge.record_processing`` writes ``OperationKind_ID`` on
  ProcessingStep and ``Stream_ID`` (not the dropped ``Channel_ID``) on
  ProcessingLineage input edges.
* ``open_dateaubase.lineage`` forward/backward/tree SQL targets the new schema:
  ``ProcessingStep.OperationKind_ID``, ``ProcessingLineage.Stream_ID``,
  ``Channel.Stream_ID`` / ``Channel.ProducedByStep_ID`` — and never references
  the dropped ``ProcessingKind`` table or ``ProcessingLineage.Channel_ID``.

They are red against the pre-Slice-12 code (which used ``processing_kind_id`` and
the old RoleInProcessingStep / Channel_ID SQL) and green against the new code.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from open_dateaubase import lineage
from api.v1.services import lineage_service


# ---------------------------------------------------------------------------
# lineage_service.persist_processing forwards operation_kind_id
# ---------------------------------------------------------------------------


def test_persist_processing_forwards_operation_kind_id():
    conn = MagicMock()
    with patch.object(
        lineage_service, "record_processing", return_value=42
    ) as rec:
        step_id = lineage_service.persist_processing(
            conn,
            source_metadata_ids=[1, 2],
            method_name="outlier_removal",
            method_version="meteaudata 0.5.1",
            operation_kind_id=2,
            method_parameters={"window": 5},
            executed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            executed_by_person_id=None,
        )

    assert step_id == 42
    kwargs = rec.call_args.kwargs
    # New contract: forwarded under the operation_kind_id name.
    assert kwargs["operation_kind_id"] == 2
    assert "processing_kind_id" not in kwargs


def test_persist_processing_has_no_processing_kind_id_param():
    import inspect

    params = inspect.signature(lineage_service.persist_processing).parameters
    assert "operation_kind_id" in params
    assert "processing_kind_id" not in params


# ---------------------------------------------------------------------------
# meteaudata_bridge.record_processing writes OperationKind_ID + Stream_ID
# ---------------------------------------------------------------------------


def test_record_processing_writes_operationkind_and_stream_id():
    from open_dateaubase.meteaudata_bridge import record_processing

    cursor = MagicMock()
    # Idempotency check returns no existing row; then OUTPUT returns the new ID.
    cursor.fetchone.side_effect = [None, (7,)]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    step_id = record_processing(
        source_metadata_ids=[10, 11],
        method_name="smoothing",
        method_version=None,
        operation_kind_id=5,
        method_parameters={"window": 3},
        executed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        executed_by_person_id=None,
        conn=conn,
    )

    assert step_id == 7

    executed_sql = " ".join(call.args[0] for call in cursor.execute.call_args_list)
    # ProcessingStep carries OperationKind_ID, not the dropped ProcessingKind_ID.
    assert "[OperationKind_ID]" in executed_sql
    assert "ProcessingKind" not in executed_sql
    # Input edges land on ProcessingLineage.Stream_ID (Channel_ID was dropped).
    assert "[Stream_ID]" in executed_sql
    assert (
        "INSERT INTO [dbo].[ProcessingLineage] ([ProcessingStep_ID], [Channel_ID])"
        not in executed_sql
    )
    # operation_kind_id (5) is bound on the INSERT of the step.
    insert_call = cursor.execute.call_args_list[1]
    assert 5 in insert_call.args


def test_record_processing_has_no_processing_kind_id_param():
    import inspect

    from open_dateaubase.meteaudata_bridge import record_processing

    params = inspect.signature(record_processing).parameters
    assert "operation_kind_id" in params
    assert "processing_kind_id" not in params


# ---------------------------------------------------------------------------
# lineage raw SQL targets the new schema
# ---------------------------------------------------------------------------


def _run_and_capture(func, *args):
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value = cursor
    func(*args, conn)
    return " ".join(call.args[0] for call in cursor.execute.call_args_list)


@pytest.mark.parametrize(
    "func",
    [lineage.get_lineage_forward, lineage.get_lineage_backward, lineage.get_full_lineage_tree],
)
def test_lineage_sql_uses_operationkind_and_stream_not_processingkind(func):
    sql = _run_and_capture(func, 99)
    assert "OperationKind_ID" in sql
    # The dropped table / column must not appear.
    assert "ProcessingKind" not in sql
    assert "[Channel_ID]" not in sql
    # New edge model: ProcessingLineage.Stream_ID + Channel.ProducedByStep_ID.
    assert "[Stream_ID]" in sql
    assert "ProducedByStep_ID" in sql
    # The dropped role column must not be referenced.
    assert "RoleInProcessingStep" not in sql


def test_forward_lineage_emits_operation_kind_id_key():
    cursor = MagicMock()
    # One step row producing two output channels.
    cursor.fetchall.return_value = [
        (1, "step", None, "m", "v", 5, "{}", None, None, 20),
        (1, "step", None, "m", "v", 5, "{}", None, None, 21),
    ]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    out = lineage.get_lineage_forward(10, conn)

    assert len(out) == 1
    step = out[0]["processing_step"]
    assert step["OperationKind_ID"] == 5
    assert "ProcessingKind_ID" not in step
    assert out[0]["output_channel_ids"] == [20, 21]


def test_full_lineage_tree_nodes_carry_operation_kind_id():
    cursor = MagicMock()
    # ancestor rows then descendant rows: (chan, step, name, opkind, other, depth)
    cursor.fetchall.side_effect = [
        [(3, 1, "clean", 2, 5, 1)],  # ancestors
        [(7, 9, "smooth", 5, 5, 1)],  # descendants
    ]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    tree = lineage.get_full_lineage_tree(5, conn)

    assert tree["channel_id"] == 5
    assert tree["parents"][0]["operation_kind_id"] == 2
    assert tree["children"][0]["operation_kind_id"] == 5
    assert "processing_kind_id" not in tree["parents"][0]
