"""Equipment Story — a read-only lifetime view of one piece of equipment.

Tracks a sensor through its whole life: the campaigns it joined, everywhere it
has been installed, every lifecycle event, the streams it produced, and the
annotations on those streams. The merged chronological timeline is the spine.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app.api_client import APIError, get_equipment_story, list_equipment_lookup
from app.components import entity_story as story


def _short_date(v) -> str:
    """ISO timestamp -> 'YYYY-MM-DD' (or '' / passthrough)."""
    if not v:
        return ""
    return str(v)[:10]


def _sort_key(v) -> datetime:
    """Parse an ISO date for descending sort; missing dates sort oldest."""
    if not v:
        return datetime.min
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.min


def _build_timeline(s: dict) -> list[dict]:
    """Merge events, location moves, and campaign stints into one sorted spine."""
    items: list[tuple[datetime, dict]] = []

    for ev in s["events"]:
        name = (ev.get("kind") or "Event").lower()
        kind = "bad" if any(w in name for w in ("fail", "fault", "broke")) else "warn"
        when = _short_date(ev.get("start"))
        if not ev.get("instantaneous") and ev.get("end"):
            when += f" → {_short_date(ev['end'])}"
        items.append((_sort_key(ev.get("start")), {
            "when": when, "title": ev.get("kind") or "Event",
            "desc": ev.get("notes") or "", "kind": kind, "tag": "Event",
        }))

    for loc in s["location_history"]:
        when = _short_date(loc.get("valid_from"))
        if loc.get("valid_to"):
            when += f" → {_short_date(loc['valid_to'])}"
        desc = loc.get("campaign") or loc.get("notes") or ""
        items.append((_sort_key(loc.get("valid_from")), {
            "when": when, "title": f"Installed at {loc.get('location') or '?'}",
            "desc": desc, "kind": "note", "tag": "Move",
        }))

    for c in s["campaigns"]:
        when = _short_date(c.get("start"))
        if c.get("end"):
            when += f" → {_short_date(c['end'])}"
        items.append((_sort_key(c.get("start")), {
            "when": when, "title": c.get("name") or "Campaign",
            "desc": c.get("role") or (c.get("kind") or ""), "kind": "", "tag": "Campaign",
        }))

    items.sort(key=lambda t: t[0], reverse=True)
    return [it for _, it in items]


story.inject()
st.markdown("## Equipment Story")

try:
    equipment = list_equipment_lookup()
except APIError as exc:
    st.error(f"Could not load equipment: {exc.message}")
    st.stop()

if not equipment:
    st.info("No equipment yet. Add some in the Equipment page.")
    st.stop()

labels = {e["equipment_id"]: e.get("identifier") or f"Equipment {e['equipment_id']}" for e in equipment}
# Allow the Equipment CRUD page to deep-link a selection.
_target = st.session_state.pop("equipment_story_target", None)
if _target in labels:
    st.session_state["equipment_story_pick"] = _target
eid = st.selectbox(
    "Equipment", options=list(labels), format_func=lambda i: labels[i],
    key="equipment_story_pick",
)

try:
    s = get_equipment_story(eid)
except APIError as exc:
    st.error(f"Could not load equipment story: {exc.message}")
    st.stop()

eq = s["equipment"]

# --- Header band -----------------------------------------------------------
story.header(
    eq.get("identifier") or f"Equipment {eq['equipment_id']}",
    crumb=f"Reports › Equipment Story · Equipment_ID {eq['equipment_id']}",
    badges=[
        (eq.get("model") or "Equipment", "blue", False),
        ("In service", "ok", True) if eq.get("is_active") else ("Decommissioned", "grey", True),
    ],
    meta=[
        ("Model", eq.get("model") or "—"),
        ("Serial", eq.get("serial_number") or "—"),
        ("Owner", eq.get("owner") or "—"),
        ("Currently at", eq.get("current_location") or "—"),
        ("Purchased", eq.get("purchase_date") or "—"),
    ],
)

# --- KPI strip -------------------------------------------------------------
story.kpis([
    ("Campaigns", len(s["campaigns"])),
    ("Lifecycle events", len(s["events"])),
    ("Streams produced", len(s["streams"])),
    ("Locations", len(s["location_history"])),
])

# --- Timeline (dominant) + side panels -------------------------------------
left, right = st.columns([1.5, 1])
with left:
    with st.container(border=True):
        st.markdown("#### Lifetime")
        st.caption("events · moves · campaigns, merged")
        story.timeline(_build_timeline(s))
with right:
    with st.container(border=True):
        st.markdown("#### Where it's been")
        if s["location_history"]:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Location": loc.get("location"),
                        "From": _short_date(loc.get("valid_from")),
                        "To": _short_date(loc.get("valid_to")) or "now",
                    }
                    for loc in s["location_history"]
                ]),
                hide_index=True, use_container_width=True,
            )
        else:
            st.caption("No location history.")
    with st.container(border=True):
        st.markdown("#### Streams produced")
        if s["streams"]:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Parameter": st_.get("parameter_name"),
                        "Unit": st_.get("unit_name"),
                        "Kind": st_.get("channel_kind"),
                        "Points": st_.get("point_count"),
                    }
                    for st_ in s["streams"]
                ]),
                hide_index=True, use_container_width=True,
            )
        else:
            st.caption("No streams produced.")

# --- Annotations -----------------------------------------------------------
with st.container(border=True):
    st.markdown(f"#### Annotations on this equipment's streams · {len(s['annotations'])}")
    story.annotation_feed(s["annotations"])
