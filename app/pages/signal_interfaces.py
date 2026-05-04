"""Signal Interfaces CRUD page with ports and channels detail tabs."""

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
    create_signal_interface,
    create_signal_interface_port,
    delete_signal_interface,
    delete_signal_interface_port,
    list_channels_for_interface,
    list_das_lookup,
    list_signal_interface_port_kinds,
    list_signal_interface_ports,
    list_signal_interface_types,
    list_signal_interfaces,
    update_signal_interface,
)
from app.components.form_dialog import create_form_dialog, edit_form_dialog


st.title("Signal Interfaces")

# Load lookup data for dropdowns
try:
    with st.spinner("Loading..."):
        das_lookup = list_das_lookup()
        si_types_lookup = list_signal_interface_types()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

# Prepare dropdown options
das_options = [{"id": d["das_id"], "label": d["name"]} for d in das_lookup]
si_type_options = [
    {"id": t["signal_interface_kind_id"], "label": t["name"]} for t in si_types_lookup
]

# Filter section
st.markdown("### Filters")
filter_col1, filter_col2 = st.columns([3, 9])

with filter_col1:
    das_filter_options = [{"id": None, "label": "All"}] + das_options
    selected_das_label = st.selectbox(
        "Data Acquisition System",
        options=[opt["label"] for opt in das_filter_options],
        index=0,
        key="filter_das",
        help="Filter interfaces belonging to a specific Data Acquisition System",
    )
    das_id_filter = next(
        (opt["id"] for opt in das_filter_options if opt["label"] == selected_das_label),
        None,
    )

with filter_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    apply_filters = st.button("Apply Filters", type="primary")

# Load interfaces with filters
if apply_filters or "signal_interfaces_loaded" not in st.session_state:
    try:
        with st.spinner("Loading signal interfaces..."):
            interfaces_data = list_signal_interfaces(das_id=das_id_filter)
            interfaces = (
                interfaces_data.get("items", [])
                if isinstance(interfaces_data, dict)
                else interfaces_data
            )
            st.session_state.signal_interfaces_loaded = True
            st.session_state.signal_interfaces = interfaces
    except APIError as e:
        st.error(f"Cannot load signal interfaces: {e.message}")
        interfaces = []
else:
    interfaces = st.session_state.get("signal_interfaces", [])


# Handler functions
def handle_create(data: dict) -> bool:
    try:
        create_signal_interface(data)
        st.success("Signal interface created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create signal interface: {e.message}")
        return False


def handle_update(si_id: int, data: dict) -> bool:
    try:
        update_signal_interface(si_id, data)
        st.success("Signal interface updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update signal interface: {e.message}")
        return False


def handle_delete(si_id: int) -> None:
    try:
        delete_signal_interface(si_id)
        st.success("Signal interface deleted successfully!")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete signal interface: {e.message}")


# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])

with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=[
                {
                    "name": "name",
                    "label": "Name",
                    "type": "text",
                    "required": True,
                    "help": "Human-readable unique name of this interface (e.g. 'hedi_plc', 'sc1000_primary')",
                },
                {
                    "name": "signal_interface_kind_id",
                    "label": "Interface Kind",
                    "type": "select",
                    "required": True,
                    "options": si_type_options,
                    "help": "Kind of this interface (PLC, SCADA, Basestation, ...)",
                },
                {
                    "name": "das_id",
                    "label": "Data Acquisition System",
                    "type": "select",
                    "required": True,
                    "options": das_options,
                    "help": "The DAS that reads data from this interface",
                },
                {
                    "name": "serial_number",
                    "label": "Serial Number",
                    "type": "text",
                    "required": False,
                    "help": "Serial number if known",
                },
                {
                    "name": "make",
                    "label": "Make",
                    "type": "text",
                    "required": False,
                    "help": "Manufacturer (e.g. 'Rockwell', 'Hach', 'WTW')",
                },
                {
                    "name": "model",
                    "label": "Model",
                    "type": "text",
                    "required": False,
                    "help": "Model designation (e.g. 'Logix5000', 'SC1000', 'TresCON')",
                },
            ],
            on_submit=lambda data: handle_create(data),
            title="Create New Signal Interface",
        )

# Store selected row
if "selected_signal_interface_id" not in st.session_state:
    st.session_state.selected_signal_interface_id = None

# Display table
selected_interface = None
if interfaces:
    df = pd.DataFrame(interfaces)
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_signal_interface_id = df.iloc[row_idx][
            "signal_interface_id"
        ]
        selected_interface = interfaces[row_idx]
    else:
        selected_interface = None
        st.session_state.selected_signal_interface_id = None
else:
    st.info("No signal interfaces found. Click 'New' to create one or adjust filters.")
    selected_interface = None

with col2:
    if st.button("✏️ Edit", disabled=selected_interface is None):
        if selected_interface:
            edit_form_dialog(
                item_data=selected_interface,
                fields=[
                    {
                        "name": "name",
                        "label": "Name",
                        "type": "text",
                        "required": True,
                        "help": "Human-readable unique name of this interface (e.g. 'hedi_plc', 'sc1000_primary')",
                    },
                    {
                        "name": "signal_interface_kind_id",
                        "label": "Interface Kind",
                        "type": "select",
                        "required": True,
                        "options": si_type_options,
                        "help": "Kind of this interface (PLC, SCADA, Basestation, ...)",
                    },
                    {
                        "name": "das_id",
                        "label": "Data Acquisition System",
                        "type": "select",
                        "required": True,
                        "options": das_options,
                        "help": "The DAS that reads data from this interface",
                    },
                    {
                        "name": "serial_number",
                        "label": "Serial Number",
                        "type": "text",
                        "required": False,
                        "help": "Serial number if known",
                    },
                    {
                        "name": "make",
                        "label": "Make",
                        "type": "text",
                        "required": False,
                        "help": "Manufacturer (e.g. 'Rockwell', 'Hach', 'WTW')",
                    },
                    {
                        "name": "model",
                        "label": "Model",
                        "type": "text",
                        "required": False,
                        "help": "Model designation (e.g. 'Logix5000', 'SC1000', 'TresCON')",
                    },
                ],
                on_submit=lambda data: handle_update(
                    selected_interface["signal_interface_id"], data
                ),
                title=f"Edit Signal Interface: {selected_interface.get('name', '')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_interface is None, type="secondary"):
        if selected_interface:
            handle_delete(selected_interface["signal_interface_id"])

# Detail panel when interface is selected
if selected_interface:
    st.markdown("---")
    st.subheader(f"Interface: {selected_interface.get('name', '')}")

    si_id = selected_interface["signal_interface_id"]

    tab_ports, tab_channels, tab_wiring = st.tabs(
        ["Ports", "Channels", "Wiring History"]
    )

    with tab_ports:
        try:
            port_kinds_lookup = list_signal_interface_port_kinds()
            port_kind_options = [
                {"id": pk["signal_interface_port_kind_id"], "label": pk["name"]}
                for pk in port_kinds_lookup
            ]
        except APIError:
            port_kind_options = []

        try:
            ports = list_signal_interface_ports(si_id)
        except APIError as e:
            st.error(f"Failed to load ports: {e.message}")
            ports = []

        if ports:
            st.dataframe(pd.DataFrame(ports), use_container_width=True)
        else:
            st.info("No ports configured for this interface.")

        if st.button("➕ Add Port", key=f"add_port_{si_id}"):
            create_form_dialog(
                fields=[
                    {
                        "name": "port_identifier",
                        "label": "Port Identifier",
                        "type": "text",
                        "required": True,
                        "help": "Identifier used by the interface (e.g. 'slot6/Ch0', 'COM2', 'ProbeA')",
                    },
                    {
                        "name": "signal_interface_port_kind_id",
                        "label": "Port Kind",
                        "type": "select",
                        "required": True,
                        "options": port_kind_options,
                        "help": "Physical kind of port (analog/digital/serial/...)",
                    },
                    {
                        "name": "description",
                        "label": "Description",
                        "type": "text",
                        "required": False,
                        "help": "Free-text notes about this port",
                    },
                ],
                on_submit=lambda data: _handle_create_port(si_id, data),
                title="Add Port",
            )

    with tab_channels:
        try:
            channels = list_channels_for_interface(si_id)
            if channels:
                st.dataframe(pd.DataFrame(channels), use_container_width=True)
            else:
                st.info("No channels configured for this interface.")
        except APIError as e:
            st.error(f"Failed to load channels: {e.message}")

    with tab_wiring:
        st.info("Wiring history view is not yet available.")


def _handle_create_port(si_id: int, data: dict) -> bool:
    try:
        create_signal_interface_port(si_id, data)
        st.success("Port created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create port: {e.message}")
        return False
