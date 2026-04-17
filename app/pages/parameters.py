"""Parameters CRUD page with form-based editing."""

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
    create_parameter,
    delete_parameter,
    list_parameters_full,
    list_units_lookup,
    update_parameter,
)
from app.components.form_dialog import create_form_dialog, edit_form_dialog



st.title("Parameters")

# Load parameters and units for dropdown
try:
    with st.spinner("Loading..."):
        parameters = list_parameters_full()
        units = list_units_lookup()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    st.stop()

# Prepare unit options for dropdown
unit_options = [{"id": u["unit_id"], "label": u["unit"]} for u in units]


# Handler functions
def handle_create_parameter(data: dict) -> bool:
    try:
        create_parameter(data)
        st.success("Parameter created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create parameter: {e.message}")
        return False


def handle_update_parameter(param_id: int, data: dict) -> bool:
    try:
        update_parameter(param_id, data)
        st.success("Parameter updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update parameter: {e.message}")
        return False


def handle_delete_parameter(param_id: int) -> None:
    try:
        delete_parameter(param_id)
        st.success("Parameter deleted successfully!")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete parameter: {e.message}")


_FORM_FIELDS = [
    {"name": "parameter", "type": "text", "required": True},
    {
        "name": "unit_id",
        "type": "select",
        "required": False,
        "options": unit_options,
    },
    {"name": "description", "type": "textarea", "required": False},
]

# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=_FORM_FIELDS,
            on_submit=lambda data: handle_create_parameter(data),
            title="Create New Parameter",
        )

# Store selected row
if "selected_parameter_id" not in st.session_state:
    st.session_state.selected_parameter_id = None

# Display table
if parameters:
    df = pd.DataFrame(parameters)
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_parameter_id = df.iloc[row_idx]["parameter_id"]
        selected_item = parameters[row_idx]
    else:
        selected_item = None
        st.session_state.selected_parameter_id = None
else:
    st.info("No parameters found. Click 'New' to create one.")
    selected_item = None

with col2:
    if st.button("✏️ Edit", disabled=selected_item is None):
        if selected_item:
            edit_form_dialog(
                item_data=selected_item,
                fields=_FORM_FIELDS,
                on_submit=lambda data: handle_update_parameter(
                    selected_item["parameter_id"], data
                ),
                title=f"Edit Parameter: {selected_item.get('parameter_name', '')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_item is None, type="secondary"):
        if selected_item:
            handle_delete_parameter(selected_item["parameter_id"])
