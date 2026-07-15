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

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


import pandas as pd
import streamlit as st

from app.api_client import (
    APIError,
    bulk_set_quality_code,
    create_annotation,
    get_channel_stats,
    get_image_thumbnail,
    get_image_file,
    list_annotation_kinds,
    list_event_kinds,
    list_quality_codes,
    create_event,
    list_analysis_series_lookup,
    list_deployment_traces_lookup,
    get_stream_story,
    get_stream_pedigree,
    get_channel_timeseries,
    get_analysis_series_timeseries,
    get_equipment_events,
    get_campaign,
    list_campaigns_lookup,
)
from app.components import entity_story as story
from app.components import explore_export as export
from app.components.labels import NONE_LABEL
from app.components.schema_registry import describe

# Provenance inspector lives in its own module (Phase 5 split). Re-exported here
# so the panel is callable as before and tests can reach the helpers via
# ``explore.<name>``. The panel receives ``_add_node_to_plot`` and
# ``_inspect_stream`` as callbacks so it never needs to import this page.
from app.components.explore_provenance import (  # noqa: E402,F401
    PROVENANCE_COLORS,
    DEFAULT_PROVENANCE_COLOR,
    OPERATION_COLORS,
    DEFAULT_OPERATION_COLOR,
    _ancestor_stream_ids,
    _descendant_stream_ids,
    _ordered_ancestor_steps,
    _build_dag_dot,
    _prov_badge_html,
    _op_badge_html,
    _trait_pills_html,
    _load_provenance,
    _render_provenance_panel,
)
from app.components.explore_vector import (  # noqa: F401
    _bin_label,
    _vector_value_label,
    build_vector_heatmap_option,
    build_vector_surface_option,
    build_vector_slice_time_option,
    build_vector_slice_bin_option,
)
from app.components.explore_matrix import (  # noqa: F401
    _matrix_axis_label_map,
    build_matrix_timeslice_option,
    build_matrix_slice_line_option,
)
from app.components.explore_echarts import (  # noqa: F401
    BRUSH_SELECTED_JS,
    CLICK_SELECTED_JS,
    IMAGE_CLICK_JS,
    IMAGE_TIMELINE_HEIGHT,
    build_image_timeline_option,
    build_scalar_echarts_option,
    resolve_brush_selection,
    thumbnail_data_uri,
)
from app.components.explore_image import _image_viewer_dialog  # noqa: F401
from streamlit_echarts import st_echarts


# ---------------------------------------------------------------------------
# Constants & data loaders live in app.components.explore_data (re-exported
# below). Provenance colour maps live in explore_provenance (re-exported above).
# ---------------------------------------------------------------------------

from app.components.explore_data import (  # noqa: E402,F401
    VALUE_TYPE_SCALAR,
    VALUE_TYPE_VECTOR,
    VALUE_TYPE_MATRIX,
    VALUE_TYPE_IMAGE,
    VALUE_TYPE_NAMES,
    QUALITY_COLORS,
    DEFAULT_QUALITY_COLOR,
    VIZ_MAX_POINTS,
    _VALUE_TYPE_OPTIONS,
    _local_to_utc_iso,
    _load_timeseries,
    _load_series_timeseries,
    _fetch_series_stats,
    _load_trace_data,
    _kind_options,
    _load_annotations,
    _api_list_annotations_for_channel,
    _load_series_annotations,
    _api_list_annotations_for_series,
    _load_equipment_events,
)


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
        # Multi-plot workspace: streams stay in the canonical active_* lists; this
        # layer just groups them across one or more scalar plots.
        "explore_plots": [1],           # ordered list of plot ids
        "explore_next_plot_id": 2,      # next id handed out by "+ Add plot"
        "explore_plot_of": {},          # "ch:<id>" / "s:<id>" -> plot id
        "explore_target_plot": 1,       # plot new streams are added to
        "explore_campaign_filter_id": None,  # page-level campaign scope (None=off)
        "explore_start": date.today() - timedelta(days=30),
        "explore_end": date.today(),
        "explore_mode": "viz",
        "explore_data": {},  # (channel_id, start, end) → timeseries dict
        "explore_annotations": {},  # channel_id → list[dict]
        "explore_series_annotations": {},  # analysis_series_id → list[dict]
        "explore_eq_events": {},  # equipment_id → list[dict]
        "explore_channel_stats": {},     # channel_id -> stats dict (cached)
        "explore_selected_images": [],  # list[int] observation ids
        "explore_image_detail_ch": None,
        "explore_image_detail_obs": None,
        "explore_image_detail_ts": None,
        "_img_click_t": None,  # nonce of the last handled timeline-tick click
        "_show_annotation_dialog": False,
        "_ann_trace": None,  # (kind, id) of the stream the lightbox asked to annotate
        "_ann_obs_id": None,
        "_ann_start": None,
        "_ann_end": None,
        # Unified picker filter state
        "picker_campaign_id": None,
        "picker_location_id": None,
        "picker_parameter_id": None,
        "picker_equipment_id": None,
        "picker_vtype_id": None,
        "picker_search_text": "",
        # Provenance panel
        "explore_inspect_trail": [],       # list[tuple[str, int]] — current = trail[-1]
        "explore_provenance_cache": {},    # stream_id -> resolved provenance graph
        "explore_prov_tab": "Lineage",     # active sub-tab in the panel
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _invalidate_data_cache() -> None:
    st.session_state.explore_data = {}
    st.session_state.explore_annotations = {}
    st.session_state.explore_series_annotations = {}
    st.session_state.explore_eq_events = {}


def _channel_label(ch: dict) -> str:
    eq = ch.get("equipment_identifier") or ch.get("tag_name") or f"EQ-{ch.get('equipment_id') or '?'}"
    param = ch.get("parameter_name") or f"P-{ch.get('parameter_id', '?')}"
    vtype = ch.get("value_type_name") or VALUE_TYPE_NAMES.get(ch.get("value_kind_id"), "?")
    return f"CH-{ch['channel_id']}: {eq} / {param} [{vtype}]"


# ---------------------------------------------------------------------------
# Multi-plot workspace helpers (scalar plots only)
# ---------------------------------------------------------------------------


def _stream_key(kind: str, sid: int) -> str:
    """Assignment-map key for a stream. kind is "ch" (sensor) or "s" (lab)."""
    return f"{kind}:{sid}"


def _plot_of(kind: str, sid: int) -> int:
    """Plot a stream is assigned to (defaults to the first plot)."""
    plots = st.session_state.explore_plots
    default = plots[0] if plots else 1
    return st.session_state.explore_plot_of.get(_stream_key(kind, sid), default)


def _assign_stream_to_plot(kind: str, sid: int, plot_id: int) -> None:
    st.session_state.explore_plot_of[_stream_key(kind, sid)] = plot_id


def _add_plot() -> int:
    """Append a new empty plot and make it the target for new streams."""
    pid = st.session_state.explore_next_plot_id
    st.session_state.explore_plots.append(pid)
    st.session_state.explore_next_plot_id = pid + 1
    st.session_state.explore_target_plot = pid
    return pid


def _delete_plot(plot_id: int) -> None:
    """Delete a plot. Its streams are not removed — they fall back to the first
    remaining plot (each stream keeps its own ✕ for actual removal). Never
    deletes the last plot."""
    plots = st.session_state.explore_plots
    if plot_id not in plots or len(plots) <= 1:
        return
    plots.remove(plot_id)
    fallback = plots[0]
    for k, v in list(st.session_state.explore_plot_of.items()):
        if v == plot_id:
            st.session_state.explore_plot_of[k] = fallback
    if st.session_state.explore_target_plot == plot_id:
        st.session_state.explore_target_plot = fallback


def _render_plot_badges() -> None:
    """Plot-management zone: one badge per plot (click to make it the target for
    new streams; ✕ to delete it) plus an Add-plot control."""
    plots = st.session_state.explore_plots
    target = st.session_state.explore_target_plot
    st.caption("**Plots** — click a badge to send new streams there, ✕ to delete")
    cols = st.columns(len(plots) + 1)
    for i, pid in enumerate(plots):
        is_target = pid == target
        sel_col, del_col = cols[i].columns([3, 1])
        if sel_col.button(
            f"{'🎯 ' if is_target else ''}Plot {pid}",
            key=f"seltgt_{pid}",
            type="primary" if is_target else "secondary",
            help="Send newly added streams to this plot",
            use_container_width=True,
        ):
            st.session_state.explore_target_plot = pid
            st.rerun()
        if del_col.button(
            "✕", key=f"delplot_{pid}", disabled=len(plots) <= 1,
            help=f"Delete Plot {pid}",
        ):
            _delete_plot(pid)
            st.rerun()
    if cols[-1].button("➕ Add plot", key="btn_add_plot", use_container_width=True):
        _add_plot()
        st.rerun()


def _streams_in_plot(
    plot_id: int, active_channels: list[int], active_series: list[int]
) -> tuple[list[int], list[int]]:
    chans = [c for c in active_channels if _plot_of("ch", c) == plot_id]
    sers = [s for s in active_series if _plot_of("s", s) == plot_id]
    return chans, sers


def _plot_move_control(col, kind: str, sid: int) -> None:
    """Per-chip selectbox to move a stream to another plot (only when >1 plot)."""
    plots = st.session_state.explore_plots
    if len(plots) <= 1:
        return
    current = _plot_of(kind, sid)
    labels = {f"Plot {p}": p for p in plots}
    cur_label = next((l for l, v in labels.items() if v == current), list(labels)[0])
    sel = col.selectbox(
        "Plot", list(labels), index=list(labels).index(cur_label),
        key=f"move_{kind}_{sid}", label_visibility="collapsed",
        help="Moves this stream to another plot in the workspace.",
    )
    if labels[sel] != current:
        _assign_stream_to_plot(kind, sid, labels[sel])
        st.rerun()


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------


# --- Recording (ADR-0006 / ADR-0007, wayfinder tickets 004 + 007) -----------
#
# One gesture, one row. The user picks a *named pedigree rung* and a kind; the
# rung alone routes the write — the series takes the 5 verdicts and writes an
# Annotation, every other rung takes the 15 causes and writes an Event on that
# rung's arc FK. The Event/Annotation split never reaches the user's face.

_STREAM_RUNG = "__stream__"
_DEFAULT_RUNG = "equipment_id"
# Narrow → wide. Key = the ADR-0006 arc FK the rung writes; value = what it *is*,
# in the operator's words.
_RUNG_HINTS: dict[str, str] = {
    "channel_id": "the channel",
    "signal_interface_id": "the wire",
    "data_acquisition_system_id": "the logger",
    "equipment_id": "the probe",
    "sampling_point_id": "where it sits",
    "process_unit_id": "the unit",
    "site_id": "the plant",
    "campaign_id": "why it was there",
}


def _stream_label(ped: dict) -> str:
    parts = [ped.get("label") or f"Stream {ped['stream_id']}", ped.get("parameter")]
    return " · ".join(str(p) for p in parts if p)


def _shared_rungs(
    rung_sets: list[dict[str, tuple[int, str]]],
) -> dict[str, tuple[int, str]]:
    """The rungs every set agrees on, id included. A cause is one row on one
    thing, so a rung two selections disagree about is a rung neither can be
    blamed for — it is simply not offered."""
    if not rung_sets:
        return {}
    shared = dict(rung_sets[0])
    for other in rung_sets[1:]:
        shared = {k: v for k, v in shared.items() if other.get(k, (None, ""))[0] == v[0]}
    return shared


def _pedigree_rungs(ped: dict) -> dict[str, tuple[int, str]]:
    """Every arc target a stream's pedigree can name, as arc FK → (id, label).

    Deployment-bound rungs are intersected across the window's segments: a stream
    that was moved mid-selection has no single equipment the recording is about.
    """
    rungs: dict[str, tuple[int, str]] = {}
    if ped.get("kind") == "sensor":
        rungs["channel_id"] = (ped["stream_id"], _stream_label(ped))
    for key in ("signal_interface", "data_acquisition_system"):
        node = ped.get(key)
        if node:
            rungs[f"{key}_id"] = (node["id"], node.get("name") or f"#{node['id']}")

    seg_rungs = []
    for seg in ped.get("deployments") or []:
        one: dict[str, tuple[int, str]] = {}
        if seg.get("equipment_id"):
            one["equipment_id"] = (
                seg["equipment_id"],
                seg.get("equipment_identifier") or f"#{seg['equipment_id']}",
            )
        for arc, node, name_key in (
            ("sampling_point_id", seg.get("sampling_location"), "name"),
            ("process_unit_id", seg.get("process_unit"), "tag"),
            ("site_id", seg.get("site"), "name"),
            ("campaign_id", seg.get("campaign"), "name"),
        ):
            if node and node.get(arc):
                one[arc] = (
                    node[arc],
                    node.get(name_key) or node.get("name") or f"#{node[arc]}",
                )
        seg_rungs.append(one)
    rungs.update(_shared_rungs(seg_rungs))
    return rungs


@st.dialog("Record what happened", width="large")
def _recording_dialog(
    streams: list[tuple[str, int]],
    start_time: str | None,
    end_time: str | None,
    observation_id: int | None = None,
) -> None:
    """``streams`` is what the user selected on the chart: (anchor kind, Stream_ID)
    pairs, where the kind is "channel" (sensor) or "series" (lab)."""
    if not streams:
        st.warning("Nothing selected.")
        return

    try:
        peds = [
            get_stream_pedigree(sid, start=start_time, end=end_time)
            for _kind, sid in streams
        ]
        verdicts = list_annotation_kinds()
        causes = list_event_kinds()
    except APIError as e:
        st.error(f"Cannot load what these series passed through: {e.message}")
        return

    rungs = _shared_rungs([_pedigree_rungs(p) for p in peds])
    rung_keys = [_STREAM_RUNG] + [k for k in _RUNG_HINTS if k in rungs]
    stream_label = (
        _stream_label(peds[0]) if len(peds) == 1
        else f"The {len(peds)} selected series"
    )

    def _rung_label(key: str) -> str:
        if key == _STREAM_RUNG:
            return f"{stream_label}  ·  the series you're looking at"
        return f"{rungs[key][1]}  ·  {_RUNG_HINTS[key]}"

    target = st.selectbox(
        "What did this happen to?",
        rung_keys,
        index=rung_keys.index(_DEFAULT_RUNG) if _DEFAULT_RUNG in rung_keys else 0,
        format_func=_rung_label,
        key="rec_target",
        help=(
            "Everything these series passed through. Pick the rung it happened to — "
            "the series itself if the *data* is what's wrong."
        ),
    )
    on_stream = target == _STREAM_RUNG

    # The rung chose the vocabulary: verdicts about data, causes in the plant.
    kinds = verdicts if on_stream else causes
    id_key = "id" if on_stream else "event_kind_id"
    kind_ids = {k["name"]: k[id_key] for k in kinds}
    kind_help = {k["name"]: k.get("description") or "" for k in kinds}
    # NONE_LABEL first so nothing is silently preselected (house sentinel style);
    # Record stays disabled until a real kind is chosen.
    sel_kind = st.selectbox(
        "What's wrong with the data?" if on_stream else "What happened to it?",
        [NONE_LABEL] + list(kind_ids),
        index=0,
        format_func=lambda n: f"{n} — {kind_help[n]}" if kind_help.get(n) else n,
        key="rec_kind",
        help=(
            "A verdict about the data (drift, fouling, exclusion, …)." if on_stream
            else "Something that happened in the plant (cleaning, calibration, …)."
        ),
    )
    kind_name = None if sel_kind == NONE_LABEL else sel_kind

    when = st.segmented_control(
        "When", ["Moment", "Range", "Still going"], default="Range", key="rec_when"
    ) or "Range"
    col1, col2 = st.columns(2)
    t_start = col1.text_input(
        "Started",
        value=start_time or datetime.now(timezone.utc).isoformat(),
        key="rec_start",
    )
    t_end: str | None = None
    if when == "Range":
        t_end = col2.text_input("Ended", value=end_time or "", key="rec_end")
    else:
        col2.text_input(
            "Ended",
            value="not yet" if when == "Still going" else "—",
            disabled=True,
            key="rec_end_disabled",
        )

    pin = False
    if on_stream and observation_id is not None:
        pin = st.checkbox(
            f"Only the point I clicked (#{observation_id})",
            value=True,
            key="rec_pin",
            help=(
                "Pin this recording to the exact observation you clicked, instead "
                "of the whole selected range."
            ),
        )

    details = st.text_area(
        "Details",
        placeholder="Membrane fouled; cleaned with 5% HCl.",
        key="rec_details",
        help="Free-text note stored with the recording.",
    )

    if not st.button("Record", type="primary", disabled=not kind_name, key="rec_save"):
        return

    if on_stream:
        payload: dict = {
            "annotation_type": kind_ids[kind_name],
            "start_time": t_start,
            "end_time": t_end or None,
            "comment": details or None,
        }
        if pin:
            payload["observation_id"] = observation_id
        # One verdict per selected stream: N rows in one table, not a dual write.
        errors = []
        for anchor_kind, stream_id in streams:
            label = f"{'CH' if anchor_kind == 'channel' else 'LAB'}-{stream_id}"
            try:
                create_annotation(
                    stream_id=stream_id, data=payload, anchor_kind=anchor_kind
                )
            except APIError as e:
                if e.status_code == 422 and pin:
                    errors.append(
                        f"{label}: the point you clicked (#{observation_id}) is not "
                        "part of this series. Try refreshing the chart."
                    )
                else:
                    errors.append(f"{label}: {e.message}")
            except Exception as e:  # noqa: BLE001 - surface whatever the client raised
                errors.append(f"{label}: {e}")
        if errors:
            st.error("Some recordings failed:\n" + "\n".join(errors))
            return
        st.success(f"Recorded on {len(streams)} series.")
    else:
        try:
            create_event({
                "event_kind_id": kind_ids[kind_name],
                "start_datetime": t_start,
                "end_datetime": t_end or None,
                "is_instantaneous": when == "Moment",
                "notes": details or None,
                target: rungs[target][0],  # exactly one arc FK
            })
        except APIError as e:
            st.error(f"Failed: {e.message}")
            return
        st.success(f"Recorded on {rungs[target][1]}.")

    _invalidate_data_cache()
    st.rerun()


@st.dialog("Set quality code", width="large")
def _quality_flag_dialog(
    channel_ids: list[int],
    start_time: str | None,
    end_time: str | None,
) -> None:
    """Not a recording: this **rewrites** the stored quality flag on every point in
    the range. Sensor-only, and deliberately not a tab on the Recording dialog —
    a recording is a claim you can retract, this is an edit to the data."""
    st.warning(
        "This rewrites the stored quality code on every data point in the range, "
        "on every selected channel. It is an edit, not a note."
    )

    try:
        qc_list = list_quality_codes()
    except APIError:
        qc_list = []
    if not qc_list:
        st.warning("No quality codes available.")
        return

    qc_options = {
        f"{qc['name']} ({'usable' if qc.get('is_usable') else 'non-usable'})":
            qc["quality_code_id"]
        for qc in qc_list
    }
    sel_qc_label = st.selectbox(
        "Quality code *",
        list(qc_options),
        key="qc_sel",
        help=describe("Value", "QualityCode"),
    )

    col1, col2 = st.columns(2)
    qc_start = col1.text_input(
        "Start time (ISO)",
        value=start_time or datetime.now(timezone.utc).isoformat(),
        key="qc_start",
        help="First timestamp re-flagged.",
    )
    qc_end = col2.text_input(
        "End time (ISO)",
        value=end_time or datetime.now(timezone.utc).isoformat(),
        key="qc_end",
        help="Last timestamp re-flagged.",
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
            help=(
                f"Viz draws at most {VIZ_MAX_POINTS} points per sensor series "
                "(LTTB downsampling, for display only); Extract plots every raw "
                "point in the range. Exports always contain the full-resolution data."
            ),
        )
        st.session_state.explore_mode = "viz" if mode_val == "Viz" else "extract"


def _render_time_strip(
    channel_meta: dict[int, dict],
    channel_stats: dict[int, dict | None],
    series_stats: dict[int, dict | None],
) -> None:
    """Global time range controls: quick-select buttons + From/To date inputs.

    The date inputs are bound to the same session-state keys as the page's
    active range so quick-select buttons can update them without fighting the
    widget's own cached value. A pending-range flag is used because Streamlit
    does not allow setting a widget key after the widget has been drawn.
    """

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

    # Apply any pending quick-select range *before* the date-input widgets are
    # drawn so they pick up the new value on the next run.
    pending = st.session_state.get("_tstrip_pending")
    if pending is not None:
        st.session_state.explore_start, st.session_state.explore_end = pending
        del st.session_state["_tstrip_pending"]

    with st.container(border=True):
        btn_col1, btn_col2, btn_col3, spacer, from_col, to_col = st.columns(
            [1, 1, 1, 1, 2, 2]
        )

        if btn_col1.button("Last 7d", disabled=not has_traces, key="tstrip_7d"):
            end = global_max or date.today()
            st.session_state._tstrip_pending = (end - timedelta(days=7), end)
            _invalidate_data_cache()
            st.rerun()

        if btn_col2.button("Last 30d", disabled=not has_traces, key="tstrip_30d"):
            end = global_max or date.today()
            st.session_state._tstrip_pending = (end - timedelta(days=30), end)
            _invalidate_data_cache()
            st.rerun()

        if btn_col3.button(
            "All data",
            disabled=global_min is None or global_max is None,
            key="tstrip_all",
        ):
            if global_min and global_max:
                st.session_state._tstrip_pending = (global_min, global_max)
                _invalidate_data_cache()
                st.rerun()

        # On a real range change we must drop annotation/event caches (those are
        # keyed by id, not range); the timeseries cache is range-keyed so it
        # refreshes on its own. The callback ONLY clears the cache — it must not
        # call st.rerun() (Streamlit reruns automatically after the widget
        # change, and a rerun *inside* a callback races the widget commit and is
        # what made the date snap back to its default).
        with from_col:
            st.date_input(
                "From",
                key="explore_start",
                on_change=_invalidate_data_cache,
                help=(
                    "Start of the time window every chart, annotation overlay and "
                    "export uses. Changing it refetches the data for all active streams."
                ),
            )
        with to_col:
            st.date_input(
                "To",
                key="explore_end",
                on_change=_invalidate_data_cache,
                help=(
                    "End of the time window (inclusive, to end of day) every chart, "
                    "annotation overlay and export uses. Changing it refetches the "
                    "data for all active streams."
                ),
            )


# ---------------------------------------------------------------------------
# Unified picker (sensor Deployment Traces + lab AnalysisSeries)
# ---------------------------------------------------------------------------


def _deployment_trace_label(item: dict) -> str:
    """URI-style label for a sensor channel.

    Deployed:   Campaign › Location / Parameter (Equipment)
    Undeployed: [undeployed] Parameter (DAS identifier)
    """
    if not item.get("is_deployed", True):
        parameter = item.get("parameter_name") or "?"
        identifier = item.get("equipment_identifier") or "?"
        return f"[undeployed] {parameter} ({identifier})"
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


def _add_channel_to_plot(node: dict, *, rerun: bool = True) -> bool:
    """Add a sensor channel to the active plot from a deployment-trace-shaped meta
    dict (``channel_id`` + label fields). Returns True if newly added.

    Shared by the picker and the Provenance panel so both add paths stay in sync.
    """
    ch_id = node["channel_id"]
    active = st.session_state.explore_active_channels
    if ch_id in active:
        return False
    active.append(ch_id)
    st.session_state.explore_channel_meta[ch_id] = node
    _assign_stream_to_plot("ch", ch_id, st.session_state.explore_target_plot)
    _fetch_channel_stats(ch_id, node)
    # No cache wipe: the data cache is keyed by (channel, start, end), so adding
    # a stream can't stale the others. The new stream loads lazily on render;
    # already-plotted streams stay cached (no full reload, no slow refetch).
    if rerun:
        st.rerun()
    return True


def _add_series_to_plot(node: dict, *, rerun: bool = True) -> bool:
    """Add a lab AnalysisSeries to the active plot from a meta dict
    (``analysis_series_id`` + label fields). Returns True if newly added."""
    s_id = node["analysis_series_id"]
    active = st.session_state.explore_active_series
    if s_id in active:
        return False
    active.append(s_id)
    st.session_state.explore_series_meta[s_id] = node
    _assign_stream_to_plot("s", s_id, st.session_state.explore_target_plot)
    _fetch_series_stats(s_id)
    # No cache wipe — see _add_channel_to_plot. The cache is range-keyed, so the
    # new series loads lazily while already-plotted streams stay cached.
    if rerun:
        st.rerun()
    return True


def _add_node_to_plot(node: dict, *, rerun: bool = True) -> bool:
    """Dispatch a resolved provenance node to the right add-to-plot path."""
    if node.get("kind") == "series":
        return _add_series_to_plot(node, rerun=rerun)
    return _add_channel_to_plot(node, rerun=rerun)


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
            help: str | None = None,
        ) -> int | None:
            labels = list(opts.keys())
            cur_label = next((l for l, v in opts.items() if v == current), labels[0])
            sel = col.selectbox(
                label, labels, index=labels.index(cur_label), key=key, help=help
            )
            return opts[sel]

        new_campaign = _selectbox_id(
            c1, "Campaign", campaign_opts, campaign_id, "upicker_campaign",
            help="Narrows the stream list below to streams measured under this campaign.",
        )
        new_location = _selectbox_id(
            c2, "Location", location_opts, location_id, "upicker_location",
            help="Narrows the stream list below to streams sampled at this sampling point.",
        )
        new_parameter = _selectbox_id(
            c3, "Parameter", parameter_opts, parameter_id, "upicker_parameter",
            help="Narrows the stream list below to streams measuring this parameter.",
        )
        new_equipment = _selectbox_id(
            c4, "Equipment", equipment_opts, equipment_id, "upicker_equipment",
            help=(
                "Narrows the stream list below to sensor channels on this equipment. "
                "Lab series have no equipment, so picking one hides them."
            ),
        )

        vtype_labels = list(_VALUE_TYPE_OPTIONS.keys())
        cur_vtype_label = next(
            (l for l, v in _VALUE_TYPE_OPTIONS.items() if v == vtype_id), vtype_labels[0]
        )
        new_vtype = _VALUE_TYPE_OPTIONS[
            c5.selectbox(
                "Type", vtype_labels, index=vtype_labels.index(cur_vtype_label),
                key="upicker_vtype",
                help=(
                    "Narrows the stream list below to streams of this value shape. "
                    + describe("Channel", "value_kind_id")
                ),
            )
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
            help=(
                "Free-text filter on the stream list below: a stream is kept when the "
                "text appears in its campaign, location, parameter or equipment name. "
                "It applies on top of the dropdown filters."
            ),
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
                help=(
                    "The streams left by the filters above. The one picked here is what "
                    "'+ Add to plot' adds to the target plot; (Lab) entries are analysis "
                    "series, the others are sensor channels."
                ),
            )
            sel_kind, sel_item = options[sel_label]

        if st.button(
            "+ Add to plot",
            type="primary",
            disabled=sel_item is None,
            key="upicker_add_btn",
        ):
            if sel_kind == "channel" and sel_item is not None:
                if not _add_channel_to_plot(sel_item):
                    st.info("Channel already in plot.")
            elif sel_kind == "series" and sel_item is not None:
                if not _add_series_to_plot(sel_item):
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
    multi = len(st.session_state.explore_plots) > 1

    cols = st.columns([4, 2, 2, 2, 1, 1])
    cols[0].caption("**Stream**")
    cols[1].caption("**First value**")
    cols[2].caption("**Last value**")
    if multi:
        cols[3].caption("**Plot**")

    for ch_id in active:
        meta = channel_meta.get(ch_id, {})
        label = _deployment_trace_label(meta) if meta else f"CH-{ch_id}"

        stats = _fetch_channel_stats(ch_id, meta)
        min_ts = stats["min_timestamp"] if stats else None
        max_ts = stats["max_timestamp"] if stats else None
        min_str = str(min_ts)[:10] if min_ts else "—"
        max_str = str(max_ts)[:10] if max_ts else "—"

        with st.container(border=True):
            name_col, min_col, max_col, plot_col, insp_col, rm_col = st.columns(
                [4, 2, 2, 2, 1, 1]
            )
            name_col.markdown(label)
            min_col.markdown(min_str)
            max_col.markdown(max_str)
            _plot_move_control(plot_col, "ch", ch_id)
            if insp_col.button("🔬", key=f"insp_{ch_id}", help="Inspect provenance"):
                _inspect_stream("channel", ch_id)
            if rm_col.button("✕", key=f"rm_{ch_id}", help="Remove stream"):
                to_remove.append(ch_id)

    for ch_id in to_remove:
        st.session_state.explore_active_channels.remove(ch_id)
        st.session_state.explore_channel_meta.pop(ch_id, None)
        st.session_state.explore_channel_stats.pop(ch_id, None)
        st.session_state.explore_plot_of.pop(_stream_key("ch", ch_id), None)
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
            name_col, min_col, max_col, plot_col, insp_col, rm_col = st.columns(
                [4, 2, 2, 2, 1, 1]
            )
            name_col.markdown(label)
            min_col.markdown(min_str)
            max_col.markdown(max_str)
            _plot_move_control(plot_col, "s", s_id)
            if insp_col.button("🔬", key=f"s_insp_{s_id}", help="Inspect provenance"):
                _inspect_stream("series", s_id)
            if rm_col.button("✕", key=f"s_rm_{s_id}", help="Remove series"):
                to_remove.append(s_id)

    for s_id in to_remove:
        st.session_state.explore_active_series.remove(s_id)
        st.session_state.explore_series_meta.pop(s_id, None)
        st.session_state.explore_series_stats.pop(s_id, None)
        st.session_state.explore_plot_of.pop(_stream_key("s", s_id), None)
        _invalidate_data_cache()
        st.rerun()


# ---------------------------------------------------------------------------
# Provenance panel
# ---------------------------------------------------------------------------


def _inspect_stream(kind: str, stream_id: int) -> None:
    """Push a stream onto the breadcrumb trail and rerun. The trail is independent
    of the active-plot lists (inspecting never requires a stream to be plotted),
    so removing a plotted stream can never desync it."""
    trail = st.session_state.explore_inspect_trail
    if not trail or trail[-1] != (kind, stream_id):
        trail.append((kind, stream_id))
    st.rerun()


def _render_stream_story_panel() -> None:
    """Stream Story — the additive narrative for the currently-inspected stream.

    The provenance DAG and time-series history already live in Explore; this
    panel adds what the stream records, where it has been, its freshness, and
    its annotation log, reusing the shared entity_story components.
    """
    trail = st.session_state.explore_inspect_trail
    if not trail:
        return
    _, stream_id = trail[-1]
    try:
        s = get_stream_story(stream_id)
    except APIError:
        return

    story.inject()
    rec = s["record"]
    title = rec.get("parameter_name") or rec.get("label") or f"Stream {stream_id}"
    with st.expander(f"📖 Stream Story — {title}", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### What it records")
            kind_label = "Sensor channel" if rec.get("kind") == "sensor" else "Lab series"
            last = rec.get("last_point")
            st.markdown(
                f"- **Parameter:** {rec.get('parameter_name') or '—'}\n"
                f"- **Unit / shape:** {rec.get('unit_name') or '—'} · "
                f"{rec.get('value_kind_name') or '—'}\n"
                f"- **Kind:** {kind_label}\n"
                f"- **First point:** {rec.get('first_point') or '—'}\n"
                f"- **Last point:** {last or '—'} ({story.relative_age(last)})\n"
                f"- **Total points:** {rec.get('point_count', 0)}"
            )
        with c2:
            st.markdown("#### Where it's been")
            locs = s["location_history"]
            if locs:
                for loc in locs:
                    span = str(loc.get("valid_from") or "")[:10]
                    span += f" → {str(loc.get('valid_to'))[:10]}" if loc.get("valid_to") else " → now"
                    eq = f" · {loc['equipment']}" if loc.get("equipment") else ""
                    st.markdown(f"- **{loc.get('location') or '?'}** "
                                f"<span class='deau-stale'>{span}{eq}</span>",
                                unsafe_allow_html=True)
            else:
                st.caption("No location history.")
        st.markdown(f"#### Annotations on this stream · {len(s['annotations'])}")
        story.annotation_feed(s["annotations"])


# ---------------------------------------------------------------------------
# Visualization renderers (unchanged logic, reorganized into functions)
# ---------------------------------------------------------------------------


def _render_overlay_table(overlay_rows: list[dict]) -> None:
    """The annotations & equipment-events summary under a chart. The [#] column
    matches the [ref] labels on the chart's markLines."""
    if not overlay_rows:
        return
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


def _render_scalar_view(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    active_series: list[int] | None = None,
    series_meta: dict[int, dict] | None = None,
    suffix: str = "",
) -> None:
    # ``suffix`` namespaces every widget key so this view can be rendered once
    # per plot (multi-plot workspace) without colliding Streamlit keys.
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

    option, series_index_map, overlay_rows = build_scalar_echarts_option(
        scalar_channels, channel_meta, mode, scalar_series, series_meta
    )
    # ECharts canvas chart: native dataZoom (slider + scroll/pinch) for zoom.
    # Selection has two paths that both return the same (seriesIndex, dataIndex)
    # shape: click a marker (single point — reliable + discoverable) or use the
    # toolbox brush (rect / polygon / lineX) for multi-select. resolve_brush_selection
    # maps either back to stream/observation identity.
    brush_payload = st_echarts(
        options=option,
        events={"click": CLICK_SELECTED_JS, "brushSelected": BRUSH_SELECTED_JS},
        height="480px",
        key=f"scalar_chart{suffix}",
    )
    sel = resolve_brush_selection(brush_payload, series_index_map)
    sensor_pts = sel["sensor_pts"]
    lab_pts = sel["lab_pts"]
    selected_pts = sensor_pts + lab_pts

    # The selection *is* the target: (anchor kind, Stream_ID) is what Recording
    # writes on, whether the rung it lands on is the series or something upstream.
    streams: list[tuple[str, int]] = [
        ("channel", ch) for ch in sorted({p["id"] for p in sensor_pts})
    ] + [("series", s) for s in dict.fromkeys(p["id"] for p in lab_pts)]
    sensor_sel_ids = [sid for kind, sid in streams if kind == "channel"]
    sel_times = [p["x"] for p in selected_pts if p.get("x")]
    t_start_sel = str(min(sel_times)) if sel_times else None
    t_end_sel = str(max(sel_times)) if sel_times else None
    # One clicked point pins the recording to that exact replicate.
    single_obs_id = selected_pts[0].get("obs_id") if len(selected_pts) == 1 else None

    st.markdown("##### Record & flag")
    if not selected_pts:
        st.caption(
            "Click a point — or use the brush tool (top-right of the chart) to "
            "box / lasso-select several — to choose what a recording is about. "
            "Recordings apply to the selected points, not the view range. "
            "Scroll or drag the bottom slider to zoom."
        )

    st.caption(f"**Selected observations** · {len(selected_pts)}")
    if selected_pts:
        sel_rows = [
            {"Stream": f"CH-{p['id']}", "Kind": "sensor",
             "Timestamp": p["x"], "Value": p["y"], "Observation": p.get("obs_id")}
            for p in sensor_pts
        ] + [
            {"Stream": f"LAB-{p['id']}", "Kind": "lab",
             "Timestamp": p["x"], "Value": p["y"], "Observation": p.get("obs_id")}
            for p in lab_pts
        ]
        st.dataframe(
            pd.DataFrame(sel_rows), use_container_width=True, hide_index=True
        )

        rec_col, qc_col = st.columns(2)
        if rec_col.button(
            "Record what happened", type="primary", key=f"btn_record{suffix}"
        ):
            _recording_dialog(
                streams=streams,
                start_time=t_start_sel,
                end_time=t_end_sel if not single_obs_id else None,
                observation_id=single_obs_id,
            )
        # Rewriting quality codes is an edit, not a claim — its own gesture, and
        # sensor-only (lab values carry no quality flag).
        if sensor_sel_ids and qc_col.button(
            "Set quality code…", key=f"btn_qc{suffix}"
        ):
            _quality_flag_dialog(
                channel_ids=sensor_sel_ids,
                start_time=t_start_sel,
                end_time=t_end_sel,
            )
    else:
        st.caption("— none —")

    _render_overlay_table(overlay_rows)

    # Bulk export of all active streams lives at the page level (see
    # _render_export_section), not per value-type view.


def _render_vector_view(
    active_channels: list[int],
    channel_meta: dict[int, dict],
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
        "Select stream to display",
        list(options.keys()),
        key="vec_chan_sel",
        help="Which of the selected vector streams to plot. Vector streams store one array of values per timestamp (e.g. a particle-size distribution).",
    )
    trace = options[sel_label]

    as_3d = st.toggle(
        "Show as 3D surface",
        value=False,
        key="vec_3d",
        help="Plot bin × time × value as a surface instead of a stack of 2D lines.",
    )

    data = _load_trace_data(trace)
    if data is None:
        return

    rows = data.get("data", [])
    if not rows:
        st.info("No data in the selected time range.")
        return

    if as_3d:
        st_echarts(
            options=build_vector_surface_option(data),
            height="520px",
            key="vector_chart_3d",
        )
    else:
        st_echarts(
            options=build_vector_heatmap_option(data),
            height="440px",
            key="vector_chart_2d",
        )

    st.subheader("Slice view")
    slice_type = st.radio(
        "Slice type",
        ["None", "Time slice (value vs bin)", "Bin slice (value vs time)"],
        horizontal=True,
        key="vec_slice_type",
        help="Cut the vector series along one axis: a time slice shows every bin at one timestamp; a bin slice shows one bin over time.",
    )
    if slice_type == "Time slice (value vs bin)":
        timestamps = sorted({str(r.get("timestamp", "")) for r in rows})
        sel_ts = st.select_slider("Timestamp", options=timestamps, key="vec_slice_ts")
        st_echarts(
            options=build_vector_slice_time_option(data, sel_ts),
            height="320px",
            key="vec_slice_time_chart",
        )
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
        st_echarts(
            options=build_vector_slice_bin_option(data, sel_bin_idx),
            height="320px",
            key="vec_slice_bin_chart",
        )

    if trace[0] == "channel":
        if st.button("Record what happened", key="vec_ann_btn"):
            _recording_dialog(
                streams=[("channel", trace[1])],
                start_time=_local_to_utc_iso(st.session_state.explore_start),
                end_time=_local_to_utc_iso(st.session_state.explore_end, end_of_day=True),
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
        "Select stream",
        list(options.keys()),
        key="mat_chan_sel",
        help="Which of the selected matrix streams to plot. Matrix streams store a 2D grid of values per timestamp (e.g. a fluorescence EEM).",
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
        help="Cut the matrix along one axis: a time slice shows the whole grid at one timestamp; a row or column slice follows a single bin over time.",
        horizontal=True,
    )

    df = pd.DataFrame(rows)
    timestamps = sorted(df["timestamp"].astype(str).unique().tolist())

    if view_mode == "Time slice (heatmap at timestamp)":
        sel_ts = st.select_slider("Timestamp", options=timestamps, key="mat_ts_slider")
        st_echarts(
            options=build_matrix_timeslice_option(data, sel_ts),
            height="440px",
            key="matrix_chart",
        )

    elif view_mode == "Row slice (time series)":
        row_label_map = _matrix_axis_label_map(df, "row")
        row_options = {str(label): idx for idx, label in sorted(row_label_map.items())}
        sel_row_label = st.selectbox(
            "Row bin",
            list(row_options.keys()),
            key="mat_row_sel",
            help="Which row of the matrix to follow over time.",
        )
        sel_row = row_options[sel_row_label]
        st_echarts(
            options=build_matrix_slice_line_option(data, "row", sel_row),
            height="380px",
            key="matrix_row_chart",
        )

    else:
        col_label_map = _matrix_axis_label_map(df, "col")
        col_options = {str(label): idx for idx, label in sorted(col_label_map.items())}
        sel_col_label = st.selectbox(
            "Column bin",
            list(col_options.keys()),
            key="mat_col_sel",
            help="Which column of the matrix to follow over time.",
        )
        sel_col = col_options[sel_col_label]
        st_echarts(
            options=build_matrix_slice_line_option(data, "col", sel_col),
            height="380px",
            key="matrix_col_chart",
        )



def _render_image_view(
    active_channels: list[int],
    channel_meta: dict[int, dict],
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
        "Select image stream",
        list(options.keys()),
        key="img_chan_sel",
        help="Which of the selected image streams to browse. Image streams store one picture per timestamp.",
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

    # Fetched once and reused by both the timeline (as data URIs, hovered) and the
    # gallery below (raw bytes).
    thumbs: dict[int, bytes] = {}
    for r in rows:
        try:
            thumbs[r["observation_id"]] = get_image_thumbnail(r["observation_id"])
        except APIError:
            pass

    # Same overlay the scalar chart draws: this stream's annotations plus (for a
    # sensor channel) its equipment's lifecycle events.
    eq_id = channel_meta.get(t_id, {}).get("equipment_id") if is_channel else None
    eq_label = channel_meta.get(t_id, {}).get("equipment_identifier") or f"EQ-{eq_id}"
    option, overlay_rows = build_image_timeline_option(
        rows,
        {obs: thumbnail_data_uri(b) for obs, b in thumbs.items()},
        annotations=(
            _load_annotations(t_id) if is_channel else _load_series_annotations(t_id)
        ),
        events=_load_equipment_events(eq_id) if eq_id is not None else [],
        source=f"CH-{t_id}" if is_channel else f"LAB-{t_id}",
        equipment_label=eq_label,
    )
    clicked = st_echarts(
        option,
        events={"click": IMAGE_CLICK_JS},
        height=IMAGE_TIMELINE_HEIGHT,
        key=f"img_timeline_{trace[0]}_{t_id}",
    )
    st.caption(
        "Each tick is one image — hover to preview, click to open it. Dashed lines "
        "and shaded bands are annotations and equipment events."
    )

    # The component replays its last value on every rerun; the click's nonce is what
    # distinguishes a fresh click from that replay (see IMAGE_CLICK_JS).
    if clicked and clicked.get("t") != st.session_state._img_click_t:
        st.session_state._img_click_t = clicked["t"]
        ts_of = {r.get("observation_id"): str(r.get("timestamp", "")) for r in rows}
        st.session_state.explore_image_detail_ch = trace
        st.session_state.explore_image_detail_obs = clicked["obs"]
        st.session_state.explore_image_detail_ts = ts_of.get(clicked["obs"], "")
        st.rerun()

    _render_overlay_table(overlay_rows)

    selected_obs = st.session_state.explore_selected_images

    cols_per_row = 4
    for idx, img_meta in enumerate(rows):
        if idx % cols_per_row == 0:
            cols = st.columns(cols_per_row)
        col_obj = cols[idx % cols_per_row]
        ts_str = str(img_meta.get("timestamp", ""))
        # An image is its Observation: lab replicates of one sample all share the
        # sample-collection timestamp, so a ts key would show one picture N times.
        obs_id = img_meta.get("observation_id")
        wkey = f"{trace[0]}_{t_id}_{obs_id}"
        with col_obj:
            is_checked = st.checkbox(
                "Select",
                value=obs_id in selected_obs,
                key=f"img_sel_{wkey}",
                label_visibility="collapsed",
                help="Tick to include this image in the download.",
            )
            if is_checked and obs_id not in selected_obs:
                selected_obs.append(obs_id)
            elif not is_checked and obs_id in selected_obs:
                selected_obs.remove(obs_id)

            if obs_id in thumbs:
                st.image(thumbs[obs_id], caption=ts_str[:16], use_container_width=True)
            else:
                st.caption(
                    f"[{img_meta.get('image_width', '?')}x{img_meta.get('image_height', '?')}]"
                )
                st.caption(ts_str[:16])

            if st.button("View", key=f"view_{wkey}"):
                st.session_state.explore_image_detail_ch = trace
                st.session_state.explore_image_detail_obs = obs_id
                st.session_state.explore_image_detail_ts = ts_str
                st.rerun()

    if st.session_state.explore_image_detail_ch is not None:
        _image_viewer_dialog(
            trace=st.session_state.explore_image_detail_ch,
            observation_id=st.session_state.explore_image_detail_obs,
            timestamp=st.session_state.explore_image_detail_ts,
        )
        st.session_state.explore_image_detail_ch = None
        st.session_state.explore_image_detail_obs = None
        st.session_state.explore_image_detail_ts = None

    st.divider()
    # Annotations span a time range, so map the selected images back to their times.
    selected_ts = [
        str(r.get("timestamp", "")) for r in rows if r.get("observation_id") in selected_obs
    ]
    if selected_obs:
        st.markdown(f"**{len(selected_obs)} image(s) selected.**")
        if st.button("Record what happened", type="primary"):
            # An image *is* its observation, so a single selected image pins the
            # recording to that exact replicate — co-timed lab replicates would
            # otherwise all be tagged by a shared timestamp.
            single_obs = selected_obs[0] if len(selected_obs) == 1 else None
            _recording_dialog(
                streams=[("channel" if is_channel else "series", t_id)],
                start_time=min(selected_ts) if selected_ts else None,
                end_time=(
                    max(selected_ts) if selected_ts and not single_obs else None
                ),
                observation_id=single_obs,
            )
    else:
        st.caption("Check image thumbnails above to select them for bulk actions.")



# ---------------------------------------------------------------------------
# Dynamic visualization area
# ---------------------------------------------------------------------------


def _render_visualization_area(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    active_series: list[int] | None = None,
    series_meta: dict[int, dict] | None = None,
) -> None:
    """Render the visualization area.

    Scalar streams render in a multi-plot workspace — one ECharts chart per plot,
    grouped by each stream's plot assignment (see _streams_in_plot). Vector /
    matrix / image are single-stream pickers, so they render once over all active
    streams (multi-plot adds nothing there)."""
    active_series = active_series or []
    series_meta = series_meta or {}

    if not active_channels and not active_series:
        st.info(
            "No streams added yet. Use the Sensor and Lab pickers above to add "
            "channels and analysis series to your plot."
        )
        return

    def _is_scalar(vt) -> bool:
        return vt in (None, VALUE_TYPE_SCALAR)

    scalar_present = any(
        _is_scalar(channel_meta.get(c, {}).get("value_kind_id")) for c in active_channels
    ) or any(
        _is_scalar(series_meta.get(s, {}).get("value_kind_id")) for s in active_series
    )

    plots = st.session_state.explore_plots

    # --- Scalar multi-plot workspace ---
    if scalar_present or len(plots) > 1:
        _render_plot_badges()
        for plot_id in plots:
            p_chans, p_sers = _streams_in_plot(plot_id, active_channels, active_series)
            with st.container(border=True):
                st.markdown(f"**Plot {plot_id}**")
                _render_scalar_view(
                    p_chans, channel_meta, p_sers, series_meta,
                    suffix=f"_p{plot_id}",
                )

    # --- Non-scalar views (vector / matrix / image), once over all streams ---
    non_scalar = [VALUE_TYPE_VECTOR, VALUE_TYPE_MATRIX, VALUE_TYPE_IMAGE]
    types_present = [
        vt for vt in non_scalar
        if any(channel_meta.get(c, {}).get("value_kind_id") == vt for c in active_channels)
        or any(series_meta.get(s, {}).get("value_kind_id") == vt for s in active_series)
    ]
    if not types_present:
        return

    render_map = {
        VALUE_TYPE_VECTOR: lambda: _render_vector_view(
            active_channels, channel_meta, active_series, series_meta
        ),
        VALUE_TYPE_MATRIX: lambda: _render_matrix_view(
            active_channels, channel_meta, active_series, series_meta
        ),
        VALUE_TYPE_IMAGE: lambda: _render_image_view(
            active_channels, channel_meta, active_series, series_meta,
        ),
    }

    if len(types_present) == 1:
        render_map[types_present[0]]()
        return

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
# Bulk export: zip of per-stream CSV (UTC) + pedigree YAML
# ---------------------------------------------------------------------------


def _raw_annotations(path: str, start_iso: str, end_iso: str) -> list[dict]:
    """List a stream's annotations over [start,end] WITHOUT the display-time
    local conversion the cached loaders apply — the export keeps UTC throughout."""
    import httpx
    from app.api_client import _get_client, _raise_for_status

    try:
        with _get_client() as client:
            r = client.get(path, params={"from": start_iso, "to": end_iso})
        _raise_for_status(r)
    except (httpx.ConnectError, APIError):
        return []
    return r.json().get("annotations", [])


def _stream_export_filename(prefix: str, sid: int, meta: dict) -> str:
    parameter = meta.get("parameter_name") or "data"
    loc = meta.get("sampling_point_label") or meta.get("equipment_identifier") or ""
    base = f"{prefix}-{sid}_{parameter}"
    return f"{base}_{loc}" if loc else base


def _stream_images(data: dict | None) -> dict:
    """Fetch full-res image bytes per observation id for an image stream."""
    images: dict = {}
    if not data:
        return images
    for row in data.get("data", []):
        obs_id = row.get("observation_id")
        if obs_id is None:
            continue
        try:
            images[obs_id] = get_image_file(obs_id)
        except APIError:
            pass
    return images


def _build_export_entries(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    active_series: list[int],
    series_meta: dict[int, dict],
) -> list[dict]:
    """Assemble one export-entry dict per active stream (raw UTC data + overlay
    annotations/events + pedigree + images). Pure-builder input for
    explore_export.build_export_zip."""
    start_iso = _local_to_utc_iso(st.session_state.explore_start)
    end_iso = _local_to_utc_iso(st.session_state.explore_end, end_of_day=True)
    entries: list[dict] = []

    for ch_id in active_channels:
        meta = channel_meta.get(ch_id, {})
        try:
            data = get_channel_timeseries(ch_id, start=start_iso, end=end_iso)
        except APIError:
            continue
        anns = [
            export.overlay_from_annotation(a)
            for a in _raw_annotations(f"/timeseries/{ch_id}/annotations", start_iso, end_iso)
        ]
        events = []
        eq_id = meta.get("equipment_id")
        if eq_id:
            try:
                events = [
                    export.overlay_from_event(e)
                    for e in get_equipment_events(eq_id, from_dt=start_iso, to_dt=end_iso)
                ]
            except APIError:
                events = []
        images = (
            _stream_images(data)
            if meta.get("value_kind_id") == VALUE_TYPE_IMAGE else {}
        )
        try:
            pedigree = get_stream_pedigree(ch_id, start=start_iso, end=end_iso)
        except APIError:
            pedigree = {}
        entries.append({
            "filename": _stream_export_filename("CH", ch_id, meta),
            "value_kind": meta.get("value_kind_id"),
            "data": data or {},
            "annotations": anns,
            "events": events,
            "pedigree": pedigree,
            "images": images,
        })

    for s_id in active_series:
        meta = series_meta.get(s_id, {})
        try:
            data = get_analysis_series_timeseries(s_id, start=start_iso, end=end_iso)
        except APIError:
            continue
        anns = [
            export.overlay_from_annotation(a)
            for a in _raw_annotations(f"/analysis-series/{s_id}/annotations", start_iso, end_iso)
        ]
        images = (
            _stream_images(data)
            if meta.get("value_kind_id") == VALUE_TYPE_IMAGE else {}
        )
        try:
            pedigree = get_stream_pedigree(s_id, start=start_iso, end=end_iso)
        except APIError:
            pedigree = {}
        entries.append({
            "filename": _stream_export_filename("LAB", s_id, meta),
            "value_kind": meta.get("value_kind_id"),
            "data": data or {},
            "annotations": anns,
            "events": [],  # lab series have no equipment events
            "pedigree": pedigree,
            "images": images,
        })

    return entries


def _render_export_section(
    active_channels: list[int],
    channel_meta: dict[int, dict],
    active_series: list[int],
    series_meta: dict[int, dict],
) -> None:
    """Two-step export: 'Generate export' builds the zip once into session_state,
    then 'Download zip' serves it (avoids rebuilding on every rerun)."""
    if not active_channels and not active_series:
        return
    st.divider()
    st.subheader("⬇ Export data")
    n = len(active_channels) + len(active_series)
    st.caption(
        f"Bundle all {n} active stream(s) as a zip: one CSV per stream "
        "(UTC timestamps, plus annotation & equipment-event columns) and a "
        "pedigree YAML for each."
    )
    if st.button("Generate export", key="btn_generate_export"):
        with st.spinner("Building export…"):
            try:
                quality_labels = {
                    q["quality_code_id"]: q.get("name") for q in list_quality_codes()
                }
            except APIError:
                quality_labels = {}
            entries = _build_export_entries(
                active_channels, channel_meta, active_series, series_meta
            )
            st.session_state.explore_export_zip = export.build_export_zip(
                entries, quality_labels
            )
            st.session_state.explore_export_count = len(entries)

    blob = st.session_state.get("explore_export_zip")
    if blob:
        st.download_button(
            f"Download zip ({len(blob) // 1024} KB · "
            f"{st.session_state.get('explore_export_count', 0)} stream(s))",
            data=blob,
            file_name="dateaubase_export.zip",
            mime="application/zip",
            key="btn_download_export",
        )


# ---------------------------------------------------------------------------
# Campaign filter: scope the whole explorer (plot + export) to one campaign
# ---------------------------------------------------------------------------


def _apply_campaign_window(campaign_id: int) -> None:
    """Snap the active time range to a campaign's date span. Uses the pending-range
    flag so the date-input widgets pick it up on the next run (they can't be set
    after being drawn)."""
    try:
        campaign = get_campaign(campaign_id)
    except APIError:
        return

    def _to_date(value) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    start = _to_date(campaign.get("start_date"))
    end = _to_date(campaign.get("end_date")) or date.today()
    if start:
        st.session_state._tstrip_pending = (start, end)


def _scope_to_campaign(
    deployment_traces: list[dict],
    series_list: list[dict],
    campaign_id: int | None,
) -> tuple[list[dict], list[dict]]:
    """Restrict the pickable sensor traces + lab series to one campaign. With the
    source lists scoped, the picker can only add that campaign's streams, so the
    plot and the export stay within the campaign (its time window is snapped
    separately)."""
    if campaign_id is None:
        return deployment_traces, series_list
    return (
        [d for d in deployment_traces if d.get("campaign_id") == campaign_id],
        [s for s in series_list if s.get("campaign_id") == campaign_id],
    )


def _render_campaign_filter(campaigns: list[dict]) -> None:
    """Page-level campaign scope. Selecting a campaign snaps the time window to
    its span and restricts the stream picker to that campaign — so the plot and
    the export both cover only that campaign's data. '(all campaigns)' clears it."""
    opts: dict[str, int | None] = {"📂 All campaigns (no filter)": None}
    for c in campaigns:
        opts[c.get("name") or str(c.get("campaign_id"))] = c.get("campaign_id")

    current = st.session_state.explore_campaign_filter_id
    labels = list(opts.keys())
    cur_label = next((l for l, v in opts.items() if v == current), labels[0])

    sel = st.selectbox(
        "Campaign filter",
        labels,
        index=labels.index(cur_label),
        key="explore_campaign_filter_sel",
        help="Scope the explorer (plot + download) to one campaign: snaps the time "
        "range to the campaign span and limits the picker to its streams.",
    )
    new_id = opts[sel]
    if new_id != current:
        st.session_state.explore_campaign_filter_id = new_id
        if new_id is not None:
            _apply_campaign_window(new_id)
        _invalidate_data_cache()
        st.rerun()

    if current is not None:
        st.caption(
            "Scoped to this campaign — the time range and the stream picker are "
            "restricted, and exports cover only this span."
        )


def _render_page_body(
    deployment_traces: list[dict],
    series_list: list[dict],
    campaigns: list[dict],
) -> None:
    """Render the main content area of the Explore page (picker, chips, time
    strip, and visualization).  When a provenance trail is active, this is
    placed in the left column of a global two-column layout so the provenance
    panel can sit as a right-hand sidebar at the page level.
    """
    # --- Top bar: title + Viz/Extract toggle ---
    _render_top_bar()

    # --- Page-level campaign filter (scopes plot + export) ---
    _render_campaign_filter(campaigns)

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

    # --- Recording dialog (triggered from the image lightbox, which cannot open a
    # dialog from inside a dialog and so hands the request over via session state) ---
    if st.session_state._show_annotation_dialog:
        st.session_state._show_annotation_dialog = False
        _kind, _t_id = st.session_state._ann_trace or ("channel", None)
        if _t_id is not None:
            _recording_dialog(
                streams=[(_kind, _t_id)],
                start_time=st.session_state._ann_start,
                end_time=st.session_state._ann_end,
                observation_id=st.session_state._ann_obs_id,
            )

    # --- Visualization area ---
    _render_visualization_area(
        active_channels, channel_meta, active_series, series_meta,
    )

    # --- Bulk export (all active streams → zip) ---
    _render_export_section(active_channels, channel_meta, active_series, series_meta)


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def main() -> None:
    _init_state()

    # Recording resolves its own vocabulary + pedigree per gesture (see
    # _recording_dialog), so the page no longer preloads kinds/equipment lookups.
    try:
        series_list = list_analysis_series_lookup()
    except APIError:
        series_list = []

    try:
        campaigns = list_campaigns_lookup()
    except APIError:
        campaigns = []

    # Deployment traces filtered by the active time window
    from_dt = _local_to_utc_iso(st.session_state.explore_start)
    to_dt = _local_to_utc_iso(st.session_state.explore_end, end_of_day=True)
    try:
        deployment_traces = list_deployment_traces_lookup(from_dt=from_dt, to_dt=to_dt)
    except APIError:
        deployment_traces = []

    # Page-level campaign scope: restrict the pickable streams to the campaign.
    deployment_traces, series_list = _scope_to_campaign(
        deployment_traces, series_list, st.session_state.explore_campaign_filter_id
    )

    _render_sidebar_minimal()

    # --- Global page layout: provenance panel as a right-hand sidebar ---
    if st.session_state.explore_inspect_trail:
        body_col, prov_col = st.columns([7, 3])
        with body_col:
            _render_page_body(deployment_traces, series_list, campaigns)
        with prov_col:
            _render_provenance_panel(_add_node_to_plot, _inspect_stream)
    else:
        _render_page_body(deployment_traces, series_list, campaigns)

    # Stream Story — additive narrative panel for the inspected stream.
    _render_stream_story_panel()


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
