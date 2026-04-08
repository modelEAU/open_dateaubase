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
from app.components.crud_form import render_form_field
from app.components.location_picker import render_location_picker, _clear_location_state

require_auth()

with st.sidebar:
    user = get_current_user()
    if user:
        st.write(f"Logged in as: **{user['name']}**")
    if st.button("Sign out"):
        logout()

# --- Session state init ---
if "sites_mode" not in st.session_state:
    st.session_state.sites_mode = None  # None | "create" | "edit"
if "sites_edit_target" not in st.session_state:
    st.session_state.sites_edit_target = None


def _go_table() -> None:
    _clear_location_state("create_site")
    _clear_location_state("edit_site")
    st.session_state.sites_mode = None
    st.session_state.sites_edit_target = None
    st.rerun()


# ── CREATE FORM ──────────────────────────────────────────────────────────────

def _render_create_form() -> None:
    st.title("New Site")
    if st.button("← Back to sites"):
        _go_table()
        return

    name = render_form_field("name", "text", required=True)
    site_type = render_form_field("type", "text", required=False)
    description = render_form_field("description", "textarea", required=False)

    st.divider()
    st.subheader("Location")
    location = render_location_picker(key_prefix="create_site")

    st.divider()
    if st.button("Create site", type="primary"):
        if not name:
            st.error("Name is required.")
        else:
            try:
                create_site({
                    "name": name,
                    "type": site_type or None,
                    "description": description or None,
                    **location,
                })
                st.success("Site created!")
                _go_table()
            except APIError as e:
                st.error(f"Failed to create site: {e.message}")


# ── EDIT FORM ─────────────────────────────────────────────────────────────────

def _render_edit_form(site: dict) -> None:
    st.title(f"Edit Site: {site.get('name', '')}")
    if st.button("← Back to sites"):
        _go_table()
        return

    name = render_form_field("name", "text", value=site.get("name"), required=True)
    site_type = render_form_field("type", "text", value=site.get("type"), required=False)
    description = render_form_field("description", "textarea", value=site.get("description"), required=False)

    st.divider()
    st.subheader("Location")
    location = render_location_picker(
        lat=site.get("lat_wgs84"),
        lng=site.get("long_wgs84"),
        city=site.get("city"),
        province=site.get("province"),
        country=site.get("country"),
        key_prefix="edit_site",
    )

    st.divider()
    if st.button("Save changes", type="primary"):
        if not name:
            st.error("Name is required.")
        else:
            try:
                patch_site(site["id"], {
                    "name": name,
                    "type": site_type or None,
                    "description": description or None,
                    **location,
                })
                st.success("Site updated!")
                _go_table()
            except APIError as e:
                st.error(f"Failed to update site: {e.message}")


# ── TABLE VIEW ────────────────────────────────────────────────────────────────

def _render_table() -> None:
    st.title("Sites")

    try:
        with st.spinner("Loading sites..."):
            sites_data = list_sites()
            sites = (
                sites_data.get("items", []) if isinstance(sites_data, dict) else sites_data
            )
    except APIError as e:
        st.error(f"Cannot load sites: {e.message}")
        st.stop()

    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("➕ New", type="primary"):
            st.session_state.sites_mode = "create"
            st.rerun()

    if "selected_site_id" not in st.session_state:
        st.session_state.selected_site_id = None

    selected_site = None
    if sites:
        df = pd.DataFrame(sites)
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

    with col2:
        if st.button("✏️ Edit", disabled=selected_site is None):
            if selected_site:
                st.session_state.sites_mode = "edit"
                st.session_state.sites_edit_target = selected_site
                st.rerun()

    with col3:
        if st.button("🗑️ Delete", disabled=selected_site is None, type="secondary"):
            if selected_site:
                try:
                    delete_site(selected_site["id"])
                    st.success("Site deleted!")
                    st.rerun()
                except APIError as e:
                    st.error(f"Failed to delete site: {e.message}")


# ── ROUTER ────────────────────────────────────────────────────────────────────

if st.session_state.sites_mode == "create":
    _render_create_form()
elif st.session_state.sites_mode == "edit" and st.session_state.sites_edit_target:
    _render_edit_form(st.session_state.sites_edit_target)
else:
    _render_table()
