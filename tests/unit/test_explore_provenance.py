"""Unit tests for the Data Explorer Provenance panel helpers.

Pure functions only — no Streamlit runtime (the _in_streamlit_run() guard keeps
importing the page from running main()). Exercises the showcase DAG returned by
GET /lineage/streams/{id}/provenance: raw CH-7 -> CH-12 -> CH-18, fused with lab
LAB-3 into CH-22.
"""

from __future__ import annotations

from unittest.mock import patch

from app.pages import explore


def _node(sid, kind, *, derived, prov, label, traits=None):
    return {
        "stream_id": sid,
        "kind": kind,
        "label": label,
        "is_derived": derived,
        "provenance_kind_name": prov,
        "traits": traits or [],
        "channel_id": sid if kind == "channel" else None,
        "analysis_series_id": sid if kind == "series" else None,
    }


def _showcase_graph():
    return {
        "root_id": 22,
        "nodes": [
            _node(22, "channel", derived=True, prov="Derived", label="TSS reconstructed",
                  traits=[{"operation_kind_id": 6, "name": "Interpolation"}]),
            _node(18, "channel", derived=True, prov="Derived", label="TSS smoothed"),
            _node(12, "channel", derived=True, prov="Derived", label="TSS outlier-free"),
            _node(7, "channel", derived=False, prov="Sensor", label="TSS raw"),
            _node(3, "series", derived=False, prov="Laboratory", label="TSS lab @ Effluent"),
        ],
        "ancestors": [
            {"processing_step_id": 1, "operation_kind_name": "OutlierRemoval",
             "method_name": "mad_outlier_removal", "input_stream_ids": [7],
             "output_stream_ids": [12]},
            {"processing_step_id": 2, "operation_kind_name": "Smoothing",
             "method_name": "moving_average", "input_stream_ids": [12],
             "output_stream_ids": [18]},
            {"processing_step_id": 3, "operation_kind_name": "Interpolation",
             "method_name": "lab_anchored_gapfill", "input_stream_ids": [3, 18],
             "output_stream_ids": [22]},
        ],
        "descendants": [],
    }


# ---------------------------------------------------------------------------
# ancestor / descendant stream id collection
# ---------------------------------------------------------------------------


def test_ancestor_stream_ids_excludes_root_includes_lab_and_intermediates():
    graph = _showcase_graph()
    assert explore._ancestor_stream_ids(graph, 22) == [3, 7, 12, 18]


def test_descendant_stream_ids_empty_for_final_stream():
    graph = _showcase_graph()
    assert explore._descendant_stream_ids(graph, 22) == []


def test_descendant_stream_ids_for_mid_chain():
    # Re-root conceptually at CH-12: its descendants live in the "descendants" list.
    graph = {
        "root_id": 12,
        "nodes": [],
        "ancestors": [],
        "descendants": [
            {"processing_step_id": 2, "operation_kind_name": "Smoothing",
             "input_stream_ids": [12], "output_stream_ids": [18]},
            {"processing_step_id": 3, "operation_kind_name": "Interpolation",
             "input_stream_ids": [3, 18], "output_stream_ids": [22]},
        ],
    }
    assert explore._descendant_stream_ids(graph, 12) == [3, 18, 22]


# ---------------------------------------------------------------------------
# ancestor step ordering (nearest-to-root first)
# ---------------------------------------------------------------------------


def test_ordered_ancestor_steps_nearest_first():
    graph = _showcase_graph()
    order = explore._ordered_ancestor_steps(graph, 22)
    assert [s["processing_step_id"] for s in order] == [3, 2, 1]


def test_ordered_ancestor_steps_empty_for_raw():
    graph = {"root_id": 7, "nodes": [], "ancestors": [], "descendants": []}
    assert explore._ordered_ancestor_steps(graph, 7) == []


# ---------------------------------------------------------------------------
# Graphviz DOT
# ---------------------------------------------------------------------------


def test_build_dag_dot_marks_root_and_draws_fusion_edges():
    graph = _showcase_graph()
    nodes = {n["stream_id"]: n for n in graph["nodes"]}
    dot = explore._build_dag_dot(graph, nodes, 22)

    assert dot.startswith("digraph prov")
    # Root node is emphasised.
    assert '"22" [label="TSS reconstructed"' in dot
    assert "penwidth=2" in dot
    # Multi-input fusion: both LAB-3 and CH-18 point at CH-22.
    assert '"3" -> "22"' in dot
    assert '"18" -> "22"' in dot
    assert '"7" -> "12"' in dot
    assert 'label="Interpolation"' in dot
    # Lab node coloured as Laboratory provenance.
    assert explore.PROVENANCE_COLORS["Laboratory"] in dot


# ---------------------------------------------------------------------------
# add-to-plot dispatch
# ---------------------------------------------------------------------------


def test_add_node_to_plot_dispatches_by_kind():
    chan = _node(12, "channel", derived=True, prov="Derived", label="x")
    lab = _node(3, "series", derived=False, prov="Laboratory", label="y")
    with patch.object(explore, "_add_channel_to_plot", return_value=True) as add_ch, \
         patch.object(explore, "_add_series_to_plot", return_value=True) as add_s:
        explore._add_node_to_plot(chan, rerun=False)
        explore._add_node_to_plot(lab, rerun=False)

    add_ch.assert_called_once_with(chan, rerun=False)
    add_s.assert_called_once_with(lab, rerun=False)


# ---------------------------------------------------------------------------
# HTML badge / pill builders
# ---------------------------------------------------------------------------


def test_prov_badge_and_trait_pills_use_colour_maps():
    badge = explore._prov_badge_html("Laboratory")
    assert explore.PROVENANCE_COLORS["Laboratory"] in badge

    pills = explore._trait_pills_html([{"operation_kind_id": 5, "name": "Smoothing"}])
    assert "Smoothing" in pills
    assert explore.OPERATION_COLORS["Smoothing"] in pills

    assert "no traits" in explore._trait_pills_html([])
