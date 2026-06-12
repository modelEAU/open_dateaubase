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
    create_annotation,
    get_channel_stats,
    get_channel_timeseries,
    get_channel_thumbnail,
    get_channel_image,
    get_equipment_events,
    list_annotation_kinds,
    list_equipment_lookup,
    list_equipment_event_kinds,
    list_quality_codes,
    create_equipment_event,
    list_analysis_series_lookup,
    list_deployment_traces_lookup,
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
        # Unified picker filter state
        "picker_campaign_id": None,
        "picker_location_id": None,
        "picker_parameter_id": None,
        "picker_equipment_id": None,
        "picker_vtype_id": None,
        "picker_search_text": "",
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
        # Build obs_id lookup before LTTB (which selects a subset of original timestamps)
        ts_to_obs: dict = {r.get("timestamp"): r.get("observation_id") for r in rows}

        if mode == "viz":
            ts_list, v_list = lttb(ts_list, v_list, VIZ_MAX_POINTS)
            qc_list = qc_list[: len(ts_list)]  # approximate — just for color

        meta = channel_meta.get(ch_id, {})
        label = f"CH-{ch_id}: {meta.get('equipment_identifier', '?')} / {meta.get('parameter_name', '?')}"
        color = palette[idx % len(palette)]

        marker_colors = [
            QUALITY_COLORS.get(qc, DEFAULT_QUALITY_COLOR) for qc in qc_list
        ]
        obs_id_list = [ts_to_obs.get(ts) for ts in ts_list]

        fig.add_trace(
            go.Scatter(
                x=ts_list,
                y=v_list,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=1.5),
                marker=dict(color=marker_colors, size=5),
                customdata=[["sensor", ch_id, obs_id] for obs_id in obs_id_list],
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
        obs_id_list_lab = [r.get("observation_id") for r in rows]

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
                customdata=[["lab", s_id, obs_id] for obs_id in obs_id_list_lab],
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
    observation_id: int | None = None,
    point_value: float | None = None,
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
        if observation_id is not None:
            val_str = f" (value: {point_value})" if point_value is not None else ""
            st.info(
                f"Pinning to Observation #{observation_id}{val_str} — "
                "this annotation is anchored to the exact replicate you clicked."
            )
        else:
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
            payload: dict = {
                "annotation_type": type_options[sel_type_name],
                "start_time": t_start,
                "end_time": t_end or None,
                "title": title or None,
                "comment": comment or None,
            }
            if observation_id is not None:
                payload["observation_id"] = observation_id

            errors = []

            # Stream-anchored writes: the path id is a Stream_ID. Sensor
            # channels post via anchor_kind="channel", lab series via
            # anchor_kind="series" (api_client routes to the right URL arm).
            if is_lab:
                targets = [(s_id, "series", f"LAB-{s_id}") for s_id in series_ids]
            else:
                targets = [(ch_id, "channel", f"CH-{ch_id}") for ch_id in channel_ids]

            for stream_id, anchor_kind, label in targets:
                try:
                    create_annotation(
                        stream_id=stream_id, data=payload, anchor_kind=anchor_kind
                    )
                except APIError as e:
                    if e.status_code == 422:
                        errors.append(
                            f"{label}: the selected point is not part of this series "
                            f"(Observation #{observation_id}). "
                            "Try refreshing the chart."
                        )
                    else:
                        errors.append(f"{label}: {e.message}")
                except Exception as e:
                    errors.append(f"{label}: {e}")

            if errors:
                st.error("Some annotations failed:\n" + "\n".join(errors))
            else:
                st.success(f"Annotation saved for {len(targets)} stream(s).")
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

    # Image-level annotation is sensor-only for now. Lab AnalysisSeries traces
    # are fully annotatable from the scalar chart view (range + point, via
    # /analysis-series/{id}/annotations); only this per-image affordance remains
    # channel-only.
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
    """Render the full-width top bar: title left, Viz/Extract toggle right."""
    title_col, _, mode_col = st.columns([4, 2, 2])
    with title_col:
        st.title("Data Explorer")
    with mode_col:
        mode_val = st.radio(
            "Mode",
            options=["Viz", "Extract"],
            index=0 if st.session_state.explore_mode == "viz" else 1,
            key="mode_radio",
            horizontal=True,
        )
        st.session_state.explore_mode = "viz" if mode_val == "Viz" else "extract"


def _render_time_strip(
    channel_meta: dict[int, dict],
    channel_stats: dict[int, dict | None],
    series_stats: dict[int, dict | None],
) -> None:
    """Global time range controls: quick-select buttons + From/To date inputs.

    Placed between the active traces list and the visualization area so the
    spatial relationship with the chart is obvious."""

    def _to_date(ts) -> date | None:
        if ts is None:
            return None
        return ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])

    # Collect min/max across all active traces (eager stats already fetched at add time)
    all_min: list[date] = []
    all_max: list[date] = []
    for stats in channel_stats.values():
        if stats:
            d = _to_date(stats.get("min_timestamp"))
            if d:
                all_min.append(d)
            d = _to_date(stats.get("max_timestamp"))
            if d:
                all_max.append(d)
    for stats in series_stats.values():
        if stats:
            d = _to_date(stats.get("min_timestamp"))
            if d:
                all_min.append(d)
            d = _to_date(stats.get("max_timestamp"))
            if d:
                all_max.append(d)

    global_min = min(all_min) if all_min else None
    global_max = max(all_max) if all_max else None

    has_traces = bool(channel_stats or series_stats)

    with st.container(border=True):
        btn_col1, btn_col2, btn_col3, spacer, from_col, to_col = st.columns(
            [1, 1, 1, 1, 2, 2]
        )

        range_update: tuple[date, date] | None = None

        if btn_col1.button("Last 7d", disabled=not has_traces, key="tstrip_7d"):
            end = global_max or date.today()
            range_update = (end - timedelta(days=7), end)

        if btn_col2.button("Last 30d", disabled=not has_traces, key="tstrip_30d"):
            end = global_max or date.today()
            range_update = (end - timedelta(days=30), end)

        if btn_col3.button(
            "All data",
            disabled=global_min is None or global_max is None,
            key="tstrip_all",
        ):
            if global_min and global_max:
                range_update = (global_min, global_max)

        with from_col:
            new_start = st.date_input(
                "From",
                value=st.session_state.explore_start,
                key="tstrip_from",
            )
        with to_col:
            new_end = st.date_input(
                "To",
                value=st.session_state.explore_end,
                key="tstrip_to",
            )

        if range_update is not None:
            st.session_state.explore_start, st.session_state.explore_end = range_update
            _invalidate_data_cache()
            st.rerun()

        if (
            new_start != st.session_state.explore_start
            or new_end != st.session_state.explore_end
        ):
            st.session_state.explore_start = new_start
            st.session_state.explore_end = new_end
            _invalidate_data_cache()
            st.rerun()


# ---------------------------------------------------------------------------
# Unified picker (sensor Deployment Traces + lab AnalysisSeries)
# ---------------------------------------------------------------------------


def _deployment_trace_label(item: dict) -> str:
    """URI-style label: Campaign › Location / Parameter (Equipment)."""
    campaign = item.get("campaign_name") or "—"
    location = item.get("sampling_point_label") or "?"
    parameter = item.get("parameter_name") or "?"
    equipment = item.get("equipment_identifier") or "?"
    return f"{campaign} › {location} / {parameter} ({equipment})"


def _series_label(item: dict) -> str:
    """URI-style label: Campaign › Location / Parameter (Lab)."""
    campaign = item.get("campaign_name") or "—"
    location = item.get("sampling_point_label") or "?"
    parameter = item.get("parameter_name") or "?"
    return f"{campaign} › {location} / {parameter} (Lab)"


def _build_picker_opts(
    deployment_traces: list[dict],
    series_list: list[dict],
) -> tuple[
    dict[str, int | None],
    dict[str, int | None],
    dict[str, int | None],
    dict[str, int | None],
]:
    """Build campaign / location / parameter / equipment option dicts from the combined lists."""
    campaign_opts: dict[str, int | None] = {"(all campaigns)": None}
    location_opts: dict[str, int | None] = {"(all locations)": None}
    parameter_opts: dict[str, int | None] = {"(all parameters)": None}
    equipment_opts: dict[str, int | None] = {"(all equipment)": None}

    seen_campaigns: set = set()
    seen_locations: set = set()
    seen_parameters: set = set()
    seen_equipment: set = set()

    for item in deployment_traces:
        cid = item.get("campaign_id")
        if cid and cid not in seen_campaigns:
            seen_campaigns.add(cid)
            campaign_opts[item.get("campaign_name") or str(cid)] = cid
        lid = item.get("sampling_point_id")
        if lid and lid not in seen_locations:
            seen_locations.add(lid)
            location_opts[item.get("sampling_point_label") or str(lid)] = lid
        pid = item.get("parameter_id")
        if pid and pid not in seen_parameters:
            seen_parameters.add(pid)
            parameter_opts[item.get("parameter_name") or str(pid)] = pid
        eid = item.get("equipment_id")
        if eid and eid not in seen_equipment:
            seen_equipment.add(eid)
            equipment_opts[item.get("equipment_identifier") or str(eid)] = eid

    for item in series_list:
        cid = item.get("campaign_id")
        if cid and cid not in seen_campaigns:
            seen_campaigns.add(cid)
            campaign_opts[item.get("campaign_name") or str(cid)] = cid
        lid = item.get("sampling_point_id")
        if lid and lid not in seen_locations:
            seen_locations.add(lid)
            location_opts[item.get("sampling_point_label") or str(lid)] = lid
        pid = item.get("parameter_id")
        if pid and pid not in seen_parameters:
            seen_parameters.add(pid)
            parameter_opts[item.get("parameter_name") or str(pid)] = pid

    return campaign_opts, location_opts, parameter_opts, equipment_opts


def _apply_picker_filters(
    deployment_traces: list[dict],
    series_list: list[dict],
    campaign_id: int | None,
    location_id: int | None,
    parameter_id: int | None,
    equipment_id: int | None,
    vtype_id: int | None,
    search_text: str,
) -> tuple[list[dict], list[dict]]:
    """Filter both lists by active dropdown values and text search."""
    needle = search_text.strip().lower()

    def dt_matches(item: dict) -> bool:
        if campaign_id is not None and item.get("campaign_id") != campaign_id:
            return False
        if location_id is not None and item.get("sampling_point_id") != location_id:
            return False
        if parameter_id is not None and item.get("parameter_id") != parameter_id:
            return False
        if equipment_id is not None and item.get("equipment_id") != equipment_id:
            return False
        if vtype_id is not None and item.get("value_kind_id") != vtype_id:
            return False
        if needle:
            haystack = " ".join([
                item.get("campaign_name") or "",
                item.get("sampling_point_label") or "",
                item.get("parameter_name") or "",
                item.get("equipment_identifier") or "",
            ]).lower()
            if needle not in haystack:
                return False
        return True

    def series_matches(item: dict) -> bool:
        if campaign_id is not None and item.get("campaign_id") != campaign_id:
            return False
        if location_id is not None and item.get("sampling_point_id") != location_id:
            return False
        if parameter_id is not None and item.get("parameter_id") != parameter_id:
            return False
        if vtype_id is not None and item.get("value_kind_id") != vtype_id:
            return False
        if needle:
            haystack = " ".join([
                item.get("campaign_name") or "",
                item.get("sampling_point_label") or "",
                item.get("parameter_name") or "",
            ]).lower()
            if needle not in haystack:
                return False
        return True

    return (
        [dt for dt in deployment_traces if dt_matches(dt)],
        [s for s in series_list if series_matches(s)],
    )


def _render_unified_picker(
    deployment_traces: list[dict],
    series_list: list[dict],
) -> None:
    """Unified sensor + lab picker with in-memory cross-filtering.

    Sensor side: Deployment Traces (Channel × EquipmentLocationHistory, already
    filtered by the active time window by the caller).
    Lab side: AnalysisSeries, filtered in-memory.
    Both appear in one merged results list, distinguished by (Equipment) vs (Lab)."""

    with st.expander("🔍 Add streams", expanded=True):
        campaign_id = st.session_state.picker_campaign_id
        location_id = st.session_state.picker_location_id
        parameter_id = st.session_state.picker_parameter_id
        equipment_id = st.session_state.picker_equipment_id
        vtype_id = st.session_state.picker_vtype_id
        search_text = st.session_state.picker_search_text

        campaign_opts, location_opts, parameter_opts, equipment_opts = (
            _build_picker_opts(deployment_traces, series_list)
        )

        # --- Five filter dropdowns in one row ---
        c1, c2, c3, c4, c5 = st.columns(5)

        def _selectbox_id(
            col,
            label: str,
            opts: dict[str, int | None],
            current: int | None,
            key: str,
        ) -> int | None:
            labels = list(opts.keys())
            cur_label = next((l for l, v in opts.items() if v == current), labels[0])
            sel = col.selectbox(label, labels, index=labels.index(cur_label), key=key)
            return opts[sel]

        new_campaign = _selectbox_id(c1, "Campaign", campaign_opts, campaign_id, "upicker_campaign")
        new_location = _selectbox_id(c2, "Location", location_opts, location_id, "upicker_location")
        new_parameter = _selectbox_id(c3, "Parameter", parameter_opts, parameter_id, "upicker_parameter")
        new_equipment = _selectbox_id(c4, "Equipment", equipment_opts, equipment_id, "upicker_equipment")

        vtype_labels = list(_VALUE_TYPE_OPTIONS.keys())
        cur_vtype_label = next(
            (l for l, v in _VALUE_TYPE_OPTIONS.items() if v == vtype_id), vtype_labels[0]
        )
        new_vtype = _VALUE_TYPE_OPTIONS[
            c5.selectbox("Type", vtype_labels, index=vtype_labels.index(cur_vtype_label), key="upicker_vtype")
        ]

        # Persist filter changes
        changed = (
            new_campaign != campaign_id
            or new_location != location_id
            or new_parameter != parameter_id
            or new_equipment != equipment_id
            or new_vtype != vtype_id
        )
        if changed:
            st.session_state.picker_campaign_id = new_campaign
            st.session_state.picker_location_id = new_location
            st.session_state.picker_parameter_id = new_parameter
            st.session_state.picker_equipment_id = new_equipment
            st.session_state.picker_vtype_id = new_vtype
            st.rerun()

        # --- Text search ---
        new_search = st.text_input(
            "Search",
            value=search_text,
            placeholder="type location, parameter, equipment, or campaign…",
            key="upicker_search",
            label_visibility="collapsed",
        )
        if new_search != search_text:
            st.session_state.picker_search_text = new_search
            st.rerun()

        st.divider()

        # --- Filter both lists ---
        filtered_traces, filtered_series = _apply_picker_filters(
            deployment_traces, series_list,
            new_campaign, new_location, new_parameter, new_equipment, new_vtype, new_search,
        )

        # Build merged option dict: label -> ("channel"|"series", item)
        options: dict[str, tuple[str, dict]] = {}
        for dt in filtered_traces:
            lbl = _deployment_trace_label(dt)
            # Deduplicate: same channel in same deployment shows once
            key = f"dt_{dt['equipment_location_history_id']}_{dt['channel_id']}"
            if lbl not in options:
                options[lbl] = ("channel", dt)
        for s in filtered_series:
            lbl = _series_label(s)
            if lbl not in options:
                options[lbl] = ("series", s)

        active_channels: list[int] = st.session_state.explore_active_channels
        active_series: list[int] = st.session_state.explore_active_series

        sel_kind: str | None = None
        sel_item: dict | None = None

        if not options:
            st.caption("No streams match the current filters.")
        else:
            sel_label = st.selectbox(
                "Matching streams",
                list(options.keys()),
                key="upicker_trace_select",
                label_visibility="collapsed",
            )
            sel_kind, sel_item = options[sel_label]

        if st.button(
            "+ Add to plot",
            type="primary",
            disabled=sel_item is None,
            key="upicker_add_btn",
        ):
            if sel_kind == "channel" and sel_item is not None:
                ch_id = sel_item["channel_id"]
                if ch_id not in active_channels:
                    active_channels.append(ch_id)
                    st.session_state.explore_channel_meta[ch_id] = sel_item
                    _fetch_channel_stats(ch_id, sel_item)
                    _invalidate_data_cache()
                    st.rerun()
                else:
                    st.info("Channel already in plot.")
            elif sel_kind == "series" and sel_item is not None:
                s_id = sel_item["analysis_series_id"]
                if s_id not in active_series:
                    active_series.append(s_id)
                    st.session_state.explore_series_meta[s_id] = sel_item
                    _fetch_series_stats(s_id)
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
    """Render active Deployment Traces as a list with data range and remove button."""
    active = st.session_state.explore_active_channels

    if not active and not st.session_state.explore_active_series:
        st.caption("No streams added yet — use the picker above.")
        return

    to_remove: list[int] = []

    cols = st.columns([5, 2, 2, 1])
    cols[0].caption("**Stream**")
    cols[1].caption("**First value**")
    cols[2].caption("**Last value**")

    for ch_id in active:
        meta = channel_meta.get(ch_id, {})
        label = _deployment_trace_label(meta) if meta else f"CH-{ch_id}"

        stats = _fetch_channel_stats(ch_id, meta)
        min_ts = stats["min_timestamp"] if stats else None
        max_ts = stats["max_timestamp"] if stats else None
        min_str = str(min_ts)[:10] if min_ts else "—"
        max_str = str(max_ts)[:10] if max_ts else "—"

        with st.container(border=True):
            name_col, min_col, max_col, rm_col = st.columns([5, 2, 2, 1])
            name_col.markdown(label)
            min_col.markdown(min_str)
            max_col.markdown(max_str)
            if rm_col.button("✕", key=f"rm_{ch_id}", help="Remove stream"):
                to_remove.append(ch_id)

    for ch_id in to_remove:
        st.session_state.explore_active_channels.remove(ch_id)
        st.session_state.explore_channel_meta.pop(ch_id, None)
        st.session_state.explore_channel_stats.pop(ch_id, None)
        _invalidate_data_cache()
        st.rerun()


def _render_series_chips(series_meta: dict[int, dict]) -> None:
    """Render active lab AnalysisSeries as a list with data range and remove button."""
    active = st.session_state.explore_active_series
    if not active:
        return

    to_remove: list[int] = []

    for s_id in active:
        meta = series_meta.get(s_id, {})
        label = _series_label(meta) if meta else f"LAB-{s_id}"

        stats = _fetch_series_stats(s_id)
        min_ts = stats["min_timestamp"] if stats else None
        max_ts = stats["max_timestamp"] if stats else None
        min_str = str(min_ts)[:10] if min_ts else "—"
        max_str = str(max_ts)[:10] if max_ts else "—"

        with st.container(border=True):
            name_col, min_col, max_col, rm_col = st.columns([5, 2, 2, 1])
            name_col.markdown(label)
            min_col.markdown(min_str)
            max_col.markdown(max_str)
            if rm_col.button("✕", key=f"s_rm_{s_id}", help="Remove series"):
                to_remove.append(s_id)

    for s_id in to_remove:
        st.session_state.explore_active_series.remove(s_id)
        st.session_state.explore_series_meta.pop(s_id, None)
        st.session_state.explore_series_stats.pop(s_id, None)
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
        st.info("No scalar streams in the active selection.")
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

    # Split selected points into sensor vs lab using the customdata type tag.
    # customdata format: ["sensor", ch_id, obs_id] or ["lab", s_id, obs_id]
    selected = selection.get("selection", {}) if selection else {}
    selected_pts = selected.get("points", [])

    def _cd(pt: dict) -> list:
        return pt.get("customdata") or []

    sensor_pts = [p for p in selected_pts if _cd(p) and _cd(p)[0] == "sensor"]
    lab_pts = [p for p in selected_pts if _cd(p) and _cd(p)[0] == "lab"]

    if sensor_pts or lab_pts:
        st.markdown(
            f"**{len(selected_pts)} points selected** across "
            f"{len({p.get('curve_number') for p in selected_pts})} streams."
        )

    if sensor_pts:
        sel_times = [p.get("x") for p in sensor_pts if p.get("x")]
        t_start_sel = min(sel_times) if sel_times else None
        t_end_sel = max(sel_times) if sel_times else None

        # Single sensor point → pin to its exact observation
        single_sensor_obs_id: int | None = None
        single_sensor_val: float | None = None
        if len(sensor_pts) == 1:
            cd = _cd(sensor_pts[0])
            single_sensor_obs_id = cd[2] if len(cd) > 2 else None
            single_sensor_val = sensor_pts[0].get("y")

        col1, col2 = st.columns(2)
        with col1:
            btn_label = "Create Annotation (point)" if single_sensor_obs_id else "Create Annotation"
            if st.button(btn_label, type="primary", key="btn_sensor_ann"):
                _annotation_dialog(
                    channel_ids=scalar_channels,
                    start_time=str(t_start_sel) if t_start_sel else None,
                    end_time=str(t_end_sel) if t_end_sel else None,
                    annotation_types=annotation_types,
                    observation_id=single_sensor_obs_id,
                    point_value=single_sensor_val,
                )
        with col2:
            if st.button("Tag Equipment Event", key="btn_eq_event"):
                st.session_state._show_event_dialog = True
                st.session_state._ann_start = str(t_start_sel)
                st.session_state._ann_end = str(t_end_sel)
                st.rerun()  # dialog check runs before visualization area in script order

    if lab_pts:
        lab_times = [p.get("x") for p in lab_pts if p.get("x")]
        t_lab_start = min(lab_times) if lab_times else None
        t_lab_end = max(lab_times) if lab_times else None

        # Group by series to support multi-series box selections
        lab_series_ids: list[int] = list(dict.fromkeys(
            _cd(p)[1] for p in lab_pts if len(_cd(p)) > 1
        ))

        # Single lab point → pin to exact replicate observation
        single_lab_obs_id: int | None = None
        single_lab_val: float | None = None
        if len(lab_pts) == 1:
            cd = _cd(lab_pts[0])
            single_lab_obs_id = cd[2] if len(cd) > 2 else None
            single_lab_val = lab_pts[0].get("y")

        lab_btn_label = (
            "Create Lab Annotation (point)" if single_lab_obs_id
            else "Create Lab Annotation (range)"
        )
        if st.button(lab_btn_label, type="primary", key="btn_lab_ann_pt"):
            _annotation_dialog(
                channel_ids=[],
                series_ids=lab_series_ids,
                start_time=str(t_lab_start) if t_lab_start else None,
                end_time=str(t_lab_end) if (t_lab_end and not single_lab_obs_id) else None,
                annotation_types=annotation_types,
                observation_id=single_lab_obs_id,
                point_value=single_lab_val,
            )

    if not selected_pts:
        st.caption("Use box or lasso selection on the chart to select points.")

    # Sensor channel annotation — range over the current view window.
    if scalar_channels and annotation_types:
        sel_ch = st.selectbox(
            "Annotate sensor channel (range)",
            options=scalar_channels,
            format_func=lambda ch: f"CH-{ch}: "
            f"{channel_meta.get(ch, {}).get('parameter_name', '?')} "
            f"({channel_meta.get(ch, {}).get('equipment_identifier', '?')})",
            key="sensor_ann_chan_sel",
        )
        if st.button("Create Annotation (view range)", key="btn_sensor_ann_range"):
            start = st.session_state.explore_start
            end = st.session_state.explore_end
            _annotation_dialog(
                channel_ids=[sel_ch],
                start_time=datetime.combine(start, datetime.min.time()).isoformat(),
                end_time=datetime.combine(end, datetime.max.time()).isoformat(),
                annotation_types=annotation_types,
            )

    # Lab AnalysisSeries annotation — range over the current view window.
    if scalar_series and annotation_types:
        sel_lab = st.selectbox(
            "Annotate lab series (range)",
            options=scalar_series,
            format_func=lambda s: f"LAB-{s}: "
            f"{series_meta.get(s, {}).get('name') or series_meta.get(s, {}).get('parameter_name', '?')}",
            key="lab_ann_series_sel",
        )
        if st.button("Create Lab Annotation (view range)", key="btn_lab_ann"):
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
        st.info("No vector streams in the active selection.")
        return

    sel_label = st.selectbox(
        "Select stream to display", list(options.keys()), key="vec_chan_sel"
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
        st.info("No matrix streams in the active selection.")
        return

    sel_label = st.selectbox(
        "Select stream", list(options.keys()), key="mat_chan_sel"
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
        st.info("No image streams in the active selection.")
        return

    sel_label = st.selectbox(
        "Select image stream", list(options.keys()), key="img_chan_sel"
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
            "No streams added yet. Use the Sensor and Lab pickers above to add "
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
        equipment = list_equipment_lookup()
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

    # Deployment traces filtered by the active time window
    from_dt = datetime.combine(st.session_state.explore_start, datetime.min.time()).isoformat()
    to_dt = datetime.combine(st.session_state.explore_end, datetime.max.time()).isoformat()
    try:
        deployment_traces = list_deployment_traces_lookup(from_dt=from_dt, to_dt=to_dt)
    except APIError:
        deployment_traces = []

    _render_sidebar_minimal()

    # --- Top bar: title + Viz/Extract toggle ---
    _render_top_bar()

    st.divider()

    # --- Unified picker: sensor Deployment Traces + lab AnalysisSeries ---
    _render_unified_picker(deployment_traces, series_list)

    st.divider()

    # --- Active channels / series meta ---
    active_channels: list[int] = st.session_state.explore_active_channels
    channel_meta: dict[int, dict] = dict(st.session_state.explore_channel_meta)

    active_series: list[int] = st.session_state.explore_active_series
    series_meta: dict[int, dict] = dict(st.session_state.explore_series_meta)

    # Fill meta gaps after page reload from deployment traces list
    missing = [ch for ch in active_channels if ch not in channel_meta]
    if missing:
        dt_by_channel = {dt["channel_id"]: dt for dt in deployment_traces}
        for ch_id in missing:
            rec = dt_by_channel.get(ch_id)
            if rec:
                channel_meta[ch_id] = rec
                st.session_state.explore_channel_meta[ch_id] = rec

    missing_s = [s for s in active_series if s not in series_meta]
    if missing_s:
        by_id = {s["analysis_series_id"]: s for s in series_list}
        for s_id in missing_s:
            rec = by_id.get(s_id)
            if rec:
                series_meta[s_id] = rec
                st.session_state.explore_series_meta[s_id] = rec

    # --- Active trace chips ---
    _render_active_chips(channel_meta)
    _render_series_chips(series_meta)

    # --- Global time range strip ---
    _render_time_strip(
        channel_meta,
        st.session_state.explore_channel_stats,
        st.session_state.explore_series_stats,
    )

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
