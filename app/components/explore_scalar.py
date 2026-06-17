"""Scalar value-type figure builder for the Explore page.

Extracted from explore.py (Phase 5 follow-up). Unlike the vector/matrix
builders, this one loads its own data (sensor channels + lab AnalysisSeries
overlays + annotations + equipment events) via the explore_data loaders, then
returns (figure, overlay_rows). Re-exported from explore.py so callers and tests
reach it as ``explore._build_scalar_figure``.
"""

from __future__ import annotations

import plotly.graph_objects as go

from app.components.lttb import lttb
from app.components.explore_data import (
    DEFAULT_QUALITY_COLOR,
    QUALITY_COLORS,
    VIZ_MAX_POINTS,
    _load_annotations,
    _load_equipment_events,
    _load_series_annotations,
    _load_series_timeseries,
    _load_timeseries,
)


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
