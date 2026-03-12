"""Sites CRUD page with form-based editing."""

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
    create_site,
    delete_site,
    list_sites,
    patch_site,
)
from app.auth import get_current_user, logout, require_auth
from app.components.form_dialog import create_form_dialog, edit_form_dialog

require_auth()


st.title("Sites")

# Load sites
try:
    with st.spinner("Loading sites..."):
        sites_data = list_sites()
        sites = (
            sites_data.get("items", []) if isinstance(sites_data, dict) else sites_data
        )
except APIError as e:
    st.error(f"Cannot load sites: {e.message}")
    st.stop()

# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=[
                {"name": "name", "type": "text", "required": True},
                {"name": "type", "type": "text", "required": False},
                {"name": "description", "type": "textarea", "required": False},
                {"name": "lat_wgs84", "type": "number", "required": False},
                {"name": "long_wgs84", "type": "number", "required": False},
                {"name": "city", "type": "text", "required": False},
                {"name": "province", "type": "text", "required": False},
                {"name": "country", "type": "text", "required": False},
            ],
            on_submit=lambda data: handle_create_site(data),
            title="Create New Site",
        )

# Store selected row in session state
if "selected_site_id" not in st.session_state:
    st.session_state.selected_site_id = None

# Display table with selection
if sites:
    df = pd.DataFrame(sites)

    # Create a selection column
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_site_id = df.iloc[row_idx]["id"]
        selected_site = sites[row_idx]
    else:
        selected_site = None
        st.session_state.selected_site_id = None
else:
    st.info("No sites found. Click 'New' to create one.")
    selected_site = None

with col2:
    if st.button("✏️ Edit", disabled=selected_site is None):
        if selected_site:
            edit_form_dialog(
                item_data=selected_site,
                fields=[
                    {"name": "name", "type": "text", "required": True},
                    {"name": "type", "type": "text", "required": False},
                    {"name": "description", "type": "textarea", "required": False},
                    {"name": "lat_wgs84", "type": "number", "required": False},
                    {"name": "long_wgs84", "type": "number", "required": False},
                    {"name": "city", "type": "text", "required": False},
                    {"name": "province", "type": "text", "required": False},
                    {"name": "country", "type": "text", "required": False},
                ],
                on_submit=lambda data: handle_patch_site(selected_site["id"], data),
                title=f"Edit Site: {selected_site.get('name', '')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_site is None, type="secondary"):
        if selected_site:
            handle_delete_site(selected_site["id"])


# Handler functions
def handle_create_site(data: dict) -> bool:
    try:
        create_site(data)
        st.success("Site created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create site: {e.message}")
        return False


def handle_patch_site(site_id: int, data: dict) -> bool:
    try:
        patch_site(site_id, data)
        st.success("Site updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update site: {e.message}")
        return False


def handle_delete_site(site_id: int) -> None:
    try:
        delete_site(site_id)
        st.success("Site deleted successfully!")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete site: {e.message}")
