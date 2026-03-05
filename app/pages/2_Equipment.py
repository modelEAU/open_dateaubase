"""Equipment CRUD page with form-based editing."""

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
    create_equipment,
    delete_equipment,
    list_equipment,
    list_equipment_models_lookup,
    patch_equipment,
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

st.title("Equipment")

# Load equipment and models for dropdown
try:
    with st.spinner("Loading..."):
        equipment_data = list_equipment()
        equipment = (
            equipment_data.get("items", [])
            if isinstance(equipment_data, dict)
            else equipment_data
        )
        models = list_equipment_models_lookup()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    st.stop()

# Prepare model options for dropdown
model_options = [
    {"id": m["model_id"], "label": f"{m['manufacturer']} - {m['model_name']}"}
    for m in models
]


# Handler functions
def handle_create_equipment(data: dict) -> bool:
    try:
        create_equipment(data)
        st.success("Equipment created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create equipment: {e.message}")
        return False


def handle_patch_equipment(equipment_id: int, data: dict) -> bool:
    try:
        patch_equipment(equipment_id, data)
        st.success("Equipment updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update equipment: {e.message}")
        return False


def handle_delete_equipment(equipment_id: int) -> None:
    try:
        delete_equipment(equipment_id)
        st.success("Equipment deleted successfully!")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete equipment: {e.message}")


# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=[
                {"name": "identifier", "type": "text", "required": True},
                {"name": "serial_number", "type": "text", "required": False},
                {
                    "name": "model_id",
                    "type": "select",
                    "required": False,
                    "options": model_options,
                },
                {"name": "owner", "type": "text", "required": False},
                {"name": "purchase_date", "type": "date", "required": False},
            ],
            on_submit=lambda data: handle_create_equipment(data),
            title="Create New Equipment",
        )

# Store selected row
if "selected_equipment_id" not in st.session_state:
    st.session_state.selected_equipment_id = None

# Display table
if equipment:
    df = pd.DataFrame(equipment)
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_equipment_id = df.iloc[row_idx]["equipment_id"]
        selected_item = equipment[row_idx]
    else:
        selected_item = None
        st.session_state.selected_equipment_id = None
else:
    st.info("No equipment found. Click 'New' to create one.")
    selected_item = None

with col2:
    if st.button("✏️ Edit", disabled=selected_item is None):
        if selected_item:
            edit_form_dialog(
                item_data=selected_item,
                fields=[
                    {"name": "identifier", "type": "text", "required": True},
                    {"name": "serial_number", "type": "text", "required": False},
                    {
                        "name": "model_id",
                        "type": "select",
                        "required": False,
                        "options": model_options,
                    },
                    {"name": "owner", "type": "text", "required": False},
                    {"name": "purchase_date", "type": "date", "required": False},
                ],
                on_submit=lambda data: handle_patch_equipment(
                    selected_item["equipment_id"], data
                ),
                title=f"Edit Equipment: {selected_item.get('identifier', '')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_item is None, type="secondary"):
        if selected_item:
            handle_delete_equipment(selected_item["equipment_id"])
