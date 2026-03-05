"""Sensor Data Ingest page for scalar time series data."""

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
    list_data_provenance_lookup,
    list_equipment_lookup,
    list_parameters_lookup,
    list_processing_degrees_lookup,
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

st.title("Sensor Data Ingest")
st.markdown(
    "Upload or paste timestamped scalar measurements. The channel is "
    "created automatically if it does not yet exist."
)

# Initialize session state for parsed data
if "parsed_rows" not in st.session_state:
    st.session_state.parsed_rows = []
if "parse_errors" not in st.session_state:
    st.session_state.parse_errors = []

# Load lookup data for dropdowns
try:
    with st.spinner("Loading lookup data..."):
        equipment_lookup = list_equipment_lookup()
        parameters_lookup = list_parameters_lookup()
        units_lookup = list_units_lookup()
        provenance_lookup = list_data_provenance_lookup()
        processing_degrees_lookup = list_processing_degrees_lookup()
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()

# Get Sensor provenance name from database (ID=1 is Sensor)
sensor_provenance = next(
    (p for p in provenance_lookup if p["data_provenance_id"] == 1),
    {"data_provenance_name": "Sensor"},  # fallback if not found
)
sensor_provenance_name = sensor_provenance["data_provenance_name"]

# Channel Identification Section
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
        )
        equipment_id = next(
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
        )
        parameter_id = next(
            (
                opt["id"]
                for opt in parameter_options
                if opt["label"] == selected_parameter_label
            ),
            None,
        )

    with col3:
        unit_options = [{"id": u["unit_id"], "label": u["unit"]} for u in units_lookup]
        unit_labels = [opt["label"] for opt in unit_options]
        selected_unit_label = st.selectbox(
            "Unit",
            options=unit_labels,
            index=None,
            placeholder="Select unit...",
        )
        unit_id = next(
            (opt["id"] for opt in unit_options if opt["label"] == selected_unit_label),
            None,
        )

    col4, col5 = st.columns(2)

    with col4:
        st.markdown(f"**Data Provenance:** {sensor_provenance_name}")
        data_provenance_id = 1

    with col5:
        processing_options = [
            {"id": d["processing_degree_id"], "label": d["name"]}
            for d in processing_degrees_lookup
        ]
        processing_labels = [opt["label"] for opt in processing_options]
        selected_processing_label = st.selectbox(
            "Processing Degree",
            options=processing_labels,
            index=0,
            help="Auto-created if new channel",
        )
        processing_degree_id = next(
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

    input_mode = st.radio(
        "Input method",
        ["Paste CSV", "Upload CSV file"],
        horizontal=True,
    )

    raw_csv = ""

    if input_mode == "Paste CSV":
        raw_csv = st.text_area(
            "Paste CSV data",
            placeholder="""timestamp,value,quality_code
2024-01-15T08:00:00,7.42,
2024-01-15T08:15:00,7.45,
2024-01-15T08:30:00,7.51,""",
            height=200,
        )
        st.caption(
            "ISO timestamps (YYYY-MM-DDTHH:MM:SS). quality_code column optional."
        )
    else:
        uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])
        if uploaded_file is not None:
            raw_csv = uploaded_file.read().decode("utf-8")


# Parse and Preview Section
def parse_csv_data(csv_text: str) -> tuple[list[dict], list[dict]]:
    """Parse CSV data into valid rows and errors."""
    valid_rows = []
    errors = []

    if not csv_text.strip():
        return valid_rows, errors

    # Strip BOM if present
    csv_text = csv_text.lstrip("\ufeff")

    try:
        reader = csv.reader(StringIO(csv_text))
        rows = list(reader)

        if not rows:
            return valid_rows, errors

        # Detect header: if first cell looks like a header
        start_idx = 0
        first_cell = rows[0][0].strip().lower() if rows[0] else ""
        if first_cell in {"timestamp", "datetime", "time", "date"}:
            start_idx = 1

        for idx, row in enumerate(rows[start_idx:], start=start_idx + 1):
            if not row or all(cell.strip() == "" for cell in row):
                continue

            try:
                # Expected columns: timestamp, value, [quality_code]
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

                # Parse timestamp
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

                # Parse value
                if value_str == "":
                    value = None
                else:
                    try:
                        value = float(value_str)
                    except ValueError:
                        errors.append(
                            {"row": idx, "error": f"Invalid numeric value: {value_str}"}
                        )
                        continue

                # Parse quality_code
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


# Parse button or auto-parse when raw_csv changes
if raw_csv.strip():
    if st.button("Preview", type="secondary") or raw_csv != st.session_state.get(
        "last_raw_csv", ""
    ):
        valid_rows, parse_errors = parse_csv_data(raw_csv)
        st.session_state.parsed_rows = valid_rows
        st.session_state.parse_errors = parse_errors
        st.session_state.last_raw_csv = raw_csv

# Display preview if we have parsed data
if st.session_state.parsed_rows or st.session_state.parse_errors:
    if st.session_state.parse_errors:
        st.warning(
            f"{len(st.session_state.parse_errors)} rows had parse errors and will be skipped."
        )
        with st.expander("Parse errors"):
            for err in st.session_state.parse_errors:
                st.text(f"Row {err['row']}: {err['error']}")

    if st.session_state.parsed_rows:
        preview_df = pd.DataFrame(st.session_state.parsed_rows[:20])
        st.dataframe(preview_df, use_container_width=True)
        st.caption(
            f"{len(st.session_state.parsed_rows)} valid rows total. Showing first 20."
        )


# Submit Section
st.markdown("---")

valid_rows = st.session_state.get("parsed_rows", [])
has_required_fields = all([equipment_id, parameter_id, unit_id])
submit_disabled = len(valid_rows) == 0 or not has_required_fields

if not has_required_fields and len(valid_rows) > 0:
    st.info("Please select Equipment, Parameter, and Unit to enable submission.")

if st.button("Submit to Database", disabled=submit_disabled, type="primary"):
    payload = {
        "equipment_id": equipment_id,
        "parameter_id": parameter_id,
        "unit_id": unit_id,
        "data_provenance_id": data_provenance_id,
        "processing_degree_id": processing_degree_id,
        "values": [
            {
                "timestamp": r["timestamp"].isoformat(),
                "value": r["value"],
                "quality_code": r["quality_code"],
            }
            for r in valid_rows
        ],
    }

    try:
        with st.spinner("Submitting..."):
            result = ingest_sensor(payload)
        st.success(
            f"✅ Ingested {result['rows_written']} rows into channel **{result['channel_id']}**"
        )
        # Clear parsed data after successful submission
        st.session_state.parsed_rows = []
        st.session_state.parse_errors = []
        st.session_state.last_raw_csv = ""
    except APIError as e:
        st.error(f"Ingest failed: {e.message}")
