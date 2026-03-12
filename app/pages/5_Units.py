"""Units CRUD page with form-based editing."""

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
    create_unit,
    delete_unit,
    list_units_lookup,
    update_unit,
)
from app.auth import get_current_user, logout, require_auth
from app.components.form_dialog import create_form_dialog, edit_form_dialog

require_auth()


st.title("Units")

try:
    with st.spinner("Loading..."):
        units = list_units_lookup()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    st.stop()


# Handler functions
def handle_create_unit(data: dict) -> bool:
    unit_name = (data.get("unit") or "").strip()
    if not unit_name:
        st.error("Unit name is required.")
        return False
    try:
        create_unit(unit_name)
        st.success("Unit created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create unit: {e.message}")
        return False


def handle_update_unit(unit_id: int, data: dict) -> bool:
    unit_name = (data.get("unit") or "").strip()
    if not unit_name:
        st.error("Unit name is required.")
        return False
    try:
        update_unit(unit_id, unit_name)
        st.success("Unit updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update unit: {e.message}")
        return False


def handle_delete_unit(unit_id: int) -> None:
    try:
        delete_unit(unit_id)
        st.success("Unit deleted successfully!")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete unit: {e.message}")


_FORM_FIELDS = [
    {"name": "unit", "type": "text", "required": True},
]

# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=_FORM_FIELDS,
            on_submit=lambda data: handle_create_unit(data),
            title="Create New Unit",
        )

# Store selected row
if "selected_unit_id" not in st.session_state:
    st.session_state.selected_unit_id = None

# Display table
if units:
    df = pd.DataFrame(units)
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_unit_id = df.iloc[row_idx]["unit_id"]
        selected_item = units[row_idx]
    else:
        selected_item = None
        st.session_state.selected_unit_id = None
else:
    st.info("No units found. Click 'New' to create one.")
    selected_item = None

with col2:
    if st.button("✏️ Edit", disabled=selected_item is None):
        if selected_item:
            edit_form_dialog(
                item_data=selected_item,
                fields=_FORM_FIELDS,
                on_submit=lambda data: handle_update_unit(
                    selected_item["unit_id"], data
                ),
                title=f"Edit Unit: {selected_item.get('unit', '')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_item is None, type="secondary"):
        if selected_item:
            handle_delete_unit(selected_item["unit_id"])
