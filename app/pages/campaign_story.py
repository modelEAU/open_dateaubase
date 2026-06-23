"""Campaign Story — a read-only narrative view of a single campaign.

Pulls together everything tied to a campaign: the site/watershed, the sampling
points monitored, the data acquisition systems and equipment deployed (with
status), a combined plot of every series tracked (reusing the Explore scalar
figure builder), the lab series and panels, per-stream freshness, and the
campaign annotation log.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app.api_client import (
    APIError,
    get_campaign_overview,
    list_campaigns_lookup,
    list_channels,
)
from app.components import entity_story as story
from app.components import theme
from app.components.explore_scalar import _build_scalar_figure

_MAX_PLOT_CHANNELS = 12  # chart-noise ceiling; lab series added on top
_MAX_PLOT_SERIES = 8


def _parse_date(v) -> date | None:
    """Parse an ISO timestamp/date to a date; None when missing/unparseable."""
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _to_date(v, fallback: date) -> date:
    """Parse to a date, falling back when missing/unparseable."""
    return _parse_date(v) or fallback


def _plot_window(overview: dict, campaign: dict) -> tuple[date, date]:
    """Time window for the combined plot: span the streams' actual data so
    sparse or out-of-period series still appear; fall back to the campaign span."""
    pts = [
        d
        for f in overview["freshness"]
        for d in (_parse_date(f.get("first_point")), _parse_date(f.get("last_point")))
        if d
    ]
    if pts:
        return min(pts), max(pts) + timedelta(days=1)
    return (
        _to_date(campaign.get("start_date"), date.today() - timedelta(days=365)),
        _to_date(campaign.get("end_date"), date.today()),
    )


def _seed_explore_state(start: date, end: date) -> None:
    """Seed the session-state keys the reused Explore figure builder reads.

    ``_build_scalar_figure`` pulls data through explore_data's loaders, which
    read a time window and per-entity caches from session state. This page isn't
    Explore, so it must provide them; the window is the campaign's own span.
    """
    st.session_state["explore_start"] = start
    st.session_state["explore_end"] = end
    for cache in (
        "explore_data", "explore_annotations", "explore_series_annotations",
        "explore_eq_events", "explore_series_stats", "explore_channel_stats",
    ):
        st.session_state.setdefault(cache, {})


def _status_badge(e: dict) -> tuple[str, str, bool]:
    """Map a campaign-equipment row to a (label, tone, dot) status badge."""
    if e.get("ongoing_event"):
        return (e["ongoing_event"], "warn", True)
    if not e.get("is_active", True):
        return ("Decommissioned", "grey", True)
    return ("In service", "ok", True)


story.inject()
st.markdown("## Campaign Story")

# --- Campaign picker -------------------------------------------------------
try:
    campaigns = list_campaigns_lookup()
except APIError as exc:
    st.error(f"Could not load campaigns: {exc.message}")
    st.stop()

if not campaigns:
    st.info("No campaigns yet. Create one in the Campaigns page.")
    st.stop()

labels = {c["campaign_id"]: c["name"] for c in campaigns}
cid = st.selectbox(
    "Campaign",
    options=list(labels),
    format_func=lambda i: labels[i],
    key="campaign_story_pick",
)

try:
    ov = get_campaign_overview(cid)
except APIError as exc:
    st.error(f"Could not load campaign overview: {exc.message}")
    st.stop()

camp = ov["campaign"]

# --- Header band -----------------------------------------------------------
ongoing = camp.get("end_date") is None
period = f"{(camp.get('start_date') or '—')} → {camp.get('end_date') or 'ongoing'}"
ws = ov.get("watershed") or {}
story.header(
    camp["name"],
    crumb=f"Reports › Campaign Story · Campaign_ID {camp['campaign_id']}",
    badges=[
        (camp.get("campaign_kind_name") or "Campaign", "blue", False),
        ("Ongoing" if ongoing else "Ended", "ok" if ongoing else "grey", True),
    ],
    meta=[
        ("Site", camp.get("site_name") or "—"),
        ("Watershed", ws.get("name") or "—"),
        ("Period", period),
        ("Lead", camp.get("responsible_person_name") or "—"),
    ],
)

# --- KPI strip -------------------------------------------------------------
n_sensor = sum(1 for f in ov["freshness"] if f["kind"] == "sensor")
n_lab = sum(1 for f in ov["freshness"] if f["kind"] == "lab")
story.kpis([
    ("Sampling points", len(ov["sampling_points"])),
    ("Equipment / DAS", f"{len(ov['equipment'])} / {len(ov['data_acquisition_systems'])}"),
    ("Streams", f"{n_sensor + n_lab}"),
    ("Lab series / panels", f"{len(ov['lab_series'])} / {len(ov['lab_panels'])}"),
])

# --- Sites surveilled (map) + freshness ------------------------------------
left, right = st.columns([1.4, 1])
with left:
    with st.container(border=True):
        st.markdown("#### Where it's monitored")
        pts = [p for p in ov["sampling_points"] if p.get("lat") and p.get("lon")]
        if pts:
            st.map(pd.DataFrame([{"lat": p["lat"], "lon": p["lon"]} for p in pts]))
        if ov["sampling_points"]:
            st.caption(" · ".join(p["name"] for p in ov["sampling_points"]))
        else:
            st.caption("No sampling points recorded for this campaign.")
with right:
    with st.container(border=True):
        st.markdown("#### Data freshness")
        st.caption("last point per stream — no SLA judgment")
        story.freshness_table(ov["freshness"])

# --- Equipment & status ----------------------------------------------------
with st.container(border=True):
    st.markdown("#### Equipment & current status")
    if ov["equipment"]:
        rows = []
        for e in ov["equipment"]:
            label, tone, dot = _status_badge(e)
            rows.append(
                "<tr>"
                f"<td>{story._esc(e.get('identifier') or e['equipment_id'])}</td>"
                f"<td>{story._esc(e.get('model') or '—')}</td>"
                f"<td>{story._esc(e.get('role') or '—')}</td>"
                f"<td>{story._esc(e.get('location') or '—')}</td>"
                f"<td>{theme.badge(label, tone=tone, dot=dot)}</td>"
                "</tr>"
            )
        st.markdown(
            "<table style='width:100%;border-collapse:collapse' class='deau-num'>"
            "<thead><tr style='text-align:left;color:#475569;font-size:12px'>"
            "<th>Equipment</th><th>Model</th><th>Role</th><th>Location</th><th>Status</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("No equipment deployed.")

# --- Combined series plot (reuses Explore's scalar figure builder) ---------
with st.container(border=True):
    st.markdown("#### All series tracked")
    ch_items = list_channels(campaign_id=cid, page_size=300).get("items", [])
    meta_by_id = {it["channel_id"]: it for it in ch_items}
    sensor_ids = [f["stream_id"] for f in ov["freshness"] if f["kind"] == "sensor"]

    active_channels: list[int] = []
    channel_meta: dict[int, dict] = {}
    for sid in sensor_ids:
        m = meta_by_id.get(sid, {})
        if m.get("channel_kind_name", "Value") != "Value":
            continue  # skip Status/Alarm/Uncertainty sub-channels
        active_channels.append(sid)
        channel_meta[sid] = {
            "parameter_name": m.get("parameter_name"),
            "unit_name": m.get("unit_name"),
            "equipment_identifier": m.get("equipment_identifier"),
            "equipment_id": m.get("equipment_id"),
        }
    active_channels = active_channels[:_MAX_PLOT_CHANNELS]

    active_series = [s["stream_id"] for s in ov["lab_series"]][:_MAX_PLOT_SERIES]
    series_meta = {
        s["stream_id"]: {
            "name": s.get("name"),
            "parameter_name": s.get("parameter_name"),
            "sampling_point_label": s.get("sampling_point_label"),
            "unit_name": s.get("unit_name"),
        }
        for s in ov["lab_series"]
    }

    if active_channels or active_series:
        # The reused Explore builder reads its time window + caches from session
        # state; seed them to the streams' actual data span so series show.
        win_start, win_end = _plot_window(ov, camp)
        _seed_explore_state(win_start, win_end)
        fig, _ = _build_scalar_figure(
            active_channels, channel_meta, "viz", active_series, series_meta
        )
        st.plotly_chart(fig, use_container_width=True)
        if n_sensor > len(active_channels):
            st.caption(f"Showing {len(active_channels)} of {n_sensor} sensor streams (value channels).")
    else:
        st.info("No scalar series to plot for this campaign yet.")

# --- Lab series / panels + annotation log ----------------------------------
lcol, rcol = st.columns(2)
with lcol:
    with st.container(border=True):
        st.markdown("#### Lab series & panels")
        if ov["lab_series"]:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Series": s.get("name"),
                        "Parameter": s.get("parameter_name"),
                        "Unit": s.get("unit_name"),
                        "Type": s.get("value_kind_name"),
                    }
                    for s in ov["lab_series"]
                ]),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.caption("No lab series in this campaign.")
        for p in ov["lab_panels"]:
            st.markdown(
                theme.badge("Panel", tone="grey") + f" {story._esc(p['name'])} "
                f"<span class='deau-stale'>· {p['series_count']} series</span>",
                unsafe_allow_html=True,
            )
with rcol:
    with st.container(border=True):
        st.markdown(f"#### Campaign log · {len(ov['annotations'])}")
        story.annotation_feed(ov["annotations"])
