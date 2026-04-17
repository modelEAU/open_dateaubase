"""Channels CRUD page with filtering and form-based editing."""

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
    create_channel,
    delete_channel,
    list_channels,
    list_parameters_lookup,
    list_processing_degrees_lookup,
    list_signal_ports,
    update_channel,
)
from app.components.form_dialog import create_form_dialog, edit_form_dialog



st.title("Channels")

# Load lookup data for dropdowns
try:
    with st.spinner("Loading..."):
        signal_ports_data = list_signal_ports(page_size=500)
        parameters_lookup = list_parameters_lookup()
        processing_degrees_lookup = list_processing_degrees_lookup()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

# Prepare dropdown options
signal_port_options = [
    {"id": sp["signal_port_id"], "label": f"{sp['das_name']} / {sp['tag']}"}
    for sp in signal_ports_data.get("items", [])
]
parameter_options = [
    {"id": p["parameter_id"], "label": p["parameter_name"]} for p in parameters_lookup
]
degree_options = [
    {"id": d["processing_degree_id"], "label": d["name"]}
    for d in processing_degrees_lookup
]

# Filter section
st.markdown("### Filters")
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

with filter_col1:
    signal_port_filter_options = [{"id": None, "label": "All"}] + signal_port_options
    selected_signal_port_label = st.selectbox(
        "Signal Port",
        options=[opt["label"] for opt in signal_port_filter_options],
        index=0,
        key="filter_signal_port",
    )
    signal_port_id_filter = next(
        (
            opt["id"]
            for opt in signal_port_filter_options
            if opt["label"] == selected_signal_port_label
        ),
        None,
    )

with filter_col2:
    parameter_filter_options = [{"id": None, "label": "All"}] + parameter_options
    selected_parameter_label = st.selectbox(
        "Parameter",
        options=[opt["label"] for opt in parameter_filter_options],
        index=0,
        key="filter_parameter",
    )
    parameter_id_filter = next(
        (
            opt["id"]
            for opt in parameter_filter_options
            if opt["label"] == selected_parameter_label
        ),
        None,
    )

with filter_col3:
    degree_filter_options = [{"id": None, "label": "All"}] + degree_options
    selected_degree_label = st.selectbox(
        "Processing Degree",
        options=[opt["label"] for opt in degree_filter_options],
        index=0,
        key="filter_degree",
    )
    degree_id_filter = next(
        (
            opt["id"]
            for opt in degree_filter_options
            if opt["label"] == selected_degree_label
        ),
        None,
    )

with filter_col4:
    st.markdown("<br>", unsafe_allow_html=True)
    apply_filters = st.button("Apply Filters", type="primary")

# Load channels with filters
if apply_filters or "channels_loaded" not in st.session_state:
    try:
        with st.spinner("Loading channels..."):
            channels_data = list_channels(
                signal_port_id=signal_port_id_filter,
                parameter_id=parameter_id_filter,
                processing_degree_id=degree_id_filter,
            )
            channels = (
                channels_data.get("items", [])
                if isinstance(channels_data, dict)
                else channels_data
            )
            st.session_state.channels_loaded = True
            st.session_state.channels = channels
    except APIError as e:
        st.error(f"Cannot load channels: {e.message}")
        channels = []
else:
    channels = st.session_state.get("channels", [])


# Handler functions
def handle_create_channel(data: dict) -> bool:
    try:
        create_channel(data)
        st.success("Channel created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create channel: {e.message}")
        return False


def handle_update_channel(channel_id: int, data: dict) -> bool:
    try:
        update_channel(channel_id, data)
        st.success("Channel updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update channel: {e.message}")
        return False


def handle_delete_channel(channel_id: int) -> None:
    try:
        delete_channel(channel_id)
        st.success("Channel deleted successfully!")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete channel: {e.message}")


# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=[
                {
                    "name": "signal_port_id",
                    "type": "select",
                    "required": True,
                    "options": signal_port_options,
                },
                {
                    "name": "parameter_id",
                    "type": "select",
                    "required": False,
                    "options": parameter_options,
                },
                {
                    "name": "data_provenance_id",
                    "type": "number",
                    "required": False,
                },
                {
                    "name": "processing_degree_id",
                    "type": "select",
                    "required": False,
                    "options": degree_options,
                },
                {
                    "name": "value_type_id",
                    "type": "number",
                    "required": False,
                },
            ],
            on_submit=lambda data: handle_create_channel(data),
            title="Create New Channel",
        )

# Store selected row
if "selected_channel_id" not in st.session_state:
    st.session_state.selected_channel_id = None

# Display table
if channels:
    df = pd.DataFrame(channels)
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_channel_id = df.iloc[row_idx]["channel_id"]
        selected_item = channels[row_idx]
    else:
        selected_item = None
        st.session_state.selected_channel_id = None
else:
    st.info("No channels found. Click 'New' to create one or adjust filters.")
    selected_item = None

with col2:
    if st.button("✏️ Edit", disabled=selected_item is None):
        if selected_item:
            edit_form_dialog(
                item_data=selected_item,
                fields=[
                    {
                        "name": "signal_port_id",
                        "type": "select",
                        "required": True,
                        "options": signal_port_options,
                    },
                    {
                        "name": "parameter_id",
                        "type": "select",
                        "required": False,
                        "options": parameter_options,
                    },
                    {
                        "name": "data_provenance_id",
                        "type": "number",
                        "required": False,
                    },
                    {
                        "name": "processing_degree_id",
                        "type": "select",
                        "required": False,
                        "options": degree_options,
                    },
                    {
                        "name": "value_type_id",
                        "type": "number",
                        "required": False,
                    },
                ],
                on_submit=lambda data: handle_update_channel(
                    selected_item["channel_id"], data
                ),
                title=f"Edit Channel: {selected_item.get('channel_id', '')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_item is None, type="secondary"):
        if selected_item:
            handle_delete_channel(selected_item["channel_id"])
