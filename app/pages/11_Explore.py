"""Data Explorer page.

Supports multi-series visualization and extraction for all four value types:
  Scalar  — overlaid line charts with annotation overlays and point selection
  Vector  — 2D heatmap (time × bin, color = value) with optional 3D toggle
  Matrix  — time-slice heatmap OR row/col slice line chart
  Image   — thumbnail gallery with fullscreen dialog and multi-select actions
"""

from __future__ import annotations

import io
import csv
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.api_client import (
    APIError,
    get_channel_timeseries,
    get_channel_thumbnail,
    get_channel_image,
    get_equipment_events,
    list_annotation_types,
    list_campaigns_lookup,
    list_equipment_lookup,
    list_parameters_lookup,
    list_channels,
    list_signal_ports,
    list_equipment_event_types,
    create_equipment_event,
)
from app.components.lttb import lttb

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALUE_TYPE_SCALAR = 1
VALUE_TYPE_VECTOR = 2
VALUE_TYPE_MATRIX = 3
VALUE_TYPE_IMAGE = 4

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

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------


def _init_state() -> None:
    defaults: dict = {
        "explore_active_channels": [],  # list[int]
        "explore_start": date.today() - timedelta(days=30),
        "explore_end": date.today(),
        "explore_mode": "viz",
        "explore_data": {},  # (channel_id, start, end) → timeseries dict
        "explore_annotations": {},  # channel_id → list[dict]
        "explore_eq_events": {},  # equipment_id → list[dict]
        "explore_selected_points": {},  # Plotly selection result
        "explore_selected_images": [],  # list[str] timestamps
        "explore_image_detail_ch": None,
        "explore_image_detail_ts": None,
        "_show_annotation_dialog": False,
        "_show_event_dialog": False,
        "_ann_channel_id": None,
        "_ann_start": None,
        "_ann_end": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _invalidate_data_cache() -> None:
    st.session_state.explore_data = {}
    st.session_state.explore_annotations = {}
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
# Chart builders
# ---------------------------------------------------------------------------


def _build_scalar_figure(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    mode: str,
) -> tuple[go.Figure, list[dict]]:
    """Build a multi-trace Plotly figure for scalar data.

    Returns (fig, overlay_rows) where overlay_rows is a list of annotation and
    equipment-event records for the summary table rendered below the chart.
    """
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

    fig.update_layout(
        dragmode="select",
        selectdirection="any",
        xaxis_title="Time",
        yaxis_title="Value",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=40, b=50),
        height=480,
    )
    return fig, overlay_rows


def _build_vector_heatmap(data: dict, as_3d: bool = False) -> go.Figure:
    """Build a 2D heatmap (time × bin) or 3D surface for vector data."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()

    df = pd.DataFrame(rows)
    if df.empty or "bin_index" not in df.columns:
        return go.Figure()

    pivot = df.pivot_table(
        index="bin_index", columns="timestamp", values="value", aggfunc="first"
    )
    z = pivot.values.tolist()
    x = [str(c) for c in pivot.columns.tolist()]
    y = pivot.index.tolist()

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
                zaxis=dict(title="Value"),
            ),
            height=520,
        )
    else:
        fig = go.Figure(
            data=go.Heatmap(z=z, x=x, y=y, colorscale="Viridis", hoverongaps=False)
        )
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Bin index",
            height=420,
        )
    return fig


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

    pivot = slice_df.pivot_table(
        index="row_bin_index", columns="col_bin_index", values="value", aggfunc="first"
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
    if axis == "row":
        slice_df = df[df["row_bin_index"] == bin_idx]
        label = f"Row {bin_idx}"
    else:
        slice_df = df[df["col_bin_index"] == bin_idx]
        label = f"Col {bin_idx}"

    fig = go.Figure(
        go.Scatter(
            x=slice_df["timestamp"].tolist(),
            y=slice_df["value"].tolist(),
            mode="lines+markers",
            name=label,
        )
    )
    fig.update_layout(xaxis_title="Time", yaxis_title="Value", height=380)
    return fig


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------


@st.dialog("Create Annotation", width="large")
def _annotation_dialog(
    channel_ids: list[int],
    start_time: str | None,
    end_time: str | None,
    annotation_types: list[dict],
) -> None:
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
        )
    with col2:
        t_end = st.text_input("End time (ISO, optional)", value=end_time or "")

    title = st.text_input("Title (optional)")
    comment = st.text_area("Comment (optional)")

    if st.button("Save Annotation", type="primary"):
        payload = {
            "annotation_type": type_options[sel_type_name],
            "start_time": t_start,
            "end_time": t_end or None,
            "title": title or None,
            "comment": comment or None,
        }
        errors = []
        from app.api_client import _get_client, _raise_for_status, APIError
        import httpx

        for ch_id in channel_ids:
            try:
                with _get_client() as client:
                    r = client.post(f"/timeseries/{ch_id}/annotations", json=payload)
                _raise_for_status(r)
            except (APIError, Exception) as e:
                errors.append(f"CH-{ch_id}: {e}")

        if errors:
            st.error("Some annotations failed:\n" + "\n".join(errors))
        else:
            st.success(f"Annotation saved for {len(channel_ids)} channel(s).")
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
    channel_id: int,
    timestamp: str,
    annotation_types: list[dict],
) -> None:
    try:
        img_bytes = get_channel_image(channel_id, timestamp)
        st.image(img_bytes, caption=timestamp, use_container_width=True)
    except APIError as e:
        st.warning(f"Could not load full image: {e.message}")

    st.divider()
    if st.button("Create Annotation for this image"):
        st.session_state._show_annotation_dialog = True
        st.session_state._ann_channel_id = channel_id
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


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


_VALUE_TYPE_OPTIONS = {
    "(all types)": None,
    "Scalar": 1,
    "Vector": 2,
    "Matrix": 3,
    "Image": 4,
}


def _render_sidebar(
    campaigns: list[dict],
    equipment: list[dict],
    parameters: list[dict],
) -> None:
    with st.sidebar:
        st.header("Channel selector")

        # --- Campaign filter ---
        campaign_options: dict = {"(all campaigns)": None}
        campaign_options.update(
            {c.get("name", str(c["campaign_id"])): c["campaign_id"] for c in campaigns}
        )
        sel_campaign_name = st.selectbox(
            "Campaign", list(campaign_options.keys()), key="sidebar_campaign"
        )
        sel_campaign_id: int | None = campaign_options[sel_campaign_name]

        # Load channels filtered by campaign to build equipment & parameter lists
        try:
            base_ch = list_channels(
                campaign_id=sel_campaign_id,
                signal_port_id=sel_sp_id,
                page_size=1000
            ).get("items", [])
        except APIError:
            base_ch = []

        # --- Equipment filter (restricted to campaign's equipment) ---
        eq_ids_in_campaign = {
            c["equipment_id"] for c in base_ch if c.get("equipment_id") is not None
        }
        filtered_eq = (
            [e for e in equipment if e["equipment_id"] in eq_ids_in_campaign]
            if sel_campaign_id
            else equipment
        )
        eq_options: dict = {"(all equipment)": None}
        eq_options.update(
            {
                e.get("identifier", str(e["equipment_id"])): e["equipment_id"]
                for e in filtered_eq
            }
        )
        sel_eq_name = st.selectbox(
            "Equipment", list(eq_options.keys()), key="sidebar_equip"
        )
        sel_eq_id: int | None = eq_options[sel_eq_name]

        # --- Parameter filter (restricted to campaign+equipment channels) ---
        param_ids_available = {
            c["parameter_id"]
            for c in base_ch
            if c.get("parameter_id") is not None
            and (sel_eq_id is None or c.get("equipment_id") == sel_eq_id)
        }
        filtered_params = (
            [p for p in parameters if p["parameter_id"] in param_ids_available]
            if base_ch
            else parameters
        )
        param_options: dict = {"(all parameters)": None}
        param_options.update(
            {
                p.get("parameter_name", str(p["parameter_id"])): p["parameter_id"]
                for p in filtered_params
            }
        )
        sel_param_name = st.selectbox(
            "Parameter", list(param_options.keys()), key="sidebar_param"
        )
        sel_param_id: int | None = param_options[sel_param_name]

        # --- Value type filter ---
        sel_vtype_name = st.selectbox("Value type", list(_VALUE_TYPE_OPTIONS.keys()), key="sidebar_vtype")
        sel_vtype_id: int | None = _VALUE_TYPE_OPTIONS[sel_vtype_name]

        # --- Signal Port filter ---
        try:
            sp_data = list_signal_ports(page_size=500).get("items", [])
        except APIError:
            sp_data = []
        sp_options: dict = {"(all signal ports)": None}
        sp_options.update({f"{sp.get('das_name')} / {sp.get('tag')}": sp["signal_port_id"] for sp in sp_data})
        sel_sp_name = st.selectbox("Signal Port", list(sp_options.keys()), key="sidebar_signalport")
        sel_sp_id: int | None = sp_options[sel_sp_name]

        # --- Channel list (fully filtered) ---
        try:
            ch_data = list_channels(
                campaign_id=sel_campaign_id,
                equipment_id=sel_eq_id,
                parameter_id=sel_param_id,
                value_type_id=sel_vtype_id,
                signal_port_id=sel_sp_id,
                page_size=500,
            )
        sel_vtype_id: int | None = _VALUE_TYPE_OPTIONS[sel_vtype_name]

        # --- Channel list (fully filtered) ---
        try:
            ch_data = list_channels(
                campaign_id=sel_campaign_id,
                equipment_id=sel_eq_id,
                parameter_id=sel_param_id,
                value_type_id=sel_vtype_id,
                page_size=500,
            )
            channels = ch_data.get("items", [])
        except APIError as e:
            st.error(f"Cannot load channels: {e.message}")
            channels = []

        if channels:
            ch_options = {
                f"CH-{c['channel_id']}: {c.get('equipment_identifier', '?')} / {c.get('parameter_name', '?')} [{c.get('value_type_name', '?')}]": c[
                    "channel_id"
                ]
                for c in channels
            }
            sel_ch_label = st.selectbox(
                "Channel", list(ch_options.keys()), key="sidebar_chan"
            )
            sel_ch_id = ch_options[sel_ch_label]
        else:
            st.caption("No channels match the current filters.")
            sel_ch_id = None

        if st.button("+ Add to plot", type="primary", disabled=sel_ch_id is None):
            active = st.session_state.explore_active_channels
            if sel_ch_id not in active:
                active.append(sel_ch_id)
                _invalidate_data_cache()
                st.rerun()
            else:
                st.info("Channel already in plot.")

        st.divider()

        # Active series list
        active = st.session_state.explore_active_channels
        if active:
            st.subheader("Active series")
            to_remove = []
            for ch_id in active:
                # Find channel info
                meta = next((c for c in channels if c["channel_id"] == ch_id), None)
                if meta is None:
                    label = f"CH-{ch_id}"
                else:
                    label = f"CH-{ch_id}: {meta.get('equipment_identifier', '?')} / {meta.get('parameter_name', '?')}"
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.caption(label)
                with col_b:
                    if st.button("x", key=f"rm_{ch_id}"):
                        to_remove.append(ch_id)
            for ch_id in to_remove:
                st.session_state.explore_active_channels.remove(ch_id)
                _invalidate_data_cache()
                st.rerun()
        else:
            st.caption("No channels selected. Use the selector above.")

        st.divider()

        # Time range
        st.subheader("Time range")
        new_start = st.date_input(
            "From", value=st.session_state.explore_start, key="date_from"
        )
        new_end = st.date_input("To", value=st.session_state.explore_end, key="date_to")
        if st.button("Apply time range"):
            if (
                new_start != st.session_state.explore_start
                or new_end != st.session_state.explore_end
            ):
                st.session_state.explore_start = new_start
                st.session_state.explore_end = new_end
                _invalidate_data_cache()
                st.rerun()

        st.divider()

        # Mode toggle
        st.subheader("Mode")
        mode = st.radio(
            "Data mode",
            options=["Visualization (downsampled)", "Extraction (raw)"],
            index=0 if st.session_state.explore_mode == "viz" else 1,
            key="mode_radio",
            label_visibility="collapsed",
        )
        st.session_state.explore_mode = "viz" if "Visualization" in mode else "extract"


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------


def _render_scalar_tab(
    active_channels: list[int], channel_meta: dict, annotation_types: list[dict]
) -> None:
    if not active_channels:
        st.info("Add scalar channels from the sidebar to begin.")
        return

    scalar_channels = [
        ch
        for ch in active_channels
        if channel_meta.get(ch, {}).get("value_type_id") in (None, VALUE_TYPE_SCALAR)
    ]
    if not scalar_channels:
        st.info("None of the active channels have scalar data (value_type = 1).")
        return

    mode = st.session_state.explore_mode
    if mode == "viz":
        st.caption(
            f"Visualization mode: up to {VIZ_MAX_POINTS} points per series (LTTB downsampled)."
        )
    else:
        st.caption("Extraction mode: full raw data displayed.")

    fig, overlay_rows = _build_scalar_figure(scalar_channels, channel_meta, mode)
    selection = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode=["points", "box", "lasso"],
        key="scalar_chart",
    )
    st.session_state.explore_selected_points = selection

    # Selection actions
    selected = selection.get("selection", {}) if selection else {}
    selected_pts = selected.get("points", [])

    if selected_pts:
        st.markdown(
            f"**{len(selected_pts)} points selected** across {len({p.get('curve_number') for p in selected_pts})} series."
        )

        # Determine time range of selection
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
    else:
        st.caption("Use box or lasso selection on the chart to select points.")

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

    # Download
    st.divider()
    all_rows = _flat_scalar_rows(scalar_channels, channel_meta)
    if all_rows:
        csv_bytes = _make_csv(all_rows)
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="explore_scalar.csv",
            mime="text/csv",
        )


def _render_vector_tab(
    active_channels: list[int], channel_meta: dict, annotation_types: list[dict]
) -> None:
    vector_channels = [
        ch
        for ch in active_channels
        if channel_meta.get(ch, {}).get("value_type_id") == VALUE_TYPE_VECTOR
    ]
    if not vector_channels:
        st.info("Add vector channels (value_type = 2) from the sidebar.")
        return

    ch_options = {
        f"CH-{ch}: {channel_meta.get(ch, {}).get('equipment_identifier', '?')} / {channel_meta.get(ch, {}).get('parameter_name', '?')}": ch
        for ch in vector_channels
    }
    sel_label = st.selectbox(
        "Select channel to display", list(ch_options.keys()), key="vec_chan_sel"
    )
    ch_id = ch_options[sel_label]

    as_3d = st.toggle("Show as 3D surface", value=False, key="vec_3d")

    data = _load_timeseries(ch_id)
    if data is None:
        return

    rows = data.get("data", [])
    if not rows:
        st.info("No data in the selected time range.")
        return

    fig = _build_vector_heatmap(data, as_3d=as_3d)
    st.plotly_chart(fig, use_container_width=True, key="vector_chart")

    # Annotation creation for vector
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Annotation", key="vec_ann_btn"):
            start = st.session_state.explore_start
            end = st.session_state.explore_end
            _annotation_dialog(
                channel_ids=[ch_id],
                start_time=datetime.combine(start, datetime.min.time()).isoformat(),
                end_time=datetime.combine(end, datetime.max.time()).isoformat(),
                annotation_types=annotation_types,
            )

    # Download
    st.divider()
    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="explore_vector.csv",
        mime="text/csv",
    )


def _render_matrix_tab(active_channels: list[int], channel_meta: dict) -> None:
    matrix_channels = [
        ch
        for ch in active_channels
        if channel_meta.get(ch, {}).get("value_type_id") == VALUE_TYPE_MATRIX
    ]
    if not matrix_channels:
        st.info("Add matrix channels (value_type = 3) from the sidebar.")
        return

    ch_options = {
        f"CH-{ch}: {channel_meta.get(ch, {}).get('equipment_identifier', '?')} / {channel_meta.get(ch, {}).get('parameter_name', '?')}": ch
        for ch in matrix_channels
    }
    sel_label = st.selectbox(
        "Select channel", list(ch_options.keys()), key="mat_chan_sel"
    )
    ch_id = ch_options[sel_label]

    data = _load_timeseries(ch_id)
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
        row_bins = sorted(df["row_bin_index"].unique().tolist())
        sel_row = st.selectbox("Row bin index", row_bins, key="mat_row_sel")
        fig = _build_matrix_slice_line(data, "row", sel_row)
        st.plotly_chart(fig, use_container_width=True, key="matrix_row_chart")

    else:
        col_bins = sorted(df["col_bin_index"].unique().tolist())
        sel_col = st.selectbox("Column bin index", col_bins, key="mat_col_sel")
        fig = _build_matrix_slice_line(data, "col", sel_col)
        st.plotly_chart(fig, use_container_width=True, key="matrix_col_chart")

    # Download
    st.divider()
    csv_bytes = df.to_csv(index=False).encode()
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="explore_matrix.csv",
        mime="text/csv",
    )


def _render_image_tab(
    active_channels: list[int],
    channel_meta: dict,
    annotation_types: list[dict],
    equipment: list[dict],
    event_types: list[dict],
) -> None:
    image_channels = [
        ch
        for ch in active_channels
        if channel_meta.get(ch, {}).get("value_type_id") == VALUE_TYPE_IMAGE
    ]
    if not image_channels:
        st.info("Add image channels (value_type = 4) from the sidebar.")
        return

    ch_options = {
        f"CH-{ch}: {channel_meta.get(ch, {}).get('equipment_identifier', '?')} / {channel_meta.get(ch, {}).get('parameter_name', '?')}": ch
        for ch in image_channels
    }
    sel_label = st.selectbox(
        "Select image channel", list(ch_options.keys()), key="img_chan_sel"
    )
    ch_id = ch_options[sel_label]

    data = _load_timeseries(ch_id)
    if data is None:
        return
    rows = data.get("data", [])
    if not rows:
        st.info("No images in the selected time range.")
        return

    st.markdown(f"**{len(rows)} image(s)** in range. Click to view full size.")

    # Multi-select state
    selected_ts = st.session_state.explore_selected_images

    # Gallery grid — 4 columns
    cols_per_row = 4
    for row_start in range(0, len(rows), cols_per_row):
        chunk = rows[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col_obj, img_meta in zip(cols, chunk):
            ts_str = str(img_meta.get("timestamp", ""))
            with col_obj:
                # Checkbox for multi-select
                is_checked = st.checkbox(
                    "", value=ts_str in selected_ts, key=f"img_sel_{ts_str}"
                )
                if is_checked and ts_str not in selected_ts:
                    selected_ts.append(ts_str)
                elif not is_checked and ts_str in selected_ts:
                    selected_ts.remove(ts_str)

                # Thumbnail
                try:
                    thumb = get_channel_thumbnail(ch_id, ts_str)
                    st.image(thumb, caption=ts_str[:16], use_container_width=True)
                except APIError:
                    st.caption(
                        f"[{img_meta.get('image_width', '?')}×{img_meta.get('image_height', '?')}]"
                    )
                    st.caption(ts_str[:16])

                # View full size
                if st.button("View", key=f"view_{ts_str}"):
                    st.session_state.explore_image_detail_ch = ch_id
                    st.session_state.explore_image_detail_ts = ts_str
                    st.rerun()

    # Open fullscreen dialog if requested
    if st.session_state.explore_image_detail_ch is not None:
        _image_viewer_dialog(
            channel_id=st.session_state.explore_image_detail_ch,
            timestamp=st.session_state.explore_image_detail_ts,
            annotation_types=annotation_types,
        )
        st.session_state.explore_image_detail_ch = None
        st.session_state.explore_image_detail_ts = None

    # Multi-select action bar
    st.divider()
    if selected_ts:
        st.markdown(f"**{len(selected_ts)} image(s) selected.**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Annotate selected images", type="primary"):
                _annotation_dialog(
                    channel_ids=[ch_id],
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
    else:
        st.caption("Check image thumbnails above to select them for bulk actions.")

    # Download image list
    img_df = pd.DataFrame(rows)
    csv_bytes = img_df.to_csv(index=False).encode()
    st.download_button(
        "Download image list CSV",
        data=csv_bytes,
        file_name="explore_images.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="Data Explorer", layout="wide")
    st.title("Data Explorer")

    _init_state()

    # Load lookup data
    try:
        campaigns = list_campaigns_lookup()
        equipment = list_equipment_lookup()
        parameters = list_parameters_lookup()
    except APIError as e:
        st.error(f"Cannot load lookup data: {e.message}")
        st.stop()

    try:
        annotation_types = list_annotation_types()
    except APIError:
        annotation_types = []

    try:
        event_types = list_equipment_event_types()
    except APIError:
        event_types = []

    _render_sidebar(campaigns, equipment, parameters)

    active_channels = st.session_state.explore_active_channels

    # Build channel meta map for all active channels
    channel_meta: dict[int, dict] = {}
    if active_channels:
        try:
            all_ch_data = list_channels(page_size=1000)
            for ch in all_ch_data.get("items", []):
                if ch["channel_id"] in active_channels:
                    channel_meta[ch["channel_id"]] = ch
        except APIError:
            pass

    # Equipment event dialog (triggered from scalar tab)
    if st.session_state._show_event_dialog:
        st.session_state._show_event_dialog = False
        _equipment_event_dialog(
            start_time=st.session_state._ann_start,
            end_time=st.session_state._ann_end,
            equipment_options=equipment,
            event_type_options=event_types,
        )

    # Main tabs
    tab_scalar, tab_vector, tab_matrix, tab_image = st.tabs(
        ["Scalar", "Vector", "Matrix", "Image"]
    )

    with tab_scalar:
        _render_scalar_tab(active_channels, channel_meta, annotation_types)

    with tab_vector:
        _render_vector_tab(active_channels, channel_meta, annotation_types)

    with tab_matrix:
        _render_matrix_tab(active_channels, channel_meta)

    with tab_image:
        _render_image_tab(
            active_channels, channel_meta, annotation_types, equipment, event_types
        )


main()
