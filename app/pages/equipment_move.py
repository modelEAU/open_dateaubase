"""Equipment Move — guided 4-step wizard to relocate equipment.

Step 1: Select the equipment to move.
Step 2: Choose destination sampling point and move timestamp.
Step 3: Optionally record an equipment event alongside the move.
Step 4: Review and confirm.

In v4.0.0, location is tracked per Equipment via EquipmentLocationHistory.
Relocating an equipment automatically affects all channels wired to it.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from app.api_client import (
    APIError,
    create_equipment_event,
    get_location_at_time,
    list_equipment_event_types,
    list_equipment_lookup,
    list_sampling_points_lookup,
    relocate_equipment,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STEPS = ["Select equipment", "Move details", "Equipment event", "Review & confirm"]

# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------

_DEFAULTS: dict = {
    "mv_step": 1,
    "mv_equipment_id": None,
    "mv_equipment_label": None,
    "mv_dest_sp_id": None,
    "mv_dest_sp_label": None,
    "mv_date": None,
    "mv_time": None,
    "mv_notes": "",
    "mv_add_event": False,
    "mv_event_type_id": None,
    "mv_event_type_label": None,
    "mv_event_desc": "",
}


def _init() -> None:
    for k, v in _DEFAULTS.items():
        st.session_state.setdefault(k, v)


def _reset() -> None:
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Header & navigation
# ---------------------------------------------------------------------------


def _render_header(step: int) -> None:
    fraction = (step - 1) / max(len(STEPS) - 1, 1)
    st.progress(fraction)
    st.caption(f"Step {step} / {len(STEPS)}: **{STEPS[step - 1]}**")
    st.markdown(f"## {STEPS[step - 1]}")


def _nav(step: int, *, on_next, next_label: str = "Next ▶") -> None:
    st.divider()
    col_cancel, col_back, _, col_next = st.columns([1, 1, 5, 2])
    with col_cancel:
        if st.button("✖ Cancel", key=f"mv_cancel_{step}"):
            _reset()
            st.rerun()
    with col_back:
        if st.button("◀ Back", key=f"mv_back_{step}", disabled=step == 1):
            st.session_state.mv_step -= 1
            st.rerun()
    with col_next:
        if st.button(next_label, key=f"mv_next_{step}", type="primary"):
            errors = on_next()
            if errors:
                for e in errors:
                    st.error(e)
            else:
                if step < len(STEPS):
                    st.session_state.mv_step += 1
                st.rerun()


# ---------------------------------------------------------------------------
# Step 1: Select equipment
# ---------------------------------------------------------------------------


def _step_select_equipment(equipment_lookup: list[dict]) -> None:
    eq_map = {e["identifier"]: e["equipment_id"] for e in equipment_lookup}
    eq_labels = list(eq_map.keys())

    if not eq_labels:
        st.warning("No equipment found in the database.")
        _nav(1, on_next=lambda: ["No equipment available."])
        return

    # Restore previous selection index
    prev_label = st.session_state.mv_equipment_label
    default_idx = eq_labels.index(prev_label) if prev_label in eq_labels else 0

    selected_label = st.selectbox(
        "Equipment *",
        eq_labels,
        index=default_idx,
        key="mv_eq_select",
    )
    if selected_label is None:
        st.error("Please select an equipment.")
        _nav(1, on_next=lambda: ["No equipment selected."])
        return

    selected_eq_id = eq_map[selected_label]

    # Live info panel
    now_str = _now_utc().isoformat()
    try:
        loc = get_location_at_time(selected_eq_id, now_str)
    except APIError:
        loc = {}

    _render_equipment_info_panel(selected_label, loc)

    def on_next() -> list[str]:
        st.session_state.mv_equipment_id = selected_eq_id
        st.session_state.mv_equipment_label = selected_label
        return []

    _nav(1, on_next=on_next)


def _render_equipment_info_panel(label: str, loc: dict) -> None:
    with st.container(border=True):
        st.markdown(f"**{label}**")
        sp_name = loc.get("sampling_point_name") or "—"
        since = loc.get("valid_from")
        delta = f"since {since[:10]}" if since else ""
        st.metric("Current sampling point", sp_name, delta=delta, delta_color="off")


# ---------------------------------------------------------------------------
# Step 2: Move details
# ---------------------------------------------------------------------------


def _step_move_details(sp_opts: list[dict]) -> None:
    eq_label = st.session_state.mv_equipment_label
    st.info(f"Moving **{eq_label}**.")

    sp_map = {s["label"]: s["sampling_point_id"] for s in sp_opts}
    sp_labels = list(sp_map.keys())

    if not sp_labels:
        st.error(
            "No sampling points found. Add one via Sites → Sampling Locations first."
        )
        _nav(2, on_next=lambda: ["No destination sampling points available."])
        return

    default_idx = (
        sp_labels.index(st.session_state.mv_dest_sp_label)
        if st.session_state.mv_dest_sp_label in sp_labels
        else 0
    )
    dest_label = st.selectbox(
        "Destination sampling point *",
        sp_labels,
        index=default_idx,
        key="mv_dest_label_widget",
    )

    col_date, col_time = st.columns(2)
    with col_date:
        move_date = st.date_input(
            "Move date *",
            value=st.session_state.mv_date or date.today(),
            key="mv_date_widget",
        )
    with col_time:
        move_time = st.time_input(
            "Move time (UTC) *",
            value=st.session_state.mv_time
            or _now_utc().time().replace(second=0, microsecond=0),
            key="mv_time_widget",
            step=60,
        )

    notes = st.text_area(
        "Notes (optional)",
        value=st.session_state.mv_notes,
        key="mv_notes_widget",
        placeholder="Reason for move, calibration status, etc.",
    )

    def on_next() -> list[str]:
        dest_sp_id = sp_map.get(dest_label)
        if dest_sp_id is None:
            return ["Select a destination sampling point."]

        # Guard: destination must differ from current location
        now_str = _now_utc().isoformat()
        try:
            current_loc = get_location_at_time(
                st.session_state.mv_equipment_id, now_str
            )
        except APIError:
            current_loc = {}
        current_sp_id = current_loc.get("sampling_point_id")
        if current_sp_id is not None and current_sp_id == dest_sp_id:
            return [
                "Destination is the same as the current sampling point. "
                "Choose a different destination."
            ]

        st.session_state.mv_dest_sp_id = dest_sp_id
        st.session_state.mv_dest_sp_label = dest_label
        st.session_state.mv_date = move_date
        st.session_state.mv_time = move_time
        st.session_state.mv_notes = notes
        return []

    _nav(2, on_next=on_next)


# ---------------------------------------------------------------------------
# Step 3: Equipment event (optional)
# ---------------------------------------------------------------------------


def _step_equipment_event(event_types: list[dict]) -> None:
    st.write(
        "Optionally record an equipment event (maintenance, re-calibration, inspection) "
        "triggered by this move."
    )

    add_event = st.checkbox(
        "Record an equipment event alongside this move",
        value=st.session_state.mv_add_event,
        key="mv_add_event_widget",
    )

    et_labels: list[str] = []
    et_map: dict[str, int] = {}
    et_label: str | None = None
    event_desc: str = ""

    if add_event:
        et_map = {et["event_type_name"]: et["event_type_id"] for et in event_types}
        et_labels = list(et_map.keys())

        if not et_labels:
            st.warning("No equipment event types found in the database.")
        else:
            default_idx = (
                et_labels.index(st.session_state.mv_event_type_label)
                if st.session_state.mv_event_type_label in et_labels
                else 0
            )
            et_label = st.selectbox(
                "Event type *",
                et_labels,
                index=default_idx,
                key="mv_event_type_widget",
            )
            event_desc = st.text_area(
                "Description",
                value=st.session_state.mv_event_desc or "",
                key="mv_event_desc_widget",
            )

    def on_next() -> list[str]:
        st.session_state.mv_add_event = add_event
        if add_event:
            if not et_labels:
                return [
                    "No event types available — uncheck the event option to proceed."
                ]
            if et_label is None:
                return ["Select an event type."]
            st.session_state.mv_event_type_id = et_map.get(et_label)
            st.session_state.mv_event_type_label = et_label
            st.session_state.mv_event_desc = event_desc or ""
        else:
            st.session_state.mv_event_type_id = None
            st.session_state.mv_event_type_label = None
            st.session_state.mv_event_desc = ""
        return []

    _nav(3, on_next=on_next)


# ---------------------------------------------------------------------------
# Step 4: Review & Confirm
# ---------------------------------------------------------------------------


def _step_review() -> None:
    eq_label = st.session_state.mv_equipment_label

    move_dt = datetime.combine(
        st.session_state.mv_date,
        st.session_state.mv_time,
        tzinfo=timezone.utc,
    )

    st.write("Review the details below and click **Confirm Move** to apply.")

    with st.container(border=True):
        st.markdown(f"**Equipment:** {eq_label}")
        st.markdown(f"**To:** {st.session_state.mv_dest_sp_label}")
        st.markdown(f"**Move timestamp (UTC):** {move_dt.strftime('%Y-%m-%d %H:%M')}")
        if st.session_state.mv_notes:
            st.markdown(f"**Notes:** {st.session_state.mv_notes}")

    if st.session_state.mv_add_event:
        with st.container(border=True):
            st.markdown("**Equipment event will be recorded:**")
            st.markdown(f"- Type: {st.session_state.mv_event_type_label or '—'}")
            if st.session_state.mv_event_desc:
                st.markdown(f"- Description: {st.session_state.mv_event_desc}")

    def on_next() -> list[str]:
        move_ts = move_dt.isoformat()
        payload: dict = {
            "sampling_point_id": st.session_state.mv_dest_sp_id,
            "valid_from": move_ts,
        }
        if st.session_state.mv_notes:
            payload["notes"] = st.session_state.mv_notes

        errors: list[str] = []

        try:
            relocate_equipment(st.session_state.mv_equipment_id, payload)
        except APIError as e:
            errors.append(f"Move failed for {eq_label}: {e.message}")

        if errors:
            return errors

        if st.session_state.mv_add_event and st.session_state.mv_event_type_id:
            try:
                create_equipment_event(
                    {
                        "equipment_id": st.session_state.mv_equipment_id,
                        "event_type_id": st.session_state.mv_event_type_id,
                        "start_datetime": move_ts,
                        "description": st.session_state.mv_event_desc or None,
                    }
                )
            except APIError as e:
                errors.append(
                    f"Move succeeded but equipment event could not be recorded: {e.message}"
                )

        if not errors:
            dest = st.session_state.mv_dest_sp_label
            st.toast(f"**{eq_label}** moved to **{dest}** ✓", icon="✅")
            _reset()
        return errors

    _nav(4, on_next=on_next, next_label="Confirm Move ✓")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Equipment Move")
st.markdown(
    "Guided workflow to relocate equipment to a new sampling point "
    "and optionally log an equipment event. In v4.0.0, location is tracked "
    "per equipment; all associated channels are affected automatically."
)

_init()

try:
    with st.spinner("Loading…"):
        _sp_opts = list_sampling_points_lookup()
        _event_types = list_equipment_event_types()
        _equipment_lookup = list_equipment_lookup()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

step = st.session_state.mv_step
_render_header(step)

if step == 1:
    _step_select_equipment(_equipment_lookup)
elif step == 2:
    _step_move_details(_sp_opts)
elif step == 3:
    _step_equipment_event(_event_types)
elif step == 4:
    _step_review()
