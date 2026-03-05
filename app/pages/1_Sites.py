"""Sites CRUD page."""
from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from app.api_client import APIError, create_site, delete_site, list_sites, update_site
from app.auth import get_current_user, logout, require_auth
from app.components.crud_table import crud_data_editor

require_auth()

with st.sidebar:
    user = get_current_user()
    if user:
        st.write(f"Logged in as: **{user['name']}**")
    if st.button("Sign out"):
        logout()

st.title("Sites")

column_config = {
    "id": st.column_config.NumberColumn("ID", disabled=True),
    "name": st.column_config.TextColumn("Name", required=True),
    "type": st.column_config.TextColumn("Type"),
    "description": st.column_config.TextColumn("Description"),
    "lat_wgs84": st.column_config.NumberColumn("Latitude"),
    "long_wgs84": st.column_config.NumberColumn("Longitude"),
    "city": st.column_config.TextColumn("City"),
    "province": st.column_config.TextColumn("Province"),
    "country": st.column_config.TextColumn("Country"),
}

try:
    with st.spinner("Loading sites..."):
        items = list_sites()

    added, changed, deleted_ids = crud_data_editor(items, column_config, id_field="id")

    if added or changed or deleted_ids:
        has_error = False

        for row in added:
            try:
                create_site(row)
            except APIError as e:
                st.error(f"Failed to create site: {e.message}")
                has_error = True

        for row in changed:
            try:
                update_site(int(row["id"]), row)
            except APIError as e:
                st.error(f"Failed to update site {row.get('id')}: {e.message}")
                has_error = True

        for site_id in deleted_ids:
            try:
                delete_site(site_id)
            except APIError as e:
                st.error(f"Failed to delete site {site_id}: {e.message}")
                has_error = True

        if not has_error:
            st.rerun()

except APIError as e:
    st.error(f"Cannot load sites: {e.message}")
