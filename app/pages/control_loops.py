"""Control Loops page with ports management and lifecycle operations."""

from __future__ import annotations

import sys
from datetime import datetime
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
    list_control_loop_ports,
    list_control_loops,
    list_channels,
    open_application,
    retune_control_loop,
)
from app.components.form_dialog import create_form_dialog


st.title("Control Loops")

# Load lookup data
try:
    with st.spinner("Loading..."):
        channels = list_channels(page_size=1000).get("items", [])
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

channel_options = [
    {
        "id": ch["channel_id"],
        "label": f"{ch.get('signal_interface_name', '—')} / {ch['tag_name']}",
    }
    for ch in channels
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
def handle_create_loop(data: dict) -> bool:
    try:
        result = create_control_loop(data)
        st.success(f"Control loop created: ID {result['control_loop_id']}")
        st.session_state.control_loops_loaded = False
        return True
    except APIError as e:
        st.error(f"Failed to create control loop: {e.message}")
        return False


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


# Action buttons
col1, col2 = st.columns([1, 9])
with col1:
    if st.button("➕ New Loop", type="primary"):
        create_form_dialog(
            fields=[
                {"name": "name", "type": "text", "required": True},
                {"name": "description", "type": "text", "required": False},
                {
                    "name": "controller_application_id",
                    "type": "number",
                    "required": False,
                },
            ],
            on_submit=lambda data: handle_create_loop(data),
            title="Create New Control Loop",
        )

# Store selected row
if "selected_loop_id" not in st.session_state:
    st.session_state.selected_loop_id = None

# Display table
if loops:
    df = pd.DataFrame(loops)
    selected_indices = st.dataframe(
        df,
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
                    fields=[
                        {
                            "name": "channel_id",
                            "type": "select",
                            "required": True,
                            "options": channel_options,
                        },
                        {
                            "name": "role",
                            "type": "select",
                            "required": True,
                            "options": [
                                {
                                    "id": "process_variable",
                                    "label": "Process Variable (PV)",
                                },
                                {"id": "setpoint", "label": "Setpoint (SP)"},
                                {
                                    "id": "controlled_variable",
                                    "label": "Controlled Variable (CV)",
                                },
                                {
                                    "id": "manipulated_variable",
                                    "label": "Manipulated Variable (MV)",
                                },
                                {
                                    "id": "disturbance_variable",
                                    "label": "Disturbance Variable (DV)",
                                },
                            ],
                        },
                        {
                            "name": "priority",
                            "type": "number",
                            "required": False,
                            "default": 1,
                        },
                    ],
                    on_submit=lambda data: handle_add_port(
                        selected_loop["control_loop_id"], data
                    ),
                    title="Add Port to Control Loop",
                )

        try:
            loop_ports = list_control_loop_ports(selected_loop["control_loop_id"])
            if loop_ports and "items" in loop_ports and loop_ports["items"]:
                st.dataframe(
                    pd.DataFrame(loop_ports["items"]), use_container_width=True
                )
            else:
                st.info("No ports assigned to this control loop.")
        except APIError as e:
            st.error(f"Failed to load loop ports: {e.message}")

    with tab_application:
        try:
            active_app = get_active_application(selected_loop["control_loop_id"])

            if active_app:
                st.markdown("##### Active Controller Application")
                st.json(active_app, expanded=False)

                if st.button("Retune Controller", type="secondary"):
                    create_form_dialog(
                        fields=[
                            {
                                "name": "parameter_set_id",
                                "type": "number",
                                "required": True,
                            },
                            {
                                "name": "timestamp",
                                "type": "datetime-local",
                                "required": True,
                                "default": datetime.now().isoformat(timespec="seconds"),
                            },
                            {"name": "reason", "type": "text", "required": False},
                        ],
                        on_submit=lambda data: handle_retune(
                            selected_loop["control_loop_id"], data
                        ),
                        title="Retune Control Loop",
                    )
            else:
                st.info("No active application running on this control loop.")

                if st.button("Open Application", type="primary"):
                    create_form_dialog(
                        fields=[
                            {
                                "name": "application_id",
                                "type": "number",
                                "required": True,
                            },
                            {
                                "name": "start_timestamp",
                                "type": "datetime-local",
                                "required": True,
                                "default": datetime.now().isoformat(timespec="seconds"),
                            },
                            {"name": "comments", "type": "text", "required": False},
                        ],
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
