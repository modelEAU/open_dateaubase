"""Data-access layer for the Explore page.

Extracted from explore.py (Phase 5 follow-up): the value-type / quality
constants and the cached time-series / annotation / equipment-event loaders.
These read the shared explore_* session-state cache (seeded by explore.py's
_init_state) and call api_client; they hold no rendering logic. Re-exported from
explore.py so callers and tests reach them as ``explore.<name>``.
"""

from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from app.api_client import (
    APIError,
    get_analysis_series_stats,
    get_analysis_series_timeseries,
    get_channel_timeseries,
    get_equipment_events,
)

# ---------------------------------------------------------------------------
# Value-type constants
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
