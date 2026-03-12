"""Equipment Models CRUD page with form-based editing."""

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
    create_equipment_model,
    delete_equipment_model,
    list_equipment_models,
    update_equipment_model,
)
from app.auth import get_current_user, logout, require_auth
from app.components.form_dialog import create_form_dialog, edit_form_dialog

require_auth()


st.title("Equipment Models")

# Load equipment models
try:
    with st.spinner("Loading..."):
        models = list_equipment_models()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    st.stop()


# Handler functions
def handle_create_model(data: dict) -> bool:
    try:
        create_equipment_model(data)
        st.success("Equipment model created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create equipment model: {e.message}")
        return False


def handle_update_model(model_id: int, data: dict) -> bool:
    try:
        update_equipment_model(model_id, data)
        st.success("Equipment model updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update equipment model: {e.message}")
        return False


def handle_delete_model(model_id: int) -> None:
    try:
        delete_equipment_model(model_id)
        st.success("Equipment model deleted successfully!")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete equipment model: {e.message}")


_FORM_FIELDS = [
    {"name": "equipment_model", "type": "text", "required": True},
    {"name": "manufacturer", "type": "text", "required": False},
    {"name": "method", "type": "text", "required": False},
    {"name": "functions", "type": "textarea", "required": False},
    {"name": "manual_location", "type": "text", "required": False},
]

# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=_FORM_FIELDS,
            on_submit=lambda data: handle_create_model(data),
            title="Create New Equipment Model",
        )

# Store selected row
if "selected_model_id" not in st.session_state:
    st.session_state.selected_model_id = None

# Display table
if models:
    df = pd.DataFrame(models)
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_model_id = df.iloc[row_idx]["model_id"]
        selected_item = models[row_idx]
    else:
        selected_item = None
        st.session_state.selected_model_id = None
else:
    st.info("No equipment models found. Click 'New' to create one.")
    selected_item = None

with col2:
    if st.button("✏️ Edit", disabled=selected_item is None):
        if selected_item:
            edit_form_dialog(
                item_data=selected_item,
                fields=_FORM_FIELDS,
                on_submit=lambda data: handle_update_model(
                    selected_item["model_id"], data
                ),
                title=f"Edit Equipment Model: {selected_item.get('equipment_model', '')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_item is None, type="secondary"):
        if selected_item:
            handle_delete_model(selected_item["model_id"])
