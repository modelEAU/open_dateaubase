"""Equipment Move — guided 4-step wizard to relocate signal port(s).

Step 1: Select what to move — an individual port, or all ports of an equipment.
Step 2: Choose destination sampling point and move timestamp.
Step 3: Optionally record an equipment event alongside the move.
Step 4: Review and confirm.

Sub-ports are never relocated directly: they follow their top-level parent
automatically (enforced by the API).
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
    get_equipment_at_port,
    get_location_at_port,
    list_equipment_event_types,
    list_equipment_lookup,
    list_sampling_points_lookup,
    list_signal_ports,
    relocate_signal_port,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STEPS = ["Select port(s)", "Move details", "Equipment event", "Review & confirm"]

# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------

_DEFAULTS: dict = {
    "mv_step": 1,
    "mv_selection_mode": "port",       # "port" | "equipment"
    "mv_port_ids": [],                 # list[int] — ports to relocate
    "mv_port_infos": [],               # list[dict] — {id, label, current_loc, current_eq}
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
# Step 1: Select port(s)
# ---------------------------------------------------------------------------


def _fetch_port_info(port_id: int) -> dict:
    """Return {id, label, current_loc, current_eq} for one top-level port."""
    now_str = _now_utc().isoformat()
    try:
        loc = get_location_at_port(port_id, now_str)
    except APIError:
        loc = {}
    try:
        eq = get_equipment_at_port(port_id, now_str)
    except APIError:
        eq = {}
    return {"id": port_id, "loc": loc, "eq": eq}


def _step_select_port(top_level_ports: list[dict], equipment_lookup: list[dict]) -> None:
    st.write(
        "Select what to move. Sub-ports always follow their parent automatically "
        "and cannot be relocated independently."
    )

    mode = st.radio(
        "Selection mode",
        ["Individual port", "All ports of an equipment"],
        key="mv_mode_radio",
        horizontal=True,
        index=0 if st.session_state.mv_selection_mode == "port" else 1,
    )
    is_equipment_mode = mode == "All ports of an equipment"

    if is_equipment_mode:
        _step_select_by_equipment(equipment_lookup)
    else:
        _step_select_by_port(top_level_ports)


def _step_select_by_port(top_level_ports: list[dict]) -> None:
    port_map = {p["label"]: p["id"] for p in top_level_ports}
    port_labels = list(port_map.keys())

    if not port_labels:
        st.warning("No relocatable top-level signal ports found.")
        _nav(1, on_next=lambda: ["No ports available."])
        return

    # Restore previous selection index
    prev_label = (st.session_state.mv_port_infos or [{}])[0].get("label") if st.session_state.mv_port_infos else None
    default_idx = port_labels.index(prev_label) if prev_label in port_labels else 0

    selected_label = st.selectbox(
        "Signal port *",
        port_labels,
        index=default_idx,
        key="mv_port_select",
    )
    selected_id = port_map[selected_label]

    # Live info panel
    now_str = _now_utc().isoformat()
    try:
        loc = get_location_at_port(selected_id, now_str)
        eq = get_equipment_at_port(selected_id, now_str)
    except APIError as e:
        st.error(f"Could not load port details: {e.message}")
        loc, eq = {}, {}

    _render_port_info_panel(selected_label, loc, eq)

    def on_next() -> list[str]:
        st.session_state.mv_selection_mode = "port"
        st.session_state.mv_port_ids = [selected_id]
        st.session_state.mv_port_infos = [
            {"id": selected_id, "label": selected_label, "loc": loc, "eq": eq}
        ]
        return []

    _nav(1, on_next=on_next)


def _step_select_by_equipment(equipment_lookup: list[dict]) -> None:
    eq_map = {e["identifier"]: e["equipment_id"] for e in equipment_lookup}
    eq_labels = list(eq_map.keys())

    if not eq_labels:
        st.warning("No equipment found in the database.")
        _nav(1, on_next=lambda: ["No equipment available."])
        return

    selected_eq_label = st.selectbox(
        "Equipment *",
        eq_labels,
        key="mv_eq_select",
    )
    selected_eq_id = eq_map[selected_eq_label]

    # Fetch top-level ports currently assigned to this equipment
    try:
        ports_page = list_signal_ports(equipment_id=selected_eq_id, page_size=500)
        all_eq_ports = ports_page.get("items", [])
    except APIError as e:
        st.error(f"Could not load ports for equipment: {e.message}")
        _nav(1, on_next=lambda: ["Failed to load equipment ports."])
        return

    top_level = [p for p in all_eq_ports if p.get("parent_port_id") is None]

    if not top_level:
        st.info(
            f"**{selected_eq_label}** has no active top-level signal ports. "
            "Either it is not registered at any port, or all ports are sub-ports."
        )
        _nav(1, on_next=lambda: [f"No relocatable ports found for {selected_eq_label}."])
        return

    st.markdown(f"**{len(top_level)} top-level port(s)** will be moved:")
    now_str = _now_utc().isoformat()
    port_infos: list[dict] = []
    for p in top_level:
        port_id = p["signal_port_id"]
        label = f"{p['tag']}  —  {p.get('das_name') or 'no DAS'}"
        try:
            loc = get_location_at_port(port_id, now_str)
            eq = get_equipment_at_port(port_id, now_str)
        except APIError:
            loc, eq = {}, {}
        port_infos.append({"id": port_id, "label": label, "loc": loc, "eq": eq})
        _render_port_info_panel(label, loc, eq)

    if len(top_level) > 1:
        st.caption(
            "All ports will be relocated to the same destination in the next step."
        )

    def on_next() -> list[str]:
        st.session_state.mv_selection_mode = "equipment"
        st.session_state.mv_port_ids = [pi["id"] for pi in port_infos]
        st.session_state.mv_port_infos = port_infos
        return []

    _nav(1, on_next=on_next)


def _render_port_info_panel(label: str, loc: dict, eq: dict) -> None:
    with st.container(border=True):
        st.markdown(f"**{label}**")
        col_loc, col_eq = st.columns(2)
        with col_loc:
            sp_name = loc.get("sampling_point_name") or "—"
            since = loc.get("start_time")
            delta = f"since {since[:10]}" if since else ""
            st.metric("Current sampling point", sp_name, delta=delta, delta_color="off")
        with col_eq:
            eq_label = eq.get("equipment_identifier") or "—"
            st.metric("Equipment", eq_label)


# ---------------------------------------------------------------------------
# Step 2: Move details
# ---------------------------------------------------------------------------


def _step_move_details(sp_opts: list[dict]) -> None:
    port_infos = st.session_state.mv_port_infos
    port_count = len(port_infos)
    subject = (
        f"**{port_infos[0]['label']}**"
        if port_count == 1
        else f"**{port_count} ports**"
    )
    current_sp = (port_infos[0]["loc"] or {}).get("sampling_point_name") or "unknown"
    st.info(f"Moving {subject} away from **{current_sp}**.")

    sp_map = {s["label"]: s["sampling_point_id"] for s in sp_opts}
    sp_labels = list(sp_map.keys())

    if not sp_labels:
        st.error("No sampling points found. Add one via Sites → Sampling Locations first.")
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
            value=st.session_state.mv_time or _now_utc().time().replace(second=0, microsecond=0),
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

        # Guard: destination must differ from *all* current locations
        current_sp_ids = {
            (pi["loc"] or {}).get("sampling_point_id")
            for pi in port_infos
            if (pi["loc"] or {}).get("sampling_point_id") is not None
        }
        if current_sp_ids == {dest_sp_id}:
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
                value=st.session_state.mv_event_desc,
                key="mv_event_desc_widget",
            )

    def on_next() -> list[str]:
        st.session_state.mv_add_event = add_event
        if add_event:
            if not et_labels:
                return ["No event types available — uncheck the event option to proceed."]
            st.session_state.mv_event_type_id = et_map.get(et_label)
            st.session_state.mv_event_type_label = et_label
            st.session_state.mv_event_desc = event_desc
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
    port_infos = st.session_state.mv_port_infos
    port_count = len(port_infos)

    move_dt = datetime.combine(
        st.session_state.mv_date,
        st.session_state.mv_time,
        tzinfo=timezone.utc,
    )

    st.write("Review the details below and click **Confirm Move** to apply.")

    # Port summary
    with st.container(border=True):
        if port_count == 1:
            pi = port_infos[0]
            current_sp = (pi["loc"] or {}).get("sampling_point_name") or "unknown"
            st.markdown(f"**Port:** {pi['label']}")
            st.markdown(f"**From:** {current_sp}")
        else:
            st.markdown(f"**{port_count} ports will be moved:**")
            for pi in port_infos:
                current_sp = (pi["loc"] or {}).get("sampling_point_name") or "unknown"
                st.markdown(f"- {pi['label']}  (currently at: {current_sp})")
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
            "start_time": move_ts,
        }
        if st.session_state.mv_notes:
            payload["notes"] = st.session_state.mv_notes

        errors: list[str] = []

        # Relocate each top-level port
        for pi in port_infos:
            try:
                relocate_signal_port(pi["id"], payload)
            except APIError as e:
                errors.append(f"Move failed for {pi['label']}: {e.message}")

        if errors:
            return errors

        # Optionally create one equipment event per unique equipment
        if st.session_state.mv_add_event and st.session_state.mv_event_type_id:
            seen_eq_ids: set[int] = set()
            for pi in port_infos:
                equipment_id = (pi["eq"] or {}).get("equipment_id")
                if equipment_id and equipment_id not in seen_eq_ids:
                    seen_eq_ids.add(equipment_id)
                    try:
                        create_equipment_event(
                            {
                                "equipment_id": equipment_id,
                                "event_type_id": st.session_state.mv_event_type_id,
                                "event_timestamp": move_ts,
                                "description": st.session_state.mv_event_desc or None,
                            }
                        )
                    except APIError as e:
                        errors.append(
                            f"Move succeeded but equipment event could not be recorded: {e.message}"
                        )

        if not errors:
            dest = st.session_state.mv_dest_sp_label
            subject = port_infos[0]["label"] if port_count == 1 else f"{port_count} ports"
            st.toast(f"**{subject}** moved to **{dest}** ✓", icon="✅")
            _reset()
        return errors

    _nav(4, on_next=on_next, next_label="Confirm Move ✓")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Equipment Move")
st.markdown(
    "Guided workflow to relocate signal port(s) to a new sampling point "
    "and optionally log an equipment event. You can move a single port or "
    "all ports currently assigned to a piece of equipment."
)

_init()

try:
    with st.spinner("Loading…"):
        _raw_ports = list_signal_ports(page_size=500)
        _sp_opts = list_sampling_points_lookup()
        _event_types = list_equipment_event_types()
        _equipment_lookup = list_equipment_lookup()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

# Top-level ports only (sub-ports follow their parent automatically)
_top_level_ports = [
    {
        "id": p["signal_port_id"],
        "label": f"{p['tag']}  —  {p.get('das_name') or 'no DAS'}",
    }
    for p in _raw_ports.get("items", [])
    if p.get("parent_port_id") is None
]

step = st.session_state.mv_step
_render_header(step)

if step == 1:
    _step_select_port(_top_level_ports, _equipment_lookup)
elif step == 2:
    _step_move_details(_sp_opts)
elif step == 3:
    _step_equipment_event(_event_types)
elif step == 4:
    _step_review()
