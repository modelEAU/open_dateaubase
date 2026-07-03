"""Events — generalised Event CRUD page (PRD-2 S4).

Displays all Events with list/create/delete.  No inline edit form needed for
MVP — create + delete covers the acceptance criteria in issue #38.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import pandas as pd

from app.api_client import (
    APIError,
    create_event,
    delete_event,
    list_event_kinds_lookup,
    list_events,
)
from app.auth import require_auth

require_auth()

st.title("Events")

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

_ARC_TARGETS = [
    "channel_id",
    "equipment_id",
    "signal_interface_id",
    "data_acquisition_system_id",
    "sampling_point_id",
    "process_unit_id",
    "site_id",
    "campaign_id",
]

try:
    event_kinds = list_event_kinds_lookup()
except APIError as e:
    st.error(f"Cannot load event kinds: {e.message}")
    event_kinds = []

event_kind_options = {ek["name"]: ek["event_kind_id"] for ek in event_kinds}

# ---------------------------------------------------------------------------
# Load events
# ---------------------------------------------------------------------------

try:
    events = list_events()
except APIError as e:
    st.error(f"Cannot load events: {e.message}")
    events = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _target_summary(row: dict) -> str:
    """Return '<field>=<id>' for the single non-null arc FK, or '—'."""
    for field in _ARC_TARGETS:
        val = row.get(field)
        if val is not None:
            return f"{field}={val}"
    return "—"


# ---------------------------------------------------------------------------
# Create form (inside a dialog / expander)
# ---------------------------------------------------------------------------

@st.dialog("Create Event")
def _create_dialog() -> None:
    with st.form("create_event_form"):
        kind_name = st.selectbox(
            "Event kind *",
            options=list(event_kind_options.keys()),
            index=0 if event_kind_options else None,
        )
        start_dt = st.text_input("Start datetime * (YYYY-MM-DD HH:MM:SS)")
        end_dt = st.text_input("End datetime (optional, YYYY-MM-DD HH:MM:SS)")
        notes = st.text_area("Notes")

        st.markdown("**Target** — pick exactly one arc FK")
        target_type = st.selectbox("Target type *", options=_ARC_TARGETS)
        target_id = st.number_input("Target ID *", min_value=1, step=1)

        submitted = st.form_submit_button("Create", type="primary")

    if submitted:
        if not kind_name or not start_dt or not target_id:
            st.error("Event kind, start datetime, and target ID are required.")
            return
        if kind_name not in event_kind_options:
            st.error("Please select a valid event kind.")
            return
        payload: dict = {
            "event_kind_id": event_kind_options[kind_name],
            "start_datetime": start_dt,
            target_type: int(target_id),
        }
        if end_dt:
            payload["end_datetime"] = end_dt
        if notes:
            payload["notes"] = notes
        try:
            create_event(payload)
            st.success("Event created.")
            st.rerun()
        except APIError as e:
            st.error(f"Failed to create event: {e.message}")


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

col1, _rest = st.columns([1, 9])
with col1:
    if st.button("➕ New", type="primary"):
        _create_dialog()

# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

if events:
    df = pd.DataFrame(events)
    # Add a human-readable target column
    df["target"] = df.apply(_target_summary, axis=1)

    display_cols = [c for c in ["event_id", "event_kind_name", "target", "start_datetime", "notes"]
                    if c in df.columns]
    display_df = df[display_cols]

    selected = st.dataframe(
        display_df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = selected.get("selection", {}).get("rows", []) if selected else []
    selected_item = events[selected_rows[0]] if selected_rows else None

    if selected_item:
        event_id = selected_item["event_id"]
        st.markdown(f"**Selected event ID:** {event_id}")
        if st.button("🗑️ Delete selected event", type="secondary"):
            try:
                delete_event(event_id)
                st.success(f"Event {event_id} deleted.")
                st.rerun()
            except APIError as e:
                st.error(f"Failed to delete event: {e.message}")
else:
    st.info("No events found. Click '➕ New' to create one.")
