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
    list_channel_roles,
    list_parameters_lookup,
    list_signal_interfaces_lookup,
    update_channel,
)
from app.components.form_dialog import create_form_dialog, edit_form_dialog


st.title("Channels")

# Load lookup data for dropdowns
try:
    with st.spinner("Loading..."):
        signal_interfaces_lookup = list_signal_interfaces_lookup()
        parameters_lookup = list_parameters_lookup()
        channel_roles_lookup = list_channel_roles()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

# Prepare dropdown options
signal_interface_options = [
    {
        "id": si["signal_interface_id"],
        "label": si.get("name", f"SI-{si['signal_interface_id']}"),
    }
    for si in signal_interfaces_lookup
]
parameter_options = [
    {"id": p["parameter_id"], "label": p["parameter_name"]} for p in parameters_lookup
]
channel_role_options = [
    {"id": cr["channel_kind_id"], "label": cr["name"]} for cr in channel_roles_lookup
]

# Filter section
st.markdown("### Filters")
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    signal_interface_filter_options = [
        {"id": None, "label": "All"}
    ] + signal_interface_options
    selected_signal_interface_label = st.selectbox(
        "Signal Interface",
        options=[opt["label"] for opt in signal_interface_filter_options],
        index=0,
        key="filter_signal_interface",
        help="Filter channels by their publishing interface (PLC, SCADA, basestation, ...)",
    )
    signal_interface_id_filter = next(
        (
            opt["id"]
            for opt in signal_interface_filter_options
            if opt["label"] == selected_signal_interface_label
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
        help="Filter channels by measured analyte or parameter",
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
    st.markdown("<br>", unsafe_allow_html=True)
    apply_filters = st.button("Apply Filters", type="primary")

# Load channels with filters
if apply_filters or "channels_loaded" not in st.session_state:
    try:
        with st.spinner("Loading channels..."):
            channels_data = list_channels(
                signal_interface_id=signal_interface_id_filter,
                parameter_id=parameter_id_filter,
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


# Form field definitions (shared between create and edit)
_FORM_FIELDS = [
    {
        "name": "signal_interface_id",
        "label": "Signal Interface",
        "type": "select",
        "required": True,
        "options": signal_interface_options,
        "help": "The SignalInterface (PLC, SCADA, basestation, ...) that publishes this tag",
    },
    {
        "name": "signal_interface_port_id",
        "label": "Signal Interface Port",
        "type": "number",
        "required": False,
        "help": "Current physical port (if known) this Channel is gated through",
    },
    {
        "name": "tag_name",
        "label": "Tag Name",
        "type": "text",
        "required": True,
        "help": "Tag string as published by the SignalInterface (case-preserved)",
    },
    {
        "name": "parent_channel_id",
        "label": "Parent Channel",
        "type": "number",
        "required": False,
        "help": "For sub-signal Channels (Status, Alarm, Uncertainty), points to the parent Value Channel",
    },
    {
        "name": "channel_kind_id",
        "label": "Channel Kind",
        "type": "select",
        "required": False,
        "options": channel_role_options,
        "help": "Kind of information this Channel carries (Value, Status, Alarm, Uncertainty)",
    },
    {
        "name": "parameter_id",
        "label": "Parameter",
        "type": "select",
        "required": False,
        "options": parameter_options,
        "help": "Measured analyte or parameter (e.g. TSS, pH)",
    },
    {
        "name": "data_provenance_id",
        "label": "Data Provenance",
        "type": "number",
        "required": False,
        "help": "How this data was produced (Sensor, Laboratory, Manual Entry, ...)",
    },
    {
        "name": "value_kind_id",
        "label": "Value Kind",
        "type": "number",
        "required": False,
        "help": "Shape of stored values (1=Scalar, 2=Vector, 3=Matrix, 4=Image)",
    },
]

# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=_FORM_FIELDS,
            on_submit=lambda data: handle_create_channel(data),
            title="Create New Channel",
        )

# Store selected row
if "selected_channel_id" not in st.session_state:
    st.session_state.selected_channel_id = None

# Display table
if channels:
    df = pd.DataFrame(channels)
    # A channel's processing state is the accumulated OperationKind trait set
    # (ChannelTrait), not a single processing degree (ADR 0005). Render the
    # trait list as a readable comma-joined "Operations" column when present.
    if "traits" in df.columns:
        df["traits"] = df["traits"].apply(
            lambda t: ", ".join(t) if isinstance(t, (list, tuple)) else t
        )
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
                fields=_FORM_FIELDS,
                on_submit=lambda data: handle_update_channel(
                    selected_item["channel_id"], data
                ),
                title=f"Edit Channel: {selected_item.get('channel_id', '')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_item is None, type="secondary"):
        if selected_item:
            handle_delete_channel(selected_item["channel_id"])
