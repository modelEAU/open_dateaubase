"""Lab Analysis Ingest page — Scalar, Vector, Matrix, and Image tabs.

Uses the LabIngestRequest / LabImageIngestResponse API introduced in Wave D/F3.
"""

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
    ingest_lab_image,
    list_campaigns_lookup,
    list_laboratories_lookup,
    list_parameters_lookup,
    list_procedures_lookup,
    list_processing_kinds_lookup,
    list_samples_lookup,
    list_sampling_points_lookup,
    list_units_lookup,
)

st.title("Lab Analysis Ingest")
st.markdown(
    "Record laboratory analysis results. Choose the shape that matches your data "
    "(Scalar, Vector, Matrix, or Image), fill in the experiment details, and submit."
)

# ---------------------------------------------------------------------------
# Load lookups once
# ---------------------------------------------------------------------------

try:
    with st.spinner("Loading reference data..."):
        _samples = list_samples_lookup()
        _sp = list_sampling_points_lookup()
        _campaigns = list_campaigns_lookup()
        _labs = list_laboratories_lookup()
        _procedures = list_procedures_lookup()
        _parameters = list_parameters_lookup()
        _units = list_units_lookup()
        _processing_kinds = list_processing_kinds_lookup()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

# Reverse-lookup dicts (name → id)
_param_name_to_id: dict[str, int] = {p["parameter_name"]: p["parameter_id"] for p in _parameters}
_unit_name_to_id: dict[str, int] = {u["unit"]: u["unit_id"] for u in _units}
_sp_label_to_id: dict[str, int] = {s["label"]: s["sampling_point_id"] for s in _sp}

# ---------------------------------------------------------------------------
# Section A — Experiment header
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.subheader("Experiment")
    col1, col2 = st.columns(2)
    with col1:
        exp_name = st.text_input(
            "Experiment name *",
            placeholder="e.g. Run-2026-05-21-A",
            key="lab_exp_name",
        )
    with col2:
        camp_options = [{"id": None, "label": "— none —"}] + [
            {"id": c["campaign_id"], "label": c["name"]} for c in _campaigns
        ]
        selected_camp = st.selectbox(
            "Campaign (optional)",
            options=[o["label"] for o in camp_options],
            index=0,
            key="lab_exp_campaign",
        )
        exp_campaign_id = next((o["id"] for o in camp_options if o["label"] == selected_camp), None)

    col3, col4 = st.columns(2)
    with col3:
        exp_date = st.date_input("Experiment date *", value=datetime.now(), key="lab_exp_date")
    with col4:
        exp_time = st.time_input("Experiment time *", value=time(12, 0), key="lab_exp_time")
    exp_datetime = datetime.combine(exp_date, exp_time)

    exp_description = st.text_area("Description (optional)", max_chars=500, key="lab_exp_desc")
    exp_person_id = st.number_input(
        "Created by Person ID (optional)", min_value=1, step=1, value=None, key="lab_exp_person"
    )

# ---------------------------------------------------------------------------
# Section B — Sample
# ---------------------------------------------------------------------------

if "lab_created_sample_id" not in st.session_state:
    st.session_state["lab_created_sample_id"] = None

with st.container(border=True):
    st.subheader("Sample")
    sample_mode = st.radio(
        "Sample",
        ["Use existing sample", "Create new sample"],
        horizontal=True,
        label_visibility="collapsed",
        key="lab_sample_mode",
    )
    sample_id: int | None = None

    if sample_mode == "Use existing sample":
        st.session_state["lab_created_sample_id"] = None
        s_options = [{"id": None, "label": "— none —"}] + [
            {"id": s["sample_id"], "label": s["label"]} for s in _samples
        ]
        selected_s = st.selectbox(
            "Select sample",
            options=[o["label"] for o in s_options],
            index=0,
            key="lab_sample_select",
        )
        sample_id = next((o["id"] for o in s_options if o["label"] == selected_s), None)
    else:
        col1, col2 = st.columns(2)
        with col1:
            sp_labels = [s["label"] for s in _sp]
            sel_sp = st.selectbox(
                "Sampling point *",
                options=sp_labels,
                index=None,
                placeholder="Select sampling point...",
                key="lab_new_sample_sp",
            )
            new_sample_sp_id = _sp_label_to_id.get(sel_sp or "", None) if sel_sp else None
        with col2:
            camp_opts2 = [{"id": None, "label": "— none —"}] + [
                {"id": c["campaign_id"], "label": c["name"]} for c in _campaigns
            ]
            sel_camp2 = st.selectbox(
                "Campaign (optional)",
                options=[o["label"] for o in camp_opts2],
                index=0,
                key="lab_new_sample_camp",
            )
            new_sample_camp_id = next(
                (o["id"] for o in camp_opts2 if o["label"] == sel_camp2), None
            )

        col3, col4 = st.columns(2)
        with col3:
            ns_start_date = st.date_input("Start date *", value=datetime.now(), key="lab_ns_start_date")
            ns_start_time = st.time_input("Start time *", value=time(12, 0), key="lab_ns_start_time")
        with col4:
            ns_end_date = st.date_input("End date (optional)", value=None, key="lab_ns_end_date")
            ns_end_time = st.time_input("End time (optional)", value=None, key="lab_ns_end_time")

        ns_description = st.text_area("Description (optional)", max_chars=500, key="lab_ns_desc")
        ns_person_id = st.number_input(
            "Sampled by Person ID (optional)", min_value=1, step=1, value=None, key="lab_ns_person"
        )

        if st.button("Create Sample", type="secondary", key="lab_create_sample_btn"):
            if new_sample_sp_id is None:
                st.error("Sampling point is required.")
            else:
                ns_start = datetime.combine(ns_start_date, ns_start_time)
                ns_end = None
                if ns_end_date and ns_end_time:
                    ns_end = datetime.combine(ns_end_date, ns_end_time)
                try:
                    result = create_sample({
                        "sampling_point_id": new_sample_sp_id,
                        "campaign_id": new_sample_camp_id,
                        "sample_datetime_start": ns_start.isoformat(),
                        "sample_datetime_end": ns_end.isoformat() if ns_end else None,
                        "description": ns_description or None,
                        "sampled_by_person_id": ns_person_id,
                    })
                    st.session_state["lab_created_sample_id"] = result["sample_id"]
                    st.success(f"Sample {result['sample_id']} created.")
                except APIError as e:
                    st.error(f"Failed to create sample: {e.message}")

        if st.session_state["lab_created_sample_id"]:
            sample_id = st.session_state["lab_created_sample_id"]
            st.info(f"Using created sample: ID {sample_id}")

# ---------------------------------------------------------------------------
# Section C — Shared measurement defaults
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.subheader("Measurement defaults")
    st.caption("Applied to every measurement in this submission.")
    col1, col2, col3 = st.columns(3)
    with col1:
        lab_opts = [{"id": None, "label": "— none —"}] + [
            {"id": l["laboratory_id"], "label": l["name"]} for l in _labs
        ]
        sel_lab = st.selectbox(
            "Laboratory",
            options=[o["label"] for o in lab_opts],
            index=0,
            key="lab_shared_lab",
        )
        shared_lab_id = next((o["id"] for o in lab_opts if o["label"] == sel_lab), None)
    with col2:
        proc_opts = [{"id": None, "label": "— none —"}] + [
            {"id": p["procedure_id"], "label": p["procedure_name"]} for p in _procedures
        ]
        sel_proc = st.selectbox(
            "Procedure",
            options=[o["label"] for o in proc_opts],
            index=0,
            key="lab_shared_proc",
        )
        shared_proc_id = next((o["id"] for o in proc_opts if o["label"] == sel_proc), None)
    with col3:
        pk_opts = [{"id": p["processing_kind_id"], "label": p["name"]} for p in _processing_kinds]
        sel_pk = st.selectbox(
            "Processing kind",
            options=[o["label"] for o in pk_opts],
            index=0,
            key="lab_shared_pk",
        )
        shared_pk_id = next(
            (o["id"] for o in pk_opts if o["label"] == sel_pk),
            1,
        )
    shared_analyst_id = st.number_input(
        "Analyst Person ID (optional)", min_value=1, step=1, value=None, key="lab_shared_analyst"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_param_names = [p["parameter_name"] for p in _parameters]
_unit_names = [u["unit"] for u in _units]
_sp_labels = [s["label"] for s in _sp]

_default_row_scalar = {
    "parameter_name": None,
    "sampling_point_label": None,
    "unit_name": None,
    "series_name": "",
    "value": None,
    "replicate": 1,
    "quality_code_id": None,
    "notes": "",
}

_default_row_vector = {
    "parameter_name": None,
    "sampling_point_label": None,
    "unit_name": None,
    "series_name": "",
    "value": "",
    "replicate": 1,
    "quality_code_id": None,
    "notes": "",
}

_default_row_matrix = {
    "parameter_name": None,
    "sampling_point_label": None,
    "unit_name": None,
    "series_name": "",
    "value": "",
    "replicate": 1,
    "quality_code_id": None,
    "notes": "",
}


def _auto_series_name(param: str | None, sp: str | None) -> str:
    if param and sp:
        return f"{param}@{sp}"
    return ""


def _build_measurements(rows: list[dict], value_kind_id: int) -> tuple[list[dict], list[str]]:
    """Resolve names to IDs and build LabMeasurementItem dicts. Returns (measurements, errors)."""
    measurements: list[dict] = []
    errors: list[str] = []
    for i, row in enumerate(rows, start=1):
        param_name = row.get("parameter_name")
        sp_label = row.get("sampling_point_label")
        unit_name = row.get("unit_name")
        raw_value = row.get("value")

        if not param_name or raw_value is None or raw_value == "":
            continue  # skip empty rows

        param_id = _param_name_to_id.get(param_name)
        sp_id = _sp_label_to_id.get(sp_label or "")
        unit_id = _unit_name_to_id.get(unit_name or "")

        if param_id is None:
            errors.append(f"Row {i}: unknown parameter '{param_name}'")
            continue
        if sp_id is None:
            errors.append(f"Row {i}: unknown sampling point '{sp_label}'")
            continue
        if unit_id is None:
            errors.append(f"Row {i}: unknown unit '{unit_name}'")
            continue

        series = row.get("series_name") or _auto_series_name(param_name, sp_label)

        if value_kind_id == 1:
            try:
                parsed_value = float(raw_value)
            except (TypeError, ValueError):
                errors.append(f"Row {i}: cannot parse value '{raw_value}' as float")
                continue
        elif value_kind_id == 2:
            try:
                parsed_value = [float(x.strip()) for x in str(raw_value).split(",") if x.strip()]
                if not parsed_value:
                    raise ValueError("empty")
            except ValueError:
                errors.append(f"Row {i}: cannot parse '{raw_value}' as comma-separated floats")
                continue
        elif value_kind_id == 3:
            try:
                parsed_value = [
                    [float(x.strip()) for x in row_str.split(",") if x.strip()]
                    for row_str in str(raw_value).split(";")
                    if row_str.strip()
                ]
                if not parsed_value:
                    raise ValueError("empty")
            except ValueError:
                errors.append(
                    f"Row {i}: cannot parse '{raw_value}' as matrix "
                    "(format: '1,2;3,4' — semicolons separate rows, commas separate columns)"
                )
                continue
        else:
            parsed_value = None

        measurements.append({
            "parameter_id": param_id,
            "sampling_point_id": sp_id,
            "unit_id": unit_id,
            "value_kind_id": value_kind_id,
            "processing_kind_id": shared_pk_id,
            "series_name": series,
            "sample_id": sample_id,
            "value": parsed_value,
            "laboratory_id": shared_lab_id,
            "analyst_person_id": shared_analyst_id,
            "procedure_id": shared_proc_id,
            "replicate": int(row.get("replicate") or 1),
            "quality_code_id": row.get("quality_code_id"),
            "notes": row.get("notes") or None,
        })
    return measurements, errors


def _submit_lab(rows: list[dict], value_kind_id: int) -> None:
    """Validate, build payload, call ingest_lab, show result."""
    if not exp_name:
        st.error("Experiment name is required.")
        return
    if sample_id is None:
        st.error("A sample must be selected or created before submitting.")
        return

    measurements, errors = _build_measurements(rows, value_kind_id)
    if errors:
        for err in errors:
            st.error(err)
        return
    if not measurements:
        st.error("No valid measurement rows found. Fill in at least one row.")
        return

    payload = {
        "name": exp_name,
        "experiment_datetime": exp_datetime.isoformat(),
        "campaign_id": exp_campaign_id,
        "description": exp_description or None,
        "created_by_person_id": exp_person_id,
        "measurements": measurements,
    }
    try:
        with st.spinner("Submitting..."):
            result = ingest_lab(payload)
        st.success(
            f"✅ Experiment **{result['lab_experiment_id']}** created — "
            f"{result['rows_written']} observation(s) stored."
        )
    except APIError as e:
        st.error(f"Ingest failed: {e.message}")


# ---------------------------------------------------------------------------
# Section D — Measurement tabs
# ---------------------------------------------------------------------------

tab_scalar, tab_vector, tab_matrix, tab_image = st.tabs(["Scalar", "Vector", "Matrix", "Image"])

# ---- Scalar ---------------------------------------------------------------
with tab_scalar:
    st.markdown("One numeric value per measurement.")
    if "lab_scalar_rows" not in st.session_state:
        st.session_state["lab_scalar_rows"] = [_default_row_scalar.copy()]

    edited_scalar = st.data_editor(
        pd.DataFrame(st.session_state["lab_scalar_rows"]),
        column_config={
            "parameter_name": st.column_config.SelectboxColumn("Parameter *", options=_param_names),
            "sampling_point_label": st.column_config.SelectboxColumn("Sampling Point *", options=_sp_labels),
            "unit_name": st.column_config.SelectboxColumn("Unit *", options=_unit_names),
            "series_name": st.column_config.TextColumn("Series name (auto if blank)"),
            "value": st.column_config.NumberColumn("Value *"),
            "replicate": st.column_config.NumberColumn("Replicate", min_value=1, default=1),
            "quality_code_id": st.column_config.NumberColumn("Quality code"),
            "notes": st.column_config.TextColumn("Notes"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="lab_scalar_editor",
    )
    if edited_scalar is not None:
        st.session_state["lab_scalar_rows"] = edited_scalar.to_dict("records")

    col_dup, col_sub = st.columns([1, 9])
    with col_dup:
        if st.button("Duplicate last", key="lab_scalar_dup"):
            if st.session_state["lab_scalar_rows"]:
                last = st.session_state["lab_scalar_rows"][-1].copy()
                last["replicate"] = int(last.get("replicate") or 1) + 1
                st.session_state["lab_scalar_rows"].append(last)
                st.rerun()
    with col_sub:
        if st.button("Submit Scalar Experiment", type="primary", key="lab_scalar_submit"):
            _submit_lab(st.session_state["lab_scalar_rows"], value_kind_id=1)

# ---- Vector ---------------------------------------------------------------
with tab_vector:
    st.markdown(
        "One vector observation per row. Enter values as comma-separated floats, e.g. `1.2,3.4,5.6`."
    )
    if "lab_vector_rows" not in st.session_state:
        st.session_state["lab_vector_rows"] = [_default_row_vector.copy()]

    edited_vector = st.data_editor(
        pd.DataFrame(st.session_state["lab_vector_rows"]),
        column_config={
            "parameter_name": st.column_config.SelectboxColumn("Parameter *", options=_param_names),
            "sampling_point_label": st.column_config.SelectboxColumn("Sampling Point *", options=_sp_labels),
            "unit_name": st.column_config.SelectboxColumn("Unit *", options=_unit_names),
            "series_name": st.column_config.TextColumn("Series name (auto if blank)"),
            "value": st.column_config.TextColumn("Values * (comma-separated)"),
            "replicate": st.column_config.NumberColumn("Replicate", min_value=1, default=1),
            "quality_code_id": st.column_config.NumberColumn("Quality code"),
            "notes": st.column_config.TextColumn("Notes"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="lab_vector_editor",
    )
    if edited_vector is not None:
        st.session_state["lab_vector_rows"] = edited_vector.to_dict("records")

    col_dup, col_sub = st.columns([1, 9])
    with col_dup:
        if st.button("Duplicate last", key="lab_vector_dup"):
            if st.session_state["lab_vector_rows"]:
                last = st.session_state["lab_vector_rows"][-1].copy()
                last["replicate"] = int(last.get("replicate") or 1) + 1
                st.session_state["lab_vector_rows"].append(last)
                st.rerun()
    with col_sub:
        if st.button("Submit Vector Experiment", type="primary", key="lab_vector_submit"):
            _submit_lab(st.session_state["lab_vector_rows"], value_kind_id=2)

# ---- Matrix ---------------------------------------------------------------
with tab_matrix:
    st.markdown(
        "One 2D matrix observation per row. Format: rows separated by `;`, "
        "columns by `,` — e.g. `1,2;3,4` is a 2×2 matrix."
    )
    if "lab_matrix_rows" not in st.session_state:
        st.session_state["lab_matrix_rows"] = [_default_row_matrix.copy()]

    edited_matrix = st.data_editor(
        pd.DataFrame(st.session_state["lab_matrix_rows"]),
        column_config={
            "parameter_name": st.column_config.SelectboxColumn("Parameter *", options=_param_names),
            "sampling_point_label": st.column_config.SelectboxColumn("Sampling Point *", options=_sp_labels),
            "unit_name": st.column_config.SelectboxColumn("Unit *", options=_unit_names),
            "series_name": st.column_config.TextColumn("Series name (auto if blank)"),
            "value": st.column_config.TextColumn("Values * (rows=';', cols=',')"),
            "replicate": st.column_config.NumberColumn("Replicate", min_value=1, default=1),
            "quality_code_id": st.column_config.NumberColumn("Quality code"),
            "notes": st.column_config.TextColumn("Notes"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="lab_matrix_editor",
    )
    if edited_matrix is not None:
        st.session_state["lab_matrix_rows"] = edited_matrix.to_dict("records")

    col_dup, col_sub = st.columns([1, 9])
    with col_dup:
        if st.button("Duplicate last", key="lab_matrix_dup"):
            if st.session_state["lab_matrix_rows"]:
                last = st.session_state["lab_matrix_rows"][-1].copy()
                last["replicate"] = int(last.get("replicate") or 1) + 1
                st.session_state["lab_matrix_rows"].append(last)
                st.rerun()
    with col_sub:
        if st.button("Submit Matrix Experiment", type="primary", key="lab_matrix_submit"):
            _submit_lab(st.session_state["lab_matrix_rows"], value_kind_id=3)

# ---- Image ----------------------------------------------------------------
with tab_image:
    st.markdown(
        "Upload one or more images. Multiple files = replicates of the same measurement "
        "(each file gets its own LabAnalysis row with replicate index 1, 2, …)."
    )
    with st.container(border=True):
        st.subheader("Image Measurement Identity")
        col1, col2, col3 = st.columns(3)
        with col1:
            img_param = st.selectbox(
                "Parameter *",
                options=_param_names,
                index=None,
                placeholder="Select parameter...",
                key="lab_img_param",
            )
            img_param_id = _param_name_to_id.get(img_param or "")
        with col2:
            img_sp = st.selectbox(
                "Sampling point *",
                options=_sp_labels,
                index=None,
                placeholder="Select sampling point...",
                key="lab_img_sp",
            )
            img_sp_id = _sp_label_to_id.get(img_sp or "")
        with col3:
            img_unit = st.selectbox(
                "Unit *",
                options=_unit_names,
                index=None,
                placeholder="Select unit...",
                key="lab_img_unit",
            )
            img_unit_id = _unit_name_to_id.get(img_unit or "")

        auto_series = _auto_series_name(img_param, img_sp)
        img_series_name = st.text_input(
            "Series name",
            value=auto_series,
            placeholder=auto_series or "e.g. Turbidity@Inlet",
            key="lab_img_series",
        )
        img_quality_code = st.number_input(
            "Quality code (optional)", value=None, min_value=0, step=1, key="lab_img_qc"
        )
        img_notes = st.text_input("Notes (optional)", key="lab_img_notes")

    uploaded_images = st.file_uploader(
        "Select image file(s)",
        type=["jpg", "jpeg", "png", "tif", "tiff", "bmp"],
        accept_multiple_files=True,
        key="lab_img_upload",
    )

    if uploaded_images:
        st.caption(f"{len(uploaded_images)} file(s) selected — will be stored as replicate(s) 1…{len(uploaded_images)}.")
        cols = st.columns(min(len(uploaded_images), 4))
        for i, f in enumerate(uploaded_images):
            with cols[i % 4]:
                st.image(f, caption=f.name, width=120)

        img_has_required = all([
            exp_name,
            sample_id is not None,
            img_param_id,
            img_sp_id,
            img_unit_id,
            img_series_name,
        ])

        if st.button(
            "Upload Images",
            type="primary",
            key="lab_img_submit",
            disabled=not img_has_required,
        ):
            if not exp_name:
                st.error("Experiment name is required.")
            elif sample_id is None:
                st.error("A sample must be selected or created before submitting.")
            elif img_param_id is None or img_sp_id is None or img_unit_id is None:
                st.error("Parameter, sampling point, and unit are required.")
            else:
                image_files = [(f.name, f.read()) for f in uploaded_images]
                try:
                    with st.spinner("Uploading..."):
                        result = ingest_lab_image(
                            name=exp_name,
                            experiment_datetime=exp_datetime.isoformat(),
                            sample_id=sample_id,
                            parameter_id=img_param_id,
                            sampling_point_id=img_sp_id,
                            unit_id=img_unit_id,
                            series_name=img_series_name or auto_series,
                            image_files=image_files,
                            processing_kind_id=shared_pk_id,
                            campaign_id=exp_campaign_id,
                            description=exp_description or None,
                            created_by_person_id=exp_person_id,
                            laboratory_id=shared_lab_id,
                            analyst_person_id=shared_analyst_id,
                            procedure_id=shared_proc_id,
                            quality_code=img_quality_code,
                            notes=img_notes or None,
                        )
                    st.success(
                        f"✅ {result['rows_written']} image(s) stored. "
                        f"Experiment ID: {result['lab_experiment_id']}"
                    )
                    for path in result["storage_paths"]:
                        st.caption(f"Stored at: {path}")
                except APIError as e:
                    st.error(f"Upload failed: {e.message}")
    else:
        st.info("Select one or more image files above to upload.")
