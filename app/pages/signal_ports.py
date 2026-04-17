"""Signal Ports CRUD page with filtering and lifecycle operations."""

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
    create_signal_port,
    get_sub_signals,
    get_equipment_at_port,
    get_location_at_port,
    list_das_lookup,
    list_equipment_lookup,
    list_sampling_points_lookup,
    list_signal_ports,
    list_signal_port_types_lookup,
    patch_signal_port,
    register_equipment_at_port,
    relocate_signal_port,
    swap_equipment_at_port,
)
from app.auth import get_current_user, logout, require_auth
from app.components.form_dialog import create_form_dialog, edit_form_dialog

require_auth()

with st.sidebar:
    user = get_current_user()
    if user:
        st.write(f"Logged in as: **{user['name']}**")
    if st.button("Sign out"):
        logout()

st.title("Signal Ports")

# Load lookup data for dropdowns
try:
    with st.spinner("Loading..."):
        das_lookup = list_das_lookup()
        port_types_lookup = list_signal_port_types_lookup()
        equipment_lookup = list_equipment_lookup()
        sampling_points_lookup = list_sampling_points_lookup()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

# Prepare dropdown options
das_options = [{"id": d["das_id"], "label": d["name"]} for d in das_lookup]
port_type_options = [
    {"id": t["signal_port_type_id"], "label": t["name"]} for t in port_types_lookup
]
equipment_options = [
    {"id": e["equipment_id"], "label": e["identifier"]} for e in equipment_lookup
]
sampling_point_options = [
    {"id": sp["sampling_point_id"], "label": sp["name"]}
    for sp in sampling_points_lookup
]

# Filter section
st.markdown("### Filters")
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

with filter_col1:
    das_filter_options = [{"id": None, "label": "All"}] + das_options
    selected_das_label = st.selectbox(
        "Data Acquisition System",
        options=[opt["label"] for opt in das_filter_options],
        index=0,
        key="filter_das",
    )
    das_id_filter = next(
        (opt["id"] for opt in das_filter_options if opt["label"] == selected_das_label),
        None,
    )

with filter_col2:
    is_active_filter = st.selectbox(
        "Status",
        options=["All", "Active", "Inactive"],
        index=0,
        key="filter_status",
    )
    is_active_val = (
        None if is_active_filter == "All" else (is_active_filter == "Active")
    )

with filter_col3:
    type_filter_options = [{"id": None, "label": "All"}] + port_type_options
    selected_type_label = st.selectbox(
        "Port Type",
        options=[opt["label"] for opt in type_filter_options],
        index=0,
        key="filter_type",
    )
    type_id_filter = next(
        (
            opt["id"]
            for opt in type_filter_options
            if opt["label"] == selected_type_label
        ),
        None,
    )

with filter_col4:
    st.markdown("<br>", unsafe_allow_html=True)
    apply_filters = st.button("Apply Filters", type="primary")

# Load ports with filters
if apply_filters or "signal_ports_loaded" not in st.session_state:
    try:
        with st.spinner("Loading signal ports..."):
            ports_data = list_signal_ports(
                das_id=das_id_filter,
                is_active=is_active_val,
                signal_port_type_id=type_id_filter,
            )
            ports = (
                ports_data.get("items", [])
                if isinstance(ports_data, dict)
                else ports_data
            )
            st.session_state.signal_ports_loaded = True
            st.session_state.signal_ports = ports
    except APIError as e:
        st.error(f"Cannot load signal ports: {e.message}")
        ports = []
else:
    ports = st.session_state.get("signal_ports", [])


# Handler functions
def handle_create_port(data: dict) -> bool:
    try:
        create_signal_port(data)
        st.success("Signal port created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create signal port: {e.message}")
        return False


def handle_update_port(port_id: int, data: dict) -> bool:
    try:
        patch_signal_port(port_id, data)
        st.success("Signal port updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update signal port: {e.message}")
        return False


# Action buttons
col1, col2 = st.columns([1, 9])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=[
                {
                    "name": "das_id",
                    "type": "select",
                    "required": True,
                    "options": das_options,
                },
                {"name": "tag", "type": "text", "required": True},
                {
                    "name": "signal_port_type_id",
                    "type": "select",
                    "required": True,
                    "options": port_type_options,
                },
                {"name": "description", "type": "text", "required": False},
            ],
            on_submit=lambda data: handle_create_port(data),
            title="Create New Signal Port",
        )

# Store selected row
if "selected_port_id" not in st.session_state:
    st.session_state.selected_port_id = None

# Display table
if ports:
    df = pd.DataFrame(ports)
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_port_id = df.iloc[row_idx]["signal_port_id"]
        selected_port = ports[row_idx]
    else:
        selected_port = None
        st.session_state.selected_port_id = None
else:
    st.info("No signal ports found. Click 'New' to create one or adjust filters.")
    selected_port = None

# Detail panel when port is selected
if selected_port:
    st.markdown("---")
    st.subheader(f"Port: {selected_port['tag']}")

    tab_subsignals, tab_lifecycle, tab_pointintime = st.tabs(
        ["Sub Signals", "Lifecycle Actions", "Point-in-Time"]
    )

    with tab_subsignals:
        try:
            sub_signals = get_sub_signals(selected_port["signal_port_id"])
            if sub_signals and "items" in sub_signals and sub_signals["items"]:
                st.dataframe(
                    pd.DataFrame(sub_signals["items"]), use_container_width=True
                )
            else:
                st.info("No sub signals configured for this port.")
        except APIError as e:
            st.error(f"Failed to load sub signals: {e.message}")

    with tab_lifecycle:
        st.markdown("#### Lifecycle Operations")

        lc_col1, lc_col2, lc_col3 = st.columns(3)

        with lc_col1:
            if st.button("Register Equipment", use_container_width=True):
                create_form_dialog(
                    fields=[
                        {
                            "name": "equipment_id",
                            "type": "select",
                            "required": True,
                            "options": equipment_options,
                        },
                        {
                            "name": "timestamp",
                            "type": "datetime-local",
                            "required": True,
                            "default": datetime.now().isoformat(timespec="seconds"),
                        },
                        {"name": "comments", "type": "text", "required": False},
                    ],
                    on_submit=lambda data: (
                        register_equipment_at_port(
                            selected_port["signal_port_id"], data
                        )
                        and st.success("Equipment registered successfully")
                    ),
                    title="Register Equipment at Port",
                )

        with lc_col2:
            if st.button("Swap Equipment", use_container_width=True):
                create_form_dialog(
                    fields=[
                        {
                            "name": "new_equipment_id",
                            "type": "select",
                            "required": True,
                            "options": equipment_options,
                        },
                        {
                            "name": "timestamp",
                            "type": "datetime-local",
                            "required": True,
                            "default": datetime.now().isoformat(timespec="seconds"),
                        },
                        {"name": "reason", "type": "text", "required": False},
                    ],
                    on_submit=lambda data: (
                        swap_equipment_at_port(selected_port["signal_port_id"], data)
                        and st.success("Equipment swapped successfully")
                    ),
                    title="Swap Equipment at Port",
                )

        with lc_col3:
            if st.button("Relocate Port", use_container_width=True):
                create_form_dialog(
                    fields=[
                        {
                            "name": "sampling_point_id",
                            "type": "select",
                            "required": True,
                            "options": sampling_point_options,
                        },
                        {
                            "name": "timestamp",
                            "type": "datetime-local",
                            "required": True,
                            "default": datetime.now().isoformat(timespec="seconds"),
                        },
                        {"name": "comments", "type": "text", "required": False},
                    ],
                    on_submit=lambda data: (
                        relocate_signal_port(selected_port["signal_port_id"], data)
                        and st.success("Port relocated successfully")
                    ),
                    title="Relocate Port to Sampling Point",
                )

    with tab_pointintime:
        st.markdown("#### Point-in-Time Lookup")
        pit_date = st.date_input("Date", value=datetime.now())
        pit_time = st.time_input("Time", value=datetime.now().time())
        pit_timestamp = datetime.combine(pit_date, pit_time).isoformat(
            timespec="seconds"
        )

        if st.button("Query State", type="primary"):
            col_equip, col_loc = st.columns(2)

            with col_equip:
                try:
                    equip_at = get_equipment_at_port(
                        selected_port["signal_port_id"], pit_timestamp
                    )
                    st.markdown("##### Equipment at this time")
                    if equip_at:
                        st.json(equip_at, expanded=False)
                    else:
                        st.info("No equipment was registered at this time")
                except APIError as e:
                    st.error(f"Equipment lookup failed: {e.message}")

            with col_loc:
                try:
                    loc_at = get_location_at_port(
                        selected_port["signal_port_id"], pit_timestamp
                    )
                    st.markdown("##### Location at this time")
                    if loc_at:
                        st.json(loc_at, expanded=False)
                    else:
                        st.info("No location was assigned at this time")
                except APIError as e:
                    st.error(f"Location lookup failed: {e.message}")
