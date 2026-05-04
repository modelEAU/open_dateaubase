"""Equipment Move — guided wizard to relocate equipment or change its wiring.

Change Location tab:
  Step 1: Select the equipment to move.
  Step 2: Choose destination sampling point and move timestamp.
  Step 3: Optionally record an equipment event alongside the move.
  Step 4: Review and confirm.

Change Wiring tab:
  Step 1: Select the equipment to rewire.
  Step 2: Choose destination signal interface / port and timestamp.
  Step 3: Optionally record an equipment event alongside the rewire.
  Step 4: Review and confirm.

In v4.0.0, location and wiring are tracked per Equipment via history tables.
Relocating or rewiring an equipment automatically affects all channels wired to it.
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
    get_wiring_at_time,
    list_equipment_event_kinds,
    list_equipment_lookup,
    list_sampling_points_lookup,
    list_signal_interface_ports,
    list_signal_interfaces_lookup,
    relocate_equipment,
    rewire_equipment,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RELOCATE_STEPS = [
    "Select equipment",
    "Move details",
    "Equipment event",
    "Review & confirm",
]

REWIRE_STEPS = [
    "Select equipment",
    "Wiring details",
    "Equipment event",
    "Review & confirm",
]

# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------

_DEFAULTS_MV: dict = {
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

_DEFAULTS_MW: dict = {
    "mw_step": 1,
    "mw_equipment_id": None,
    "mw_equipment_label": None,
    "mw_dest_si_id": None,
    "mw_dest_si_label": None,
    "mw_dest_port_id": None,
    "mw_dest_port_label": None,
    "mw_date": None,
    "mw_time": None,
    "mw_notes": "",
    "mw_add_event": False,
    "mw_event_type_id": None,
    "mw_event_type_label": None,
    "mw_event_desc": "",
}


def _init() -> None:
    for k, v in {**_DEFAULTS_MV, **_DEFAULTS_MW}.items():
        st.session_state.setdefault(k, v)


def _reset(prefix: str) -> None:
    defaults = {**_DEFAULTS_MV, **_DEFAULTS_MW}
    for k, v in defaults.items():
        if k.startswith(prefix):
            st.session_state[k] = v


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Header & navigation
# ---------------------------------------------------------------------------


def _render_header(step: int, steps: list[str]) -> None:
    fraction = (step - 1) / max(len(steps) - 1, 1)
    st.progress(fraction)
    st.caption(f"Step {step} / {len(steps)}: **{steps[step - 1]}**")
    st.markdown(f"## {steps[step - 1]}")


def _nav(
    step: int,
    *,
    prefix: str,
    step_key: str,
    total_steps: int,
    on_next,
    next_label: str = "Next ▶",
    reset_fn,
) -> None:
    st.divider()
    col_cancel, col_back, _, col_next = st.columns([1, 1, 5, 2])
    with col_cancel:
        if st.button("✖ Cancel", key=f"{prefix}_cancel_{step}"):
            reset_fn()
            st.rerun()
    with col_back:
        if st.button("◀ Back", key=f"{prefix}_back_{step}", disabled=step == 1):
            st.session_state[step_key] -= 1
            st.rerun()
    with col_next:
        if st.button(next_label, key=f"{prefix}_next_{step}", type="primary"):
            errors = on_next()
            if errors:
                for e in errors:
                    st.error(e)
            else:
                if step < total_steps:
                    st.session_state[step_key] += 1
                st.rerun()


# ---------------------------------------------------------------------------
# Step 1: Select equipment
# ---------------------------------------------------------------------------


def _step_select_equipment(
    equipment_lookup: list[dict],
    *,
    prefix: str,
    step_key: str,
    total_steps: int,
    show_wiring: bool = False,
) -> None:
    eq_map = {e["identifier"]: e["equipment_id"] for e in equipment_lookup}
    eq_labels = list(eq_map.keys())

    if not eq_labels:
        st.warning("No equipment found in the database.")
        _nav(
            1,
            prefix=prefix,
            step_key=step_key,
            total_steps=total_steps,
            on_next=lambda: ["No equipment available."],
            reset_fn=lambda: _reset(prefix),
        )
        return

    # Restore previous selection index
    equipment_label_key = f"{prefix}_equipment_label"
    prev_label = st.session_state.get(equipment_label_key)
    default_idx = (
        eq_labels.index(prev_label) if prev_label and prev_label in eq_labels else 0
    )

    selected_label = st.selectbox(
        "Equipment *",
        eq_labels,
        index=default_idx,
        key=f"{prefix}_eq_select",
        help="The physical instrument whose location or wiring will be changed",
    )
    if selected_label is None:
        st.error("Please select an equipment.")
        _nav(
            1,
            prefix=prefix,
            step_key=step_key,
            total_steps=total_steps,
            on_next=lambda: ["No equipment selected."],
            reset_fn=lambda: _reset(prefix),
        )
        return

    selected_eq_id = eq_map[selected_label]

    # Live info panel
    now_str = _now_utc().isoformat()
    try:
        loc = get_location_at_time(selected_eq_id, now_str)
    except APIError:
        loc = {}

    _render_equipment_info_panel(selected_label, loc)

    if show_wiring:
        try:
            wiring = get_wiring_at_time(selected_eq_id, now_str)
        except APIError:
            wiring = {}
        _render_equipment_wiring_info(wiring)

    def on_next() -> list[str]:
        st.session_state[f"{prefix}_equipment_id"] = selected_eq_id
        st.session_state[equipment_label_key] = selected_label
        return []

    _nav(
        1,
        prefix=prefix,
        step_key=step_key,
        total_steps=total_steps,
        on_next=on_next,
        reset_fn=lambda: _reset(prefix),
    )


def _render_equipment_info_panel(label: str, loc: dict) -> None:
    with st.container(border=True):
        st.markdown(f"**{label}**")
        sp_name = loc.get("sampling_point_name") or "—"
        since = loc.get("valid_from")
        delta = f"since {since[:10]}" if since else ""
        st.metric("Current sampling point", sp_name, delta=delta, delta_color="off")


def _render_equipment_wiring_info(wiring: dict) -> None:
    with st.container(border=True):
        st.markdown("**Current wiring**")
        si_name = wiring.get("signal_interface_name") or "—"
        port_id = wiring.get("signal_interface_port_identifier") or "—"
        since = wiring.get("valid_from")
        delta = f"since {since[:10]}" if since else ""
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Interface", si_name, delta=delta, delta_color="off")
        with col2:
            st.metric("Port", port_id)


# ---------------------------------------------------------------------------
# Step 2: Move details (relocate)
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
        _nav(
            2,
            prefix="mv",
            step_key="mv_step",
            total_steps=len(RELOCATE_STEPS),
            on_next=lambda: ["No destination sampling points available."],
            reset_fn=lambda: _reset("mv"),
        )
        return

    prev_label = st.session_state.mv_dest_sp_label
    default_idx = (
        sp_labels.index(prev_label) if prev_label and prev_label in sp_labels else 0
    )
    dest_label = st.selectbox(
        "Destination sampling point *",
        sp_labels,
        index=default_idx,
        key="mv_dest_label_widget",
        help="Sampling location where this equipment will be installed",
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
        help="Free-text notes about the deployment or relocation",
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

    _nav(
        2,
        prefix="mv",
        step_key="mv_step",
        total_steps=len(RELOCATE_STEPS),
        on_next=on_next,
        reset_fn=lambda: _reset("mv"),
    )


# ---------------------------------------------------------------------------
# Step 2: Wiring details (rewire)
# ---------------------------------------------------------------------------


def _step_mw_wiring_details(si_opts: list[dict]) -> None:
    eq_label = st.session_state.mw_equipment_label
    st.info(f"Rewiring **{eq_label}**.")

    si_map = {s["label"]: s["signal_interface_id"] for s in si_opts}
    si_labels = list(si_map.keys())

    if not si_labels:
        st.error("No signal interfaces found.")
        _nav(
            2,
            prefix="mw",
            step_key="mw_step",
            total_steps=len(REWIRE_STEPS),
            on_next=lambda: ["No signal interfaces available."],
            reset_fn=lambda: _reset("mw"),
        )
        return

    prev_label = st.session_state.mw_dest_si_label
    default_idx = (
        si_labels.index(prev_label) if prev_label and prev_label in si_labels else 0
    )
    dest_si_label = st.selectbox(
        "Destination signal interface *",
        si_labels,
        index=default_idx,
        key="mw_dest_si_label_widget",
        help="The SignalInterface (PLC, SCADA, basestation, ...) this equipment will be wired to",
    )
    dest_si_id = si_map.get(dest_si_label)

    # Load ports for selected interface
    port_opts: list[dict] = []
    if dest_si_id:
        try:
            port_opts = list_signal_interface_ports(dest_si_id)
        except APIError:
            port_opts = []

    port_map = {p["port_identifier"]: p["signal_interface_port_id"] for p in port_opts}
    port_labels = list(port_map.keys())

    # Add "No port" option
    port_labels_with_none = ["No port (interface-level only)"] + port_labels
    port_map_with_none: dict[str, int | None] = {"No port (interface-level only)": None}
    port_map_with_none.update(port_map)

    prev_port_label = st.session_state.mw_dest_port_label
    default_port_idx = (
        port_labels_with_none.index(prev_port_label)
        if prev_port_label and prev_port_label in port_labels_with_none
        else 0
    )

    dest_port_label = st.selectbox(
        "Destination port (optional)",
        port_labels_with_none,
        index=default_port_idx,
        key="mw_dest_port_label_widget",
        help="Specific port on the interface (e.g. 'slot6/Ch0', 'ProbeA'). Leave as 'No port' if unknown.",
    )
    dest_port_id = port_map_with_none.get(dest_port_label)

    col_date, col_time = st.columns(2)
    with col_date:
        rewire_date = st.date_input(
            "Rewire date *",
            value=st.session_state.mw_date or date.today(),
            key="mw_date_widget",
        )
    with col_time:
        rewire_time = st.time_input(
            "Rewire time (UTC) *",
            value=st.session_state.mw_time
            or _now_utc().time().replace(second=0, microsecond=0),
            key="mw_time_widget",
            step=60,
        )

    notes = st.text_area(
        "Notes (optional)",
        value=st.session_state.mw_notes,
        key="mw_notes_widget",
        placeholder="Reason for rewire, configuration details, etc.",
        help="Free-text notes about the wiring change",
    )

    def on_next() -> list[str]:
        if dest_si_id is None:
            return ["Select a destination signal interface."]

        # Guard: destination must differ from current wiring
        now_str = _now_utc().isoformat()
        try:
            current_wiring = get_wiring_at_time(
                st.session_state.mw_equipment_id, now_str
            )
        except APIError:
            current_wiring = {}
        current_si_id = current_wiring.get("signal_interface_id")
        current_port_id = current_wiring.get("signal_interface_port_id")
        if current_si_id == dest_si_id and current_port_id == dest_port_id:
            return [
                "Destination wiring is the same as current wiring. "
                "Choose a different destination."
            ]

        st.session_state.mw_dest_si_id = dest_si_id
        st.session_state.mw_dest_si_label = dest_si_label
        st.session_state.mw_dest_port_id = dest_port_id
        st.session_state.mw_dest_port_label = dest_port_label
        st.session_state.mw_date = rewire_date
        st.session_state.mw_time = rewire_time
        st.session_state.mw_notes = notes
        return []

    _nav(
        2,
        prefix="mw",
        step_key="mw_step",
        total_steps=len(REWIRE_STEPS),
        on_next=on_next,
        reset_fn=lambda: _reset("mw"),
    )


# ---------------------------------------------------------------------------
# Step 3: Equipment event (optional)
# ---------------------------------------------------------------------------


def _step_equipment_event(
    event_types: list[dict],
    *,
    prefix: str,
    step_key: str,
    step_num: int,
    total_steps: int,
) -> None:
    st.write(
        "Optionally record an equipment event (maintenance, re-calibration, inspection) "
        "triggered by this move."
    )

    add_event_key = f"{prefix}_add_event"
    event_type_label_key = f"{prefix}_event_type_label"
    event_type_id_key = f"{prefix}_event_type_id"
    event_desc_key = f"{prefix}_event_desc"

    add_event = st.checkbox(
        "Record an equipment event alongside this move",
        value=st.session_state.get(add_event_key, False),
        key=f"{prefix}_add_event_widget",
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
            prev_label = st.session_state.get(event_type_label_key)
            default_idx = (
                et_labels.index(prev_label)
                if prev_label and prev_label in et_labels
                else 0
            )
            et_label = st.selectbox(
                "Event type *",
                et_labels,
                index=default_idx,
                key=f"{prefix}_event_type_widget",
                help="Kind of lifecycle event (calibration, maintenance, failure, ...)",
            )
            event_desc = st.text_area(
                "Description",
                value=st.session_state.get(event_desc_key) or "",
                key=f"{prefix}_event_desc_widget",
                help="Free-text notes about the event",
            )

    def on_next() -> list[str]:
        st.session_state[add_event_key] = add_event
        if add_event:
            if not et_labels:
                return [
                    "No event types available — uncheck the event option to proceed."
                ]
            if et_label is None:
                return ["Select an event type."]
            st.session_state[event_type_id_key] = et_map.get(et_label)
            st.session_state[event_type_label_key] = et_label
            st.session_state[event_desc_key] = event_desc or ""
        else:
            st.session_state[event_type_id_key] = None
            st.session_state[event_type_label_key] = None
            st.session_state[event_desc_key] = ""
        return []

    _nav(
        step_num,
        prefix=prefix,
        step_key=step_key,
        total_steps=total_steps,
        on_next=on_next,
        reset_fn=lambda: _reset(prefix),
    )


# ---------------------------------------------------------------------------
# Step 4: Review & Confirm (relocate)
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
            _reset("mv")
        return errors

    _nav(
        4,
        prefix="mv",
        step_key="mv_step",
        total_steps=len(RELOCATE_STEPS),
        on_next=on_next,
        next_label="Confirm Move ✓",
        reset_fn=lambda: _reset("mv"),
    )


# ---------------------------------------------------------------------------
# Step 4: Review & Confirm (rewire)
# ---------------------------------------------------------------------------


def _step_mw_review() -> None:
    eq_label = st.session_state.mw_equipment_label

    rewire_dt = datetime.combine(
        st.session_state.mw_date,
        st.session_state.mw_time,
        tzinfo=timezone.utc,
    )

    st.write("Review the details below and click **Confirm Rewire** to apply.")

    with st.container(border=True):
        st.markdown(f"**Equipment:** {eq_label}")
        st.markdown(f"**To interface:** {st.session_state.mw_dest_si_label}")
        if (
            st.session_state.mw_dest_port_label
            and st.session_state.mw_dest_port_label != "No port (interface-level only)"
        ):
            st.markdown(f"**To port:** {st.session_state.mw_dest_port_label}")
        st.markdown(
            f"**Rewire timestamp (UTC):** {rewire_dt.strftime('%Y-%m-%d %H:%M')}"
        )
        if st.session_state.mw_notes:
            st.markdown(f"**Notes:** {st.session_state.mw_notes}")

    if st.session_state.mw_add_event:
        with st.container(border=True):
            st.markdown("**Equipment event will be recorded:**")
            st.markdown(f"- Type: {st.session_state.mw_event_type_label or '—'}")
            if st.session_state.mw_event_desc:
                st.markdown(f"- Description: {st.session_state.mw_event_desc}")

    def on_next() -> list[str]:
        rewire_ts = rewire_dt.isoformat()
        payload: dict = {
            "signal_interface_id": st.session_state.mw_dest_si_id,
            "valid_from": rewire_ts,
        }
        if st.session_state.mw_dest_port_id is not None:
            payload["signal_interface_port_id"] = st.session_state.mw_dest_port_id
        if st.session_state.mw_notes:
            payload["notes"] = st.session_state.mw_notes

        errors: list[str] = []

        try:
            rewire_equipment(st.session_state.mw_equipment_id, payload)
        except APIError as e:
            errors.append(f"Rewire failed for {eq_label}: {e.message}")

        if errors:
            return errors

        if st.session_state.mw_add_event and st.session_state.mw_event_type_id:
            try:
                create_equipment_event(
                    {
                        "equipment_id": st.session_state.mw_equipment_id,
                        "event_type_id": st.session_state.mw_event_type_id,
                        "start_datetime": rewire_ts,
                        "description": st.session_state.mw_event_desc or None,
                    }
                )
            except APIError as e:
                errors.append(
                    f"Rewire succeeded but equipment event could not be recorded: {e.message}"
                )

        if not errors:
            dest = st.session_state.mw_dest_si_label
            port = st.session_state.mw_dest_port_label or ""
            msg = f"**{eq_label}** rewired to **{dest}**"
            if port and port != "No port (interface-level only)":
                msg += f" port {port}"
            st.toast(msg + " ✓", icon="✅")
            _reset("mw")
        return errors

    _nav(
        4,
        prefix="mw",
        step_key="mw_step",
        total_steps=len(REWIRE_STEPS),
        on_next=on_next,
        next_label="Confirm Rewire ✓",
        reset_fn=lambda: _reset("mw"),
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Equipment Move")
st.markdown(
    "Guided workflow to relocate equipment to a new sampling point, "
    "change its wiring to a new signal interface, "
    "and optionally log an equipment event. "
    "In v4.0.0, location and wiring are tracked per equipment; "
    "all associated channels are affected automatically."
)

_init()

# Load shared lookups
try:
    with st.spinner("Loading…"):
        _event_types = list_equipment_event_kinds()
        _equipment_lookup = list_equipment_lookup()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

tab_relocate, tab_rewire = st.tabs(["Change Location", "Change Wiring"])

with tab_relocate:
    try:
        with st.spinner("Loading…"):
            _sp_opts = list_sampling_points_lookup()
    except APIError as e:
        st.error(f"Cannot load sampling points: {e.message}")
        st.stop()

    step = st.session_state.mv_step
    _render_header(step, RELOCATE_STEPS)

    if step == 1:
        _step_select_equipment(
            _equipment_lookup,
            prefix="mv",
            step_key="mv_step",
            total_steps=len(RELOCATE_STEPS),
        )
    elif step == 2:
        _step_move_details(_sp_opts)
    elif step == 3:
        _step_equipment_event(
            _event_types,
            prefix="mv",
            step_key="mv_step",
            step_num=3,
            total_steps=len(RELOCATE_STEPS),
        )
    elif step == 4:
        _step_review()

with tab_rewire:
    try:
        with st.spinner("Loading…"):
            _si_opts = list_signal_interfaces_lookup()
    except APIError as e:
        st.error(f"Cannot load signal interfaces: {e.message}")
        st.stop()

    step = st.session_state.mw_step
    _render_header(step, REWIRE_STEPS)

    if step == 1:
        _step_select_equipment(
            _equipment_lookup,
            prefix="mw",
            step_key="mw_step",
            total_steps=len(REWIRE_STEPS),
            show_wiring=True,
        )
    elif step == 2:
        _step_mw_wiring_details(_si_opts)
    elif step == 3:
        _step_equipment_event(
            _event_types,
            prefix="mw",
            step_key="mw_step",
            step_num=3,
            total_steps=len(REWIRE_STEPS),
        )
    elif step == 4:
        _step_mw_review()
