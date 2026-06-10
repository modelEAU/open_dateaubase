"""Data Explorer page.

Supports multi-series visualization and extraction for all four value types:
  Scalar  — overlaid line charts with annotation overlays and point selection
  Vector  — 2D heatmap (time × bin, color = value) with optional 3D toggle
  Matrix  — time-slice heatmap OR row/col slice line chart
  Image   — thumbnail gallery with fullscreen dialog and multi-select actions

Layout (issue #16):
  - Top bar: title left, time range + mode toggle right
  - Channel picker panel (collapsible, main content area) with bidirectional
    cross-filtering across Equipment / Parameter / Value Type
  - Active series chips row below picker
  - Visualization area: dynamic tabs only for types present in active channels
"""

from __future__ import annotations

import io
import csv
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.api_client import (
    APIError,
    bulk_set_quality_code,
    get_channel_stats,
    get_channel_timeseries,
    get_channel_thumbnail,
    get_channel_image,
    get_equipment_events,
    list_annotation_kinds,
    list_campaigns_lookup,
    list_equipment_lookup,
    list_parameters_lookup,
    list_channels,
    list_equipment_event_kinds,
    list_quality_codes,
    create_equipment_event,
    list_analysis_series_lookup,
    get_analysis_series_timeseries,
    get_analysis_series_stats,
    get_analysis_series_thumbnail,
    get_analysis_series_image,
)
from app.components.lttb import lttb


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALUE_TYPE_SCALAR = 1
VALUE_TYPE_VECTOR = 2
VALUE_TYPE_MATRIX = 3
VALUE_TYPE_IMAGE = 4

VALUE_TYPE_NAMES = {
    VALUE_TYPE_SCALAR: "Scalar",
    VALUE_TYPE_VECTOR: "Vector",
    VALUE_TYPE_MATRIX: "Matrix",
    VALUE_TYPE_IMAGE: "Image",
}

QUALITY_COLORS = {
    1: "#2ecc71",  # Accepted — green
    2: "#f39c12",  # Suspect — orange
    3: "#e74c3c",  # Rejected — red
    4: "#95a5a6",  # BelowLoD — grey
    5: "#8e44ad",  # AboveLoQ — purple
    6: "#3498db",  # Outlier — blue
}
DEFAULT_QUALITY_COLOR = "#aaaaaa"

VIZ_MAX_POINTS = 1000

_VALUE_TYPE_OPTIONS: dict[str, int | None] = {
    "(all types)": None,
    "Scalar": VALUE_TYPE_SCALAR,
    "Vector": VALUE_TYPE_VECTOR,
    "Matrix": VALUE_TYPE_MATRIX,
    "Image": VALUE_TYPE_IMAGE,
}


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------


def _init_state() -> None:
    defaults: dict = {
        "explore_active_channels": [],  # list[int]
        "explore_channel_meta": {},     # channel_id -> channel dict (cached lookup)
        "explore_active_series": [],    # list[int] analysis_series_id (lab Traces)
        "explore_series_meta": {},      # series_id -> AnalysisSeries dict
        "explore_series_stats": {},     # series_id -> stats dict (cached)
        "explore_start": date.today() - timedelta(days=30),
        "explore_end": date.today(),
        "explore_mode": "viz",
        "explore_data": {},  # (channel_id, start, end) → timeseries dict
        "explore_annotations": {},  # channel_id → list[dict]
        "explore_series_annotations": {},  # analysis_series_id → list[dict]
        "explore_eq_events": {},  # equipment_id → list[dict]
        "explore_selected_points": {},  # Plotly selection result
        "explore_channel_stats": {},     # channel_id -> stats dict (cached)
        "explore_selected_images": [],  # list[str] timestamps
        "explore_image_detail_ch": None,
        "explore_image_detail_ts": None,
        "_show_annotation_dialog": False,
        "_show_event_dialog": False,
        "_ann_channel_id": None,
        "_ann_start": None,
        "_ann_end": None,
        # Picker filter state — kept in session state so cross-filter changes
        # don't cause rerun loops from widget key collisions.
        "picker_campaign_id": None,
        "picker_eq_id": None,
        "picker_param_id": None,
        "picker_vtype_id": None,
        # Lab picker cross-filter state (campaign is the shared top-level filter)
        "picker_series_param_id": None,
        "picker_series_sp_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _invalidate_data_cache() -> None:
    st.session_state.explore_data = {}
    st.session_state.explore_annotations = {}
    st.session_state.explore_series_annotations = {}
    st.session_state.explore_eq_events = {}


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_timeseries(channel_id: int) -> dict | None:
    start = st.session_state.explore_start
    end = st.session_state.explore_end
    cache = st.session_state.explore_data
    key = (channel_id, str(start), str(end))
    if key not in cache:
        try:
            data = get_channel_timeseries(
                channel_id,
                start=datetime.combine(start, datetime.min.time()).isoformat(),
                end=datetime.combine(end, datetime.max.time()).isoformat(),
            )
            cache[key] = data
        except APIError as e:
            st.error(f"Failed to load channel {channel_id}: {e.message}")
            return None
    return cache[key]


def _load_series_timeseries(series_id: int) -> dict | None:
    """Load and cache the time series for a lab AnalysisSeries (Trace).

    Shares the explore_data cache with sensor channels, namespaced by a
    ("series", ...) key so the two id spaces never collide."""
    start = st.session_state.explore_start
    end = st.session_state.explore_end
    cache = st.session_state.explore_data
    key = ("series", series_id, str(start), str(end))
    if key not in cache:
        try:
            cache[key] = get_analysis_series_timeseries(
                series_id,
                start=datetime.combine(start, datetime.min.time()).isoformat(),
                end=datetime.combine(end, datetime.max.time()).isoformat(),
            )
        except APIError as e:
            st.error(f"Failed to load series {series_id}: {e.message}")
            return None
    return cache[key]


def _fetch_series_stats(series_id: int) -> dict | None:
    cache = st.session_state.explore_series_stats
    if series_id not in cache:
        try:
            cache[series_id] = get_analysis_series_stats(series_id)
        except APIError:
            cache[series_id] = None
    return cache[series_id]


def _load_trace_data(trace: tuple[str, int]) -> dict | None:
    """Load a single trace's data by ('channel'|'series', id)."""
    kind, _id = trace
    return _load_series_timeseries(_id) if kind == "series" else _load_timeseries(_id)


def _kind_options(
    value_type: int,
    active_channels: list[int],
    channel_meta: dict[int, dict],
    active_series: list[int],
    series_meta: dict[int, dict],
) -> dict[str, tuple[str, int]]:
    """Build a {label: ('channel'|'series', id)} option map for a value type,
    merging sensor channels and lab series of that type."""
    opts: dict[str, tuple[str, int]] = {}
    for ch in active_channels:
        m = channel_meta.get(ch, {})
        if m.get("value_kind_id") == value_type:
            label = f"CH-{ch}: {m.get('equipment_identifier', '?')} / {m.get('parameter_name', '?')}"
            opts[label] = ("channel", ch)
    for s in active_series:
        m = series_meta.get(s, {})
        if m.get("value_kind_id") == value_type:
            label = f"LAB-{s}: {m.get('parameter_name', '?')} @ {m.get('sampling_point_label', '?')}"
            opts[label] = ("series", s)
    return opts


def _load_annotations(channel_id: int) -> list[dict]:
    cache = st.session_state.explore_annotations
    if channel_id not in cache:
        try:
            start = st.session_state.explore_start
            end = st.session_state.explore_end
            cache[channel_id] = _api_list_annotations_for_channel(
                channel_id, start, end
            )
        except APIError:
            cache[channel_id] = []
    return cache[channel_id]


def _api_list_annotations_for_channel(
    channel_id: int, start: date, end: date
) -> list[dict]:
    """Call GET /timeseries/{channel_id}/annotations with time range."""
    from app.api_client import _get_client, _raise_for_status, APIError
    import httpx

    params = {
        "from": datetime.combine(start, datetime.min.time()).isoformat(),
        "to": datetime.combine(end, datetime.max.time()).isoformat(),
    }
    try:
        with _get_client() as client:
            r = client.get(f"/timeseries/{channel_id}/annotations", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    data = r.json()
    return data.get("annotations", [])


def _load_series_annotations(series_id: int) -> list[dict]:
    cache = st.session_state.explore_series_annotations
    if series_id not in cache:
        try:
            start = st.session_state.explore_start
            end = st.session_state.explore_end
            cache[series_id] = _api_list_annotations_for_series(
                series_id, start, end
            )
        except APIError:
            cache[series_id] = []
    return cache[series_id]


def _api_list_annotations_for_series(
    series_id: int, start: date, end: date
) -> list[dict]:
    """Call GET /analysis-series/{series_id}/annotations with time range."""
    from app.api_client import _get_client, _raise_for_status, APIError
    import httpx

    params = {
        "from": datetime.combine(start, datetime.min.time()).isoformat(),
        "to": datetime.combine(end, datetime.max.time()).isoformat(),
    }
    try:
        with _get_client() as client:
            r = client.get(f"/analysis-series/{series_id}/annotations", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    data = r.json()
    return data.get("annotations", [])


def _load_equipment_events(equipment_id: int) -> list[dict]:
    """Load and cache equipment events for a given equipment over the active time range."""
    cache = st.session_state.explore_eq_events
    if equipment_id not in cache:
        start = st.session_state.explore_start
        end = st.session_state.explore_end
        try:
            cache[equipment_id] = get_equipment_events(
                equipment_id,
                from_dt=datetime.combine(start, datetime.min.time()).isoformat(),
                to_dt=datetime.combine(end, datetime.max.time()).isoformat(),
            )
        except APIError:
            cache[equipment_id] = []
    return cache[equipment_id]


# ---------------------------------------------------------------------------
# Cross-filtering helpers
# ---------------------------------------------------------------------------


def _fetch_channels_for_filters(
    campaign_id: int | None,
    equipment_id: int | None,
    parameter_id: int | None,
    value_kind_id: int | None,
) -> list[dict]:
    """Return channel items matching ALL supplied filters (None = no filter)."""
    try:
        result = list_channels(
            campaign_id=campaign_id,
            equipment_id=equipment_id,
            parameter_id=parameter_id,
            value_kind_id=value_kind_id,
            page_size=1000,
        )
        return result.get("items", [])
    except APIError:
        return []


def _derive_available_options(
    channels: list[dict],
    equipment_lookup: list[dict],
    parameters_lookup: list[dict],
) -> tuple[dict[str, int | None], dict[str, int | None], dict[str, int | None]]:
    """Derive available Equipment, Parameter, and Value Type options from a channel list.

    Returns three {label: id} dicts with a leading "all" sentinel entry.
    """
    eq_ids = {c["equipment_id"] for c in channels if c.get("equipment_id") is not None}
    param_ids = {c["parameter_id"] for c in channels if c.get("parameter_id") is not None}
    vtype_ids = {c["value_kind_id"] for c in channels if c.get("value_kind_id") is not None}

    eq_opts: dict[str, int | None] = {"(all equipment)": None}
    eq_opts.update(
        {
            e.get("identifier", str(e["equipment_id"])): e["equipment_id"]
            for e in equipment_lookup
            if e["equipment_id"] in eq_ids
        }
    )

    param_opts: dict[str, int | None] = {"(all parameters)": None}
    param_opts.update(
        {
            p.get("parameter_name", str(p["parameter_id"])): p["parameter_id"]
            for p in parameters_lookup
            if p["parameter_id"] in param_ids
        }
    )

    vtype_opts: dict[str, int | None] = {"(all types)": None}
    for vt_id in sorted(vtype_ids):
        name = VALUE_TYPE_NAMES.get(vt_id, str(vt_id))
        vtype_opts[name] = vt_id

    return eq_opts, param_opts, vtype_opts


def _channel_label(ch: dict) -> str:
    eq = ch.get("equipment_identifier") or ch.get("tag_name") or f"EQ-{ch.get('equipment_id') or '?'}"
    param = ch.get("parameter_name") or f"P-{ch.get('parameter_id', '?')}"
    vtype = ch.get("value_type_name") or VALUE_TYPE_NAMES.get(ch.get("value_kind_id"), "?")
    return f"CH-{ch['channel_id']}: {eq} / {param} [{vtype}]"


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------


def _build_scalar_figure(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    mode: str,
    active_series: list[int] | None = None,
    series_meta: dict[int, dict] | None = None,
) -> tuple[go.Figure, list[dict]]:
    """Build a multi-trace Plotly figure for scalar data.

    Sensor channels render as lines+markers; lab AnalysisSeries (Traces) overlay
    as markers-only scatter (discrete samples) on the same axes.

    Returns (fig, overlay_rows) where overlay_rows is a list of annotation and
    equipment-event records for the summary table rendered below the chart.
    """
    active_series = active_series or []
    series_meta = series_meta or {}
    fig = go.Figure()
    overlay_rows: list[dict] = []

    palette = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    for idx, ch_id in enumerate(active_channels):
        data = _load_timeseries(ch_id)
        if data is None:
            continue

        rows = data.get("data", [])
        if not rows:
            continue

        ts_list = [r.get("timestamp") for r in rows]
        v_list = [r.get("value") for r in rows]
        qc_list = [r.get("quality_code") for r in rows]

        if mode == "viz":
            ts_list, v_list = lttb(ts_list, v_list, VIZ_MAX_POINTS)
            qc_list = qc_list[: len(ts_list)]  # approximate — just for color

        meta = channel_meta.get(ch_id, {})
        label = f"CH-{ch_id}: {meta.get('equipment_identifier', '?')} / {meta.get('parameter_name', '?')}"
        color = palette[idx % len(palette)]

        marker_colors = [
            QUALITY_COLORS.get(qc, DEFAULT_QUALITY_COLOR) for qc in qc_list
        ]

        fig.add_trace(
            go.Scatter(
                x=ts_list,
                y=v_list,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=1.5),
                marker=dict(color=marker_colors, size=5),
                customdata=[[ch_id, i] for i in range(len(ts_list))],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Time: %{x}<br>Value: %{y}<extra></extra>"
                ),
            )
        )

        # Annotation overlays — low-opacity fill + dashed start line with ref index
        annotations = _load_annotations(ch_id)
        for ann in annotations:
            t_start = ann.get("start_time")
            t_end = ann.get("end_time") or t_start
            ann_color = ann.get("type", {}).get("color") or "#888888"
            ref = len(overlay_rows) + 1
            overlay_rows.append(
                {
                    "ref": ref,
                    "kind": "Annotation",
                    "source": f"CH-{ch_id}",
                    "category": ann.get("type", {}).get("name", ""),
                    "title": ann.get("title", "") or "",
                    "start": t_start,
                    "end": ann.get("end_time") or "",
                    "comment": ann.get("comment", "") or "",
                }
            )
            fig.add_vrect(
                x0=t_start,
                x1=t_end,
                fillcolor=ann_color,
                opacity=0.08,
                line_width=0,
            )
            fig.add_vline(
                x=t_start,
                line_color=ann_color,
                line_width=1.5,
                line_dash="dash",
            )
            fig.add_annotation(
                x=t_start,
                y=1,
                yref="paper",
                text=f"[{ref}]",
                showarrow=False,
                xanchor="left",
                yanchor="top",
                font=dict(size=11, color=ann_color),
                bgcolor="rgba(0,0,0,0.55)",
                borderpad=2,
            )

        # Equipment event overlays — deduplicated per equipment
        eq_id = channel_meta.get(ch_id, {}).get("equipment_id")
        if eq_id is not None:
            already_drawn: set = getattr(fig, "_drawn_eq_ids", set())
            if eq_id not in already_drawn:
                eq_label = meta.get("equipment_identifier") or f"EQ-{eq_id}"
                for ev in _load_equipment_events(eq_id):
                    ev_start = ev.get("start_datetime")
                    ev_end = ev.get("end_datetime") or ev_start
                    ref = len(overlay_rows) + 1
                    overlay_rows.append(
                        {
                            "ref": ref,
                            "kind": "Equipment Event",
                            "source": eq_label,
                            "category": ev.get("event_type_name", "") or "",
                            "title": ev.get("notes", "") or "",
                            "start": ev_start,
                            "end": ev.get("end_datetime") or "",
                            "comment": "",
                        }
                    )
                    fig.add_vrect(
                        x0=ev_start,
                        x1=ev_end,
                        fillcolor="#5588aa",
                        opacity=0.06,
                        line_width=0,
                    )
                    fig.add_vline(
                        x=ev_start,
                        line_color="#7aaabb",
                        line_width=1,
                        line_dash="dot",
                    )
                    fig.add_annotation(
                        x=ev_start,
                        y=1,
                        yref="paper",
                        text=f"[{ref}]",
                        showarrow=False,
                        xanchor="right",
                        yanchor="top",
                        font=dict(size=10, color="#7aaabb"),
                        bgcolor="rgba(0,0,0,0.55)",
                        borderpad=2,
                    )
                try:
                    fig._drawn_eq_ids.add(eq_id)  # type: ignore[attr-defined]
                except AttributeError:
                    fig._drawn_eq_ids = {eq_id}  # type: ignore[attr-defined]

    # --- Lab AnalysisSeries (Traces): markers-only scatter overlay ---
    lab_palette = [
        "#1b9e77", "#d95f02", "#7570b3", "#e7298a",
        "#66a61e", "#e6ab02", "#a6761d", "#666666",
    ]
    for idx, s_id in enumerate(active_series):
        data = _load_series_timeseries(s_id)
        if data is None:
            continue
        rows = data.get("data", [])
        if not rows:
            continue

        ts_list = [r.get("timestamp") for r in rows]
        v_list = [r.get("value") for r in rows]
        qc_list = [r.get("quality_code") for r in rows]

        smeta = series_meta.get(s_id, {})
        label = (
            f"LAB-{s_id}: {smeta.get('name') or smeta.get('parameter_name', '?')} "
            f"@ {smeta.get('sampling_point_label', '?')}"
        )
        marker_colors = [
            QUALITY_COLORS.get(qc, DEFAULT_QUALITY_COLOR) for qc in qc_list
        ]
        outline = lab_palette[idx % len(lab_palette)]

        fig.add_trace(
            go.Scatter(
                x=ts_list,
                y=v_list,
                mode="markers",
                name=label,
                marker=dict(
                    color=marker_colors,
                    size=10,
                    symbol="diamond",
                    line=dict(color=outline, width=1.5),
                ),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Sample time: %{x}<br>Value: %{y}<extra>lab</extra>"
                ),
            )
        )

        # Annotation overlays for the lab Trace — same treatment as sensors.
        for ann in _load_series_annotations(s_id):
            t_start = ann.get("start_time")
            t_end = ann.get("end_time") or t_start
            ann_color = ann.get("type", {}).get("color") or "#888888"
            ref = len(overlay_rows) + 1
            overlay_rows.append(
                {
                    "ref": ref,
                    "kind": "Annotation",
                    "source": f"LAB-{s_id}",
                    "category": ann.get("type", {}).get("name", ""),
                    "title": ann.get("title", "") or "",
                    "start": t_start,
                    "end": ann.get("end_time") or "",
                    "comment": ann.get("comment", "") or "",
                }
            )
            fig.add_vrect(
                x0=t_start,
                x1=t_end,
                fillcolor=ann_color,
                opacity=0.08,
                line_width=0,
            )
            fig.add_vline(
                x=t_start,
                line_color=ann_color,
                line_width=1.5,
                line_dash="dash",
            )
            fig.add_annotation(
                x=t_start,
                y=1,
                yref="paper",
                text=f"[{ref}]",
                showarrow=False,
                xanchor="left",
                yanchor="top",
                font=dict(size=11, color=ann_color),
                bgcolor="rgba(0,0,0,0.55)",
                borderpad=2,
            )

    y_labels: list[str] = []
    seen_labels: set[str] = set()
    for ch_id in active_channels:
        meta = channel_meta.get(ch_id, {})
        param = meta.get("parameter_name") or ""
        unit = meta.get("unit_name") or ""
        lbl = f"{param} ({unit})" if param and unit else param or unit or "Value"
        if lbl not in seen_labels:
            seen_labels.add(lbl)
            y_labels.append(lbl)
    for s_id in active_series:
        smeta = series_meta.get(s_id, {})
        param = smeta.get("parameter_name") or ""
        unit = smeta.get("unit_name") or ""
        lbl = f"{param} ({unit})" if param and unit else param or unit or "Value"
        if lbl not in seen_labels:
            seen_labels.add(lbl)
            y_labels.append(lbl)
    y_axis_title = " / ".join(y_labels) if y_labels else "Value"

    fig.update_layout(
        dragmode="select",
        selectdirection="any",
        xaxis_title="Time",
        yaxis_title=y_axis_title,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=40, b=50),
        height=480,
    )
    return fig, overlay_rows


def _bin_label(row: dict) -> float:
    """Return a numeric label for a bin row.

    Priority: nominal_value → midpoint of (lower_bound + upper_bound) / 2 → bin_index.
    """
    nv = row.get("nominal_value")
    if nv is not None:
        return nv
    lb = row.get("lower_bound")
    ub = row.get("upper_bound")
    if lb is not None and ub is not None:
        return (lb + ub) / 2
    return row["bin_index"]


def _vector_value_label(data: dict) -> str:
    param = data.get("parameter") or ""
    unit = data.get("unit") or ""
    return f"{param} ({unit})" if param and unit else param or unit or "Value"


def _build_vector_heatmap(data: dict, as_3d: bool = False) -> go.Figure:
    """Build a 2D heatmap (time × bin) or 3D surface for vector data."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()

    df = pd.DataFrame(rows)
    if df.empty or "bin_index" not in df.columns:
        return go.Figure()

    # Build a label per bin_index (consistent across all timestamps)
    bin_label_map = (
        df.drop_duplicates("bin_index")
        .set_index("bin_index")
        .apply(_bin_label, axis=1)
    )
    df["bin_label"] = df["bin_index"].map(bin_label_map)

    pivot = df.pivot_table(
        index="bin_label", columns="timestamp", values="value", aggfunc="first"
    )
    z = pivot.values.tolist()
    x = [str(c) for c in pivot.columns.tolist()]
    y = pivot.index.tolist()

    value_label = _vector_value_label(data)

    if as_3d:
        # go.Surface requires numeric axes — use integer indices for time
        x_numeric = list(range(len(x)))
        tick_step = max(1, len(x) // 10)
        tickvals = x_numeric[::tick_step]
        ticktext = x[::tick_step]
        fig = go.Figure(data=[go.Surface(z=z, x=x_numeric, y=y, colorscale="Viridis")])
        fig.update_layout(
            scene=dict(
                xaxis=dict(title="Time", tickvals=tickvals, ticktext=ticktext),
                yaxis=dict(title="Bin"),
                zaxis=dict(title=value_label),
            ),
            height=520,
        )
    else:
        fig = go.Figure(
            data=go.Heatmap(
                z=z,
                x=x,
                y=y,
                colorscale="Viridis",
                hoverongaps=False,
                colorbar=dict(title=value_label),
            )
        )
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Bin",
            height=420,
        )
    return fig


def _build_vector_slice_time(data: dict, timestamp: str) -> go.Figure:
    """Vertical slice: value vs bin label at a fixed timestamp."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()
    df = pd.DataFrame(rows)
    bin_label_map = (
        df.drop_duplicates("bin_index")
        .set_index("bin_index")
        .apply(_bin_label, axis=1)
    )
    df["bin_label"] = df["bin_index"].map(bin_label_map)
    slice_df = df[df["timestamp"].astype(str) == timestamp].sort_values("bin_label")
    value_label = _vector_value_label(data)
    fig = go.Figure(
        go.Scatter(
            x=slice_df["bin_label"].tolist(),
            y=slice_df["value"].tolist(),
            mode="lines+markers",
        )
    )
    fig.update_layout(xaxis_title="Bin", yaxis_title=value_label, height=320)
    return fig


def _build_vector_slice_bin(data: dict, bin_idx: int) -> go.Figure:
    """Horizontal slice: value vs time at a fixed bin."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()
    df = pd.DataFrame(rows)
    bin_label_map = (
        df.drop_duplicates("bin_index")
        .set_index("bin_index")
        .apply(_bin_label, axis=1)
    )
    slice_df = df[df["bin_index"] == bin_idx].sort_values("timestamp")
    value_label = _vector_value_label(data)
    label = bin_label_map.get(bin_idx, bin_idx)
    fig = go.Figure(
        go.Scatter(
            x=slice_df["timestamp"].tolist(),
            y=slice_df["value"].tolist(),
            mode="lines+markers",
            name=f"Bin {label}",
        )
    )
    fig.update_layout(xaxis_title="Time", yaxis_title=value_label, height=320)
    return fig


def _matrix_axis_label_map(df: "pd.DataFrame", axis: str) -> dict:
    """Return {bin_index: label} for the given matrix axis ('row' or 'col').

    Label priority: nominal_value → (lower+upper)/2 → bin_index.
    """
    prefix = axis  # 'row' or 'col'
    idx_col = f"{prefix}_bin_index"
    nom_col = f"{prefix}_nominal_value"
    lb_col = f"{prefix}_lower_bound"
    ub_col = f"{prefix}_upper_bound"

    result = {}
    for _, row in df.drop_duplicates(idx_col).iterrows():
        nv = row.get(nom_col)
        if nv is not None:
            result[row[idx_col]] = nv
            continue
        lb = row.get(lb_col)
        ub = row.get(ub_col)
        if lb is not None and ub is not None:
            result[row[idx_col]] = (lb + ub) / 2
            continue
        result[row[idx_col]] = row[idx_col]
    return result


def _build_matrix_timeslice(data: dict, timestamp: str) -> go.Figure:
    """Build a 2D heatmap for a specific timestamp slice of matrix data."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()

    df = pd.DataFrame(rows)
    ts_col = "timestamp"
    df[ts_col] = df[ts_col].astype(str)
    slice_df = df[df[ts_col] == timestamp]
    if slice_df.empty:
        st.warning(f"No data at {timestamp}")
        return go.Figure()

    row_labels = _matrix_axis_label_map(df, "row")
    col_labels = _matrix_axis_label_map(df, "col")
    slice_df = slice_df.copy()
    slice_df["row_label"] = slice_df["row_bin_index"].map(row_labels)
    slice_df["col_label"] = slice_df["col_bin_index"].map(col_labels)

    pivot = slice_df.pivot_table(
        index="row_label", columns="col_label", values="value", aggfunc="first"
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values.tolist(),
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale="Viridis",
        )
    )
    fig.update_layout(
        xaxis_title="Column bin",
        yaxis_title="Row bin",
        title=f"Matrix at {timestamp}",
        height=420,
    )
    return fig


def _build_matrix_slice_line(data: dict, axis: str, bin_idx: int) -> go.Figure:
    """Build a time-series line chart for a fixed row or column slice of matrix data."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()

    df = pd.DataFrame(rows)
    label_map = _matrix_axis_label_map(df, axis)
    bin_label = label_map.get(bin_idx, bin_idx)

    if axis == "row":
        slice_df = df[df["row_bin_index"] == bin_idx]
        trace_label = f"Row {bin_label}"
    else:
        slice_df = df[df["col_bin_index"] == bin_idx]
        trace_label = f"Col {bin_label}"

    fig = go.Figure(
        go.Scatter(
            x=slice_df["timestamp"].tolist(),
            y=slice_df["value"].tolist(),
            mode="lines+markers",
            name=trace_label,
        )
    )
    fig.update_layout(xaxis_title="Time", yaxis_title="Value", height=380)
    return fig


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------


@st.dialog("Annotate / Quality Flag", width="large")
def _annotation_dialog(
    channel_ids: list[int],
    start_time: str | None,
    end_time: str | None,
    annotation_types: list[dict],
    series_ids: list[int] | None = None,
) -> None:
    # Homogeneous per-arm dialog (no mixing sensor + lab in one Save): a lab
    # series target only shows the Annotation tab (quality flags are sensor-only).
    series_ids = series_ids or []
    is_lab = bool(series_ids)
    if is_lab:
        tab_ann = st.container()
        tab_qc = None
    else:
        tab_ann, tab_qc = st.tabs(["Annotation", "Quality Flag"])

    # ------------------------------------------------------------------
    # Tab 1: Annotation
    # ------------------------------------------------------------------
    with tab_ann:
        st.markdown(
            "Fill in the annotation details. Time range is pre-filled from your selection."
        )

        type_options = {at["name"]: at["id"] for at in annotation_types}
        sel_type_name = st.selectbox("Annotation type *", list(type_options.keys()))

        col1, col2 = st.columns(2)
        with col1:
            t_start = st.text_input(
                "Start time (ISO)",
                value=start_time or datetime.now(timezone.utc).isoformat(),
                key="ann_start",
            )
        with col2:
            t_end = st.text_input(
                "End time (ISO, optional)", value=end_time or "", key="ann_end"
            )

        title = st.text_input("Title (optional)")
        comment = st.text_area("Comment (optional)")

        if st.button("Save Annotation", type="primary", key="btn_save_ann"):
            payload = {
                "annotation_type": type_options[sel_type_name],
                "start_time": t_start,
                "end_time": t_end or None,
                "title": title or None,
                "comment": comment or None,
            }
            errors = []
            from app.api_client import _get_client, _raise_for_status

            if is_lab:
                targets = [(f"/analysis-series/{s_id}/annotations", f"LAB-{s_id}") for s_id in series_ids]
            else:
                targets = [(f"/timeseries/{ch_id}/annotations", f"CH-{ch_id}") for ch_id in channel_ids]

            for url, label in targets:
                try:
                    with _get_client() as client:
                        r = client.post(url, json=payload)
                    _raise_for_status(r)
                except (APIError, Exception) as e:
                    errors.append(f"{label}: {e}")

            if errors:
                st.error("Some annotations failed:\n" + "\n".join(errors))
            else:
                st.success(f"Annotation saved for {len(targets)} trace(s).")
                _invalidate_data_cache()
                st.rerun()

    # ------------------------------------------------------------------
    # Tab 2: Quality Flag (sensor-only)
    # ------------------------------------------------------------------
    if tab_qc is None:
        return
    with tab_qc:
        st.markdown(
            "Apply a quality code to all data points in the selected time range."
        )

        try:
            qc_list = list_quality_codes()
        except APIError:
            qc_list = []

        if not qc_list:
            st.warning("No quality codes available.")
        else:
            qc_options = {
                f"{qc['name']} ({'usable' if qc.get('is_usable') else 'non-usable'})": qc["quality_code_id"]
                for qc in qc_list
            }

            sel_qc_label = st.selectbox("Quality code *", list(qc_options.keys()), key="qc_sel")

            col1, col2 = st.columns(2)
            with col1:
                qc_start = st.text_input(
                    "Start time (ISO)",
                    value=start_time or datetime.now(timezone.utc).isoformat(),
                    key="qc_start",
                )
            with col2:
                qc_end = st.text_input(
                    "End time (ISO)",
                    value=end_time or datetime.now(timezone.utc).isoformat(),
                    key="qc_end",
                )

            if st.button("Apply Quality Code", type="primary", key="btn_apply_qc"):
                errors = []
                total_updated = 0
                for ch_id in channel_ids:
                    try:
                        result = bulk_set_quality_code(
                            channel_id=ch_id,
                            start_time=qc_start,
                            end_time=qc_end,
                            quality_code_id=qc_options[sel_qc_label],
                        )
                        total_updated += result.get("updated_count", 0)
                    except APIError as e:
                        errors.append(f"CH-{ch_id}: {e.message}")

                if errors:
                    st.error("Some channels failed:\n" + "\n".join(errors))
                else:
                    st.success(
                        f"Quality code applied to {total_updated} row(s) across "
                        f"{len(channel_ids)} channel(s)."
                    )
                    _invalidate_data_cache()
                    st.rerun()


@st.dialog("Create Equipment Event", width="large")
def _equipment_event_dialog(
    start_time: str | None,
    end_time: str | None,
    equipment_options: list[dict],
    event_type_options: list[dict],
) -> None:
    eq_map = {
        e.get("identifier", str(e["equipment_id"])): e["equipment_id"]
        for e in equipment_options
    }
    et_map = {et["event_type_name"]: et["event_type_id"] for et in event_type_options}

    sel_eq = st.selectbox("Equipment *", list(eq_map.keys()))
    sel_et = st.selectbox("Event type *", list(et_map.keys()))

    col1, col2 = st.columns(2)
    with col1:
        t_start = st.text_input(
            "Start time (ISO)",
            value=start_time or datetime.now(timezone.utc).isoformat(),
        )
    with col2:
        t_end = st.text_input("End time (ISO, optional)", value=end_time or "")

    notes = st.text_area("Notes (optional)")

    if st.button("Save Event", type="primary"):
        payload = {
            "equipment_id": eq_map[sel_eq],
            "event_type_id": et_map[sel_et],
            "start_datetime": t_start,
            "end_datetime": t_end or None,
            "notes": notes or None,
        }
        try:
            create_equipment_event(payload)
            st.success("Equipment event created.")
            _invalidate_data_cache()
            st.rerun()
        except APIError as e:
            st.error(f"Failed: {e.message}")


@st.dialog("Image viewer", width="large")
def _image_viewer_dialog(
    trace: tuple[str, int],
    timestamp: str,
    annotation_types: list[dict],
) -> None:
    kind, t_id = trace
    try:
        img_bytes = (
            get_channel_image(t_id, timestamp)
            if kind == "channel"
            else get_analysis_series_image(t_id, timestamp)
        )
        st.image(img_bytes, caption=timestamp, use_container_width=True)
    except APIError as e:
        st.warning(f"Could not load full image: {e.message}")

    # Annotation is sensor-only (lab traces are read-only).
    if kind == "channel":
        st.divider()
        if st.button("Create Annotation for this image"):
            st.session_state._show_annotation_dialog = True
            st.session_state._ann_channel_id = t_id
            st.session_state._ann_start = timestamp
            st.session_state._ann_end = timestamp
            st.rerun()


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def _make_csv(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def _flat_scalar_rows(channel_ids: list[int], channel_meta: dict) -> list[dict]:
    out = []
    for ch_id in channel_ids:
        data = _load_timeseries(ch_id)
        if data is None:
            continue
        meta = channel_meta.get(ch_id, {})
        label = f"CH-{ch_id} {meta.get('equipment_identifier', '')} {meta.get('parameter_name', '')}".strip()
        for row in data.get("data", []):
            out.append(
                {
                    "channel_id": ch_id,
                    "channel_label": label,
                    "timestamp": row.get("timestamp"),
                    "value": row.get("value"),
                    "quality_code": row.get("quality_code"),
                }
            )
    return out


def _flat_series_scalar_rows(series_ids: list[int], series_meta: dict) -> list[dict]:
    out = []
    for s_id in series_ids:
        data = _load_series_timeseries(s_id)
        if data is None:
            continue
        meta = series_meta.get(s_id, {})
        label = (
            f"LAB-{s_id} {meta.get('parameter_name', '')} "
            f"@ {meta.get('sampling_point_label', '')}"
        ).strip()
        for row in data.get("data", []):
            out.append(
                {
                    "channel_id": f"LAB-{s_id}",
                    "channel_label": label,
                    "timestamp": row.get("timestamp"),
                    "value": row.get("value"),
                    "quality_code": row.get("quality_code"),
                }
            )
    return out


# ---------------------------------------------------------------------------
# Top bar (title + time range + mode toggle)
# ---------------------------------------------------------------------------


def _render_top_bar() -> None:
    """Render the full-width top bar: title left, controls right."""
    title_col, spacer_col, controls_col = st.columns([3, 1, 4])

    with title_col:
        st.title("Data Explorer")

    with controls_col:
        date_a, date_b, mode_col = st.columns([2, 2, 2])
        with date_a:
            new_start = st.date_input(
                "From",
                value=st.session_state.explore_start,
                label_visibility="collapsed",
            )
            st.caption("From")
        with date_b:
            new_end = st.date_input(
                "To",
                value=st.session_state.explore_end,
                label_visibility="collapsed",
            )
            st.caption("To")
        with mode_col:
            mode_val = st.radio(
                "Mode",
                options=["Viz", "Extract"],
                index=0 if st.session_state.explore_mode == "viz" else 1,
                key="mode_radio",
                horizontal=True,
            )
            st.session_state.explore_mode = "viz" if mode_val == "Viz" else "extract"

        # Apply time range changes immediately
        if (
            new_start != st.session_state.explore_start
            or new_end != st.session_state.explore_end
        ):
            st.session_state.explore_start = new_start
            st.session_state.explore_end = new_end
            _invalidate_data_cache()
            st.rerun()


# ---------------------------------------------------------------------------
# Channel picker panel (main content area, bidirectional cross-filtering)
# ---------------------------------------------------------------------------


def _render_campaign_selector(campaigns: list[dict]) -> None:
    """Top-level Campaign filter shared by both the sensor and lab pickers.

    Writing picker_campaign_id here scopes channels AND analysis series; changing
    it resets the downstream filters on both sides."""
    campaign_opts: dict[str, int | None] = {"(all campaigns)": None}
    campaign_opts.update(
        {c.get("name", str(c["campaign_id"])): c["campaign_id"] for c in campaigns}
    )
    campaign_labels = list(campaign_opts.keys())
    current_campaign_id = st.session_state.picker_campaign_id
    current_campaign_label = next(
        (lbl for lbl, v in campaign_opts.items() if v == current_campaign_id),
        campaign_labels[0],
    )
    sel_campaign_label = st.selectbox(
        "Campaign (filters both sensor & lab)",
        campaign_labels,
        index=campaign_labels.index(current_campaign_label),
        key="picker_campaign_select",
    )
    new_campaign_id = campaign_opts[sel_campaign_label]
    if new_campaign_id != st.session_state.picker_campaign_id:
        st.session_state.picker_campaign_id = new_campaign_id
        # Reset downstream filters on both pickers when campaign changes
        st.session_state.picker_eq_id = None
        st.session_state.picker_param_id = None
        st.session_state.picker_vtype_id = None
        st.session_state.picker_series_param_id = None
        st.session_state.picker_series_sp_id = None
        st.rerun()


def _render_channel_picker(
    campaigns: list[dict],
    equipment_lookup: list[dict],
    parameters_lookup: list[dict],
) -> None:
    """Render the collapsible channel picker with bidirectional cross-filtering.

    Campaign is the shared top-level filter (see _render_campaign_selector)."""

    with st.expander("📡 Sensor data", expanded=True):
        # --- Fetch channels matching current filter combination ---
        # For cross-filtering: when deriving available options for dimension X,
        # we query with all OTHER filters active (not X itself).
        current_eq = st.session_state.picker_eq_id
        current_param = st.session_state.picker_param_id
        current_vtype = st.session_state.picker_vtype_id
        campaign_id = st.session_state.picker_campaign_id

        # Channels matching all three filters (used for the channel selectbox)
        matched_channels = _fetch_channels_for_filters(
            campaign_id, current_eq, current_param, current_vtype
        )

        # Available equipment: fix param + vtype, query without eq filter
        channels_for_eq = _fetch_channels_for_filters(
            campaign_id, None, current_param, current_vtype
        )
        # Available parameters: fix eq + vtype, query without param filter
        channels_for_param = _fetch_channels_for_filters(
            campaign_id, current_eq, None, current_vtype
        )
        # Available value types: fix eq + param, query without vtype filter
        channels_for_vtype = _fetch_channels_for_filters(
            campaign_id, current_eq, current_param, None
        )

        eq_opts, _, _ = _derive_available_options(
            channels_for_eq, equipment_lookup, parameters_lookup
        )
        _, param_opts, _ = _derive_available_options(
            channels_for_param, equipment_lookup, parameters_lookup
        )
        _, _, vtype_opts = _derive_available_options(
            channels_for_vtype, equipment_lookup, parameters_lookup
        )

        # --- Three filter dropdowns in a row ---
        eq_col, param_col, vtype_col = st.columns(3)

        with eq_col:
            eq_labels = list(eq_opts.keys())
            current_eq_label = next(
                (lbl for lbl, v in eq_opts.items() if v == current_eq),
                eq_labels[0],
            )
            sel_eq_label = st.selectbox(
                "Equipment",
                eq_labels,
                index=eq_labels.index(current_eq_label),
                key="picker_eq_select",
            )
            new_eq_id = eq_opts[sel_eq_label]
            if new_eq_id != current_eq:
                st.session_state.picker_eq_id = new_eq_id
                st.rerun()

        with param_col:
            param_labels = list(param_opts.keys())
            current_param_label = next(
                (lbl for lbl, v in param_opts.items() if v == current_param),
                param_labels[0],
            )
            sel_param_label = st.selectbox(
                "Parameter",
                param_labels,
                index=param_labels.index(current_param_label),
                key="picker_param_select",
            )
            new_param_id = param_opts[sel_param_label]
            if new_param_id != current_param:
                st.session_state.picker_param_id = new_param_id
                st.rerun()

        with vtype_col:
            vtype_labels = list(vtype_opts.keys())
            current_vtype_label = next(
                (lbl for lbl, v in vtype_opts.items() if v == current_vtype),
                vtype_labels[0],
            )
            sel_vtype_label = st.selectbox(
                "Value Type",
                vtype_labels,
                index=vtype_labels.index(current_vtype_label),
                key="picker_vtype_select",
            )
            new_vtype_id = vtype_opts[sel_vtype_label]
            if new_vtype_id != current_vtype:
                st.session_state.picker_vtype_id = new_vtype_id
                st.rerun()

        st.divider()

        # --- Channel selectbox + Add button ---
        if not matched_channels:
            st.warning("No channels match the current filters.")
            sel_ch_id = None
        else:
            ch_label_map = {_channel_label(c): c["channel_id"] for c in matched_channels}
            ch_labels = list(ch_label_map.keys())
            sel_ch_label = st.selectbox(
                "Matching channels",
                ch_labels,
                key="picker_chan_select",
            )
            sel_ch_id = ch_label_map[sel_ch_label]

        add_disabled = sel_ch_id is None
        if st.button(
            "+ Add to plot",
            type="primary",
            disabled=add_disabled,
            key="picker_add_btn",
        ):
            active = st.session_state.explore_active_channels
            if sel_ch_id not in active:
                active.append(sel_ch_id)
                # Cache the channel meta immediately from the matched list
                ch_record = next(
                    (c for c in matched_channels if c["channel_id"] == sel_ch_id), None
                )
                if ch_record:
                    st.session_state.explore_channel_meta[sel_ch_id] = ch_record
                _invalidate_data_cache()
                st.rerun()
            else:
                st.info("Channel already in plot.")


# ---------------------------------------------------------------------------
# Lab AnalysisSeries picker (cross-filtering, in-memory from the lookup)
# ---------------------------------------------------------------------------


def _series_cross_filter(
    series_list: list[dict],
    campaign_id: int | None,
    cur_param: int | None,
    cur_sp: int | None,
) -> tuple[dict[str, int | None], dict[str, int | None], list[dict]]:
    """Pure cross-filter for the lab picker.

    Returns (param_opts, sp_opts, matches): available parameter options (fixing
    the chosen sampling point), available sampling-point options (fixing the
    chosen parameter), and the series matching all active filters. Campaign is
    the shared top-level scope."""
    scoped = [
        s for s in series_list
        if campaign_id is None or s.get("campaign_id") == campaign_id
    ]

    param_opts: dict[str, int | None] = {"(all parameters)": None}
    seen: set = set()
    for s in scoped:
        if cur_sp is not None and s["sampling_point_id"] != cur_sp:
            continue
        if s["parameter_id"] not in seen:
            seen.add(s["parameter_id"])
            param_opts[s["parameter_name"]] = s["parameter_id"]

    sp_opts: dict[str, int | None] = {"(all locations)": None}
    seen = set()
    for s in scoped:
        if cur_param is not None and s["parameter_id"] != cur_param:
            continue
        if s["sampling_point_id"] not in seen:
            seen.add(s["sampling_point_id"])
            sp_opts[s["sampling_point_label"]] = s["sampling_point_id"]

    matches = [
        s for s in scoped
        if (cur_param is None or s["parameter_id"] == cur_param)
        and (cur_sp is None or s["sampling_point_id"] == cur_sp)
    ]
    return param_opts, sp_opts, matches


def _render_series_picker(series_list: list[dict]) -> None:
    """Lab AnalysisSeries picker with parameter/sampling-point cross-filtering.

    Scoped by the shared top-level campaign. All filtering is in-memory from the
    series lookup, mirroring the sensor picker's bidirectional behavior."""
    with st.expander("🧪 Lab / analysis series", expanded=False):
        campaign_id = st.session_state.picker_campaign_id
        active = st.session_state.explore_active_series

        cur_param = st.session_state.picker_series_param_id
        cur_sp = st.session_state.picker_series_sp_id

        param_opts, sp_opts, matches = _series_cross_filter(
            series_list, campaign_id, cur_param, cur_sp
        )

        param_col, sp_col = st.columns(2)
        with param_col:
            labels = list(param_opts.keys())
            cur_label = next(
                (l for l, v in param_opts.items() if v == cur_param), labels[0]
            )
            sel = st.selectbox(
                "Parameter", labels, index=labels.index(cur_label),
                key="picker_series_param_select",
            )
            new_param = param_opts[sel]
            if new_param != cur_param:
                st.session_state.picker_series_param_id = new_param
                st.rerun()

        with sp_col:
            labels = list(sp_opts.keys())
            cur_label = next(
                (l for l, v in sp_opts.items() if v == cur_sp), labels[0]
            )
            sel = st.selectbox(
                "Sampling point", labels, index=labels.index(cur_label),
                key="picker_series_sp_select",
            )
            new_sp = sp_opts[sel]
            if new_sp != cur_sp:
                st.session_state.picker_series_sp_id = new_sp
                st.rerun()

        st.divider()

        if not matches:
            st.warning("No analysis series match the current filters.")
            sel_s_id = None
        else:
            label_map = {
                f"LAB-{s['analysis_series_id']}: {s['name']} "
                f"({s['parameter_name']} @ {s['sampling_point_label']}, "
                f"{s['unit_name']}, {VALUE_TYPE_NAMES.get(s['value_kind_id'], '?')})":
                s["analysis_series_id"]
                for s in matches
            }
            sel_label = st.selectbox(
                "Matching series", list(label_map.keys()), key="picker_series_select"
            )
            sel_s_id = label_map[sel_label]

        if st.button(
            "+ Add to plot", type="primary",
            disabled=sel_s_id is None, key="picker_series_add_btn",
        ):
            if sel_s_id not in active:
                active.append(sel_s_id)
                record = next(
                    (s for s in matches if s["analysis_series_id"] == sel_s_id), None
                )
                if record:
                    st.session_state.explore_series_meta[sel_s_id] = record
                _invalidate_data_cache()
                st.rerun()
            else:
                st.info("Series already in plot.")


# ---------------------------------------------------------------------------
# Active series chips row
# ---------------------------------------------------------------------------


def _fetch_channel_stats(ch_id: int, meta: dict) -> dict | None:
    """Lazily fetch and cache stats for a channel. Returns None on failure."""
    cache = st.session_state.explore_channel_stats
    if ch_id not in cache:
        try:
            cache[ch_id] = get_channel_stats(ch_id)
        except APIError:
            cache[ch_id] = None
    return cache[ch_id]


def _render_active_chips(channel_meta: dict[int, dict]) -> None:
    """Render active channels as a vertically growing list with range info and quick-select buttons."""
    active = st.session_state.explore_active_channels

    if not active:
        st.caption("No series added yet — use the picker above.")
        return

    to_remove: list[int] = []
    range_update: tuple[date, date] | None = None

    # Header row
    cols = st.columns([4, 2, 2, 1, 1, 1])
    cols[0].caption("**Channel**")
    cols[1].caption("**First value**")
    cols[2].caption("**Last value**")

    for ch_id in active:
        meta = channel_meta.get(ch_id, {})
        eq = meta.get("equipment_identifier") or "EQ-?"
        param = meta.get("parameter_name") or "P-?"
        vtype_id = meta.get("value_kind_id")
        vtype = VALUE_TYPE_NAMES.get(vtype_id, "?") if vtype_id else "?"
        label = f"CH-{ch_id}: {eq} / {param} [{vtype}]"

        stats = _fetch_channel_stats(ch_id, meta)
        min_ts = stats["min_timestamp"] if stats else None
        max_ts = stats["max_timestamp"] if stats else None

        min_str = str(min_ts)[:10] if min_ts else "—"
        max_str = str(max_ts)[:10] if max_ts else "—"

        with st.container(border=True):
            name_col, min_col, max_col, all_col, last7_col, rm_col = st.columns(
                [4, 2, 2, 1, 1, 1]
            )
            name_col.markdown(label)
            min_col.markdown(min_str)
            max_col.markdown(max_str)

            if all_col.button("Plot all", key=f"all_{ch_id}", disabled=not min_ts):
                range_update = (
                    min_ts.date() if hasattr(min_ts, "date") else date.fromisoformat(str(min_ts)[:10]),
                    max_ts.date() if hasattr(max_ts, "date") else date.fromisoformat(str(max_ts)[:10]),
                )

            if last7_col.button("Last 7d", key=f"last7_{ch_id}", disabled=not max_ts):
                end = max_ts.date() if hasattr(max_ts, "date") else date.fromisoformat(str(max_ts)[:10])
                range_update = (end - timedelta(days=7), end)

            if rm_col.button("✕", key=f"rm_{ch_id}", help="Remove channel"):
                to_remove.append(ch_id)

    for ch_id in to_remove:
        st.session_state.explore_active_channels.remove(ch_id)
        st.session_state.explore_channel_meta.pop(ch_id, None)
        st.session_state.explore_channel_stats.pop(ch_id, None)
        _invalidate_data_cache()
        st.rerun()

    if range_update is not None:
        start, end = range_update
        st.session_state.explore_start = start
        st.session_state.explore_end = end
        _invalidate_data_cache()
        st.rerun()


def _render_series_chips(series_meta: dict[int, dict]) -> None:
    """Render active lab AnalysisSeries (Traces) as chips with sample-time range."""
    active = st.session_state.explore_active_series
    if not active:
        return

    to_remove: list[int] = []
    range_update: tuple[date, date] | None = None

    for s_id in active:
        meta = series_meta.get(s_id, {})
        param = meta.get("parameter_name") or "P-?"
        sp = meta.get("sampling_point_label") or "?"
        vtype = VALUE_TYPE_NAMES.get(meta.get("value_kind_id"), "?")
        label = f"🧪 LAB-{s_id}: {param} @ {sp} [{vtype}]"

        stats = _fetch_series_stats(s_id)
        min_ts = stats["min_timestamp"] if stats else None
        max_ts = stats["max_timestamp"] if stats else None
        min_str = str(min_ts)[:10] if min_ts else "—"
        max_str = str(max_ts)[:10] if max_ts else "—"

        with st.container(border=True):
            name_col, min_col, max_col, all_col, last7_col, rm_col = st.columns(
                [4, 2, 2, 1, 1, 1]
            )
            name_col.markdown(label)
            min_col.markdown(min_str)
            max_col.markdown(max_str)

            if all_col.button("Plot all", key=f"s_all_{s_id}", disabled=not min_ts):
                range_update = (
                    min_ts.date() if hasattr(min_ts, "date") else date.fromisoformat(str(min_ts)[:10]),
                    max_ts.date() if hasattr(max_ts, "date") else date.fromisoformat(str(max_ts)[:10]),
                )
            if last7_col.button("Last 7d", key=f"s_last7_{s_id}", disabled=not max_ts):
                end = max_ts.date() if hasattr(max_ts, "date") else date.fromisoformat(str(max_ts)[:10])
                range_update = (end - timedelta(days=7), end)
            if rm_col.button("✕", key=f"s_rm_{s_id}", help="Remove series"):
                to_remove.append(s_id)

    for s_id in to_remove:
        st.session_state.explore_active_series.remove(s_id)
        st.session_state.explore_series_meta.pop(s_id, None)
        st.session_state.explore_series_stats.pop(s_id, None)
        _invalidate_data_cache()
        st.rerun()

    if range_update is not None:
        start, end = range_update
        st.session_state.explore_start = start
        st.session_state.explore_end = end
        _invalidate_data_cache()
        st.rerun()


# ---------------------------------------------------------------------------
# Visualization renderers (unchanged logic, reorganized into functions)
# ---------------------------------------------------------------------------


def _render_scalar_view(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    annotation_types: list[dict],
    equipment: list[dict],
    event_types: list[dict],
    active_series: list[int] | None = None,
    series_meta: dict[int, dict] | None = None,
) -> None:
    active_series = active_series or []
    series_meta = series_meta or {}
    scalar_channels = [
        ch
        for ch in active_channels
        if channel_meta.get(ch, {}).get("value_kind_id") in (None, VALUE_TYPE_SCALAR)
    ]
    scalar_series = [
        s
        for s in active_series
        if series_meta.get(s, {}).get("value_kind_id") in (None, VALUE_TYPE_SCALAR)
    ]
    if not scalar_channels and not scalar_series:
        st.info("No scalar traces in the active selection.")
        return

    mode = st.session_state.explore_mode
    if mode == "viz":
        st.caption(
            f"Visualization mode — up to {VIZ_MAX_POINTS} points per sensor series "
            "(LTTB downsampled). Lab points (diamonds) are shown in full."
        )
    else:
        st.caption("Extraction mode — full raw data displayed.")

    fig, overlay_rows = _build_scalar_figure(
        scalar_channels, channel_meta, mode, scalar_series, series_meta
    )
    selection = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode=["points", "box", "lasso"],
        key="scalar_chart",
    )
    st.session_state.explore_selected_points = selection

    # Selection actions — sensor channels only (lab traces are read-only)
    selected = selection.get("selection", {}) if selection else {}
    selected_pts = selected.get("points", [])

    if selected_pts and scalar_channels:
        st.markdown(
            f"**{len(selected_pts)} points selected** across "
            f"{len({p.get('curve_number') for p in selected_pts})} traces."
        )

        sel_times = [p.get("x") for p in selected_pts if p.get("x")]
        t_start_sel = min(sel_times) if sel_times else None
        t_end_sel = max(sel_times) if sel_times else None

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create Annotation", type="primary"):
                _annotation_dialog(
                    channel_ids=scalar_channels,
                    start_time=str(t_start_sel) if t_start_sel else None,
                    end_time=str(t_end_sel) if t_end_sel else None,
                    annotation_types=annotation_types,
                )
        with col2:
            if st.button("Tag Equipment Event"):
                st.session_state._show_event_dialog = True
                st.session_state._ann_start = str(t_start_sel)
                st.session_state._ann_end = str(t_end_sel)
    elif selected_pts and not scalar_channels:
        st.caption("Point selection actions are available for sensor channels only.")
    else:
        st.caption("Use box or lasso selection on the chart to select points.")

    # Lab AnalysisSeries annotation — range over the current view window.
    if scalar_series and annotation_types:
        sel_lab = st.selectbox(
            "Annotate lab series",
            options=scalar_series,
            format_func=lambda s: f"LAB-{s}: "
            f"{series_meta.get(s, {}).get('name') or series_meta.get(s, {}).get('parameter_name', '?')}",
            key="lab_ann_series_sel",
        )
        if st.button("Create Lab Annotation", key="btn_lab_ann"):
            start = st.session_state.explore_start
            end = st.session_state.explore_end
            _annotation_dialog(
                channel_ids=[],
                series_ids=[sel_lab],
                start_time=datetime.combine(start, datetime.min.time()).isoformat(),
                end_time=datetime.combine(end, datetime.max.time()).isoformat(),
                annotation_types=annotation_types,
            )

    # Annotations & events summary table
    if overlay_rows:
        st.divider()
        st.subheader("Annotations & equipment events")
        df_ov = pd.DataFrame(overlay_rows)[
            ["ref", "kind", "source", "category", "title", "start", "end", "comment"]
        ]
        df_ov.columns = [
            "#",
            "Type",
            "Channel / Equipment",
            "Category",
            "Title / Notes",
            "Start",
            "End",
            "Comment",
        ]
        st.dataframe(df_ov, use_container_width=True, hide_index=True)

    # Download (sensor + lab)
    st.divider()
    all_rows = _flat_scalar_rows(scalar_channels, channel_meta)
    all_rows += _flat_series_scalar_rows(scalar_series, series_meta)
    if all_rows:
        csv_bytes = _make_csv(all_rows)
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="explore_scalar.csv",
            mime="text/csv",
        )


def _render_vector_view(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    annotation_types: list[dict],
    active_series: list[int] | None = None,
    series_meta: dict[int, dict] | None = None,
) -> None:
    options = _kind_options(
        VALUE_TYPE_VECTOR, active_channels, channel_meta,
        active_series or [], series_meta or {},
    )
    if not options:
        st.info("No vector traces in the active selection.")
        return

    sel_label = st.selectbox(
        "Select trace to display", list(options.keys()), key="vec_chan_sel"
    )
    trace = options[sel_label]

    as_3d = st.toggle("Show as 3D surface", value=False, key="vec_3d")

    data = _load_trace_data(trace)
    if data is None:
        return

    rows = data.get("data", [])
    if not rows:
        st.info("No data in the selected time range.")
        return

    fig = _build_vector_heatmap(data, as_3d=as_3d)
    st.plotly_chart(fig, use_container_width=True, key="vector_chart")

    st.subheader("Slice view")
    slice_type = st.radio(
        "Slice type",
        ["None", "Time slice (value vs bin)", "Bin slice (value vs time)"],
        horizontal=True,
        key="vec_slice_type",
    )
    if slice_type == "Time slice (value vs bin)":
        timestamps = sorted({str(r.get("timestamp", "")) for r in rows})
        sel_ts = st.select_slider("Timestamp", options=timestamps, key="vec_slice_ts")
        slice_fig = _build_vector_slice_time(data, sel_ts)
        st.plotly_chart(slice_fig, use_container_width=True, key="vec_slice_time_chart")
    elif slice_type == "Bin slice (value vs time)":
        df_rows = pd.DataFrame(rows)
        bin_label_map = (
            df_rows.drop_duplicates("bin_index")
            .set_index("bin_index")
            .apply(_bin_label, axis=1)
        )
        bin_options = {str(lbl): idx for idx, lbl in sorted(bin_label_map.items())}
        sel_bin_label = st.select_slider("Bin", options=list(bin_options.keys()), key="vec_slice_bin")
        sel_bin_idx = bin_options[sel_bin_label]
        slice_fig = _build_vector_slice_bin(data, sel_bin_idx)
        st.plotly_chart(slice_fig, use_container_width=True, key="vec_slice_bin_chart")

    if trace[0] == "channel":
        if st.button("Create Annotation", key="vec_ann_btn"):
            start = st.session_state.explore_start
            end = st.session_state.explore_end
            _annotation_dialog(
                channel_ids=[trace[1]],
                start_time=datetime.combine(start, datetime.min.time()).isoformat(),
                end_time=datetime.combine(end, datetime.max.time()).isoformat(),
                annotation_types=annotation_types,
            )

    st.divider()
    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="explore_vector.csv",
        mime="text/csv",
    )


def _render_matrix_view(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    active_series: list[int] | None = None,
    series_meta: dict[int, dict] | None = None,
) -> None:
    options = _kind_options(
        VALUE_TYPE_MATRIX, active_channels, channel_meta,
        active_series or [], series_meta or {},
    )
    if not options:
        st.info("No matrix traces in the active selection.")
        return

    sel_label = st.selectbox(
        "Select trace", list(options.keys()), key="mat_chan_sel"
    )
    trace = options[sel_label]

    data = _load_trace_data(trace)
    if data is None:
        return
    rows = data.get("data", [])
    if not rows:
        st.info("No data in the selected time range.")
        return

    view_mode = st.radio(
        "View mode",
        [
            "Time slice (heatmap at timestamp)",
            "Row slice (time series)",
            "Column slice (time series)",
        ],
        key="mat_view_mode",
        horizontal=True,
    )

    df = pd.DataFrame(rows)
    timestamps = sorted(df["timestamp"].astype(str).unique().tolist())

    if view_mode == "Time slice (heatmap at timestamp)":
        sel_ts = st.select_slider("Timestamp", options=timestamps, key="mat_ts_slider")
        fig = _build_matrix_timeslice(data, sel_ts)
        st.plotly_chart(fig, use_container_width=True, key="matrix_chart")

    elif view_mode == "Row slice (time series)":
        row_label_map = _matrix_axis_label_map(df, "row")
        row_options = {str(label): idx for idx, label in sorted(row_label_map.items())}
        sel_row_label = st.selectbox("Row bin", list(row_options.keys()), key="mat_row_sel")
        sel_row = row_options[sel_row_label]
        fig = _build_matrix_slice_line(data, "row", sel_row)
        st.plotly_chart(fig, use_container_width=True, key="matrix_row_chart")

    else:
        col_label_map = _matrix_axis_label_map(df, "col")
        col_options = {str(label): idx for idx, label in sorted(col_label_map.items())}
        sel_col_label = st.selectbox("Column bin", list(col_options.keys()), key="mat_col_sel")
        sel_col = col_options[sel_col_label]
        fig = _build_matrix_slice_line(data, "col", sel_col)
        st.plotly_chart(fig, use_container_width=True, key="matrix_col_chart")

    st.divider()
    csv_bytes = df.to_csv(index=False).encode()
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="explore_matrix.csv",
        mime="text/csv",
    )


def _render_image_view(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    annotation_types: list[dict],
    equipment: list[dict],
    event_types: list[dict],
    active_series: list[int] | None = None,
    series_meta: dict[int, dict] | None = None,
) -> None:
    options = _kind_options(
        VALUE_TYPE_IMAGE, active_channels, channel_meta,
        active_series or [], series_meta or {},
    )
    if not options:
        st.info("No image traces in the active selection.")
        return

    sel_label = st.selectbox(
        "Select image trace", list(options.keys()), key="img_chan_sel"
    )
    trace = options[sel_label]
    is_channel = trace[0] == "channel"
    t_id = trace[1]

    data = _load_trace_data(trace)
    if data is None:
        return
    rows = data.get("data", [])
    if not rows:
        st.info("No images in the selected time range.")
        return

    st.markdown(f"**{len(rows)} image(s)** in range. Click to view full size.")

    selected_ts = st.session_state.explore_selected_images

    cols_per_row = 4
    for idx, img_meta in enumerate(rows):
        if idx % cols_per_row == 0:
            cols = st.columns(cols_per_row)
        col_obj = cols[idx % cols_per_row]
        ts_str = str(img_meta.get("timestamp", ""))
        # Widget keys must be unique per image. Sensor channels have a unique
        # timestamp per image, but lab replicates share one sample-collection
        # time, so the row index is required to avoid DuplicateElementKey.
        wkey = f"{trace[0]}_{t_id}_{idx}_{ts_str}"
        with col_obj:
            is_checked = st.checkbox(
                "Select",
                value=ts_str in selected_ts,
                key=f"img_sel_{wkey}",
                label_visibility="collapsed",
            )
            if is_checked and ts_str not in selected_ts:
                selected_ts.append(ts_str)
            elif not is_checked and ts_str in selected_ts:
                selected_ts.remove(ts_str)

            try:
                thumb = (
                    get_channel_thumbnail(t_id, ts_str)
                    if is_channel
                    else get_analysis_series_thumbnail(t_id, ts_str)
                )
                st.image(thumb, caption=ts_str[:16], use_container_width=True)
            except APIError:
                st.caption(
                    f"[{img_meta.get('image_width', '?')}x{img_meta.get('image_height', '?')}]"
                )
                st.caption(ts_str[:16])

            if st.button("View", key=f"view_{wkey}"):
                st.session_state.explore_image_detail_ch = trace
                st.session_state.explore_image_detail_ts = ts_str
                st.rerun()

    if st.session_state.explore_image_detail_ch is not None:
        _image_viewer_dialog(
            trace=st.session_state.explore_image_detail_ch,
            timestamp=st.session_state.explore_image_detail_ts,
            annotation_types=annotation_types,
        )
        st.session_state.explore_image_detail_ch = None
        st.session_state.explore_image_detail_ts = None

    st.divider()
    if selected_ts and is_channel:
        st.markdown(f"**{len(selected_ts)} image(s) selected.**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Annotate selected images", type="primary"):
                _annotation_dialog(
                    channel_ids=[t_id],
                    start_time=min(selected_ts) if selected_ts else None,
                    end_time=max(selected_ts) if selected_ts else None,
                    annotation_types=annotation_types,
                )
        with col2:
            if st.button("Tag equipment event"):
                _equipment_event_dialog(
                    start_time=min(selected_ts) if selected_ts else None,
                    end_time=max(selected_ts) if selected_ts else None,
                    equipment_options=equipment,
                    event_type_options=event_types,
                )
    elif selected_ts and not is_channel:
        st.caption("Annotation / event actions are available for sensor channels only.")
    else:
        st.caption("Check image thumbnails above to select them for bulk actions.")

    img_df = pd.DataFrame(rows)
    csv_bytes = img_df.to_csv(index=False).encode()
    st.download_button(
        "Download image list CSV",
        data=csv_bytes,
        file_name="explore_images.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Dynamic visualization area
# ---------------------------------------------------------------------------


def _render_visualization_area(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    annotation_types: list[dict],
    equipment: list[dict],
    event_types: list[dict],
    active_series: list[int] | None = None,
    series_meta: dict[int, dict] | None = None,
) -> None:
    """Show visualization tabs only for value types present across active Traces
    (sensor channels + lab series). Sensor and lab overlay within each type."""
    active_series = active_series or []
    series_meta = series_meta or {}

    if not active_channels and not active_series:
        st.info(
            "No traces added yet. Use the Sensor and Lab pickers above to add "
            "channels and analysis series to your plot."
        )
        return

    # Determine which value types are represented across both sources
    types_present: list[int] = []
    for ch_id in active_channels:
        vt = channel_meta.get(ch_id, {}).get("value_kind_id")
        if vt is not None and vt not in types_present:
            types_present.append(vt)
    for s_id in active_series:
        vt = series_meta.get(s_id, {}).get("value_kind_id")
        if vt is not None and vt not in types_present:
            types_present.append(vt)
    # Preserve natural order scalar < vector < matrix < image
    types_present.sort()

    render_map = {
        VALUE_TYPE_SCALAR: lambda: _render_scalar_view(
            active_channels, channel_meta, annotation_types, equipment, event_types,
            active_series, series_meta,
        ),
        VALUE_TYPE_VECTOR: lambda: _render_vector_view(
            active_channels, channel_meta, annotation_types, active_series, series_meta
        ),
        VALUE_TYPE_MATRIX: lambda: _render_matrix_view(
            active_channels, channel_meta, active_series, series_meta
        ),
        VALUE_TYPE_IMAGE: lambda: _render_image_view(
            active_channels, channel_meta, annotation_types, equipment, event_types,
            active_series, series_meta,
        ),
    }

    if len(types_present) == 0:
        # Channel meta not fully loaded yet — fall back to trying all types
        for fn in render_map.values():
            fn()
        return

    if len(types_present) == 1:
        # Single type: no tabs needed
        render_map[types_present[0]]()
        return

    # Multiple types: show only relevant tabs
    tab_names = [VALUE_TYPE_NAMES[vt] for vt in types_present]
    tabs = st.tabs(tab_names)
    for tab, vt in zip(tabs, types_present):
        with tab:
            render_map[vt]()


# ---------------------------------------------------------------------------
# Sidebar (minimal)
# ---------------------------------------------------------------------------


def _render_sidebar_minimal() -> None:
    with st.sidebar:
        st.markdown(
            "**Data Explorer** lets you visualize and extract time-series data "
            "across all sensor types. Use the picker in the main area to add channels, "
            "then explore your data below."
        )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def main() -> None:
    _init_state()

    # Load lookup data once
    try:
        campaigns = list_campaigns_lookup()
        equipment = list_equipment_lookup()
        parameters = list_parameters_lookup()
    except APIError as e:
        st.error(f"Cannot load lookup data: {e.message}")
        st.stop()

    try:
        annotation_types = list_annotation_kinds()
    except APIError:
        annotation_types = []

    try:
        event_types = list_equipment_event_kinds()
    except APIError:
        event_types = []

    try:
        series_list = list_analysis_series_lookup()
    except APIError:
        series_list = []

    _render_sidebar_minimal()

    # --- Top bar ---
    _render_top_bar()

    st.divider()

    # --- Shared top-level campaign filter ---
    _render_campaign_selector(campaigns)

    # --- Pickers: sensor channels + lab analysis series ---
    _render_channel_picker(campaigns, equipment, parameters)
    _render_series_picker(series_list)

    st.divider()

    # --- Build channel_meta for all active channels ---
    active_channels: list[int] = st.session_state.explore_active_channels
    # Start from cached meta accumulated during add operations
    channel_meta: dict[int, dict] = dict(st.session_state.explore_channel_meta)

    # Fill any gaps (e.g. after page reload) by fetching from API
    missing = [ch for ch in active_channels if ch not in channel_meta]
    if missing:
        try:
            all_ch_data = list_channels(page_size=2000)
            for ch in all_ch_data.get("items", []):
                ch_id = ch["channel_id"]
                if ch_id in active_channels:
                    channel_meta[ch_id] = ch
                    # Persist back to session cache
                    st.session_state.explore_channel_meta[ch_id] = ch
        except APIError:
            pass

    # --- Build series_meta for all active lab series ---
    active_series: list[int] = st.session_state.explore_active_series
    series_meta: dict[int, dict] = dict(st.session_state.explore_series_meta)
    missing_s = [s for s in active_series if s not in series_meta]
    if missing_s:
        by_id = {s["analysis_series_id"]: s for s in series_list}
        for s_id in missing_s:
            rec = by_id.get(s_id)
            if rec:
                series_meta[s_id] = rec
                st.session_state.explore_series_meta[s_id] = rec

    # --- Active trace chips (sensor channels + lab series) ---
    _render_active_chips(channel_meta)
    _render_series_chips(series_meta)

    st.divider()

    # --- Equipment event dialog (triggered from scalar view) ---
    if st.session_state._show_event_dialog:
        st.session_state._show_event_dialog = False
        _equipment_event_dialog(
            start_time=st.session_state._ann_start,
            end_time=st.session_state._ann_end,
            equipment_options=equipment,
            event_type_options=event_types,
        )

    # --- Visualization area ---
    _render_visualization_area(
        active_channels, channel_meta, annotation_types, equipment, event_types,
        active_series, series_meta,
    )


def _in_streamlit_run() -> bool:
    """True when executing inside a Streamlit script run (real app or AppTest).

    Lets unit tests import this module to exercise pure helpers without firing
    main() (which would hit the API)."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return True


if _in_streamlit_run():
    main()
