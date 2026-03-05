"""Equipment CRUD page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from app.api_client import (
    APIError,
    create_equipment,
    delete_equipment,
    list_equipment,
    update_equipment,
)
from app.auth import get_current_user, logout, require_auth
from app.components.crud_table import crud_data_editor

require_auth()

with st.sidebar:
    user = get_current_user()
    if user:
        st.write(f"Logged in as: **{user['name']}**")
    if st.button("Sign out"):
        logout()

st.title("Equipment")

column_config = {
    "equipment_id": st.column_config.NumberColumn("ID", disabled=True),
    "identifier": st.column_config.TextColumn("Identifier"),
    "serial_number": st.column_config.TextColumn("Serial Number"),
    "model_id": st.column_config.NumberColumn("Model ID"),
    "model_name": st.column_config.TextColumn("Model Name", disabled=True),
    "manufacturer": st.column_config.TextColumn("Manufacturer", disabled=True),
    "owner": st.column_config.TextColumn("Owner"),
    "purchase_date": st.column_config.TextColumn("Purchase Date"),
}

try:
    with st.spinner("Loading equipment..."):
        response = list_equipment()
        items = response.get("items", []) if isinstance(response, dict) else response

    added, changed, deleted_ids = crud_data_editor(
        items, column_config, id_field="equipment_id"
    )

    if added or changed or deleted_ids:
        has_error = False

        for row in added:
            # Strip read-only fields before API call
            writable_row = {
                k: v for k, v in row.items() if k not in ("model_name", "manufacturer")
            }
            try:
                create_equipment(writable_row)
            except APIError as e:
                st.error(f"Failed to create equipment: {e.message}")
                has_error = True

        for row in changed:
            # Strip read-only fields before API call
            writable_row = {
                k: v for k, v in row.items() if k not in ("model_name", "manufacturer")
            }
            try:
                update_equipment(int(row["equipment_id"]), writable_row)
            except APIError as e:
                st.error(
                    f"Failed to update equipment {row.get('equipment_id')}: {e.message}"
                )
                has_error = True

        for equipment_id in deleted_ids:
            try:
                delete_equipment(equipment_id)
            except APIError as e:
                st.error(f"Failed to delete equipment {equipment_id}: {e.message}")
                has_error = True

        if not has_error:
            st.rerun()

except APIError as e:
    st.error(f"Cannot load equipment: {e.message}")
