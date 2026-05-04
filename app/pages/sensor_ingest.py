"""Sensor Data Ingest page with Scalar, Vector, and Matrix tabs."""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import pandas as pd

from app.api_client import (
    APIError,
    ingest_sensor,
    ingest_sensor_image,
    ingest_sensor_matrix,
    ingest_sensor_tagless,
    ingest_sensor_vector,
    list_binning_axes_lookup,
    list_data_provenance_lookup,
    list_equipment_lookup,
    list_parameters_lookup,
    list_processing_kinds_lookup,
    list_units_lookup,
)


st.title("Sensor Data Ingest")
st.markdown(
    "Upload or paste timestamped sensor measurements. The channel is "
    "created automatically if it does not yet exist."
)

# Initialize session state for parsed data (per-tab)
if "scalar_parsed_rows" not in st.session_state:
    st.session_state.scalar_parsed_rows = []
if "scalar_parse_errors" not in st.session_state:
    st.session_state.scalar_parse_errors = []
if "vector_parsed" not in st.session_state:
    st.session_state.vector_parsed = []
if "vector_parse_errors" not in st.session_state:
    st.session_state.vector_parse_errors = []
if "matrix_parsed" not in st.session_state:
    st.session_state.matrix_parsed = []
if "matrix_parse_errors" not in st.session_state:
    st.session_state.matrix_parse_errors = []

# Create tabs
tab_scalar, tab_vector, tab_matrix, tab_image = st.tabs(
    ["Scalar", "Vector", "Matrix", "Image"]
)

# =============================================================================
# SCALAR TAB
# =============================================================================
with tab_scalar:
    st.subheader("Scalar Sensor Ingest")
    st.markdown(
        "Upload or paste timestamped scalar measurements (one value per timestamp)."
    )

    # Load lookup data for dropdowns
    try:
        with st.spinner("Loading lookup data..."):
            equipment_lookup = list_equipment_lookup()
            parameters_lookup = list_parameters_lookup()
            units_lookup = list_units_lookup()
            provenance_lookup = list_data_provenance_lookup()
            processing_degrees_lookup = list_processing_kinds_lookup()
    except APIError as e:
        st.error(f"Cannot load lookup data: {e.message}")
        st.stop()

    # Get Sensor provenance name from database (ID=1 is Sensor)
    sensor_provenance = next(
        (p for p in provenance_lookup if p["data_provenance_kind_id"] == 1),
        {"name": "Sensor"},
    )
    sensor_provenance_name = sensor_provenance["name"]

    # Channel Identification Section
    with st.container(border=True):
        st.subheader("Channel Identity")

        scalar_ingest_mode = st.radio(
            "Ingest mode",
            ["Tagless (direct-connect)", "Tagged (SCADA)"],
            horizontal=True,
            key="scalar_ingest_mode",
        )

        if scalar_ingest_mode == "Tagless (direct-connect)":
            col_das, col_equip = st.columns(2)
            with col_das:
                scalar_das_name = st.text_input(
                    "DAS name",
                    value="DirectConnect",
                    key="scalar_das_name_tagless",
                )
            with col_equip:
                equipment_options = [
                    {"id": e["equipment_id"], "label": e["identifier"]}
                    for e in equipment_lookup
                ]
                equipment_labels = [opt["label"] for opt in equipment_options]
                selected_equipment_label = st.selectbox(
                    "Equipment",
                    options=equipment_labels,
                    index=None,
                    placeholder="Select equipment...",
                    key="scalar_equipment_tagless",
                    help="Physical instrument this channel is directly connected to",
                )
            scalar_equipment_name = selected_equipment_label  # identifier is the name
            scalar_tag = None
            scalar_channel_role = None
        else:
            col_das, col_tag, col_spt = st.columns(3)
            with col_das:
                scalar_das_name = st.text_input(
                    "DAS name",
                    value="",
                    placeholder="e.g. SCADA_OPC",
                    key="scalar_das_name_tagged",
                )
            with col_tag:
                scalar_tag = st.text_input(
                    "Tag",
                    value="",
                    placeholder="e.g. PLC1.pH_sensor",
                    key="scalar_tag",
                )
            with col_spt:
                scalar_channel_role = st.selectbox(
                    "Channel role",
                    options=["value", "status", "alarm", "uncertainty"],
                    index=0,
                    key="scalar_channel_role",
                )
            scalar_equipment_name = None

        col2, col3 = st.columns(2)

        with col2:
            parameter_options = [
                {"id": p["parameter_id"], "label": p["parameter_name"]}
                for p in parameters_lookup
            ]
            parameter_labels = [opt["label"] for opt in parameter_options]
            selected_parameter_label = st.selectbox(
                "Parameter",
                options=parameter_labels,
                index=None,
                placeholder="Select parameter...",
                key="scalar_parameter",
                help="Measured analyte or parameter (e.g. TSS, pH)",
            )
            scalar_parameter_name = selected_parameter_label

        with col3:
            unit_options = [
                {"id": u["unit_id"], "label": u["unit"]} for u in units_lookup
            ]
            unit_labels = [opt["label"] for opt in unit_options]
            selected_unit_label = st.selectbox(
                "Unit",
                options=unit_labels,
                index=None,
                placeholder="Select unit...",
                key="scalar_unit",
                help="Unit of measurement for values stored in this channel (e.g. mg/L, NTU)",
            )
            scalar_unit_name = selected_unit_label

        col4, col5 = st.columns(2)

        with col4:
            st.markdown(f"**Data Provenance:** {sensor_provenance_name}")
            scalar_data_provenance_id = 1

        with col5:
            processing_options = [
                {"id": d["processing_kind_id"], "label": d["name"]}
                for d in processing_degrees_lookup
            ]
            processing_labels = [opt["label"] for opt in processing_options]
            selected_processing_label = st.selectbox(
                "Processing Degree",
                options=processing_labels,
                index=0,
                help="Auto-created if new channel",
                key="scalar_processing",
            )
            scalar_processing_kind_id = next(
                (
                    opt["id"]
                    for opt in processing_options
                    if opt["label"] == selected_processing_label
                ),
                None,
            )

    # Data Input Section
    with st.container(border=True):
        st.subheader("Data")

        scalar_input_mode = st.radio(
            "Input method",
            ["Paste CSV", "Upload CSV file"],
            horizontal=True,
            key="scalar_input_mode",
        )

        scalar_raw_csv = ""

        if scalar_input_mode == "Paste CSV":
            scalar_raw_csv = st.text_area(
                "Paste CSV data",
                placeholder="""timestamp,value,quality_code
2024-01-15T08:00:00,7.42,
2024-01-15T08:15:00,7.45,
2024-01-15T08:30:00,7.51,""",
                height=200,
                key="scalar_text_area",
            )
            st.caption(
                "ISO timestamps (YYYY-MM-DDTHH:MM:SS). quality_code column optional."
            )
        else:
            scalar_uploaded_file = st.file_uploader(
                "Choose CSV file", type=["csv"], key="scalar_file_uploader"
            )
            if scalar_uploaded_file is not None:
                scalar_raw_csv = scalar_uploaded_file.read().decode("utf-8")

    def parse_scalar_csv(csv_text: str) -> tuple[list[dict], list[dict]]:
        """Parse scalar CSV data into valid rows and errors."""
        valid_rows = []
        errors = []

        if not csv_text.strip():
            return valid_rows, errors

        csv_text = csv_text.lstrip("\ufeff")

        try:
            reader = csv.reader(StringIO(csv_text))
            rows = list(reader)

            if not rows:
                return valid_rows, errors

            start_idx = 0
            first_cell = rows[0][0].strip().lower() if rows[0] else ""
            if first_cell in {"timestamp", "datetime", "time", "date"}:
                start_idx = 1

            for idx, row in enumerate(rows[start_idx:], start=start_idx + 1):
                if not row or all(cell.strip() == "" for cell in row):
                    continue

                try:
                    if len(row) < 2:
                        errors.append(
                            {
                                "row": idx,
                                "error": "Insufficient columns (need at least timestamp, value)",
                            }
                        )
                        continue

                    timestamp_str = row[0].strip()
                    value_str = row[1].strip()
                    quality_code_str = row[2].strip() if len(row) > 2 else ""

                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        errors.append(
                            {
                                "row": idx,
                                "error": f"Invalid timestamp format: {timestamp_str}",
                            }
                        )
                        continue

                    if value_str == "":
                        value = None
                    else:
                        try:
                            value = float(value_str)
                        except ValueError:
                            errors.append(
                                {
                                    "row": idx,
                                    "error": f"Invalid numeric value: {value_str}",
                                }
                            )
                            continue

                    if quality_code_str == "":
                        quality_code = None
                    else:
                        try:
                            quality_code = int(quality_code_str)
                        except ValueError:
                            errors.append(
                                {
                                    "row": idx,
                                    "error": f"Invalid quality code: {quality_code_str}",
                                }
                            )
                            continue

                    valid_rows.append(
                        {
                            "timestamp": timestamp,
                            "value": value,
                            "quality_code": quality_code,
                        }
                    )

                except Exception as e:
                    errors.append({"row": idx, "error": str(e)})

        except Exception as e:
            errors.append({"row": 0, "error": f"CSV parsing error: {str(e)}"})

        return valid_rows, errors

    # Parse button or auto-parse
    if scalar_raw_csv.strip():
        if st.button(
            "Preview", type="secondary", key="scalar_preview_btn"
        ) or scalar_raw_csv != st.session_state.get("scalar_last_raw_csv", ""):
            valid_rows, parse_errors = parse_scalar_csv(scalar_raw_csv)
            st.session_state.scalar_parsed_rows = valid_rows
            st.session_state.scalar_parse_errors = parse_errors
            st.session_state.scalar_last_raw_csv = scalar_raw_csv

    # Display preview
    if st.session_state.scalar_parsed_rows or st.session_state.scalar_parse_errors:
        if st.session_state.scalar_parse_errors:
            st.warning(
                f"{len(st.session_state.scalar_parse_errors)} rows had parse errors and will be skipped."
            )
            with st.expander("Parse errors"):
                for err in st.session_state.scalar_parse_errors:
                    st.text(f"Row {err['row']}: {err['error']}")

        if st.session_state.scalar_parsed_rows:
            preview_df = pd.DataFrame(st.session_state.scalar_parsed_rows[:20])
            st.dataframe(preview_df, use_container_width=True)
            st.caption(
                f"{len(st.session_state.scalar_parsed_rows)} valid rows total. Showing first 20."
            )

    # Submit Section
    st.markdown("---")

    scalar_valid_rows = st.session_state.get("scalar_parsed_rows", [])
    if scalar_ingest_mode == "Tagless (direct-connect)":
        scalar_has_required_fields = all(
            [
                scalar_das_name,
                scalar_equipment_name,
                scalar_parameter_name,
                scalar_unit_name,
            ]
        )
        scalar_missing_hint = "Please enter DAS name, select Equipment, Parameter, and Unit to enable submission."
    else:
        scalar_has_required_fields = all(
            [scalar_das_name, scalar_tag, scalar_parameter_name, scalar_unit_name]
        )
        scalar_missing_hint = "Please enter DAS name, Tag, and select Parameter and Unit to enable submission."
    scalar_submit_disabled = (
        len(scalar_valid_rows) == 0 or not scalar_has_required_fields
    )

    if not scalar_has_required_fields and len(scalar_valid_rows) > 0:
        st.info(scalar_missing_hint)

    if st.button(
        "Submit to Database",
        disabled=scalar_submit_disabled,
        type="primary",
        key="scalar_submit_btn",
    ):
        values_payload = [
            {
                "timestamp": r["timestamp"].isoformat(),
                "value": r["value"],
                "quality_code": r["quality_code"],
            }
            for r in scalar_valid_rows
        ]
        try:
            with st.spinner("Submitting..."):
                if scalar_ingest_mode == "Tagless (direct-connect)":
                    payload = {
                        "das_name": scalar_das_name,
                        "equipment_name": scalar_equipment_name,
                        "parameter_name": scalar_parameter_name,
                        "unit_name": scalar_unit_name,
                        "data_provenance_id": scalar_data_provenance_id,
                        "processing_kind_id": scalar_processing_kind_id,
                        "values": values_payload,
                    }
                    result = ingest_sensor_tagless(payload)
                else:
                    payload = {
                        "das_name": scalar_das_name,
                        "tag": scalar_tag,
                        "channel_role": scalar_channel_role,
                        "parameter_name": scalar_parameter_name,
                        "unit_name": scalar_unit_name,
                        "data_provenance_id": scalar_data_provenance_id,
                        "processing_kind_id": scalar_processing_kind_id,
                        "values": values_payload,
                    }
                    result = ingest_sensor(payload)
            st.success(
                f"Ingested {result['rows_written']} rows into channel **{result['channel_id']}**"
            )
            st.session_state.scalar_parsed_rows = []
            st.session_state.scalar_parse_errors = []
            st.session_state.scalar_last_raw_csv = ""
        except APIError as e:
            st.error(f"Ingest failed: {e.message}")


# =============================================================================
# VECTOR TAB
# =============================================================================
with tab_vector:
    st.subheader("Vector / Spectral Sensor Ingest")
    st.markdown(
        "Each row in the CSV is one observation (one spectrum or distribution). "
        "Columns: timestamp, then one column per bin in order of BinIndex."
    )

    # Load lookup data
    try:
        with st.spinner("Loading lookup data..."):
            equipment_lookup = list_equipment_lookup()
            parameters_lookup = list_parameters_lookup()
            units_lookup = list_units_lookup()
            axes_lookup = list_binning_axes_lookup()
            provenance_lookup = list_data_provenance_lookup()
            processing_degrees_lookup = list_processing_kinds_lookup()
    except APIError as e:
        st.error(f"Cannot load lookup data: {e.message}")
        st.stop()

    sensor_provenance = next(
        (p for p in provenance_lookup if p["data_provenance_kind_id"] == 1),
        {"name": "Sensor"},
    )
    sensor_provenance_name = sensor_provenance["name"]

    # Channel Identity
    with st.container(border=True):
        st.subheader("Channel Identity")

        vector_ingest_mode = st.radio(
            "Ingest mode",
            ["Tagless (direct-connect)", "Tagged (SCADA)"],
            horizontal=True,
            key="vector_ingest_mode",
        )

        if vector_ingest_mode == "Tagless (direct-connect)":
            col_das, col_equip = st.columns(2)
            with col_das:
                vector_das_name = st.text_input(
                    "DAS name",
                    value="DirectConnect",
                    key="vector_das_name_tagless",
                )
            with col_equip:
                equipment_options = [
                    {"id": e["equipment_id"], "label": e["identifier"]}
                    for e in equipment_lookup
                ]
                equipment_labels = [opt["label"] for opt in equipment_options]
                selected_equipment_label = st.selectbox(
                    "Equipment",
                    options=equipment_labels,
                    index=None,
                    placeholder="Select equipment...",
                    key="vector_equipment_tagless",
                    help="Physical instrument this channel is directly connected to",
                )
            vector_equipment_name = selected_equipment_label  # identifier is the name
            vector_tag = None
            vector_channel_role = None
        else:
            col_das, col_tag, col_spt = st.columns(3)
            with col_das:
                vector_das_name = st.text_input(
                    "DAS name",
                    value="",
                    placeholder="e.g. SCADA_OPC",
                    key="vector_das_name_tagged",
                )
            with col_tag:
                vector_tag = st.text_input(
                    "Tag",
                    value="",
                    placeholder="e.g. PLC1.PSD_sensor",
                    key="vector_tag",
                )
            with col_spt:
                vector_channel_role = st.selectbox(
                    "Channel role",
                    options=["value", "status", "alarm", "uncertainty"],
                    index=0,
                    key="vector_channel_role",
                )
            vector_equipment_name = None

        col2, col3 = st.columns(2)

        with col2:
            parameter_options = [
                {"id": p["parameter_id"], "label": p["parameter_name"]}
                for p in parameters_lookup
            ]
            parameter_labels = [opt["label"] for opt in parameter_options]
            selected_parameter_label = st.selectbox(
                "Parameter",
                options=parameter_labels,
                index=None,
                placeholder="Select parameter...",
                key="vector_parameter",
                help="Measured analyte or parameter (e.g. TSS, pH)",
            )
            vector_parameter_name = selected_parameter_label

        with col3:
            unit_options = [
                {"id": u["unit_id"], "label": u["unit"]} for u in units_lookup
            ]
            unit_labels = [opt["label"] for opt in unit_options]
            selected_unit_label = st.selectbox(
                "Unit",
                options=unit_labels,
                index=None,
                placeholder="Select unit...",
                key="vector_unit",
                help="Unit of measurement for values stored in this channel (e.g. mg/L, NTU)",
            )
            vector_unit_name = selected_unit_label

        col4, col5, col6 = st.columns(3)

        with col4:
            st.markdown(f"**Data Provenance:** {sensor_provenance_name}")
            vector_data_provenance_id = 1

        with col5:
            processing_options = [
                {"id": d["processing_kind_id"], "label": d["name"]}
                for d in processing_degrees_lookup
            ]
            processing_labels = [opt["label"] for opt in processing_options]
            selected_processing_label = st.selectbox(
                "Processing Degree",
                options=processing_labels,
                index=0,
                key="vector_processing",
            )
            vector_processing_kind_id = next(
                (
                    opt["id"]
                    for opt in processing_options
                    if opt["label"] == selected_processing_label
                ),
                None,
            )

        with col6:
            axis_options = [
                {
                    "id": a["value_binning_axis_id"],
                    "label": f"{a['name']} ({a['number_of_bins']} bins)",
                }
                for a in axes_lookup
            ]
            axis_labels = [opt["label"] for opt in axis_options]
            selected_axis_label = st.selectbox(
                "Spectral / Distribution Axis",
                options=axis_labels,
                index=None,
                placeholder="Select axis...",
                key="vector_axis",
            )
            vector_axis_id = next(
                (
                    opt["id"]
                    for opt in axis_options
                    if opt["label"] == selected_axis_label
                ),
                None,
            )
            vector_n_bins = next(
                (
                    a["number_of_bins"]
                    for a in axes_lookup
                    if a["value_binning_axis_id"] == vector_axis_id
                ),
                0,
            )

    # Show format hint when axis is selected
    if vector_axis_id and vector_n_bins > 0:
        st.info(
            f"CSV format: timestamp, bin_0, bin_1, ..., bin_{vector_n_bins - 1} "
            f"({vector_n_bins} value columns). First row may be a header."
        )

    # Data Input
    with st.container(border=True):
        st.subheader("Data")

        vector_input_mode = st.radio(
            "Input method",
            ["Paste CSV", "Upload CSV file"],
            horizontal=True,
            key="vector_input_mode",
        )

        vector_raw_csv = ""

        if vector_input_mode == "Paste CSV":
            vector_raw_csv = st.text_area(
                "Paste CSV data",
                placeholder=f"""timestamp,bin_0,bin_1,...
2024-01-15T08:00:00,0.1,0.2,0.3,...
2024-01-15T08:15:00,0.15,0.25,0.35,...""",
                height=200,
                key="vector_text_area",
            )
        else:
            vector_uploaded_file = st.file_uploader(
                "Choose CSV file", type=["csv"], key="vector_file_uploader"
            )
            if vector_uploaded_file is not None:
                vector_raw_csv = vector_uploaded_file.read().decode("utf-8")

    def parse_vector_csv(
        csv_text: str, expected_bins: int
    ) -> tuple[list[dict], list[str]]:
        """Parse vector CSV data. Returns (observations, error_messages)."""
        observations = []
        errors = []

        if not csv_text.strip():
            return observations, errors

        csv_text = csv_text.lstrip("\ufeff")

        try:
            reader = csv.reader(StringIO(csv_text))
            rows = list(reader)

            if not rows:
                return observations, errors

            # Detect header: if first cell not parseable as datetime
            start_idx = 0
            first_cell = rows[0][0].strip() if rows[0] else ""
            try:
                datetime.fromisoformat(first_cell)
            except ValueError:
                start_idx = 1

            for idx, row in enumerate(rows[start_idx:], start=start_idx + 1):
                if not row or all(cell.strip() == "" for cell in row):
                    continue

                try:
                    timestamp_str = row[0].strip()
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        errors.append(
                            f"Row {idx}: Invalid timestamp format: {timestamp_str}"
                        )
                        continue

                    # Parse remaining columns as floats
                    values = []
                    for val_str in row[1:]:
                        val_str = val_str.strip()
                        if val_str == "":
                            values.append(None)
                        else:
                            try:
                                values.append(float(val_str))
                            except ValueError:
                                errors.append(
                                    f"Row {idx}: Invalid numeric value: {val_str}"
                                )
                                values.append(None)

                    # Pad with None if too short
                    while len(values) < expected_bins:
                        values.append(None)

                    # Truncate if too long
                    if len(values) > expected_bins:
                        values = values[:expected_bins]
                        errors.append(
                            f"Row {idx}: Extra values truncated to {expected_bins} bins"
                        )

                    observations.append(
                        {
                            "timestamp": timestamp,
                            "bin_values": values,
                            "quality_code": None,
                        }
                    )

                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")

        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")

        return observations, errors

    # Parse button
    if vector_raw_csv.strip() and vector_axis_id:
        if st.button(
            "Preview", type="secondary", key="vector_preview_btn"
        ) or vector_raw_csv != st.session_state.get("vector_last_raw_csv", ""):
            observations, parse_errors = parse_vector_csv(vector_raw_csv, vector_n_bins)
            st.session_state.vector_parsed = observations
            st.session_state.vector_parse_errors = parse_errors
            st.session_state.vector_last_raw_csv = vector_raw_csv

    # Display preview
    if st.session_state.vector_parsed or st.session_state.vector_parse_errors:
        if st.session_state.vector_parse_errors:
            st.warning(
                f"{len(st.session_state.vector_parse_errors)} parsing issues found."
            )
            with st.expander("Parse errors"):
                for err in st.session_state.vector_parse_errors:
                    st.text(err)

        if st.session_state.vector_parsed:
            # Show first 5 observations, first 10 bins
            preview_data = []
            display_bins = min(vector_n_bins, 10)
            for obs in st.session_state.vector_parsed[:5]:
                row = {"timestamp": obs["timestamp"]}
                for i in range(display_bins):
                    row[f"bin_{i}"] = (
                        obs["bin_values"][i] if i < len(obs["bin_values"]) else None
                    )
                preview_data.append(row)

            preview_df = pd.DataFrame(preview_data)
            st.dataframe(preview_df, use_container_width=True)
            st.caption(
                f"Showing first {min(len(st.session_state.vector_parsed), 5)} observations "
                f"and first {display_bins} bins of {vector_n_bins}"
            )

    # Submit Section
    st.markdown("---")

    vector_valid_obs = st.session_state.get("vector_parsed", [])
    if vector_ingest_mode == "Tagless (direct-connect)":
        vector_has_required = all(
            [
                vector_das_name,
                vector_equipment_name,
                vector_parameter_name,
                vector_unit_name,
                vector_axis_id,
            ]
        )
    else:
        vector_has_required = all(
            [
                vector_das_name,
                vector_tag,
                vector_parameter_name,
                vector_unit_name,
                vector_axis_id,
            ]
        )
    vector_submit_disabled = len(vector_valid_obs) == 0 or not vector_has_required

    if not vector_has_required and len(vector_valid_obs) > 0:
        if vector_ingest_mode == "Tagless (direct-connect)":
            st.info(
                "Please select DAS name, Equipment, Parameter, Unit, and Axis to enable submission."
            )
        else:
            st.info(
                "Please enter DAS name, Tag, select Parameter, Unit, and Axis to enable submission."
            )

    if st.button(
        "Submit to Database",
        disabled=vector_submit_disabled,
        type="primary",
        key="vector_submit_btn",
    ):
        if vector_ingest_mode == "Tagless (direct-connect)":
            payload = {
                "das_name": vector_das_name,
                "equipment_name": vector_equipment_name,
                "parameter_name": vector_parameter_name,
                "unit_name": vector_unit_name,
                "binning_axis_id": vector_axis_id,
                "data_provenance_id": vector_data_provenance_id,
                "processing_kind_id": vector_processing_kind_id,
                "observations": [
                    {
                        "timestamp": obs["timestamp"].isoformat(),
                        "bin_values": obs["bin_values"],
                        "quality_code": obs["quality_code"],
                    }
                    for obs in vector_valid_obs
                ],
            }
        else:
            payload = {
                "das_name": vector_das_name,
                "tag": vector_tag,
                "channel_role": vector_channel_role,
                "parameter_name": vector_parameter_name,
                "unit_name": vector_unit_name,
                "binning_axis_id": vector_axis_id,
                "data_provenance_id": vector_data_provenance_id,
                "processing_kind_id": vector_processing_kind_id,
                "observations": [
                    {
                        "timestamp": obs["timestamp"].isoformat(),
                        "bin_values": obs["bin_values"],
                        "quality_code": obs["quality_code"],
                    }
                    for obs in vector_valid_obs
                ],
            }

        try:
            with st.spinner("Submitting..."):
                result = ingest_sensor_vector(payload)
            st.success(
                f"✅ Ingested {result['rows_written']} rows into channel **{result['channel_id']}**"
            )
            st.session_state.vector_parsed = []
            st.session_state.vector_parse_errors = []
            st.session_state.vector_last_raw_csv = ""
        except APIError as e:
            st.error(f"Ingest failed: {e.message}")


# =============================================================================
# MATRIX TAB
# =============================================================================
with tab_matrix:
    st.subheader("Matrix / 2D Distribution Sensor Ingest")
    st.markdown(
        "Each observation is one 2D matrix at one timestamp. "
        "CSV format: first column is timestamp, then one column per (row_bin_index, col_bin_index) "
        "pair in row-major order — i.e., all col values for row 0, then all col values for row 1."
    )

    # Load lookup data
    try:
        with st.spinner("Loading lookup data..."):
            equipment_lookup = list_equipment_lookup()
            parameters_lookup = list_parameters_lookup()
            units_lookup = list_units_lookup()
            axes_lookup = list_binning_axes_lookup()
            provenance_lookup = list_data_provenance_lookup()
            processing_degrees_lookup = list_processing_kinds_lookup()
    except APIError as e:
        st.error(f"Cannot load lookup data: {e.message}")
        st.stop()

    sensor_provenance = next(
        (p for p in provenance_lookup if p["data_provenance_kind_id"] == 1),
        {"name": "Sensor"},
    )
    sensor_provenance_name = sensor_provenance["name"]

    # Channel Identity
    with st.container(border=True):
        st.subheader("Channel Identity")

        matrix_ingest_mode = st.radio(
            "Ingest mode",
            ["Tagless (direct-connect)", "Tagged (SCADA)"],
            horizontal=True,
            key="matrix_ingest_mode",
        )

        if matrix_ingest_mode == "Tagless (direct-connect)":
            col_das, col_equip = st.columns(2)
            with col_das:
                matrix_das_name = st.text_input(
                    "DAS name",
                    value="DirectConnect",
                    key="matrix_das_name_tagless",
                )
            with col_equip:
                equipment_options = [
                    {"id": e["equipment_id"], "label": e["identifier"]}
                    for e in equipment_lookup
                ]
                equipment_labels = [opt["label"] for opt in equipment_options]
                selected_equipment_label = st.selectbox(
                    "Equipment",
                    options=equipment_labels,
                    index=None,
                    placeholder="Select equipment...",
                    key="matrix_equipment_tagless",
                    help="Physical instrument this channel is directly connected to",
                )
            matrix_equipment_name = selected_equipment_label  # identifier is the name
            matrix_tag = None
            matrix_channel_role = None
        else:
            col_das, col_tag, col_spt = st.columns(3)
            with col_das:
                matrix_das_name = st.text_input(
                    "DAS name",
                    value="",
                    placeholder="e.g. SCADA_OPC",
                    key="matrix_das_name_tagged",
                )
            with col_tag:
                matrix_tag = st.text_input(
                    "Tag",
                    value="",
                    placeholder="e.g. PLC1.PSD_sensor",
                    key="matrix_tag",
                )
            with col_spt:
                matrix_channel_role = st.selectbox(
                    "Channel role",
                    options=["value", "status", "alarm", "uncertainty"],
                    index=0,
                    key="matrix_channel_role",
                )
            matrix_equipment_name = None

        col2, col3 = st.columns(2)

        with col2:
            parameter_options = [
                {"id": p["parameter_id"], "label": p["parameter_name"]}
                for p in parameters_lookup
            ]
            parameter_labels = [opt["label"] for opt in parameter_options]
            selected_parameter_label = st.selectbox(
                "Parameter",
                options=parameter_labels,
                index=None,
                placeholder="Select parameter...",
                key="matrix_parameter",
                help="Measured analyte or parameter (e.g. TSS, pH)",
            )
            matrix_parameter_name = selected_parameter_label

        with col3:
            unit_options = [
                {"id": u["unit_id"], "label": u["unit"]} for u in units_lookup
            ]
            unit_labels = [opt["label"] for opt in unit_options]
            selected_unit_label = st.selectbox(
                "Unit",
                options=unit_labels,
                index=None,
                placeholder="Select unit...",
                key="matrix_unit",
                help="Unit of measurement for values stored in this channel (e.g. mg/L, NTU)",
            )
            matrix_unit_name = selected_unit_label

        col4, col5, col6 = st.columns(3)

        with col4:
            st.markdown(f"**Data Provenance:** {sensor_provenance_name}")
            matrix_data_provenance_id = 1

        with col5:
            processing_options = [
                {"id": d["processing_kind_id"], "label": d["name"]}
                for d in processing_degrees_lookup
            ]
            processing_labels = [opt["label"] for opt in processing_options]
            selected_processing_label = st.selectbox(
                "Processing Degree",
                options=processing_labels,
                index=0,
                key="matrix_processing",
            )
            matrix_processing_kind_id = next(
                (
                    opt["id"]
                    for opt in processing_options
                    if opt["label"] == selected_processing_label
                ),
                None,
            )

        with col6:
            st.markdown("&nbsp;")  # spacer

    # Two axis selectors
    axis_col1, axis_col2 = st.columns(2)

    with axis_col1:
        axis_options = [
            {
                "id": a["value_binning_axis_id"],
                "label": f"{a['name']} ({a['number_of_bins']} bins)",
            }
            for a in axes_lookup
        ]
        axis_labels = [opt["label"] for opt in axis_options]
        selected_row_axis_label = st.selectbox(
            "Row Axis",
            options=axis_labels,
            index=None,
            placeholder="Select row axis...",
            key="matrix_row_axis",
        )
        matrix_row_axis_id = next(
            (
                opt["id"]
                for opt in axis_options
                if opt["label"] == selected_row_axis_label
            ),
            None,
        )
        matrix_n_row_bins = next(
            (
                a["number_of_bins"]
                for a in axes_lookup
                if a["value_binning_axis_id"] == matrix_row_axis_id
            ),
            0,
        )

    with axis_col2:
        selected_col_axis_label = st.selectbox(
            "Column Axis",
            options=axis_labels,
            index=None,
            placeholder="Select column axis...",
            key="matrix_col_axis",
        )
        matrix_col_axis_id = next(
            (
                opt["id"]
                for opt in axis_options
                if opt["label"] == selected_col_axis_label
            ),
            None,
        )
        matrix_n_col_bins = next(
            (
                a["number_of_bins"]
                for a in axes_lookup
                if a["value_binning_axis_id"] == matrix_col_axis_id
            ),
            0,
        )

    # Show format hint
    if matrix_row_axis_id and matrix_col_axis_id:
        total_values = matrix_n_row_bins * matrix_n_col_bins
        st.info(
            f"CSV columns: timestamp + {total_values} values "
            f"(row-major: r0c0, r0c1, ..., r{matrix_n_row_bins - 1}c{matrix_n_col_bins - 1})"
        )

    # Data Input
    with st.container(border=True):
        st.subheader("Data")

        matrix_input_mode = st.radio(
            "Input method",
            ["Paste CSV", "Upload CSV file"],
            horizontal=True,
            key="matrix_input_mode",
        )

        matrix_raw_csv = ""

        if matrix_input_mode == "Paste CSV":
            matrix_raw_csv = st.text_area(
                "Paste CSV data",
                placeholder=f"""timestamp,r0c0,r0c1,...,r0c{matrix_n_col_bins - 1},r1c0,...
2024-01-15T08:00:00,0.1,0.2,...
2024-01-15T08:15:00,0.15,0.25,...""",
                height=200,
                key="matrix_text_area",
            )
        else:
            matrix_uploaded_file = st.file_uploader(
                "Choose CSV file", type=["csv"], key="matrix_file_uploader"
            )
            if matrix_uploaded_file is not None:
                matrix_raw_csv = matrix_uploaded_file.read().decode("utf-8")

    def parse_matrix_csv(
        csv_text: str, n_rows: int, n_cols: int
    ) -> tuple[list[dict], list[str]]:
        """Parse matrix CSV data. Returns (observations, error_messages)."""
        observations = []
        errors = []
        expected_values = n_rows * n_cols

        if not csv_text.strip():
            return observations, errors

        csv_text = csv_text.lstrip("\ufeff")

        try:
            reader = csv.reader(StringIO(csv_text))
            rows = list(reader)

            if not rows:
                return observations, errors

            # Detect header
            start_idx = 0
            first_cell = rows[0][0].strip() if rows[0] else ""
            try:
                datetime.fromisoformat(first_cell)
            except ValueError:
                start_idx = 1

            for idx, row in enumerate(rows[start_idx:], start=start_idx + 1):
                if not row or all(cell.strip() == "" for cell in row):
                    continue

                try:
                    timestamp_str = row[0].strip()
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        errors.append(
                            f"Row {idx}: Invalid timestamp format: {timestamp_str}"
                        )
                        continue

                    # Parse remaining columns as floats
                    values = []
                    for val_str in row[1:]:
                        val_str = val_str.strip()
                        if val_str == "":
                            values.append(None)
                        else:
                            try:
                                values.append(float(val_str))
                            except ValueError:
                                errors.append(
                                    f"Row {idx}: Invalid numeric value: {val_str}"
                                )
                                values.append(None)

                    # Check expected count
                    if len(values) < expected_values:
                        while len(values) < expected_values:
                            values.append(None)
                        errors.append(
                            f"Row {idx}: Padded with None to reach {expected_values} values"
                        )
                    elif len(values) > expected_values:
                        values = values[:expected_values]
                        errors.append(
                            f"Row {idx}: Truncated to {expected_values} values"
                        )

                    # Reshape into matrix
                    matrix = []
                    for i in range(n_rows):
                        row_start = i * n_cols
                        row_end = row_start + n_cols
                        matrix.append(values[row_start:row_end])

                    observations.append(
                        {
                            "timestamp": timestamp,
                            "matrix": matrix,
                            "quality_code": None,
                        }
                    )

                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")

        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")

        return observations, errors

    # Parse button
    if matrix_raw_csv.strip() and matrix_row_axis_id and matrix_col_axis_id:
        if st.button(
            "Preview", type="secondary", key="matrix_preview_btn"
        ) or matrix_raw_csv != st.session_state.get("matrix_last_raw_csv", ""):
            observations, parse_errors = parse_matrix_csv(
                matrix_raw_csv, matrix_n_row_bins, matrix_n_col_bins
            )
            st.session_state.matrix_parsed = observations
            st.session_state.matrix_parse_errors = parse_errors
            st.session_state.matrix_last_raw_csv = matrix_raw_csv

    # Display preview
    if st.session_state.matrix_parsed or st.session_state.matrix_parse_errors:
        if st.session_state.matrix_parse_errors:
            st.warning(
                f"{len(st.session_state.matrix_parse_errors)} parsing issues found."
            )
            with st.expander("Parse errors"):
                for err in st.session_state.matrix_parse_errors:
                    st.text(err)

        if st.session_state.matrix_parsed:
            # Show all observations with all matrix data flattened
            preview_data = []

            for obs in st.session_state.matrix_parsed:
                row = {"timestamp": obs["timestamp"]}
                for r in range(matrix_n_row_bins):
                    for c in range(matrix_n_col_bins):
                        key = f"r{r}c{c}"
                        row[key] = (
                            obs["matrix"][r][c]
                            if r < len(obs["matrix"]) and c < len(obs["matrix"][r])
                            else None
                        )
                preview_data.append(row)

            preview_df = pd.DataFrame(preview_data)
            st.dataframe(preview_df, use_container_width=True)
            st.caption(
                f"Showing all {len(st.session_state.matrix_parsed)} observations "
                f"with full {matrix_n_row_bins}×{matrix_n_col_bins} matrix"
            )

    # Submit Section
    st.markdown("---")

    matrix_valid_obs = st.session_state.get("matrix_parsed", [])
    if matrix_ingest_mode == "Tagless (direct-connect)":
        matrix_has_required = all(
            [
                matrix_das_name,
                matrix_equipment_name,
                matrix_parameter_name,
                matrix_unit_name,
                matrix_row_axis_id,
                matrix_col_axis_id,
            ]
        )
    else:
        matrix_has_required = all(
            [
                matrix_das_name,
                matrix_tag,
                matrix_parameter_name,
                matrix_unit_name,
                matrix_row_axis_id,
                matrix_col_axis_id,
            ]
        )
    matrix_submit_disabled = len(matrix_valid_obs) == 0 or not matrix_has_required

    if not matrix_has_required and len(matrix_valid_obs) > 0:
        if matrix_ingest_mode == "Tagless (direct-connect)":
            st.info(
                "Please select DAS name, Equipment, Parameter, Unit, Row Axis, and Column Axis to enable submission."
            )
        else:
            st.info(
                "Please enter DAS name, Tag, select Parameter, Unit, Row Axis, and Column Axis to enable submission."
            )

    if st.button(
        "Submit to Database",
        disabled=matrix_submit_disabled,
        type="primary",
        key="matrix_submit_btn",
    ):
        if matrix_ingest_mode == "Tagless (direct-connect)":
            payload = {
                "das_name": matrix_das_name,
                "equipment_name": matrix_equipment_name,
                "parameter_name": matrix_parameter_name,
                "unit_name": matrix_unit_name,
                "row_axis_id": matrix_row_axis_id,
                "col_axis_id": matrix_col_axis_id,
                "data_provenance_id": matrix_data_provenance_id,
                "processing_kind_id": matrix_processing_kind_id,
                "observations": [
                    {
                        "timestamp": obs["timestamp"].isoformat(),
                        "matrix": obs["matrix"],
                        "quality_code": obs["quality_code"],
                    }
                    for obs in matrix_valid_obs
                ],
            }
        else:
            payload = {
                "das_name": matrix_das_name,
                "tag": matrix_tag,
                "channel_role": matrix_channel_role,
                "parameter_name": matrix_parameter_name,
                "unit_name": matrix_unit_name,
                "row_axis_id": matrix_row_axis_id,
                "col_axis_id": matrix_col_axis_id,
                "data_provenance_id": matrix_data_provenance_id,
                "processing_kind_id": matrix_processing_kind_id,
                "observations": [
                    {
                        "timestamp": obs["timestamp"].isoformat(),
                        "matrix": obs["matrix"],
                        "quality_code": obs["quality_code"],
                    }
                    for obs in matrix_valid_obs
                ],
            }

        try:
            with st.spinner("Submitting..."):
                result = ingest_sensor_matrix(payload)
            st.success(
                f"✅ Ingested {result['rows_written']} rows into channel **{result['channel_id']}**"
            )
            st.session_state.matrix_parsed = []
            st.session_state.matrix_parse_errors = []
            st.session_state.matrix_last_raw_csv = ""
        except APIError as e:
            st.error(f"Ingest failed: {e.message}")


# =============================================================================
# IMAGE TAB
# =============================================================================
with tab_image:
    st.subheader("Image / Camera Sensor Ingest")
    st.markdown(
        "Upload a single image captured by a sensor at a known timestamp. "
        "The file is stored on the server and linked to an auto-created image channel."
    )

    # Load lookup data
    try:
        with st.spinner("Loading lookup data..."):
            equipment_lookup = list_equipment_lookup()
            parameters_lookup = list_parameters_lookup()
            units_lookup = list_units_lookup()
            provenance_lookup = list_data_provenance_lookup()
            processing_degrees_lookup = list_processing_kinds_lookup()
    except APIError as e:
        st.error(f"Cannot load lookup data: {e.message}")
        st.stop()

    sensor_provenance = next(
        (p for p in provenance_lookup if p["data_provenance_kind_id"] == 1),
        {"name": "Sensor"},
    )
    sensor_provenance_name = sensor_provenance["name"]

    # Channel Identity
    with st.container(border=True):
        st.subheader("Channel Identity")

        col1, col2, col3 = st.columns(3)

        with col1:
            equipment_options = [
                {"id": e["equipment_id"], "label": e["identifier"]}
                for e in equipment_lookup
            ]
            equipment_labels = [opt["label"] for opt in equipment_options]
            selected_equipment_label = st.selectbox(
                "Equipment",
                options=equipment_labels,
                index=None,
                placeholder="Select equipment...",
                key="img_equipment",
                help="Physical instrument this channel is directly connected to",
            )
            img_equipment_id = next(
                (
                    opt["id"]
                    for opt in equipment_options
                    if opt["label"] == selected_equipment_label
                ),
                None,
            )

        with col2:
            parameter_options = [
                {"id": p["parameter_id"], "label": p["parameter_name"]}
                for p in parameters_lookup
            ]
            parameter_labels = [opt["label"] for opt in parameter_options]
            selected_parameter_label = st.selectbox(
                "Parameter",
                options=parameter_labels,
                index=None,
                placeholder="Select parameter...",
                key="img_parameter",
                help="Measured analyte or parameter (e.g. TSS, pH)",
            )
            img_parameter_id = next(
                (
                    opt["id"]
                    for opt in parameter_options
                    if opt["label"] == selected_parameter_label
                ),
                None,
            )

        with col3:
            unit_options = [
                {"id": u["unit_id"], "label": u["unit"]} for u in units_lookup
            ]
            unit_labels = [opt["label"] for opt in unit_options]
            selected_unit_label = st.selectbox(
                "Unit",
                options=unit_labels,
                index=None,
                placeholder="Select unit...",
                key="img_unit",
                help="Unit of measurement for values stored in this channel (e.g. mg/L, NTU)",
            )
            img_unit_id = next(
                (
                    opt["id"]
                    for opt in unit_options
                    if opt["label"] == selected_unit_label
                ),
                None,
            )

        col4, col5 = st.columns(2)

        with col4:
            st.markdown(f"**Data Provenance:** {sensor_provenance_name}")
            img_provenance_id = 1

        with col5:
            processing_options = [
                {"id": d["processing_kind_id"], "label": d["name"]}
                for d in processing_degrees_lookup
            ]
            processing_labels = [opt["label"] for opt in processing_options]
            selected_processing_label = st.selectbox(
                "Processing Degree",
                options=processing_labels,
                index=0,
                key="img_processing",
            )
            img_processing_id = next(
                (
                    opt["id"]
                    for opt in processing_options
                    if opt["label"] == selected_processing_label
                ),
                None,
            )

    # Timestamp Section
    with st.container(border=True):
        st.subheader("Timestamp")
        col1, col2 = st.columns(2)
        with col1:
            img_date = st.date_input("Measurement date", key="img_date")
        with col2:
            img_time = st.time_input("Measurement time", key="img_time")
        img_timestamp = datetime.combine(img_date, img_time)

    # File Upload Section
    with st.container(border=True):
        st.subheader("Image File")

        uploaded_image = st.file_uploader(
            "Select image file",
            type=["jpg", "jpeg", "png", "tif", "tiff", "bmp"],
            key="img_upload",
        )

        if uploaded_image is not None:
            image_bytes = uploaded_image.read()
            st.image(
                uploaded_image,
                caption=uploaded_image.name,
                use_container_width=False,
                width=300,
            )
            st.caption(
                f"File: {uploaded_image.name} | Size: {len(image_bytes) / 1024:.1f} KB"
            )

            img_quality_code = st.number_input(
                "Quality code (optional)",
                value=None,
                min_value=0,
                step=1,
                key="img_qc",
            )

            # Submit button (disabled if required fields not selected)
            img_has_required = all([img_equipment_id, img_parameter_id, img_unit_id])

            if st.button(
                "Upload Image",
                type="primary",
                key="img_submit",
                disabled=not img_has_required,
            ):
                try:
                    with st.spinner("Uploading..."):
                        result = ingest_sensor_image(
                            equipment_id=img_equipment_id,
                            parameter_id=img_parameter_id,
                            unit_id=img_unit_id,
                            timestamp=img_timestamp.isoformat(),
                            image_bytes=image_bytes,
                            filename=uploaded_image.name,
                            quality_code=img_quality_code,
                            data_provenance_id=img_provenance_id,
                            processing_kind_id=img_processing_id,
                        )
                    st.success(f"✅ Image stored at **{result['storage_path']}**")
                    st.info(
                        f"Channel ID: {result['channel_id']} | ValueImage ID: {result['value_image_id']}"
                    )
                except APIError as e:
                    st.error(f"Upload failed: {e.message}")
        else:
            st.info("Select an image file to upload.")
