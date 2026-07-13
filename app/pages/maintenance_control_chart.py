"""Maintenance Control Chart — PRD-2.5 S2.

Plots a drift Channel's values over time with:
- Horizontal upper/lower limit lines (UI-only, not persisted)
- Out-of-limit points highlighted
- Quality-flagged points shown distinctly
- Source (raw) Channel values as a second series for context
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app.api_client import (
    APIError,
    get_channel_timeseries,
    get_event_maintenance_drift,
    list_channels,
    list_quality_codes,
)


# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------


def _init_state() -> None:
    defaults: dict = {
        "mcc_drift_channel_id": None,
        "mcc_source_channel_id": None,
        "mcc_start": date.today() - timedelta(days=30),
        "mcc_end": date.today(),
        "mcc_upper_limit": 5.0,
        "mcc_lower_limit": -5.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _fetch_timeseries(channel_id: int, start: date, end: date) -> list[dict]:
    """Fetch scalar timeseries rows for a channel. Returns [] on error."""
    start_iso = start.isoformat() + "T00:00:00Z"
    end_iso = end.isoformat() + "T23:59:59Z"
    try:
        data = get_channel_timeseries(channel_id, start=start_iso, end=end_iso)
    except APIError:
        return []
    if not data:
        return []
    return data.get("data", [])


def _build_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Convert timeseries rows to a DataFrame with timestamp, value, quality columns."""
    if not rows:
        return pd.DataFrame(columns=["timestamp", "value", "quality_code_id"])
    df = pd.DataFrame(rows)
    # Normalise expected columns
    for col in ("timestamp", "value", "quality_code_id"):
        if col not in df.columns:
            df[col] = None
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["timestamp", "value"]).sort_values("timestamp")
    return df[["timestamp", "value", "quality_code_id"]]


# ---------------------------------------------------------------------------
# Chart builder
# ---------------------------------------------------------------------------


def _build_chart_option(
    drift_df: pd.DataFrame,
    source_df: pd.DataFrame,
    upper_limit: float,
    lower_limit: float,
    quality_codes: dict[int, str],
    drift_label: str = "Drift",
    source_label: str = "Raw source",
) -> dict:
    """Build an ECharts option dict for the control chart."""

    def _row_to_point(row) -> dict:
        ts = row["timestamp"]
        # Convert to milliseconds epoch for ECharts
        ts_ms = int(ts.timestamp() * 1000)
        return {"value": [ts_ms, row["value"]]}

    # Separate drift rows into normal / out-of-limit / quality-flagged
    normal_pts: list[dict] = []
    ool_pts: list[dict] = []  # out-of-limit
    flagged_pts: list[dict] = []  # non-None quality_code_id

    for _, row in drift_df.iterrows():
        pt = _row_to_point(row)
        qc = row.get("quality_code_id")
        v = row["value"]
        if qc is not None and str(qc) not in ("None", ""):
            flagged_pts.append(pt)
        elif v > upper_limit or v < lower_limit:
            ool_pts.append(pt)
        else:
            normal_pts.append(pt)

    source_pts = [_row_to_point(r) for _, r in source_df.iterrows()] if not source_df.empty else []

    series: list[dict] = [
        {
            "name": drift_label,
            "type": "line",
            "data": normal_pts,
            "showSymbol": len(normal_pts) <= 200,
            "symbol": "circle",
            "symbolSize": 5,
            "lineStyle": {"color": "#1f77b4"},
            "itemStyle": {"color": "#1f77b4"},
        },
        {
            "name": "Out of limit",
            "type": "scatter",
            "data": ool_pts,
            "symbol": "triangle",
            "symbolSize": 9,
            "itemStyle": {"color": "#d62728"},
        },
        {
            "name": "Quality-flagged",
            "type": "scatter",
            "data": flagged_pts,
            "symbol": "diamond",
            "symbolSize": 9,
            "itemStyle": {"color": "#ff7f0e"},
        },
    ]

    if source_pts:
        series.append({
            "name": source_label,
            "type": "line",
            "data": source_pts,
            "showSymbol": False,
            "lineStyle": {"color": "#aec7e8", "type": "dashed", "opacity": 0.6},
            "itemStyle": {"color": "#aec7e8"},
        })

    # Limit line markers
    mark_lines: list[dict] = []
    if upper_limit is not None:
        mark_lines.append({"yAxis": upper_limit, "name": f"UCL ({upper_limit})", "lineStyle": {"color": "#d62728", "type": "dashed"}})
    if lower_limit is not None:
        mark_lines.append({"yAxis": lower_limit, "name": f"LCL ({lower_limit})", "lineStyle": {"color": "#d62728", "type": "dashed"}})

    # Attach mark lines to the first series
    if mark_lines and series:
        series[0]["markLine"] = {
            "silent": True,
            "data": [{"yAxis": ml["yAxis"]} for ml in mark_lines],
            "lineStyle": {"color": "#d62728", "type": "dashed"},
            "label": {
                "formatter": "{b}",
                "position": "insideEndTop",
            },
        }

    option = {
        "tooltip": {"trigger": "axis"},
        "legend": {"data": [s["name"] for s in series]},
        "xAxis": {
            "type": "time",
            "axisLabel": {"formatter": "{yyyy}-{MM}-{dd}"},
        },
        "yAxis": {"type": "value"},
        "dataZoom": [
            {"type": "slider", "start": 0, "end": 100},
            {"type": "inside"},
        ],
        "series": series,
    }
    return option


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------


def _render_channel_picker(all_channels: list[dict]) -> None:
    """Sidebar: pick drift channel and (optional) source channel."""
    st.sidebar.header("Channel selection")

    channel_opts: dict[str, int | None] = {NONE_LABEL: None}
    for ch in all_channels:
        label = (
            f"CH-{ch['channel_id']}: "
            f"{ch.get('parameter_name') or 'param-?'} "
            f"[{ch.get('tag_name') or ch.get('identifier') or ''}]"
        )
        channel_opts[label] = ch["channel_id"]

    labels = list(channel_opts.keys())

    # Drift channel
    current_drift = st.session_state.mcc_drift_channel_id
    cur_drift_label = next((l for l, v in channel_opts.items() if v == current_drift), labels[0])
    sel_drift = st.sidebar.selectbox(
        "Drift channel",
        labels,
        index=labels.index(cur_drift_label),
        key="mcc_drift_sel",
        help="Pick the maintenance-drift derived channel (MethodName='maintenance_drift').",
    )
    st.session_state.mcc_drift_channel_id = channel_opts[sel_drift]

    # Source channel
    current_source = st.session_state.mcc_source_channel_id
    cur_source_label = next((l for l, v in channel_opts.items() if v == current_source), labels[0])
    sel_source = st.sidebar.selectbox(
        "Source channel (optional)",
        labels,
        index=labels.index(cur_source_label),
        key="mcc_source_sel",
        help="Raw sensor channel whose drift is being monitored (shown as reference).",
    )
    st.session_state.mcc_source_channel_id = channel_opts[sel_source]


def _render_controls() -> tuple[date, date, float, float]:
    """Sidebar: time range and limit inputs. Returns (start, end, upper, lower)."""
    st.sidebar.header("Time range")
    start = st.sidebar.date_input("From", key="mcc_start")
    end = st.sidebar.date_input("To", key="mcc_end")

    st.sidebar.header("Control limits")
    upper = st.sidebar.number_input(
        "Upper limit (UCL)", value=float(st.session_state.mcc_upper_limit),
        step=0.1, format="%.2f", key="mcc_ucl",
    )
    lower = st.sidebar.number_input(
        "Lower limit (LCL)", value=float(st.session_state.mcc_lower_limit),
        step=0.1, format="%.2f", key="mcc_lcl",
    )
    return start, end, upper, lower


def _render_stats(drift_df: pd.DataFrame, upper: float, lower: float) -> None:
    """Show a quick stat summary above the chart."""
    if drift_df.empty:
        return
    n_total = len(drift_df)
    n_ool = int(((drift_df["value"] > upper) | (drift_df["value"] < lower)).sum())
    n_flagged = int(drift_df["quality_code_id"].notna().sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Points", n_total)
    c2.metric("Out of limit", n_ool, delta=None)
    c3.metric("Quality-flagged", n_flagged)
    c4.metric(
        "In-limit %",
        f"{100 * (n_total - n_ool) / n_total:.1f}%" if n_total else "—",
    )


def _render_out_of_limit_table(drift_df: pd.DataFrame, upper: float, lower: float) -> None:
    """Show a table of out-of-limit rows."""
    ool = drift_df[(drift_df["value"] > upper) | (drift_df["value"] < lower)].copy()
    if ool.empty:
        st.caption("No out-of-limit points in this range.")
        return
    ool["timestamp"] = ool["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    ool = ool.rename(columns={"timestamp": "Timestamp", "value": "Value", "quality_code_id": "QC"})
    st.dataframe(ool, use_container_width=True, hide_index=True)


def main() -> None:
    _init_state()
    st.title("Maintenance Control Chart")
    st.caption(
        "Plot a drift channel over time with configurable upper/lower control limits. "
        "Out-of-limit points are highlighted in red; quality-flagged points in orange."
    )

    # Load channel list
    try:
        channels_data = list_channels(page_size=500)
        all_channels: list[dict] = channels_data.get("items", []) if channels_data else []
    except APIError as e:
        st.error(f"Cannot load channels: {e.message}")
        all_channels = []

    _render_channel_picker(all_channels)
    start, end, upper, lower = _render_controls()

    drift_id = st.session_state.mcc_drift_channel_id
    source_id = st.session_state.mcc_source_channel_id

    if drift_id is None:
        st.info("Select a drift channel in the sidebar to display the control chart.")
        return

    # Fetch data
    with st.spinner("Loading drift data…"):
        drift_rows = _fetch_timeseries(drift_id, start, end)
    drift_df = _build_dataframe(drift_rows)

    source_df = pd.DataFrame()
    if source_id is not None and source_id != drift_id:
        with st.spinner("Loading source data…"):
            source_rows = _fetch_timeseries(source_id, start, end)
        source_df = _build_dataframe(source_rows)

    if drift_df.empty:
        st.warning("No data found for the selected drift channel and time range.")
        return

    # Quality code labels for tooltip (best-effort)
    try:
        qc_list = list_quality_codes()
        quality_codes = {q["quality_code_id"]: q.get("name", str(q["quality_code_id"])) for q in qc_list}
    except APIError:
        quality_codes = {}

    # Stats row
    _render_stats(drift_df, upper, lower)

    # Chart
    try:
        from streamlit_echarts import st_echarts

        drift_meta = next((c for c in all_channels if c["channel_id"] == drift_id), {})
        source_meta = next((c for c in all_channels if c["channel_id"] == source_id), {})
        drift_label = (
            f"Drift — CH-{drift_id} {drift_meta.get('parameter_name') or ''}".strip()
        )
        source_label = (
            f"Raw — CH-{source_id} {source_meta.get('parameter_name') or ''}".strip()
            if source_id else "Raw source"
        )

        option = _build_chart_option(drift_df, source_df, upper, lower, quality_codes, drift_label, source_label)
        st_echarts(options=option, height="480px", key="mcc_chart")
    except ImportError:
        # Fallback: plain st.line_chart when streamlit_echarts not available
        chart_df = drift_df.set_index("timestamp")[["value"]].rename(columns={"value": drift_label})
        if not source_df.empty:
            source_chart = source_df.set_index("timestamp")[["value"]].rename(columns={"value": source_label})
            chart_df = chart_df.join(source_chart, how="outer")
        st.line_chart(chart_df)

    # Out-of-limit table
    st.divider()
    st.subheader("Out-of-limit points")
    _render_out_of_limit_table(drift_df, upper, lower)

    st.divider()
    _render_drift_readback()


def _render_drift_readback() -> None:
    """PRD-4 S4: 'drift since last cleaning' for a maintenance Event.

    Enter a maintenance Event ID; shows the before/after readings derived from
    the source stream around the event window, plus the % drift.
    """
    st.subheader("Drift since last cleaning")
    st.caption(
        "Enter a maintenance Event ID to read back the before/after values "
        "derived from the source stream around its window."
    )
    event_id = st.number_input(
        "Maintenance Event ID",
        min_value=0,
        value=0,
        step=1,
        key="mcc_event_id",
        help="The id of the maintenance Event to chart. The window around it is taken from the event's start and end times.",
    )
    if not event_id:
        return
    try:
        rb = get_event_maintenance_drift(int(event_id))
    except APIError as e:
        st.info(f"No drift read-back for Event {int(event_id)}: {e.message}")
        return

    before = rb.get("before")
    after = rb.get("after")
    pct = rb.get("percent_diff")
    c1, c2, c3 = st.columns(3)
    c1.metric("Before (fouled)", f"{before['value']:.3g}" if before and before.get("value") is not None else "—")
    c2.metric("After (clean)", f"{after['value']:.3g}" if after and after.get("value") is not None else "—")
    c3.metric("Drift", f"{pct:+.1f}%" if pct is not None else "—")
    st.caption(
        f"Drift channel CH-{rb.get('drift_channel_id')} · source CH-{rb.get('source_channel_id')} · "
        f"window {rb.get('window_start')} → {rb.get('window_end') or '(instantaneous)'}"
    )
    if before is None or after is None:
        st.warning("No source reading found on one side of the window — widen the data range.")


def _in_streamlit_run() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return True


if _in_streamlit_run():
    main()
