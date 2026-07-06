"""Control Loops page with ports management and lifecycle operations."""

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
    add_control_loop_port,
    create_control_loop,
    get_active_application,
    get_control_loop,
    get_fallback_chain,
    list_analysis_series_lookup,
    list_control_loop_ports,
    list_control_loops,
    list_controller_kinds,
    list_channels,
    open_application,
    retune_control_loop,
)
from app.components.crud_form import render_form_field, validate_required_fields
from app.components.form_dialog import _serialize_form_data, create_form_dialog
from app.components.form_specs import get_form_fields
from app.components.id_format import humanize_id_columns


st.title("Control Loops")

# Load lookup data
try:
    with st.spinner("Loading..."):
        channels = list_channels(page_size=1000).get("items", [])
        lab_series = list_analysis_series_lookup()
        controller_kinds = list_controller_kinds()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

# A control loop wires Streams — either a sensor Channel or a lab AnalysisSeries.
# Both lookups return the underlying Stream_ID, so they combine into one picker.
stream_options = [
    {
        "id": ch["channel_id"],
        "label": f"🛰 {ch.get('signal_interface_name', '—')} / {ch['tag_name']}",
    }
    for ch in channels
] + [
    {
        "id": s["analysis_series_id"],
        "label": f"🧪 {s['name']} ({s.get('parameter_name', '?')} @ {s.get('sampling_point_label', '?')})",
    }
    for s in lab_series
]

# Roles as defined by ControlLoopPortKind seed vocabulary (role_name lookup is
# case-insensitive server-side).
_ROLE_OPTIONS = [
    {"id": "MeasuredVariable", "label": "Measured / Process Variable (PV)"},
    {"id": "ManipulatedVariable", "label": "Manipulated Variable (MV)"},
    {"id": "SetPoint", "label": "Setpoint (SP)"},
    {"id": "Disturbance", "label": "Disturbance (DV)"},
    {"id": "PredictedOutput", "label": "Predicted Output"},
    {"id": "Other", "label": "Other"},
]


def _loop_identity_fields() -> list[dict]:
    """Create-loop fields with the controller-kind dropdown populated."""
    kind_options = [
        {"id": k["controller_kind_id"], "label": k["name"]} for k in controller_kinds
    ]
    fields = []
    for f in get_form_fields("control_loop"):
        f = dict(f)
        if f["name"] == "controller_kind_id":
            f["options"] = kind_options
        fields.append(f)
    return fields


def _port_fields() -> list[dict]:
    """Add-port fields matching ControlLoopPortAddRequest (stream_id + role_name)."""
    return [
        {"name": "stream_id", "type": "select", "required": True, "options": stream_options},
        {"name": "role_name", "type": "select", "required": True, "options": _ROLE_OPTIONS},
    ]


def _application_fields() -> list[dict]:
    """Open/retune-application fields matching Application{Open,Retune}Request."""
    return [
        {"name": "start_time", "type": "datetime", "required": True},
        {
            "name": "parameters",
            "type": "textarea",
            "required": False,
            "help": 'Controller parameters as JSON, e.g. {"Kp": 1.2, "Ki": 0.05}',
        },
        {"name": "notes", "type": "text", "required": False},
    ]

# Load control loops
if "control_loops_loaded" not in st.session_state:
    try:
        with st.spinner("Loading control loops..."):
            loops = list_control_loops()
            st.session_state.control_loops_loaded = True
            st.session_state.control_loops = loops
    except APIError as e:
        st.error(f"Cannot load control loops: {e.message}")
        loops = []
else:
    loops = st.session_state.get("control_loops", [])


# Handler functions
def handle_create_loop(data: dict) -> int | None:
    """Create a loop; return its new id (or None on failure)."""
    try:
        result = create_control_loop(data)
        st.session_state.control_loops_loaded = False
        return result["control_loop_id"]
    except APIError as e:
        st.error(f"Failed to create control loop: {e.message}")
        return None


def handle_add_port(loop_id: int, data: dict) -> bool:
    try:
        add_control_loop_port(loop_id, data)
        st.success("Port added to control loop")
        return True
    except APIError as e:
        st.error(f"Failed to add port: {e.message}")
        return False


def handle_open_application(loop_id: int, data: dict) -> bool:
    try:
        open_application(loop_id, data)
        st.success("Application opened successfully")
        return True
    except APIError as e:
        st.error(f"Failed to open application: {e.message}")
        return False


def handle_retune(loop_id: int, data: dict) -> bool:
    try:
        retune_control_loop(loop_id, data)
        st.success("Control loop retuned successfully")
        return True
    except APIError as e:
        st.error(f"Failed to retune loop: {e.message}")
        return False


def _render_fields(fields: list[dict]) -> tuple[dict, list[str]]:
    """Render a list of field specs inline; return (form_data, required_names)."""
    data: dict = {}
    required: list[str] = []
    for f in fields:
        if f.get("required"):
            required.append(f["name"])
        data[f["name"]] = render_form_field(
            field_name=f["name"],
            field_type=f.get("type", "text"),
            required=f.get("required", False),
            options=f.get("options"),
            help_text=f.get("help"),
            label=f.get("label"),
        )
    return data, required


def _close_wizard() -> None:
    for k in ("cl_wizard_open", "cl_wizard_step", "cl_wizard_loop_id"):
        st.session_state.pop(k, None)


def _finish_wizard() -> None:
    st.session_state.control_loops_loaded = False  # refresh the table
    st.session_state.selected_loop_id = st.session_state.get("cl_wizard_loop_id")
    _close_wizard()


def _submit(data: dict, required: list[str], action) -> bool:
    """Validate required fields, then run ``action(serialized_data)``."""
    errors = validate_required_fields(data, required)
    if errors:
        for e in errors:
            st.error(e)
        return False
    return bool(action(_serialize_form_data(data)))


def _render_loop_ports(loop_id: int) -> None:
    """Show the ports already wired to a loop (best-effort)."""
    try:
        resp = list_control_loop_ports(loop_id)
        ports = resp.get("ports") if resp else None
        if ports:
            st.dataframe(
                humanize_id_columns(pd.DataFrame(ports)), use_container_width=True
            )
        else:
            st.info("No ports wired yet.")
    except APIError as e:
        st.error(f"Failed to load loop ports: {e.message}")


@st.dialog("Create Control Loop", width="large")
def _create_loop_wizard() -> None:
    step = st.session_state.get("cl_wizard_step", 1)
    loop_id = st.session_state.get("cl_wizard_loop_id")
    st.caption(f"Step {step} of 3")

    if step == 1:
        st.markdown("#### 1 · Loop identity")
        data, required = _render_fields(_loop_identity_fields())
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("Create →", type="primary"):
                new_id = None
                if not validate_required_fields(data, required):
                    new_id = handle_create_loop(_serialize_form_data(data))
                else:
                    for e in validate_required_fields(data, required):
                        st.error(e)
                if new_id is not None:
                    st.session_state.cl_wizard_loop_id = new_id
                    st.session_state.cl_wizard_step = 2
                    st.rerun()
        with c2:
            if st.button("Cancel"):
                _close_wizard()
                st.rerun()

    elif step == 2:
        assert loop_id is not None  # set before advancing past step 1
        st.markdown("#### 2 · Ports (optional)")
        st.caption(f"Loop #{loop_id} created. Wire streams to their roles, or skip.")
        _render_loop_ports(loop_id)
        data, required = _render_fields(_port_fields())
        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            if st.button("Add port") and _submit(
                data, required, lambda d: handle_add_port(loop_id, d)
            ):
                st.rerun()
        with c2:
            if st.button("Next →", type="primary"):
                st.session_state.cl_wizard_step = 3
                st.rerun()
        with c3:
            if st.button("Finish"):
                _finish_wizard()
                st.rerun()

    else:  # step 3
        assert loop_id is not None  # set before advancing past step 1
        st.markdown("#### 3 · Initial tuning (optional)")
        st.caption("Record the controller's first parameter set / application.")
        data, required = _render_fields(_application_fields())
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("Open application", type="primary") and _submit(
                data, required, lambda d: handle_open_application(loop_id, d)
            ):
                _finish_wizard()
                st.rerun()
        with c2:
            if st.button("Finish without tuning"):
                _finish_wizard()
                st.rerun()


# Action buttons
col1, col2 = st.columns([1, 9])
with col1:
    if st.button("➕ New Loop", type="primary"):
        st.session_state.cl_wizard_open = True
        st.session_state.cl_wizard_step = 1
        st.session_state.pop("cl_wizard_loop_id", None)
        st.rerun()

if st.session_state.get("cl_wizard_open"):
    _create_loop_wizard()

# Store selected row
if "selected_loop_id" not in st.session_state:
    st.session_state.selected_loop_id = None

# Display table
if loops:
    df = pd.DataFrame(loops)
    selected_indices = st.dataframe(
        humanize_id_columns(df, pk_field="control_loop_id"),
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_loop_id = df.iloc[row_idx]["control_loop_id"]
        selected_loop = loops[row_idx]
    else:
        selected_loop = None
        st.session_state.selected_loop_id = None
else:
    st.info("No control loops found. Click 'New Loop' to create one.")
    selected_loop = None

# Detail panel when loop is selected
if selected_loop:
    st.markdown("---")
    st.subheader(f"Control Loop: {selected_loop['name']}")

    tab_ports, tab_application, tab_fallback = st.tabs(
        ["Ports", "Active Application", "Fallback Chain"]
    )

    with tab_ports:
        col_add, _ = st.columns([1, 9])
        with col_add:
            if st.button("➕ Add Port"):
                create_form_dialog(
                    fields=_port_fields(),
                    on_submit=lambda data: handle_add_port(
                        selected_loop["control_loop_id"], data
                    ),
                    title="Add Port to Control Loop",
                )

        _render_loop_ports(selected_loop["control_loop_id"])

    with tab_application:
        try:
            active_app = get_active_application(selected_loop["control_loop_id"])

            if active_app:
                st.markdown("##### Active Controller Application")
                st.json(active_app, expanded=False)

                if st.button("Retune Controller", type="secondary"):
                    create_form_dialog(
                        fields=_application_fields(),
                        on_submit=lambda data: handle_retune(
                            selected_loop["control_loop_id"], data
                        ),
                        title="Retune Control Loop",
                    )
            else:
                st.info("No active application running on this control loop.")

                if st.button("Open Application", type="primary"):
                    create_form_dialog(
                        fields=_application_fields(),
                        on_submit=lambda data: handle_open_application(
                            selected_loop["control_loop_id"], data
                        ),
                        title="Open Application on Control Loop",
                    )
        except APIError as e:
            st.error(f"Failed to load active application: {e.message}")

    with tab_fallback:
        try:
            fallback_chain = get_fallback_chain(selected_loop["control_loop_id"])
            st.markdown("##### Controller Fallback Chain")

            if fallback_chain and "chain" in fallback_chain and fallback_chain["chain"]:
                for i, entry in enumerate(fallback_chain["chain"], 1):
                    with st.container(border=True):
                        st.markdown(f"**Level {i}**: {entry.get('name', 'Unknown')}")
                        st.caption(
                            f"Priority: {entry.get('priority', 0)} | Status: {entry.get('status', 'unknown')}"
                        )
            else:
                st.info("No fallback chain configured for this control loop.")

        except APIError as e:
            st.error(f"Failed to load fallback chain: {e.message}")
