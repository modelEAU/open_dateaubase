"""Campaigns CRUD page with form-based editing."""

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
    create_campaign,
    delete_campaign,
    list_campaigns,
    list_campaign_types,
    list_sites_lookup,
    patch_campaign,
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

st.title("Campaigns")

# Load campaigns, sites, and campaign types
try:
    with st.spinner("Loading..."):
        campaigns_data = list_campaigns()
        campaigns = (
            campaigns_data.get("items", [])
            if isinstance(campaigns_data, dict)
            else campaigns_data
        )
        sites = list_sites_lookup()
        campaign_types = list_campaign_types()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    st.stop()

# Prepare dropdown options
site_options = [{"id": s["site_id"], "label": s["name"]} for s in sites]
type_options = [
    {"id": t["campaign_type_id"], "label": t["name"]} for t in campaign_types
]

# Site filter for list view
site_filter_col, _ = st.columns([2, 8])
with site_filter_col:
    filter_options = [{"id": None, "label": "All Sites"}] + site_options
    selected_site_filter = st.selectbox(
        "Filter by site",
        options=[opt["label"] for opt in filter_options],
        index=0,
    )
    site_id_filter = next(
        (opt["id"] for opt in filter_options if opt["label"] == selected_site_filter),
        None,
    )

# Filter campaigns
if site_id_filter is not None:
    filtered_campaigns = [c for c in campaigns if c.get("site_id") == site_id_filter]
else:
    filtered_campaigns = campaigns


# Handler functions
def handle_create_campaign(data: dict) -> bool:
    try:
        create_campaign(data)
        st.success("Campaign created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create campaign: {e.message}")
        return False


def handle_patch_campaign(campaign_id: int, data: dict) -> bool:
    try:
        patch_campaign(campaign_id, data)
        st.success("Campaign updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update campaign: {e.message}")
        return False


def handle_delete_campaign(campaign_id: int) -> None:
    try:
        delete_campaign(campaign_id)
        st.success("Campaign deleted successfully!")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete campaign: {e.message}")


# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=[
                {"name": "name", "type": "text", "required": True},
                {
                    "name": "campaign_type_id",
                    "type": "select",
                    "required": True,
                    "options": type_options,
                },
                {
                    "name": "site_id",
                    "type": "select",
                    "required": True,
                    "options": site_options,
                },
                {"name": "description", "type": "textarea", "required": False},
                {"name": "start_date", "type": "date", "required": False},
                {"name": "end_date", "type": "date", "required": False},
            ],
            on_submit=lambda data: handle_create_campaign(data),
            title="Create New Campaign",
        )

# Store selected row
if "selected_campaign_id" not in st.session_state:
    st.session_state.selected_campaign_id = None

# Display table
if filtered_campaigns:
    df = pd.DataFrame(filtered_campaigns)
    selected_indices = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_campaign_id = df.iloc[row_idx]["campaign_id"]
        selected_campaign = filtered_campaigns[row_idx]
    else:
        selected_campaign = None
        st.session_state.selected_campaign_id = None
else:
    st.info("No campaigns found. Click 'New' to create one.")
    selected_campaign = None

with col2:
    if st.button("✏️ Edit", disabled=selected_campaign is None):
        if selected_campaign:
            edit_form_dialog(
                item_data=selected_campaign,
                fields=[
                    {"name": "name", "type": "text", "required": True},
                    {
                        "name": "campaign_type_id",
                        "type": "select",
                        "required": True,
                        "options": type_options,
                    },
                    {
                        "name": "site_id",
                        "type": "select",
                        "required": True,
                        "options": site_options,
                    },
                    {"name": "description", "type": "textarea", "required": False},
                    {"name": "start_date", "type": "date", "required": False},
                    {"name": "end_date", "type": "date", "required": False},
                ],
                on_submit=lambda data: handle_patch_campaign(
                    selected_campaign["campaign_id"], data
                ),
                title=f"Edit Campaign: {selected_campaign.get('name', '')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_campaign is None, type="secondary"):
        if selected_campaign:
            handle_delete_campaign(selected_campaign["campaign_id"])
