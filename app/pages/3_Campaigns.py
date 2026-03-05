"""Campaigns CRUD page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from app.api_client import (
    APIError,
    create_campaign,
    delete_campaign,
    list_campaigns,
    list_sites,
    update_campaign,
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

st.title("Campaigns")

column_config = {
    "campaign_id": st.column_config.NumberColumn("ID", disabled=True),
    "name": st.column_config.TextColumn("Name", required=True),
    "campaign_type_id": st.column_config.NumberColumn("Type ID", required=True),
    "campaign_type_name": st.column_config.TextColumn("Type Name", disabled=True),
    "site_id": st.column_config.NumberColumn("Site ID", required=True),
    "site_name": st.column_config.TextColumn("Site Name", disabled=True),
    "description": st.column_config.TextColumn("Description"),
    "start_date": st.column_config.TextColumn("Start Date"),
    "end_date": st.column_config.TextColumn("End Date"),
}

try:
    # Load sites for filter dropdown
    sites_response = list_sites()
    sites = (
        sites_response.get("items", [])
        if isinstance(sites_response, dict)
        else sites_response
    )
    site_options = ["All"] + [s["name"] for s in sites]
    selected_site = st.selectbox("Filter by site", options=site_options, index=0)

    # Determine site_id filter
    site_id_filter = None
    if selected_site != "All":
        site_id_filter = next(
            (s["id"] for s in sites if s["name"] == selected_site), None
        )

    with st.spinner("Loading campaigns..."):
        response = list_campaigns()
        all_items = (
            response.get("items", []) if isinstance(response, dict) else response
        )
        # Client-side filtering by site
        items = [
            c
            for c in all_items
            if site_id_filter is None or c.get("site_id") == site_id_filter
        ]

    added, changed, deleted_ids = crud_data_editor(
        items, column_config, id_field="campaign_id"
    )

    if added or changed or deleted_ids:
        has_error = False

        for row in added:
            # Strip read-only fields before API call
            writable_row = {
                k: v
                for k, v in row.items()
                if k not in ("campaign_type_name", "site_name")
            }
            try:
                create_campaign(writable_row)
            except APIError as e:
                st.error(f"Failed to create campaign: {e.message}")
                has_error = True

        for row in changed:
            # Strip read-only fields before API call
            writable_row = {
                k: v
                for k, v in row.items()
                if k not in ("campaign_type_name", "site_name")
            }
            try:
                update_campaign(int(row["campaign_id"]), writable_row)
            except APIError as e:
                st.error(
                    f"Failed to update campaign {row.get('campaign_id')}: {e.message}"
                )
                has_error = True

        for campaign_id in deleted_ids:
            try:
                delete_campaign(campaign_id)
            except APIError as e:
                st.error(f"Failed to delete campaign {campaign_id}: {e.message}")
                has_error = True

        if not has_error:
            st.rerun()

except APIError as e:
    st.error(f"Cannot load campaigns: {e.message}")
