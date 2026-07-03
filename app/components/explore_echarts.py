"""ECharts scalar builder + brush-selection resolver for the Data Explorer.

Replaces the Plotly scalar view on the Explore page (issue: plotting UX). Two
pure, unit-testable pieces — no Streamlit, no API — plus a thin glue layer that
explore.py wires to ``st_echarts``:

* ``build_scalar_echarts_option`` — loads the same data the Plotly builder did
  (via explore_data loaders) and returns ``(option, series_index_map,
  overlay_rows)``. ``series_index_map`` lets the resolver translate ECharts
  ``(seriesIndex, dataIndex)`` back to the stream/observation identity the
  annotation workflow needs.
* ``resolve_brush_selection`` — turns the JS ``brushSelected`` payload into the
  ``{"sensor_pts": [...], "lab_pts": [...]}`` shape the annotation/QC/event
  buttons consume (mirrors the old Plotly ``customdata`` contract:
  ``["sensor"|"lab", id, obs_id]``).

The component round-trip itself can't run under AppTest (no browser/JS), so the
glue is intentionally tiny and everything decision-bearing is in these two
functions.
"""

from __future__ import annotations

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

SENSOR_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]
LAB_PALETTE = [
    "#1b9e77", "#d95f02", "#7570b3", "#e7298a",
    "#66a61e", "#e6ab02", "#a6761d", "#666666",
]
EVENT_BAND = "#5588aa"
EVENT_LINE = "#7aaabb"

# JS handler registered on the chart. ECharts fires brushSelected with a
# `batch`; each batch entry's `selected` lists the in-brush dataIndex per
# series. We hand the raw (seriesIndex, dataIndex[]) list back to Python and do
# the identity mapping there (resolve_brush_selection).
BRUSH_SELECTED_JS = (
    "function(params){"
    " var b = (params.batch && params.batch[0]) ? params.batch[0].selected : [];"
    " return b.map(function(s){return {seriesIndex: s.seriesIndex, dataIndex: s.dataIndex};});"
    "}"
)

# Click is the reliable, discoverable single-point selector (just click a marker).
# It returns the SAME shape as the brush handler so one resolver handles both.
CLICK_SELECTED_JS = (
    "function(p){"
    " if(p.componentType!=='series'){return null;}"
    " return [{seriesIndex: p.seriesIndex, dataIndex: [p.dataIndex]}];"
    "}"
)


def _qc_color(qc) -> str:
    return QUALITY_COLORS.get(qc, DEFAULT_QUALITY_COLOR)


def _series_value_label(data: dict | None, meta: dict) -> str:
    """Y-axis label as 'parameter (unit)'. The loaded time-series payload carries
    both fields reliably; the picker meta (DeploymentTraceLookupItem) has no
    unit, so prefer the data and fall back to meta."""
    data = data or {}
    param = data.get("parameter") or meta.get("parameter_name") or ""
    unit = data.get("unit") or meta.get("unit_name") or ""
    return f"{param} ({unit})" if param and unit else param or unit or "Value"


def _overlay_markers(
    overlay_rows: list[dict],
    spans: list[dict],
    *,
    source: str,
    kind: str,
    items: list[dict],
    color_of,
    band_color: str | None = None,
) -> None:
    """Append annotation/equipment-event records to overlay_rows and collect
    markArea/markLine spans (consumed below to decorate the owning series)."""
    for it in items:
        t_start = it["start"]
        t_end = it["end"] or t_start
        ref = len(overlay_rows) + 1
        color = band_color or color_of(it)
        overlay_rows.append(
            {
                "ref": ref, "kind": kind, "source": source,
                "category": it.get("category", "") or "",
                "title": it.get("title", "") or "",
                "start": t_start, "end": it["end"] or "",
                "comment": it.get("comment", "") or "",
            }
        )
        spans.append({"ref": ref, "start": t_start, "end": t_end, "color": color})


def build_scalar_echarts_option(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    mode: str,
    active_series: list[int] | None = None,
    series_meta: dict[int, dict] | None = None,
) -> tuple[dict, list[dict], list[dict]]:
    """Build the ECharts ``option`` for the scalar view.

    Returns ``(option, series_index_map, overlay_rows)``:
      * ``series_index_map[i]`` describes the i-th ECharts series — its kind
        ("sensor"/"lab"), stream id, and a per-dataIndex list of
        ``{"x","y","obs_id"}`` so a brush dataIndex maps straight to an
        observation.
      * ``overlay_rows`` feeds the annotations & equipment-events summary table.
    """
    active_series = active_series or []
    series_meta = series_meta or {}

    echarts_series: list[dict] = []
    series_index_map: list[dict] = []
    overlay_rows: list[dict] = []
    y_labels: list[str] = []
    seen_labels: set[str] = set()
    drawn_eq: set = set()

    def _track_label(lbl: str) -> None:
        if lbl not in seen_labels:
            seen_labels.add(lbl)
            y_labels.append(lbl)

    # --- Sensor channels: line+markers ---
    for idx, ch_id in enumerate(active_channels):
        data = _load_timeseries(ch_id)
        if not data or not data.get("data"):
            continue
        rows = data["data"]
        ts_list = [r.get("timestamp") for r in rows]
        v_list = [r.get("value") for r in rows]
        qc_list = [r.get("quality_code") for r in rows]
        ts_to_obs = {r.get("timestamp"): r.get("observation_id") for r in rows}

        if mode == "viz":
            ts_list, v_list = lttb(ts_list, v_list, VIZ_MAX_POINTS)
            qc_list = qc_list[: len(ts_list)]
        obs_list = [ts_to_obs.get(ts) for ts in ts_list]

        meta = channel_meta.get(ch_id, {})
        _track_label(_series_value_label(data, meta))
        label = f"CH-{ch_id}: {meta.get('equipment_identifier', '?')} / {meta.get('parameter_name', '?')}"
        color = SENSOR_PALETTE[idx % len(SENSOR_PALETTE)]

        points = [
            {"x": x, "y": y, "obs_id": o} for x, y, o in zip(ts_list, v_list, obs_list)
        ]
        ec_data = [
            {"value": [x, y], "itemStyle": {"color": _qc_color(qc)}}
            for x, y, qc in zip(ts_list, v_list, qc_list)
        ]

        spans: list[dict] = []
        _overlay_markers(
            overlay_rows, spans, source=f"CH-{ch_id}", kind="Annotation",
            items=[
                {"start": a.get("start_time"), "end": a.get("end_time"),
                 "category": (a.get("type") or {}).get("name", ""),
                 "title": a.get("title"), "comment": a.get("comment"),
                 "color": (a.get("type") or {}).get("color") or "#888888"}
                for a in _load_annotations(ch_id)
            ],
            color_of=lambda it: it["color"],
        )
        eq_id = meta.get("equipment_id")
        if eq_id is not None and eq_id not in drawn_eq:
            drawn_eq.add(eq_id)
            eq_label = meta.get("equipment_identifier") or f"EQ-{eq_id}"
            _overlay_markers(
                overlay_rows, spans, source=eq_label, kind="Equipment Event",
                items=[
                    {"start": ev.get("start_datetime"), "end": ev.get("end_datetime"),
                     "category": ev.get("event_type_name", ""), "title": ev.get("notes")}
                    for ev in _load_equipment_events(eq_id)
                ],
                color_of=lambda it: EVENT_BAND, band_color=EVENT_BAND,
            )

        # ECharts line series have no brushSelector — the toolbox brush cannot
        # point-select them. So the line is a decorative (non-selectable) layer
        # with its symbols hidden, and a companion scatter draws the markers and
        # is the brushable layer that carries point identity. The two share a
        # legend name so they toggle as one. The decorative line keeps a
        # placeholder map entry so seriesIndex stays 1:1 with series_index_map.
        line = _line_series(label, color, ec_data, spans)
        line["showSymbol"] = False
        echarts_series.append(line)
        series_index_map.append({"kind": "decor"})

        echarts_series.append(_sensor_marker_series(label, color, ec_data))
        series_index_map.append({"kind": "sensor", "id": ch_id, "points": points})

    # --- Lab AnalysisSeries: scatter (diamonds) ---
    for idx, s_id in enumerate(active_series):
        data = _load_series_timeseries(s_id)
        if not data or not data.get("data"):
            continue
        rows = data["data"]
        ts_list = [r.get("timestamp") for r in rows]
        v_list = [r.get("value") for r in rows]
        qc_list = [r.get("quality_code") for r in rows]
        obs_list = [r.get("observation_id") for r in rows]

        smeta = series_meta.get(s_id, {})
        _track_label(_series_value_label(data, smeta))
        label = (
            f"LAB-{s_id}: {smeta.get('name') or smeta.get('parameter_name', '?')} "
            f"@ {smeta.get('sampling_point_label', '?')}"
        )
        outline = LAB_PALETTE[idx % len(LAB_PALETTE)]

        points = [
            {"x": x, "y": y, "obs_id": o} for x, y, o in zip(ts_list, v_list, obs_list)
        ]
        ec_data = [
            {"value": [x, y],
             "itemStyle": {"color": _qc_color(qc), "borderColor": outline, "borderWidth": 1.5}}
            for x, y, qc in zip(ts_list, v_list, qc_list)
        ]

        spans = []
        _overlay_markers(
            overlay_rows, spans, source=f"LAB-{s_id}", kind="Annotation",
            items=[
                {"start": a.get("start_time"), "end": a.get("end_time"),
                 "category": (a.get("type") or {}).get("name", ""),
                 "title": a.get("title"), "comment": a.get("comment"),
                 "color": (a.get("type") or {}).get("color") or "#888888"}
                for a in _load_series_annotations(s_id)
            ],
            color_of=lambda it: it["color"],
        )

        echarts_series.append(
            _scatter_series(label, outline, ec_data, spans)
        )
        series_index_map.append({"kind": "lab", "id": s_id, "points": points})

    y_axis_title = " / ".join(y_labels) if y_labels else "Value"

    option = {
        "tooltip": {"trigger": "item", "axisPointer": {"type": "cross"}},
        "legend": {"top": 0, "type": "scroll"},
        "grid": {"left": 76, "right": 24, "top": 48, "bottom": 80, "containLabel": True},
        "xAxis": {
            "type": "time", "name": "Time",
            "nameLocation": "middle", "nameGap": 28,
        },
        "yAxis": {
            "type": "value", "name": y_axis_title, "scale": True,
            # Render the parameter (unit) as a proper rotated axis title, like the
            # old Plotly yaxis_title — not the tiny default label at the axis top.
            "nameLocation": "middle", "nameGap": 44,
            "nameTextStyle": {"fontWeight": "bold"},
        },
        "dataZoom": [
            {"type": "inside", "xAxisIndex": 0},
            {"type": "slider", "xAxisIndex": 0, "bottom": 8},
        ],
        "toolbox": {"feature": {"brush": {"type": ["rect", "polygon", "lineX", "clear"]}}},
        "brush": {
            "xAxisIndex": 0,
            "throttleType": "debounce",
            "throttleDelay": 300,
            "brushStyle": {"borderColor": "#5b8def", "color": "rgba(91,141,239,0.12)"},
        },
        "series": echarts_series,
    }
    return option, series_index_map, overlay_rows


def _markarea_markline(spans: list[dict]) -> dict:
    """Return markArea + markLine config drawing the [ref]-labelled bands/lines."""
    extra: dict = {}
    if not spans:
        return extra
    extra["markArea"] = {
        "silent": True,
        "data": [
            [
                {"xAxis": s["start"], "itemStyle": {"color": s["color"], "opacity": 0.08}},
                {"xAxis": s["end"]},
            ]
            for s in spans
        ],
    }
    extra["markLine"] = {
        "symbol": "none",
        "data": [
            {
                "xAxis": s["start"],
                "lineStyle": {"color": s["color"], "type": "dashed", "width": 1.5},
                "label": {"formatter": f"[{s['ref']}]", "color": s["color"]},
            }
            for s in spans
        ],
    }
    return extra


def _line_series(name: str, color: str, data: list[dict], spans: list[dict]) -> dict:
    s = {
        "name": name, "type": "line", "showSymbol": True, "symbolSize": 5,
        "lineStyle": {"color": color, "width": 1.5}, "itemStyle": {"color": color},
        "emphasis": {"focus": "series"}, "data": data,
    }
    s.update(_markarea_markline(spans))
    return s


def _sensor_marker_series(name: str, color: str, data: list[dict]) -> dict:
    """Brushable point layer sitting on the decorative sensor line. Same legend
    name as the line so the two toggle together; per-point qc colours ride on
    each data item's itemStyle (data is shared with the line)."""
    return {
        "name": name, "type": "scatter", "symbol": "circle", "symbolSize": 5,
        "itemStyle": {"color": color}, "emphasis": {"focus": "series"},
        "data": data,
    }


def _scatter_series(name: str, outline: str, data: list[dict], spans: list[dict]) -> dict:
    s = {
        "name": name, "type": "scatter", "symbol": "diamond", "symbolSize": 11,
        "itemStyle": {"color": outline}, "emphasis": {"focus": "series"}, "data": data,
    }
    s.update(_markarea_markline(spans))
    return s


def resolve_brush_selection(payload, series_index_map: list[dict]) -> dict:
    """Translate the brushSelected JS payload into the annotation workflow shape.

    ``payload`` is the list of ``{"seriesIndex", "dataIndex": [...]}`` returned
    by BRUSH_SELECTED_JS (or None when nothing is selected / no browser).
    Returns ``{"sensor_pts": [...], "lab_pts": [...]}`` where each point is
    ``{"x","y","obs_id","id"}`` — matching what _render_scalar_view consumed
    from the old Plotly customdata.
    """
    out: dict[str, list[dict]] = {"sensor_pts": [], "lab_pts": []}
    if not payload:
        return out
    for sel in payload:
        si = sel.get("seriesIndex")
        if si is None or si < 0 or si >= len(series_index_map):
            continue
        smap = series_index_map[si]
        if smap["kind"] not in ("sensor", "lab"):
            continue  # decorative line layer — not a selectable identity series
        bucket = "sensor_pts" if smap["kind"] == "sensor" else "lab_pts"
        pts = smap["points"]
        for di in sel.get("dataIndex") or []:
            if 0 <= di < len(pts):
                p = pts[di]
                out[bucket].append(
                    {"x": p["x"], "y": p["y"], "obs_id": p["obs_id"], "id": smap["id"]}
                )
    return out
