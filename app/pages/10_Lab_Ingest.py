"""Lab Analysis Ingest page for recording laboratory analysis results."""

from __future__ import annotations

import sys
from datetime import datetime, time
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app.api_client import (
    APIError,
    create_sample,
    ingest_lab,
    list_campaigns_lookup,
    list_laboratories_lookup,
    list_parameters_lookup,
    list_procedures_lookup,
    list_samples_lookup,
    list_sampling_points_lookup,
    list_units_lookup,
)
from app.auth import get_current_user, logout, require_auth

require_auth()

with st.sidebar:
    user = get_current_user()
    if user:
        st.write(f"Logged in as: **{user['name']}**")
    if st.button("Sign out"):
        logout()

st.title("Lab Analysis Ingest")
st.markdown(
    "Record the results of a laboratory analysis. Create a new sample or "
    "select an existing one, then enter measured values per parameter."
)

# Initialize session state
if "lab_rows" not in st.session_state:
    st.session_state["lab_rows"] = []
if "created_sample_id" not in st.session_state:
    st.session_state["created_sample_id"] = None

# Load lookup data
try:
    with st.spinner("Loading reference data..."):
        samples_lookup = list_samples_lookup()
        sampling_points_lookup = list_sampling_points_lookup()
        campaigns_lookup = list_campaigns_lookup()
        laboratories_lookup = list_laboratories_lookup()
        procedures_lookup = list_procedures_lookup()
        parameters_lookup = list_parameters_lookup()
        units_lookup = list_units_lookup()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

# Sample section
with st.container(border=True):
    st.subheader("Sample")

    sample_mode = st.radio(
        "Sample",
        ["Use existing sample", "Create new sample"],
        horizontal=True,
        label_visibility="collapsed",
    )

    sample_id = None

    if sample_mode == "Use existing sample":
        # Clear any created sample ID when switching modes
        st.session_state["created_sample_id"] = None

        sample_options = [
            {"id": s["sample_id"], "label": s["label"]} for s in samples_lookup
        ]
        sample_options.insert(0, {"id": None, "label": "— none —"})
        sample_labels = [opt["label"] for opt in sample_options]

        selected_sample_label = st.selectbox(
            "Select sample",
            options=sample_labels,
            index=0,
        )
        sample_id = next(
            (
                opt["id"]
                for opt in sample_options
                if opt["label"] == selected_sample_label
            ),
            None,
        )
    else:
        # "Create new sample" mode
        col1, col2 = st.columns(2)

        with col1:
            sp_options = [
                {"id": sp["sampling_point_id"], "label": sp["label"]}
                for sp in sampling_points_lookup
            ]
            sp_labels = [opt["label"] for opt in sp_options]
            selected_sp_label = st.selectbox(
                "Sampling point *",
                options=sp_labels,
                index=None,
                placeholder="Select sampling point...",
            )
            sampling_point_id = next(
                (opt["id"] for opt in sp_options if opt["label"] == selected_sp_label),
                None,
            )

        with col2:
            camp_options = [{"id": None, "label": "— none —"}] + [
                {"id": c["campaign_id"], "label": c["name"]} for c in campaigns_lookup
            ]
            camp_labels = [opt["label"] for opt in camp_options]
            selected_camp_label = st.selectbox(
                "Campaign (optional)",
                options=camp_labels,
                index=0,
            )
            campaign_id = next(
                (
                    opt["id"]
                    for opt in camp_options
                    if opt["label"] == selected_camp_label
                ),
                None,
            )

        col3, col4 = st.columns(2)

        with col3:
            start_date = st.date_input("Start date *", value=datetime.now())
            start_time = st.time_input("Start time *", value=time(12, 0))

        with col4:
            end_date = st.date_input("End date (optional)", value=None)
            end_time = st.time_input("End time (optional)", value=None)

        description = st.text_area("Description (optional)", max_chars=500)
        sampled_by_person_id = st.number_input(
            "Sampled by Person ID (optional)",
            min_value=1,
            step=1,
            value=None,
        )

        # Combine date and time
        sample_datetime_start = datetime.combine(start_date, start_time)
        sample_datetime_end = None
        if end_date and end_time:
            sample_datetime_end = datetime.combine(end_date, end_time)

        if st.button("Create Sample", type="secondary"):
            if sampling_point_id is None:
                st.error("Sampling point is required.")
            else:
                payload = {
                    "sampling_point_id": sampling_point_id,
                    "campaign_id": campaign_id,
                    "sample_datetime_start": sample_datetime_start.isoformat(),
                    "sample_datetime_end": sample_datetime_end.isoformat()
                    if sample_datetime_end
                    else None,
                    "description": description if description else None,
                    "sampled_by_person_id": sampled_by_person_id,
                }
                try:
                    result = create_sample(payload)
                    st.session_state["created_sample_id"] = result["sample_id"]
                    st.success(f"Sample {result['sample_id']} created successfully!")
                except APIError as e:
                    st.error(f"Failed to create sample: {e.message}")

        # Use created sample ID if available
        if st.session_state["created_sample_id"]:
            sample_id = st.session_state["created_sample_id"]
            st.info(f"Using created sample: ID {sample_id}")

# Analysis metadata section
with st.container(border=True):
    st.subheader("Analysis Metadata")

    col1, col2, col3 = st.columns(3)

    with col1:
        lab_options = [{"id": None, "label": "— none —"}] + [
            {"id": lab["laboratory_id"], "label": lab["name"]}
            for lab in laboratories_lookup
        ]
        lab_labels = [opt["label"] for opt in lab_options]
        selected_lab_label = st.selectbox(
            "Laboratory",
            options=lab_labels,
            index=0,
        )
        laboratory_id = next(
            (opt["id"] for opt in lab_options if opt["label"] == selected_lab_label),
            None,
        )

    with col2:
        proc_options = [{"id": None, "label": "— none —"}] + [
            {"id": proc["procedure_id"], "label": proc["procedure_name"]}
            for proc in procedures_lookup
        ]
        proc_labels = [opt["label"] for opt in proc_options]
        selected_proc_label = st.selectbox(
            "Procedure",
            options=proc_labels,
            index=0,
        )
        procedure_id = next(
            (opt["id"] for opt in proc_options if opt["label"] == selected_proc_label),
            None,
        )

    with col3:
        analyst_person_id = st.number_input(
            "Analyst Person ID",
            min_value=1,
            step=1,
            value=None,
        )

    camp_options = [{"id": None, "label": "— none —"}] + [
        {"id": c["campaign_id"], "label": c["name"]} for c in campaigns_lookup
    ]
    camp_labels = [opt["label"] for opt in camp_options]
    selected_analysis_camp_label = st.selectbox(
        "Analysis Campaign (optional)",
        options=camp_labels,
        index=0,
        key="analysis_campaign",
    )
    analysis_campaign_id = next(
        (
            opt["id"]
            for opt in camp_options
            if opt["label"] == selected_analysis_camp_label
        ),
        None,
    )

    notes = st.text_area("Notes (optional)", max_chars=1000)

# Measurement values section
with st.container(border=True):
    st.subheader("Measured Values")
    st.caption(
        "Add one row per parameter measurement. Use 'Duplicate' to copy a row "
        "before changing its value — useful for replicates."
    )

    # Initialize with one empty row if not present
    default_row = {
        "parameter_id": None,
        "unit_id": None,
        "value": None,
        "replicate": 1,
        "quality_code": None,
    }
    if not st.session_state.get("lab_rows"):
        st.session_state["lab_rows"] = [default_row.copy()]

    # Build parameter and unit options for column config
    param_options = {p["parameter_id"]: p["parameter_name"] for p in parameters_lookup}
    unit_options = {u["unit_id"]: u["unit"] for u in units_lookup}

    # Display data editor
    edited_df = st.data_editor(
        pd.DataFrame(st.session_state["lab_rows"]),
        column_config={
            "parameter_id": st.column_config.SelectboxColumn(
                "Parameter",
                options=param_options,
                required=False,
            ),
            "unit_id": st.column_config.SelectboxColumn(
                "Unit",
                options=unit_options,
                required=False,
            ),
            "value": st.column_config.NumberColumn("Value", required=False),
            "replicate": st.column_config.NumberColumn(
                "Replicate",
                min_value=1,
                default=1,
                required=False,
            ),
            "quality_code": st.column_config.NumberColumn(
                "Quality Code",
                required=False,
            ),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="lab_data_editor",
    )

    # Sync back to session state
    if edited_df is not None:
        st.session_state["lab_rows"] = edited_df.to_dict("records")

    # Duplicate button
    col1, col2 = st.columns([1, 9])
    with col1:
        if st.button("Duplicate selected"):
            if st.session_state["lab_rows"]:
                last = st.session_state["lab_rows"][-1].copy()
                last["replicate"] = (last.get("replicate") or 1) + 1
                st.session_state["lab_rows"].append(last)
                st.rerun()

# Submit section
st.markdown("---")

valid_rows = [
    r
    for r in st.session_state.get("lab_rows", [])
    if r.get("parameter_id") is not None and r.get("value") is not None
]
submit_disabled = len(valid_rows) == 0

if st.button("Submit Lab Analysis", type="primary", disabled=submit_disabled):
    payload = {
        "sample_id": sample_id,
        "laboratory_id": laboratory_id,
        "analyst_person_id": analyst_person_id,
        "procedure_id": procedure_id,
        "campaign_id": analysis_campaign_id,
        "notes": notes if notes else None,
        "values": [
            {
                "parameter_id": r["parameter_id"],
                "unit_id": r["unit_id"],
                "value": r["value"],
                "replicate": r.get("replicate") or 1,
                "quality_code": r.get("quality_code"),
            }
            for r in valid_rows
        ],
    }
    try:
        with st.spinner("Submitting..."):
            result = ingest_lab(payload)
        st.success(
            f"Lab analysis {result['lab_analysis_id']} created with "
            f"{result['rows_written']} values."
        )
        # Reset for next entry
        st.session_state["lab_rows"] = [default_row.copy()]
        st.session_state["created_sample_id"] = None
        st.rerun()
    except APIError as e:
        st.error(f"Ingest failed: {e.message}")
