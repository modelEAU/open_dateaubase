"""Provenance / lineage inspector panel for the Explore page.

Extracted from explore.py (Phase 5). Holds the lineage-graph helpers, the
colour maps used only here, and the right-hand inspector panel renderer. The
two plot/inspect actions (``_add_node_to_plot``, ``_inspect_stream``) are passed
in as callbacks by explore.py so this module never needs to import the page and
there is no risk of re-executing it. Function names are re-exported from
explore.py so existing tests that reference ``explore._build_dag_dot`` etc. keep
working.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from app.api_client import APIError, get_stream_provenance

# Provenance panel colour maps (mirror .tasks/provenance-panel/mockup.html)
PROVENANCE_COLORS = {
    "Sensor": "#1f77b4",
    "Laboratory": "#16a085",
    "Derived": "#8e44ad",
    "Model Output": "#e67e22",
    "Forecast": "#d4a017",
    "Controller Output": "#34495e",
    "External Source": "#7f8c8d",
}
DEFAULT_PROVENANCE_COLOR = "#7f8c8d"

OPERATION_COLORS = {
    "Unprocessed": "#95a5a6",
    "OutlierRemoval": "#e74c3c",
    "DriftCorrection": "#3498db",
    "FaultRemoval": "#a6761d",
    "Smoothing": "#8e44ad",
    "Interpolation": "#2ecc71",
}
DEFAULT_OPERATION_COLOR = "#95a5a6"


def _load_provenance(stream_id: int) -> dict | None:
    """Fetch and cache the resolved provenance graph for a stream."""
    cache = st.session_state.explore_provenance_cache
    if stream_id not in cache:
        try:
            cache[stream_id] = get_stream_provenance(stream_id)
        except APIError as e:
            st.error(f"Failed to load provenance for stream {stream_id}: {e.message}")
            return None
    return cache[stream_id]


def _prov_badge_html(name: str | None) -> str:
    label = name or "—"
    color = PROVENANCE_COLORS.get(label, DEFAULT_PROVENANCE_COLOR)
    return (
        f"<span style='background:{color};color:#fff;padding:2px 8px;"
        f"border-radius:999px;font-size:11px;font-weight:700'>{label}</span>"
    )


def _op_badge_html(name: str | None) -> str:
    label = name or "?"
    color = OPERATION_COLORS.get(label, DEFAULT_OPERATION_COLOR)
    return (
        f"<span style='background:{color};color:#fff;padding:2px 8px;"
        f"border-radius:999px;font-size:11px;font-weight:700'>{label}</span>"
    )


def _trait_pills_html(traits: list[dict]) -> str:
    if not traits:
        return "<span style='color:#888;font-size:11px'>no traits</span>"
    spans = []
    for t in traits:
        name = t.get("name") or "?"
        color = OPERATION_COLORS.get(name, DEFAULT_OPERATION_COLOR)
        spans.append(
            f"<span style='border:1px solid {color};color:{color};padding:1px 7px;"
            f"border-radius:6px;font-size:11px;font-weight:600;margin-right:4px'>{name}</span>"
        )
    return "".join(spans)


def _ancestor_stream_ids(graph: dict, root_id: int) -> list[int]:
    """All stream ids reachable upstream of root (intermediates + raw sources)."""
    ids: set[int] = set()
    for step in graph.get("ancestors", []):
        ids.update(step.get("input_stream_ids", []))
        ids.update(step.get("output_stream_ids", []))
    ids.discard(root_id)
    return sorted(ids)


def _descendant_stream_ids(graph: dict, root_id: int) -> list[int]:
    ids: set[int] = set()
    for step in graph.get("descendants", []):
        ids.update(step.get("input_stream_ids", []))
        ids.update(step.get("output_stream_ids", []))
    ids.discard(root_id)
    return sorted(ids)


def _ordered_ancestor_steps(graph: dict, root_id: int) -> list[dict]:
    """Ancestor steps ordered nearest-to-root first (BFS upward from root)."""
    steps_by_output: dict[int, dict] = {}
    for step in graph.get("ancestors", []):
        for out in step.get("output_stream_ids", []):
            steps_by_output[out] = step

    order: list[dict] = []
    seen: set[int] = set()
    frontier = [root_id]
    while frontier:
        nxt: list[int] = []
        for nid in frontier:
            step = steps_by_output.get(nid)
            if step and step["processing_step_id"] not in seen:
                seen.add(step["processing_step_id"])
                order.append(step)
                nxt.extend(step.get("input_stream_ids", []))
        frontier = nxt
    return order


def _build_dag_dot(graph: dict, nodes: dict[int, dict], root_id: int) -> str:
    """Build a Graphviz DOT string for the provenance DAG (orientation picture)."""
    lines = [
        "digraph prov {",
        "rankdir=LR; bgcolor=transparent;",
        'node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=10];',
    ]
    for sid, node in nodes.items():
        color = PROVENANCE_COLORS.get(
            node.get("provenance_kind_name"), DEFAULT_PROVENANCE_COLOR
        )
        label = (node.get("label") or str(sid)).replace('"', "'")
        pen = ' penwidth=2 color="#1f2733"' if sid == root_id else ""
        lines.append(
            f'"{sid}" [label="{label}" fillcolor="{color}" fontcolor="white"{pen}];'
        )
    for step in graph.get("ancestors", []) + graph.get("descendants", []):
        op = (step.get("operation_kind_name") or "").replace('"', "'")
        for src in step.get("input_stream_ids", []):
            for dst in step.get("output_stream_ids", []):
                if src in nodes and dst in nodes:
                    lines.append(f'"{src}" -> "{dst}" [label="{op}" fontsize=8];')
    lines.append("}")
    return "\n".join(lines)


def _render_prov_node_card(
    node: dict,
    key_ctx: str,
    add_node_to_plot: Callable[..., None],
    inspect_stream: Callable[[str, int], None],
) -> None:
    sid = node["stream_id"]
    with st.container(border=True):
        st.markdown(
            _prov_badge_html(node.get("provenance_kind_name"))
            + f" &nbsp;<b>{node.get('label', sid)}</b>",
            unsafe_allow_html=True,
        )
        traits = node.get("traits", [])
        if traits:
            st.markdown(_trait_pills_html(traits), unsafe_allow_html=True)
        in_plot = (
            node.get("channel_id") in st.session_state.explore_active_channels
            or node.get("analysis_series_id") in st.session_state.explore_active_series
        )
        c1, c2 = st.columns(2)
        if c1.button(
            "✓ plotted" if in_plot else "➕ plot",
            key=f"prov_plot_{key_ctx}_{sid}",
            disabled=in_plot,
            use_container_width=True,
        ):
            add_node_to_plot(node)
        if c2.button(
            "🔬 inspect",
            key=f"prov_insp_{key_ctx}_{sid}",
            use_container_width=True,
        ):
            inspect_stream(node.get("kind", "channel"), sid)


def _render_breadcrumb(trail: list) -> None:
    cols = st.columns(len(trail) + 1)
    for i, (kind, sid) in enumerate(trail):
        prefix = "LAB" if kind == "series" else "CH"
        is_last = i == len(trail) - 1
        if cols[i].button(
            f"{prefix}-{sid}",
            key=f"prov_crumb_{i}_{sid}",
            disabled=is_last,
            help="Jump back to this stream" if not is_last else "Current stream",
        ):
            st.session_state.explore_inspect_trail = trail[: i + 1]
            st.rerun()
    if cols[-1].button("✕", key="prov_crumb_close", help="Close panel"):
        st.session_state.explore_inspect_trail = []
        st.rerun()


def _render_prov_overview(root: dict) -> None:
    rows = [
        ("Parameter", root.get("parameter_name")),
        ("Unit", root.get("unit_name")),
        ("Location", root.get("sampling_point_label")),
        ("Source", root.get("equipment_identifier")),
        ("Campaign", root.get("campaign_name")),
        ("Stream ID", root.get("stream_id")),
        ("Type", root.get("kind")),
    ]
    for label, value in rows:
        shown = value if value not in (None, "") else "—"
        st.markdown(f"**{label}:** {shown}")
    st.caption(
        "Traits are the accumulated set of operations across the full lineage "
        "(ChannelTrait), not just the last step."
    )


def _render_prov_lineage(
    graph: dict,
    nodes: dict[int, dict],
    root_id: int,
    add_node_to_plot: Callable[..., None],
    inspect_stream: Callable[[str, int], None],
) -> None:
    st.graphviz_chart(_build_dag_dot(graph, nodes, root_id), use_container_width=True)

    steps = _ordered_ancestor_steps(graph, root_id)
    if not steps:
        st.caption("No ancestors — this is a raw source stream.")
    else:
        st.markdown("**Ancestors** (nearest first)")
        seen: set[int] = set()
        for step in steps:
            op = step.get("operation_kind_name") or "?"
            color = OPERATION_COLORS.get(op, DEFAULT_OPERATION_COLOR)
            st.markdown(
                f"<span style='color:{color};font-weight:600'>● {op}</span> "
                f"<span style='color:#888;font-size:12px'>· "
                f"{step.get('method_name') or ''}</span>",
                unsafe_allow_html=True,
            )
            for inp in step.get("input_stream_ids", []):
                if inp == root_id or inp in seen:
                    continue
                seen.add(inp)
                node = nodes.get(inp)
                if node:
                    _render_prov_node_card(
                        node,
                        key_ctx=f"anc{step['processing_step_id']}",
                        add_node_to_plot=add_node_to_plot,
                        inspect_stream=inspect_stream,
                    )

    desc_ids = _descendant_stream_ids(graph, root_id)
    if desc_ids:
        with st.expander(f"⬇ Downstream — what this became ({len(desc_ids)})"):
            for did in desc_ids:
                node = nodes.get(did)
                if node:
                    _render_prov_node_card(
                        node,
                        key_ctx="desc",
                        add_node_to_plot=add_node_to_plot,
                        inspect_stream=inspect_stream,
                    )


def _render_prov_steps(graph: dict) -> None:
    steps = graph.get("ancestors", [])
    if not steps:
        st.caption("No processing steps — this is a raw source stream.")
        return
    for step in steps:
        with st.container(border=True):
            st.markdown(
                _op_badge_html(step.get("operation_kind_name"))
                + f" &nbsp;<code>{step.get('method_name') or ''}"
                + (f" · {step.get('method_version')}" if step.get("method_version") else "")
                + "</code>",
                unsafe_allow_html=True,
            )
            params = step.get("method_parameters")
            if params:
                st.code(str(params), language="json")
            who = step.get("executed_by_name") or "(automated)"
            when = str(step.get("executed_at") or "")[:19]
            st.caption(f"▸ {who} · {when}")
            ins = ", ".join(str(i) for i in step.get("input_stream_ids", []))
            outs = ", ".join(str(o) for o in step.get("output_stream_ids", []))
            st.caption(f"inputs: {ins} → outputs: {outs}")


def _render_provenance_panel(
    add_node_to_plot: Callable[..., None],
    inspect_stream: Callable[[str, int], None],
) -> None:
    """Right-hand Provenance inspector for the stream at the top of the trail."""
    trail = st.session_state.explore_inspect_trail
    if not trail:
        return

    st.subheader("🔬 Provenance")
    _render_breadcrumb(trail)

    _, sid = trail[-1]
    graph = _load_provenance(sid)
    if graph is None:
        return

    nodes = {n["stream_id"]: n for n in graph.get("nodes", [])}
    root = nodes.get(sid)
    if root is None:
        st.warning("Stream not found in the provenance graph.")
        return

    st.markdown(
        _prov_badge_html(root.get("provenance_kind_name"))
        + f" &nbsp;<b>{root.get('label', sid)}</b>",
        unsafe_allow_html=True,
    )
    st.markdown(_trait_pills_html(root.get("traits", [])), unsafe_allow_html=True)

    anc_ids = _ancestor_stream_ids(graph, sid)
    raw_ids = [i for i in anc_ids if not nodes.get(i, {}).get("is_derived", False)]
    if root.get("is_derived"):
        st.caption(
            f"Derived stream — produced from {len(anc_ids)} ancestor stream(s) "
            f"({len(raw_ids)} raw source(s)) through {len(graph.get('ancestors', []))} "
            "processing step(s)."
        )
    else:
        st.caption("Raw source stream — no upstream processing.")

    if anc_ids:
        c1, c2 = st.columns(2)
        if c1.button(
            f"➕ Overlay all {len(anc_ids)} ancestors",
            key="prov_add_all",
            use_container_width=True,
        ):
            for i in anc_ids:
                if i in nodes:
                    add_node_to_plot(nodes[i], rerun=False)
            st.rerun()
        if raw_ids and c2.button(
            "➕ Raw source only", key="prov_add_raw", use_container_width=True
        ):
            for i in raw_ids:
                if i in nodes:
                    add_node_to_plot(nodes[i], rerun=False)
            st.rerun()

    tab = st.radio(
        "Provenance view",
        ["Overview", "Lineage", "Steps"],
        horizontal=True,
        label_visibility="collapsed",
        key="explore_prov_tab",
    )
    if tab == "Overview":
        _render_prov_overview(root)
    elif tab == "Steps":
        _render_prov_steps(graph)
    else:
        _render_prov_lineage(
            graph, nodes, sid, add_node_to_plot=add_node_to_plot, inspect_stream=inspect_stream
        )
