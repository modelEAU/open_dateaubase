"""Unit tests for the resolved provenance graph (Provenance panel backend).

Covers:
* ``open_dateaubase.lineage.get_traits_for_stream`` — SQL targets ChannelTrait +
  OperationKind and maps rows to ``{operation_kind_id, name}``.
* ``open_dateaubase.lineage.get_processing_step_detail`` — resolves a step with
  its OperationKind name, executor name, and multi-input / output Stream_IDs.
* ``api.v1.services.lineage_service.resolved_provenance`` — composes the DAG with
  node resolution (channel vs lab series) and per-step detail, exercising the
  showcase DAG: CH-7→CH-12→CH-18, plus lab LAB-3, fused into CH-22.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from open_dateaubase import lineage
from api.v1.services import lineage_service


# ---------------------------------------------------------------------------
# get_traits_for_stream
# ---------------------------------------------------------------------------


def test_get_traits_for_stream_sql_and_mapping():
    cursor = MagicMock()
    cursor.fetchall.return_value = [(2, "OutlierRemoval"), (5, "Smoothing")]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    traits = lineage.get_traits_for_stream(18, conn)

    sql = cursor.execute.call_args.args[0]
    assert "[ChannelTrait]" in sql
    assert "[OperationKind]" in sql
    assert "[Stream_ID]" in sql
    assert traits == [
        {"operation_kind_id": 2, "name": "OutlierRemoval"},
        {"operation_kind_id": 5, "name": "Smoothing"},
    ]


def test_get_traits_for_stream_empty():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value = cursor
    assert lineage.get_traits_for_stream(7, conn) == []


# ---------------------------------------------------------------------------
# get_processing_step_detail
# ---------------------------------------------------------------------------


def test_get_processing_step_detail_resolves_multi_input_and_executor():
    cursor = MagicMock()
    # 1) step row, 2) input Stream_IDs (multi-input), 3) output Stream_IDs
    cursor.fetchone.return_value = (
        3, "lab gap-fill", "desc", "lab_anchored_gapfill", "meteaudata 0.6.0",
        6, "Interpolation", '{"max_gap_h": 12}',
        datetime(2026, 5, 3, 9, 20, tzinfo=timezone.utc), 4, "Jean-David", "Therrien",
    )
    cursor.fetchall.side_effect = [[(3,), (18,)], [(22,)]]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    detail = lineage.get_processing_step_detail(3, conn)

    assert detail is not None
    assert detail["operation_kind_name"] == "Interpolation"
    assert detail["method_name"] == "lab_anchored_gapfill"
    assert detail["executed_by_name"] == "Jean-David Therrien"
    # Multi-input transform: both inputs surface.
    assert detail["input_stream_ids"] == [3, 18]
    assert detail["output_stream_ids"] == [22]
    join_sql = " ".join(c.args[0] for c in cursor.execute.call_args_list)
    assert "[ProcessingLineage]" in join_sql
    assert "ProducedByStep_ID" in join_sql


def test_get_processing_step_detail_missing_returns_none():
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor
    assert lineage.get_processing_step_detail(999, conn) is None


def test_get_processing_step_detail_null_person_name():
    cursor = MagicMock()
    cursor.fetchone.return_value = (
        2, "smooth", None, "moving_average", "meteaudata 0.5.1",
        5, "Smoothing", "{}", None, None, None, None,
    )
    cursor.fetchall.side_effect = [[(12,)], [(18,)]]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    detail = lineage.get_processing_step_detail(2, conn)
    assert detail["executed_by_name"] is None


# ---------------------------------------------------------------------------
# resolved_provenance — orchestration over the showcase DAG
# ---------------------------------------------------------------------------


def _channel(stream_id, param, *, derived, provenance, equip=None, vkind=1):
    return {
        "channel_id": stream_id,
        "parameter_name": param,
        "unit_name": "mg/L",
        "value_kind_id": vkind,
        "equipment_identifier": equip,
        "tag_name": f"tag-{stream_id}",
        "data_provenance_kind_name": provenance,
        "produced_by_step_id": 99 if derived else None,
        "parent_channel_id": None,
    }


def test_resolved_provenance_builds_showcase_graph():
    root = 22
    tree = {
        "channel_id": root,
        "parents": [
            {"channel_id": 18, "processing_step_id": 3, "processing_step_name": "gap-fill",
             "operation_kind_id": 6, "child_channel_id": 22, "depth": 1},
            {"channel_id": 3, "processing_step_id": 3, "processing_step_name": "gap-fill",
             "operation_kind_id": 6, "child_channel_id": 22, "depth": 1},
            {"channel_id": 12, "processing_step_id": 2, "processing_step_name": "smooth",
             "operation_kind_id": 5, "child_channel_id": 18, "depth": 2},
            {"channel_id": 7, "processing_step_id": 1, "processing_step_name": "outlier",
             "operation_kind_id": 2, "child_channel_id": 12, "depth": 3},
        ],
        "children": [],
    }

    channels = {
        22: _channel(22, "TSS", derived=True, provenance="Derived"),
        18: _channel(18, "TSS", derived=True, provenance="Derived"),
        12: _channel(12, "TSS", derived=True, provenance="Derived"),
        7: _channel(7, "TSS", derived=False, provenance="Sensor", equip="ana-2"),
    }
    series = {
        3: {"analysis_series_id": 3, "name": "TSS lab", "parameter_name": "TSS",
            "sampling_point_label": "Effluent", "unit_name": "mg/L",
            "value_kind_id": 1, "campaign_name": "WRRF"},
    }
    traits = {
        22: [{"operation_kind_id": 2, "name": "OutlierRemoval"},
             {"operation_kind_id": 5, "name": "Smoothing"},
             {"operation_kind_id": 6, "name": "Interpolation"}],
        18: [{"operation_kind_id": 2, "name": "OutlierRemoval"},
             {"operation_kind_id": 5, "name": "Smoothing"}],
        12: [{"operation_kind_id": 2, "name": "OutlierRemoval"}],
        7: [{"operation_kind_id": 1, "name": "Unprocessed"}],
        3: [],
    }
    steps = {
        1: {"processing_step_id": 1, "operation_kind_name": "OutlierRemoval",
            "input_stream_ids": [7], "output_stream_ids": [12]},
        2: {"processing_step_id": 2, "operation_kind_name": "Smoothing",
            "input_stream_ids": [12], "output_stream_ids": [18]},
        3: {"processing_step_id": 3, "operation_kind_name": "Interpolation",
            "input_stream_ids": [3, 18], "output_stream_ids": [22]},
    }

    conn = MagicMock()
    with patch.object(lineage_service, "get_full_lineage_tree", return_value=tree), \
         patch.object(lineage_service.channel_repository, "get_channel_by_id",
                      side_effect=lambda c, sid: channels.get(sid)), \
         patch.object(lineage_service.ingestion_repository, "get_analysis_series_by_id",
                      side_effect=lambda c, sid: series.get(sid)), \
         patch.object(lineage_service, "get_traits_for_stream",
                      side_effect=lambda sid, c: traits.get(sid, [])), \
         patch.object(lineage_service, "get_processing_step_detail",
                      side_effect=lambda sid, c: steps.get(sid)):
        graph = lineage_service.resolved_provenance(conn, root)

    assert graph["root_id"] == 22
    nodes_by_id = {n["stream_id"]: n for n in graph["nodes"]}
    assert set(nodes_by_id) == {3, 7, 12, 18, 22}

    # Root: derived, marked root, full trait union.
    rootn = nodes_by_id[22]
    assert rootn["is_root"] is True
    assert rootn["is_derived"] is True
    assert [t["name"] for t in rootn["traits"]] == [
        "OutlierRemoval", "Smoothing", "Interpolation"
    ]

    # Lab ancestor resolves to a series node, not a channel.
    labn = nodes_by_id[3]
    assert labn["kind"] == "series"
    assert labn["provenance_kind_name"] == "Laboratory"
    assert labn["analysis_series_id"] == 3
    assert labn["sampling_point_label"] == "Effluent"

    # Raw sensor source: a channel, not derived.
    rawn = nodes_by_id[7]
    assert rawn["kind"] == "channel"
    assert rawn["is_derived"] is False
    assert rawn["equipment_identifier"] == "ana-2"

    # Three ancestor steps; the fusion step keeps both inputs.
    assert len(graph["ancestors"]) == 3
    fusion = next(s for s in graph["ancestors"] if s["processing_step_id"] == 3)
    assert fusion["input_stream_ids"] == [3, 18]
    assert graph["descendants"] == []
