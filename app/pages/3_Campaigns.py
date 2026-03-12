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
    create_campaign_deployment,
    delete_campaign,
    delete_campaign_deployment,
    list_campaign_deployments,
    list_campaigns,
    list_campaign_types,
    list_equipment_lookup,
    list_sampling_points_lookup,
    list_sites_lookup,
    patch_campaign,
)
from app.auth import get_current_user, logout, require_auth
from app.components.form_dialog import create_form_dialog, edit_form_dialog


@st.dialog("Add Deployment")
def add_deployment_dialog(
    campaign_id: int,
    equipment_opts: list[dict],
    sp_opts: list[dict],
    deployed_equipment_ids: set[int],
):
    """Dialog for adding a new deployment to a campaign.

    Filters out equipment that is already deployed in this campaign.
    """
    st.write("Pair equipment with a sampling point for this campaign.")

    # Filter out already-deployed equipment
    available_equipment = [
        e for e in equipment_opts if e["equipment_id"] not in deployed_equipment_ids
    ]

    if not available_equipment:
        st.warning("All available equipment is already deployed for this campaign.")
        if st.button("Close"):
            st.rerun()
        return

    equipment_options = [
        {"id": e["equipment_id"], "label": e["identifier"]} for e in available_equipment
    ]
    sp_options = [
        {"id": sp["sampling_point_id"], "label": sp["label"]} for sp in sp_opts
    ]

    selected_equipment = st.selectbox(
        "Equipment *",
        options=[opt["label"] for opt in equipment_options],
        index=0 if equipment_options else None,
    )
    equipment_id = next(
        (opt["id"] for opt in equipment_options if opt["label"] == selected_equipment),
        None,
    )

    selected_sp = st.selectbox(
        "Sampling Point *",
        options=[opt["label"] for opt in sp_options],
        index=0 if sp_options else None,
    )
    sampling_point_id = next(
        (opt["id"] for opt in sp_options if opt["label"] == selected_sp),
        None,
    )

    role = st.text_input("Role (optional)")
    notes = st.text_area("Notes (optional)")

    if st.button("Add Deployment", type="primary"):
        if equipment_id is None or sampling_point_id is None:
            st.error("Please select both equipment and sampling point.")
            return
        try:
            create_campaign_deployment(
                campaign_id,
                {
                    "equipment_id": equipment_id,
                    "sampling_point_id": sampling_point_id,
                    "role": role if role else None,
                    "notes": notes if notes else None,
                },
            )
            st.success("Deployment created successfully!")
            st.rerun()
        except APIError as e:
            if e.status_code == 400:
                if "already deployed" in e.message.lower():
                    st.error("This equipment is already deployed in this campaign.")
                else:
                    st.error(
                        "Campaign must have a start date before creating deployments"
                    )
            else:
                st.error(f"Failed to create deployment: {e.message}")


require_auth()


st.title("Campaigns")

# Load campaigns, sites, campaign types, equipment, and sampling points
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
        equipment_lookup = list_equipment_lookup()
        sampling_points_lookup = list_sampling_points_lookup()
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


# Deployments panel (shown when a campaign is selected)
if selected_campaign is not None:
    st.divider()
    with st.expander("Deployments", expanded=True):
        st.subheader(f"Deployments for: {selected_campaign.get('name', '')}")

        selected_campaign_id = selected_campaign["campaign_id"]

        # Load deployments for this campaign
        try:
            deployments = list_campaign_deployments(selected_campaign_id)
        except APIError as e:
            st.error(f"Failed to load deployments: {e.message}")
            deployments = []

        # Show deployments table
        if deployments:
            deploy_df = pd.DataFrame(deployments)
            deploy_selection = st.dataframe(
                deploy_df,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                key="deploy_table",
            )
            selected_deploy_idx = None
            if deploy_selection and deploy_selection.get("selection", {}).get("rows"):
                selected_deploy_idx = deploy_selection["selection"]["rows"][0]
        else:
            st.info("No deployments yet.")
            deploy_df = pd.DataFrame()
            selected_deploy_idx = None

        # Add Deployment button
        col_add, col_remove = st.columns([1, 1])
        with col_add:
            if st.button("➕ Add Deployment", type="primary"):
                deployed_ids = {d["equipment_id"] for d in deployments}
                add_deployment_dialog(
                    selected_campaign_id,
                    equipment_lookup,
                    sampling_points_lookup,
                    deployed_ids,
                )

        # Remove Deployment button
        with col_remove:
            can_remove = selected_deploy_idx is not None and not deploy_df.empty
            if st.button(
                "🗑️ Remove Deployment", disabled=not can_remove, type="secondary"
            ):
                if selected_deploy_idx is not None:
                    deploy_row = deploy_df.iloc[selected_deploy_idx]
                    equipment_id = int(deploy_row["equipment_id"])
                    sampling_point_id = (
                        int(deploy_row["sampling_point_id"])
                        if pd.notna(deploy_row["sampling_point_id"])
                        else None
                    )
                    if sampling_point_id is None:
                        st.warning(
                            "Cannot remove deployment: missing sampling point ID"
                        )
                    else:
                        confirm_msg = f"Remove deployment of **{deploy_row.get('equipment_identifier', 'Unknown')}** at **{deploy_row.get('sampling_point_name', 'Unknown')}**?"
                        if st.checkbox(confirm_msg, key="confirm_remove"):
                            try:
                                delete_campaign_deployment(
                                    selected_campaign_id,
                                    {
                                        "equipment_id": equipment_id,
                                        "sampling_point_id": sampling_point_id,
                                    },
                                )
                                st.success("Deployment removed successfully!")
                                st.rerun()
                            except APIError as e:
                                st.error(f"Failed to remove deployment: {e.message}")
