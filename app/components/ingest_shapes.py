"""Reusable ingest blocks (scalar / vector / matrix / image).

Behavior-preserving extraction of the four tabs in `app/pages/sensor_ingest.py`.
Each block is parameterized by:

- `key_prefix`: namespace for all session_state and widget keys
- `lookups`: dict pre-loaded by the caller (avoids re-loading lookups per tab)
- `submit_fn`: callable invoked when the user clicks "Submit to Database"
- `context`: "sensor" or "lab" — reserved for lab-specific tweaks (Wave F3)

For scalar/vector/matrix, `submit_fn(mode, payload)` where ``mode`` is
``"tagless"`` or ``"tagged"`` and ``payload`` is the API request body. The fn
must return the parsed response dict containing ``rows_written`` and
``channel_id``.

For the image block, `submit_fn(**kwargs)` is called with the same keyword
arguments the sensor `ingest_sensor_image` API client exposes.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Literal

import pandas as pd
import streamlit as st

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore[no-retype]

_KNOWN_TIMEZONES = sorted(zoneinfo.available_timezones())


def _timezone_selector(key: str, label: str = "CSV timezone", help: str | None = None) -> zoneinfo.ZoneInfo:
    """Render a timezone selectbox pre-filled with the browser's local timezone.
    Returns the selected zoneinfo.ZoneInfo for timestamp localization."""
    local_tz_name = datetime.now(timezone.utc).astimezone().tzinfo.key  # type: ignore[attr-defined, union-attr]
    selected_tz_name = st.selectbox(
        label,
        options=_KNOWN_TIMEZONES,
        index=_KNOWN_TIMEZONES.index(local_tz_name) if local_tz_name in _KNOWN_TIMEZONES else _KNOWN_TIMEZONES.index("UTC"),
        key=key,
        help=help or "Timezone of the timestamps in your data. They will be converted to UTC on submit.",
    )
    return zoneinfo.ZoneInfo(selected_tz_name)

from app.api_client import APIError

Context = Literal["sensor", "lab"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_state(key_prefix: str, *suffixes: str) -> None:
    for s in suffixes:
        key = f"{key_prefix}_{s}"
        if key not in st.session_state:
            st.session_state[key] = [] if s.endswith(("_rows", "_errors", "parsed")) else ""


def _sensor_provenance_name(lookups: dict) -> str:
    provenance_lookup = lookups.get("provenance", [])
    sensor_provenance = next(
        (p for p in provenance_lookup if p.get("data_provenance_kind_id") == 1),
        {"name": "Sensor"},
    )
    return sensor_provenance["name"]


# ---------------------------------------------------------------------------
# Scalar
# ---------------------------------------------------------------------------


def scalar_ingest_block(
    *,
    key_prefix: str,
    lookups: dict,
    submit_fn: Callable[[str, dict], dict],
    context: Context = "sensor",
) -> None:
    """Render the scalar ingest UI and submit via ``submit_fn(mode, payload)``."""
    _ensure_state(key_prefix, "parsed_rows", "parse_errors")

    equipment_lookup = lookups["equipment"]
    parameters_lookup = lookups["parameters"]
    units_lookup = lookups["units"]
    processing_degrees_lookup = lookups["operation_kinds"]
    sensor_provenance_name = _sensor_provenance_name(lookups)

    with st.container(border=True):
        st.subheader("Channel Identity")

        scalar_ingest_mode = st.radio(
            "Ingest mode",
            ["Tagless (direct-connect)", "Tagged (SCADA)"],
            horizontal=True,
            key=f"{key_prefix}_ingest_mode",
        )

        _das_lookup = lookups.get("das", [])
        _tags_fn = lookups.get("tags_fn")

        if scalar_ingest_mode == "Tagless (direct-connect)":
            col_das, col_equip = st.columns(2)
            with col_das:
                if _das_lookup:
                    _das_names_tl = [d["name"] for d in _das_lookup]
                    _sel_das_tl = st.selectbox(
                        "DAS",
                        options=_das_names_tl,
                        index=None,
                        placeholder="Select DAS...",
                        key=f"{key_prefix}_das_name_tagless",
                    )
                    scalar_das_name = _sel_das_tl or ""
                else:
                    scalar_das_name = st.text_input(
                        "DAS name",
                        value="DirectConnect",
                        key=f"{key_prefix}_das_name_tagless",
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
                    key=f"{key_prefix}_equipment_tagless",
                    help="Physical instrument this channel is directly connected to",
                )
            scalar_equipment_name = selected_equipment_label
            scalar_tag = None
            scalar_channel_role = None
        else:
            col_das, col_tag, col_spt = st.columns(3)
            with col_das:
                if _das_lookup:
                    _das_names_tg = [d["name"] for d in _das_lookup]
                    _sel_das_tg = st.selectbox(
                        "DAS",
                        options=_das_names_tg,
                        index=None,
                        placeholder="Select DAS...",
                        key=f"{key_prefix}_das_name_tagged",
                    )
                    scalar_das_name = _sel_das_tg or ""
                    _scalar_das_id = next(
                        (d["das_id"] for d in _das_lookup if d["name"] == _sel_das_tg),
                        None,
                    )
                else:
                    scalar_das_name = st.text_input(
                        "DAS name",
                        value="",
                        placeholder="e.g. SCADA_OPC",
                        key=f"{key_prefix}_das_name_tagged",
                    )
                    _scalar_das_id = None
            with col_tag:
                if _das_lookup and _tags_fn and _scalar_das_id is not None:
                    _tag_cache_key = f"{key_prefix}_tags_cache_{_scalar_das_id}"
                    if _tag_cache_key not in st.session_state:
                        try:
                            st.session_state[_tag_cache_key] = [
                                t["name"] for t in _tags_fn(_scalar_das_id)
                            ]
                        except Exception:
                            st.session_state[_tag_cache_key] = []
                    scalar_tag = st.selectbox(
                        "Tag",
                        options=st.session_state[_tag_cache_key],
                        index=None,
                        placeholder="Select tag...",
                        key=f"{key_prefix}_tag",
                    )
                else:
                    scalar_tag = st.text_input(
                        "Tag",
                        value="",
                        placeholder="e.g. PLC1.pH_sensor",
                        key=f"{key_prefix}_tag",
                    )
            with col_spt:
                scalar_channel_role = st.selectbox(
                    "Channel role",
                    options=["value", "status", "alarm", "uncertainty"],
                    index=0,
                    key=f"{key_prefix}_channel_role",
                )
            scalar_equipment_name = None

        col2, col3 = st.columns(2)
        with col2:
            parameter_options = [
                {"id": p["parameter_id"], "label": p["parameter_name"]}
                for p in parameters_lookup
            ]
            parameter_labels = [opt["label"] for opt in parameter_options]
            scalar_parameter_name = st.selectbox(
                "Parameter",
                options=parameter_labels,
                index=None,
                placeholder="Select parameter...",
                key=f"{key_prefix}_parameter",
                help="Measured analyte or parameter (e.g. TSS, pH)",
            )

        with col3:
            unit_options = [{"id": u["unit_id"], "label": u["unit"]} for u in units_lookup]
            unit_labels = [opt["label"] for opt in unit_options]
            scalar_unit_name = st.selectbox(
                "Unit",
                options=unit_labels,
                index=None,
                placeholder="Select unit...",
                key=f"{key_prefix}_unit",
                help="Unit of measurement for values stored in this channel (e.g. mg/L, NTU)",
            )

        col4, col5 = st.columns(2)
        with col4:
            st.markdown(f"**Data Provenance:** {sensor_provenance_name}")
            scalar_data_provenance_id = 1
        with col5:
            processing_options = [
                {"id": d["operation_kind_id"], "label": d["name"]}
                for d in processing_degrees_lookup
            ]
            processing_labels = [opt["label"] for opt in processing_options]
            selected_processing_label = st.selectbox(
                "Processing Degree",
                options=processing_labels,
                index=0,
                help="Auto-created if new channel",
                key=f"{key_prefix}_processing",
            )
            scalar_operation_kind_id = next(
                (opt["id"] for opt in processing_options if opt["label"] == selected_processing_label),
                None,
            )

    # Data Input
    with st.container(border=True):
        st.subheader("Data")

        scalar_input_mode = st.radio(
            "Input method",
            ["Paste CSV", "Upload CSV file"],
            horizontal=True,
            key=f"{key_prefix}_input_mode",
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
                key=f"{key_prefix}_text_area",
            )
            st.caption("ISO timestamps (YYYY-MM-DDTHH:MM:SS). quality_code column optional.")
        else:
            uploaded = st.file_uploader(
                "Choose CSV file", type=["csv"], key=f"{key_prefix}_file_uploader"
            )
            if uploaded is not None:
                scalar_raw_csv = uploaded.read().decode("utf-8")

    def parse_scalar_csv(csv_text: str) -> tuple[list[dict], list[dict]]:
        valid_rows: list[dict] = []
        errors: list[dict] = []
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
                        errors.append({"row": idx, "error": "Insufficient columns (need at least timestamp, value)"})
                        continue
                    timestamp_str = row[0].strip()
                    value_str = row[1].strip()
                    quality_code_str = row[2].strip() if len(row) > 2 else ""
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        errors.append({"row": idx, "error": f"Invalid timestamp format: {timestamp_str}"})
                        continue
                    if value_str == "":
                        value: float | None = None
                    else:
                        try:
                            value = float(value_str)
                        except ValueError:
                            errors.append({"row": idx, "error": f"Invalid numeric value: {value_str}"})
                            continue
                    if quality_code_str == "":
                        quality_code: int | None = None
                    else:
                        try:
                            quality_code = int(quality_code_str)
                        except ValueError:
                            errors.append({"row": idx, "error": f"Invalid quality code: {quality_code_str}"})
                            continue
                    valid_rows.append({"timestamp": timestamp, "value": value, "quality_code": quality_code})
                except Exception as e:
                    errors.append({"row": idx, "error": str(e)})
        except Exception as e:
            errors.append({"row": 0, "error": f"CSV parsing error: {str(e)}"})
        return valid_rows, errors

    last_raw_key = f"{key_prefix}_last_raw_csv"
    parsed_key = f"{key_prefix}_parsed_rows"
    errors_key = f"{key_prefix}_parse_errors"

    if scalar_raw_csv.strip():
        if (
            st.button("Preview", type="secondary", key=f"{key_prefix}_preview_btn")
            or scalar_raw_csv != st.session_state.get(last_raw_key, "")
        ):
            valid_rows, parse_errors = parse_scalar_csv(scalar_raw_csv)
            st.session_state[parsed_key] = valid_rows
            st.session_state[errors_key] = parse_errors
            st.session_state[last_raw_key] = scalar_raw_csv

    # Timezone selector for CSV data (entries may be in local time)
    source_tz = _timezone_selector(
        key=f"{key_prefix}_csv_timezone",
        label="CSV timezone",
    )

    if st.session_state.get(parsed_key) or st.session_state.get(errors_key):
        if st.session_state.get(errors_key):
            st.warning(f"{len(st.session_state[errors_key])} rows had parse errors and will be skipped.")
            with st.expander("Parse errors"):
                for err in st.session_state[errors_key]:
                    st.text(f"Row {err['row']}: {err['error']}")
        if st.session_state.get(parsed_key):
            preview_df = pd.DataFrame(st.session_state[parsed_key][:20])
            st.dataframe(preview_df, use_container_width=True)
            st.caption(f"{len(st.session_state[parsed_key])} valid rows total. Showing first 20.")

    st.markdown("---")

    scalar_valid_rows = st.session_state.get(parsed_key, [])
    if scalar_ingest_mode == "Tagless (direct-connect)":
        has_required = all([scalar_das_name, scalar_equipment_name, scalar_parameter_name, scalar_unit_name])
        missing_hint = "Please enter DAS name, select Equipment, Parameter, and Unit to enable submission."
    else:
        has_required = all([scalar_das_name, scalar_tag, scalar_parameter_name, scalar_unit_name])
        missing_hint = "Please enter DAS name, Tag, and select Parameter and Unit to enable submission."
    submit_disabled = len(scalar_valid_rows) == 0 or not has_required

    if not has_required and len(scalar_valid_rows) > 0:
        st.info(missing_hint)

    if st.button(
        "Submit to Database",
        disabled=submit_disabled,
        type="primary",
        key=f"{key_prefix}_submit_btn",
    ):
        values_payload = [
            {
                "timestamp": r["timestamp"].replace(tzinfo=source_tz).astimezone(timezone.utc).isoformat(),
                "value": r["value"],
                "quality_code": r["quality_code"],
            }
            for r in scalar_valid_rows
        ]
        try:
            with st.spinner("Submitting..."):
                _strict = bool(lookups.get("das"))
                if scalar_ingest_mode == "Tagless (direct-connect)":
                    payload = {
                        "das_name": scalar_das_name,
                        "equipment_name": scalar_equipment_name,
                        "parameter_name": scalar_parameter_name,
                        "unit_name": scalar_unit_name,
                        "data_provenance_kind_id": scalar_data_provenance_id,
                        "strict": _strict,
                        "values": values_payload,
                    }
                    result = submit_fn("tagless", payload)
                else:
                    payload = {
                        "das_name": scalar_das_name,
                        "tag": scalar_tag,
                        "channel_kind": scalar_channel_role,
                        "parameter_name": scalar_parameter_name,
                        "unit_name": scalar_unit_name,
                        "data_provenance_kind_id": scalar_data_provenance_id,
                        "strict": _strict,
                        "values": values_payload,
                    }
                    result = submit_fn("tagged", payload)
            st.success(
                f"Ingested {result['rows_written']} rows into channel **{result['channel_id']}**"
            )
            st.session_state[parsed_key] = []
            st.session_state[errors_key] = []
            st.session_state[last_raw_key] = ""
        except APIError as e:
            st.error(f"Ingest failed: {e.message}")


# ---------------------------------------------------------------------------
# Vector
# ---------------------------------------------------------------------------


def vector_ingest_block(
    *,
    key_prefix: str,
    lookups: dict,
    submit_fn: Callable[[str, dict], dict],
    context: Context = "sensor",
) -> None:
    """Render the vector / spectral ingest UI and submit via ``submit_fn(mode, payload)``."""
    _ensure_state(key_prefix, "parsed", "parse_errors")

    equipment_lookup = lookups["equipment"]
    parameters_lookup = lookups["parameters"]
    units_lookup = lookups["units"]
    axes_lookup = lookups["binning_axes"]
    processing_degrees_lookup = lookups["operation_kinds"]
    sensor_provenance_name = _sensor_provenance_name(lookups)

    with st.container(border=True):
        st.subheader("Channel Identity")

        vector_ingest_mode = st.radio(
            "Ingest mode",
            ["Tagless (direct-connect)", "Tagged (SCADA)"],
            horizontal=True,
            key=f"{key_prefix}_ingest_mode",
        )

        _das_lookup = lookups.get("das", [])
        _tags_fn = lookups.get("tags_fn")

        if vector_ingest_mode == "Tagless (direct-connect)":
            col_das, col_equip = st.columns(2)
            with col_das:
                if _das_lookup:
                    _das_names_tl = [d["name"] for d in _das_lookup]
                    _sel_das_tl = st.selectbox(
                        "DAS",
                        options=_das_names_tl,
                        index=None,
                        placeholder="Select DAS...",
                        key=f"{key_prefix}_das_name_tagless",
                    )
                    vector_das_name = _sel_das_tl or ""
                else:
                    vector_das_name = st.text_input(
                        "DAS name", value="DirectConnect", key=f"{key_prefix}_das_name_tagless"
                    )
            with col_equip:
                equipment_options = [
                    {"id": e["equipment_id"], "label": e["identifier"]} for e in equipment_lookup
                ]
                equipment_labels = [opt["label"] for opt in equipment_options]
                selected_equipment_label = st.selectbox(
                    "Equipment",
                    options=equipment_labels,
                    index=None,
                    placeholder="Select equipment...",
                    key=f"{key_prefix}_equipment_tagless",
                    help="Physical instrument this channel is directly connected to",
                )
            vector_equipment_name = selected_equipment_label
            vector_tag = None
            vector_channel_role = None
        else:
            col_das, col_tag, col_spt = st.columns(3)
            with col_das:
                if _das_lookup:
                    _das_names_tg = [d["name"] for d in _das_lookup]
                    _sel_das_tg = st.selectbox(
                        "DAS",
                        options=_das_names_tg,
                        index=None,
                        placeholder="Select DAS...",
                        key=f"{key_prefix}_das_name_tagged",
                    )
                    vector_das_name = _sel_das_tg or ""
                    _vector_das_id = next(
                        (d["das_id"] for d in _das_lookup if d["name"] == _sel_das_tg),
                        None,
                    )
                else:
                    vector_das_name = st.text_input(
                        "DAS name", value="", placeholder="e.g. SCADA_OPC", key=f"{key_prefix}_das_name_tagged"
                    )
                    _vector_das_id = None
            with col_tag:
                if _das_lookup and _tags_fn and _vector_das_id is not None:
                    _tag_cache_key = f"{key_prefix}_tags_cache_{_vector_das_id}"
                    if _tag_cache_key not in st.session_state:
                        try:
                            st.session_state[_tag_cache_key] = [
                                t["name"] for t in _tags_fn(_vector_das_id)
                            ]
                        except Exception:
                            st.session_state[_tag_cache_key] = []
                    vector_tag = st.selectbox(
                        "Tag",
                        options=st.session_state[_tag_cache_key],
                        index=None,
                        placeholder="Select tag...",
                        key=f"{key_prefix}_tag",
                    )
                else:
                    vector_tag = st.text_input(
                        "Tag", value="", placeholder="e.g. PLC1.PSD_sensor", key=f"{key_prefix}_tag"
                    )
            with col_spt:
                vector_channel_role = st.selectbox(
                    "Channel role",
                    options=["value", "status", "alarm", "uncertainty"],
                    index=0,
                    key=f"{key_prefix}_channel_role",
                )
            vector_equipment_name = None

        col2, col3 = st.columns(2)
        with col2:
            parameter_options = [
                {"id": p["parameter_id"], "label": p["parameter_name"]} for p in parameters_lookup
            ]
            parameter_labels = [opt["label"] for opt in parameter_options]
            vector_parameter_name = st.selectbox(
                "Parameter",
                options=parameter_labels,
                index=None,
                placeholder="Select parameter...",
                key=f"{key_prefix}_parameter",
                help="Measured analyte or parameter (e.g. TSS, pH)",
            )
        with col3:
            unit_options = [{"id": u["unit_id"], "label": u["unit"]} for u in units_lookup]
            unit_labels = [opt["label"] for opt in unit_options]
            vector_unit_name = st.selectbox(
                "Unit",
                options=unit_labels,
                index=None,
                placeholder="Select unit...",
                key=f"{key_prefix}_unit",
                help="Unit of measurement for values stored in this channel (e.g. mg/L, NTU)",
            )

        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown(f"**Data Provenance:** {sensor_provenance_name}")
            vector_data_provenance_id = 1
        with col5:
            processing_options = [
                {"id": d["operation_kind_id"], "label": d["name"]} for d in processing_degrees_lookup
            ]
            processing_labels = [opt["label"] for opt in processing_options]
            selected_processing_label = st.selectbox(
                "Processing Degree", options=processing_labels, index=0, key=f"{key_prefix}_processing"
            )
            vector_operation_kind_id = next(
                (opt["id"] for opt in processing_options if opt["label"] == selected_processing_label),
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
                key=f"{key_prefix}_axis",
            )
            vector_axis_id = next(
                (opt["id"] for opt in axis_options if opt["label"] == selected_axis_label),
                None,
            )
            vector_n_bins = next(
                (a["number_of_bins"] for a in axes_lookup if a["value_binning_axis_id"] == vector_axis_id),
                0,
            )

    if vector_axis_id and vector_n_bins > 0:
        st.info(
            f"CSV format: timestamp, bin_0, bin_1, ..., bin_{vector_n_bins - 1} "
            f"({vector_n_bins} value columns). First row may be a header."
        )

    with st.container(border=True):
        st.subheader("Data")
        vector_input_mode = st.radio(
            "Input method",
            ["Paste CSV", "Upload CSV file"],
            horizontal=True,
            key=f"{key_prefix}_input_mode",
        )
        vector_raw_csv = ""
        if vector_input_mode == "Paste CSV":
            vector_raw_csv = st.text_area(
                "Paste CSV data",
                placeholder="""timestamp,bin_0,bin_1,...
2024-01-15T08:00:00,0.1,0.2,0.3,...
2024-01-15T08:15:00,0.15,0.25,0.35,...""",
                height=200,
                key=f"{key_prefix}_text_area",
            )
        else:
            uploaded = st.file_uploader(
                "Choose CSV file", type=["csv"], key=f"{key_prefix}_file_uploader"
            )
            if uploaded is not None:
                vector_raw_csv = uploaded.read().decode("utf-8")

    def parse_vector_csv(csv_text: str, expected_bins: int) -> tuple[list[dict], list[str]]:
        observations: list[dict] = []
        errors: list[str] = []
        if not csv_text.strip():
            return observations, errors
        csv_text = csv_text.lstrip("﻿")
        try:
            reader = csv.reader(StringIO(csv_text))
            rows = list(reader)
            if not rows:
                return observations, errors
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
                        errors.append(f"Row {idx}: Invalid timestamp format: {timestamp_str}")
                        continue
                    values: list[float | None] = []
                    for val_str in row[1:]:
                        val_str = val_str.strip()
                        if val_str == "":
                            values.append(None)
                        else:
                            try:
                                values.append(float(val_str))
                            except ValueError:
                                errors.append(f"Row {idx}: Invalid numeric value: {val_str}")
                                values.append(None)
                    while len(values) < expected_bins:
                        values.append(None)
                    if len(values) > expected_bins:
                        values = values[:expected_bins]
                        errors.append(f"Row {idx}: Extra values truncated to {expected_bins} bins")
                    observations.append({"timestamp": timestamp, "bin_values": values, "quality_code": None})
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        return observations, errors

    last_raw_key = f"{key_prefix}_last_raw_csv"
    parsed_key = f"{key_prefix}_parsed"
    errors_key = f"{key_prefix}_parse_errors"

    if vector_raw_csv.strip() and vector_axis_id:
        if (
            st.button("Preview", type="secondary", key=f"{key_prefix}_preview_btn")
            or vector_raw_csv != st.session_state.get(last_raw_key, "")
        ):
            observations, parse_errors = parse_vector_csv(vector_raw_csv, vector_n_bins)
            st.session_state[parsed_key] = observations
            st.session_state[errors_key] = parse_errors
            st.session_state[last_raw_key] = vector_raw_csv

    if st.session_state.get(parsed_key) or st.session_state.get(errors_key):
        if st.session_state.get(errors_key):
            st.warning(f"{len(st.session_state[errors_key])} parsing issues found.")
            with st.expander("Parse errors"):
                for err in st.session_state[errors_key]:
                    st.text(err)
        if st.session_state.get(parsed_key):
            preview_data = []
            display_bins = min(vector_n_bins, 10)
            for obs in st.session_state[parsed_key][:5]:
                row: dict[str, Any] = {"timestamp": obs["timestamp"]}
                for i in range(display_bins):
                    row[f"bin_{i}"] = obs["bin_values"][i] if i < len(obs["bin_values"]) else None
                preview_data.append(row)
            preview_df = pd.DataFrame(preview_data)
            st.dataframe(preview_df, use_container_width=True)
            st.caption(
                f"Showing first {min(len(st.session_state[parsed_key]), 5)} observations "
                f"and first {display_bins} bins of {vector_n_bins}"
            )

    st.markdown("---")

    # Timezone selector for CSV data
    source_tz = _timezone_selector(
        key=f"{key_prefix}_csv_timezone",
        label="CSV timezone",
    )

    vector_valid_obs = st.session_state.get(parsed_key, [])
    if vector_ingest_mode == "Tagless (direct-connect)":
        has_required = all(
            [vector_das_name, vector_equipment_name, vector_parameter_name, vector_unit_name, vector_axis_id]
        )
    else:
        has_required = all(
            [vector_das_name, vector_tag, vector_parameter_name, vector_unit_name, vector_axis_id]
        )
    submit_disabled = len(vector_valid_obs) == 0 or not has_required

    if not has_required and len(vector_valid_obs) > 0:
        if vector_ingest_mode == "Tagless (direct-connect)":
            st.info("Please select DAS name, Equipment, Parameter, Unit, and Axis to enable submission.")
        else:
            st.info("Please enter DAS name, Tag, select Parameter, Unit, and Axis to enable submission.")

    if st.button(
        "Submit to Database",
        disabled=submit_disabled,
        type="primary",
        key=f"{key_prefix}_submit_btn",
    ):
        observations_payload = [
            {
                "timestamp": obs["timestamp"].replace(tzinfo=source_tz).astimezone(timezone.utc).isoformat(),
                "bin_values": obs["bin_values"],
                "quality_code": obs["quality_code"],
            }
            for obs in vector_valid_obs
        ]
        _strict = bool(lookups.get("das"))
        if vector_ingest_mode == "Tagless (direct-connect)":
            payload = {
                "das_name": vector_das_name,
                "equipment_name": vector_equipment_name,
                "parameter_name": vector_parameter_name,
                "unit_name": vector_unit_name,
                "binning_axis_id": vector_axis_id,
                "data_provenance_kind_id": vector_data_provenance_id,
                "strict": _strict,
                "observations": observations_payload,
            }
            mode = "tagless"
        else:
            payload = {
                "das_name": vector_das_name,
                "tag": vector_tag,
                "channel_kind": vector_channel_role,
                "parameter_name": vector_parameter_name,
                "unit_name": vector_unit_name,
                "binning_axis_id": vector_axis_id,
                "data_provenance_kind_id": vector_data_provenance_id,
                "strict": _strict,
                "observations": observations_payload,
            }
            mode = "tagged"
        try:
            with st.spinner("Submitting..."):
                result = submit_fn(mode, payload)
            st.success(
                f"✅ Ingested {result['rows_written']} rows into channel **{result['channel_id']}**"
            )
            st.session_state[parsed_key] = []
            st.session_state[errors_key] = []
            st.session_state[last_raw_key] = ""
        except APIError as e:
            st.error(f"Ingest failed: {e.message}")


# ---------------------------------------------------------------------------
# Matrix
# ---------------------------------------------------------------------------


def matrix_ingest_block(
    *,
    key_prefix: str,
    lookups: dict,
    submit_fn: Callable[[str, dict], dict],
    context: Context = "sensor",
) -> None:
    """Render the matrix / 2D-distribution ingest UI and submit via ``submit_fn(mode, payload)``."""
    _ensure_state(key_prefix, "parsed", "parse_errors")

    equipment_lookup = lookups["equipment"]
    parameters_lookup = lookups["parameters"]
    units_lookup = lookups["units"]
    axes_lookup = lookups["binning_axes"]
    processing_degrees_lookup = lookups["operation_kinds"]
    sensor_provenance_name = _sensor_provenance_name(lookups)

    with st.container(border=True):
        st.subheader("Channel Identity")
        matrix_ingest_mode = st.radio(
            "Ingest mode",
            ["Tagless (direct-connect)", "Tagged (SCADA)"],
            horizontal=True,
            key=f"{key_prefix}_ingest_mode",
        )

        _das_lookup = lookups.get("das", [])
        _tags_fn = lookups.get("tags_fn")

        if matrix_ingest_mode == "Tagless (direct-connect)":
            col_das, col_equip = st.columns(2)
            with col_das:
                if _das_lookup:
                    _das_names_tl = [d["name"] for d in _das_lookup]
                    _sel_das_tl = st.selectbox(
                        "DAS",
                        options=_das_names_tl,
                        index=None,
                        placeholder="Select DAS...",
                        key=f"{key_prefix}_das_name_tagless",
                    )
                    matrix_das_name = _sel_das_tl or ""
                else:
                    matrix_das_name = st.text_input(
                        "DAS name", value="DirectConnect", key=f"{key_prefix}_das_name_tagless"
                    )
            with col_equip:
                equipment_options = [
                    {"id": e["equipment_id"], "label": e["identifier"]} for e in equipment_lookup
                ]
                equipment_labels = [opt["label"] for opt in equipment_options]
                selected_equipment_label = st.selectbox(
                    "Equipment",
                    options=equipment_labels,
                    index=None,
                    placeholder="Select equipment...",
                    key=f"{key_prefix}_equipment_tagless",
                    help="Physical instrument this channel is directly connected to",
                )
            matrix_equipment_name = selected_equipment_label
            matrix_tag = None
            matrix_channel_role = None
        else:
            col_das, col_tag, col_spt = st.columns(3)
            with col_das:
                if _das_lookup:
                    _das_names_tg = [d["name"] for d in _das_lookup]
                    _sel_das_tg = st.selectbox(
                        "DAS",
                        options=_das_names_tg,
                        index=None,
                        placeholder="Select DAS...",
                        key=f"{key_prefix}_das_name_tagged",
                    )
                    matrix_das_name = _sel_das_tg or ""
                    _matrix_das_id = next(
                        (d["das_id"] for d in _das_lookup if d["name"] == _sel_das_tg),
                        None,
                    )
                else:
                    matrix_das_name = st.text_input(
                        "DAS name", value="", placeholder="e.g. SCADA_OPC", key=f"{key_prefix}_das_name_tagged"
                    )
                    _matrix_das_id = None
            with col_tag:
                if _das_lookup and _tags_fn and _matrix_das_id is not None:
                    _tag_cache_key = f"{key_prefix}_tags_cache_{_matrix_das_id}"
                    if _tag_cache_key not in st.session_state:
                        try:
                            st.session_state[_tag_cache_key] = [
                                t["name"] for t in _tags_fn(_matrix_das_id)
                            ]
                        except Exception:
                            st.session_state[_tag_cache_key] = []
                    matrix_tag = st.selectbox(
                        "Tag",
                        options=st.session_state[_tag_cache_key],
                        index=None,
                        placeholder="Select tag...",
                        key=f"{key_prefix}_tag",
                    )
                else:
                    matrix_tag = st.text_input(
                        "Tag", value="", placeholder="e.g. PLC1.PSD_sensor", key=f"{key_prefix}_tag"
                    )
            with col_spt:
                matrix_channel_role = st.selectbox(
                    "Channel role",
                    options=["value", "status", "alarm", "uncertainty"],
                    index=0,
                    key=f"{key_prefix}_channel_role",
                )
            matrix_equipment_name = None

        col2, col3 = st.columns(2)
        with col2:
            parameter_options = [
                {"id": p["parameter_id"], "label": p["parameter_name"]} for p in parameters_lookup
            ]
            parameter_labels = [opt["label"] for opt in parameter_options]
            matrix_parameter_name = st.selectbox(
                "Parameter",
                options=parameter_labels,
                index=None,
                placeholder="Select parameter...",
                key=f"{key_prefix}_parameter",
                help="Measured analyte or parameter (e.g. TSS, pH)",
            )
        with col3:
            unit_options = [{"id": u["unit_id"], "label": u["unit"]} for u in units_lookup]
            unit_labels = [opt["label"] for opt in unit_options]
            matrix_unit_name = st.selectbox(
                "Unit",
                options=unit_labels,
                index=None,
                placeholder="Select unit...",
                key=f"{key_prefix}_unit",
                help="Unit of measurement for values stored in this channel (e.g. mg/L, NTU)",
            )

        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown(f"**Data Provenance:** {sensor_provenance_name}")
            matrix_data_provenance_id = 1
        with col5:
            processing_options = [
                {"id": d["operation_kind_id"], "label": d["name"]} for d in processing_degrees_lookup
            ]
            processing_labels = [opt["label"] for opt in processing_options]
            selected_processing_label = st.selectbox(
                "Processing Degree", options=processing_labels, index=0, key=f"{key_prefix}_processing"
            )
            matrix_operation_kind_id = next(
                (opt["id"] for opt in processing_options if opt["label"] == selected_processing_label),
                None,
            )
        with col6:
            st.markdown("&nbsp;")

    axis_col1, axis_col2 = st.columns(2)
    axis_options = [
        {
            "id": a["value_binning_axis_id"],
            "label": f"{a['name']} ({a['number_of_bins']} bins)",
        }
        for a in axes_lookup
    ]
    axis_labels = [opt["label"] for opt in axis_options]
    with axis_col1:
        selected_row_axis_label = st.selectbox(
            "Row Axis",
            options=axis_labels,
            index=None,
            placeholder="Select row axis...",
            key=f"{key_prefix}_row_axis",
        )
        matrix_row_axis_id = next(
            (opt["id"] for opt in axis_options if opt["label"] == selected_row_axis_label),
            None,
        )
        matrix_n_row_bins = next(
            (a["number_of_bins"] for a in axes_lookup if a["value_binning_axis_id"] == matrix_row_axis_id),
            0,
        )
    with axis_col2:
        selected_col_axis_label = st.selectbox(
            "Column Axis",
            options=axis_labels,
            index=None,
            placeholder="Select column axis...",
            key=f"{key_prefix}_col_axis",
        )
        matrix_col_axis_id = next(
            (opt["id"] for opt in axis_options if opt["label"] == selected_col_axis_label),
            None,
        )
        matrix_n_col_bins = next(
            (a["number_of_bins"] for a in axes_lookup if a["value_binning_axis_id"] == matrix_col_axis_id),
            0,
        )

    if matrix_row_axis_id and matrix_col_axis_id:
        total_values = matrix_n_row_bins * matrix_n_col_bins
        st.info(
            f"CSV columns: timestamp + {total_values} values "
            f"(row-major: r0c0, r0c1, ..., r{matrix_n_row_bins - 1}c{matrix_n_col_bins - 1})"
        )

    with st.container(border=True):
        st.subheader("Data")
        matrix_input_mode = st.radio(
            "Input method",
            ["Paste CSV", "Upload CSV file"],
            horizontal=True,
            key=f"{key_prefix}_input_mode",
        )
        matrix_raw_csv = ""
        if matrix_input_mode == "Paste CSV":
            matrix_raw_csv = st.text_area(
                "Paste CSV data",
                placeholder=f"""timestamp,r0c0,r0c1,...,r0c{matrix_n_col_bins - 1},r1c0,...
2024-01-15T08:00:00,0.1,0.2,...
2024-01-15T08:15:00,0.15,0.25,...""",
                height=200,
                key=f"{key_prefix}_text_area",
            )
        else:
            uploaded = st.file_uploader(
                "Choose CSV file", type=["csv"], key=f"{key_prefix}_file_uploader"
            )
            if uploaded is not None:
                matrix_raw_csv = uploaded.read().decode("utf-8")

    def parse_matrix_csv(csv_text: str, n_rows: int, n_cols: int) -> tuple[list[dict], list[str]]:
        observations: list[dict] = []
        errors: list[str] = []
        expected_values = n_rows * n_cols
        if not csv_text.strip():
            return observations, errors
        csv_text = csv_text.lstrip("﻿")
        try:
            reader = csv.reader(StringIO(csv_text))
            rows = list(reader)
            if not rows:
                return observations, errors
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
                        errors.append(f"Row {idx}: Invalid timestamp format: {timestamp_str}")
                        continue
                    values: list[float | None] = []
                    for val_str in row[1:]:
                        val_str = val_str.strip()
                        if val_str == "":
                            values.append(None)
                        else:
                            try:
                                values.append(float(val_str))
                            except ValueError:
                                errors.append(f"Row {idx}: Invalid numeric value: {val_str}")
                                values.append(None)
                    if len(values) < expected_values:
                        while len(values) < expected_values:
                            values.append(None)
                        errors.append(f"Row {idx}: Padded with None to reach {expected_values} values")
                    elif len(values) > expected_values:
                        values = values[:expected_values]
                        errors.append(f"Row {idx}: Truncated to {expected_values} values")
                    matrix = []
                    for i in range(n_rows):
                        row_start = i * n_cols
                        row_end = row_start + n_cols
                        matrix.append(values[row_start:row_end])
                    observations.append({"timestamp": timestamp, "matrix": matrix, "quality_code": None})
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        return observations, errors

    last_raw_key = f"{key_prefix}_last_raw_csv"
    parsed_key = f"{key_prefix}_parsed"
    errors_key = f"{key_prefix}_parse_errors"

    if matrix_raw_csv.strip() and matrix_row_axis_id and matrix_col_axis_id:
        if (
            st.button("Preview", type="secondary", key=f"{key_prefix}_preview_btn")
            or matrix_raw_csv != st.session_state.get(last_raw_key, "")
        ):
            observations, parse_errors = parse_matrix_csv(matrix_raw_csv, matrix_n_row_bins, matrix_n_col_bins)
            st.session_state[parsed_key] = observations
            st.session_state[errors_key] = parse_errors
            st.session_state[last_raw_key] = matrix_raw_csv

    if st.session_state.get(parsed_key) or st.session_state.get(errors_key):
        if st.session_state.get(errors_key):
            st.warning(f"{len(st.session_state[errors_key])} parsing issues found.")
            with st.expander("Parse errors"):
                for err in st.session_state[errors_key]:
                    st.text(err)
        if st.session_state.get(parsed_key):
            preview_data = []
            for obs in st.session_state[parsed_key]:
                row: dict[str, Any] = {"timestamp": obs["timestamp"]}
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
                f"Showing all {len(st.session_state[parsed_key])} observations "
                f"with full {matrix_n_row_bins}×{matrix_n_col_bins} matrix"
            )

    st.markdown("---")

    source_tz = _timezone_selector(
        key=f"{key_prefix}_csv_timezone",
        label="CSV timezone",
    )

    matrix_valid_obs = st.session_state.get(parsed_key, [])
    if matrix_ingest_mode == "Tagless (direct-connect)":
        has_required = all(
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
        has_required = all(
            [
                matrix_das_name,
                matrix_tag,
                matrix_parameter_name,
                matrix_unit_name,
                matrix_row_axis_id,
                matrix_col_axis_id,
            ]
        )
    submit_disabled = len(matrix_valid_obs) == 0 or not has_required

    if not has_required and len(matrix_valid_obs) > 0:
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
        disabled=submit_disabled,
        type="primary",
        key=f"{key_prefix}_submit_btn",
    ):
        observations_payload = [
            {
                "timestamp": obs["timestamp"].replace(tzinfo=source_tz).astimezone(timezone.utc).isoformat(),
                "matrix": obs["matrix"],
                "quality_code": obs["quality_code"],
            }
            for obs in matrix_valid_obs
        ]
        _strict = bool(lookups.get("das"))
        if matrix_ingest_mode == "Tagless (direct-connect)":
            payload = {
                "das_name": matrix_das_name,
                "equipment_name": matrix_equipment_name,
                "parameter_name": matrix_parameter_name,
                "unit_name": matrix_unit_name,
                "row_axis_id": matrix_row_axis_id,
                "col_axis_id": matrix_col_axis_id,
                "data_provenance_kind_id": matrix_data_provenance_id,
                "strict": _strict,
                "observations": observations_payload,
            }
            mode = "tagless"
        else:
            payload = {
                "das_name": matrix_das_name,
                "tag": matrix_tag,
                "channel_kind": matrix_channel_role,
                "parameter_name": matrix_parameter_name,
                "unit_name": matrix_unit_name,
                "row_axis_id": matrix_row_axis_id,
                "col_axis_id": matrix_col_axis_id,
                "data_provenance_kind_id": matrix_data_provenance_id,
                "strict": _strict,
                "observations": observations_payload,
            }
            mode = "tagged"
        try:
            with st.spinner("Submitting..."):
                result = submit_fn(mode, payload)
            st.success(
                f"✅ Ingested {result['rows_written']} rows into channel **{result['channel_id']}**"
            )
            st.session_state[parsed_key] = []
            st.session_state[errors_key] = []
            st.session_state[last_raw_key] = ""
        except APIError as e:
            st.error(f"Ingest failed: {e.message}")


# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------


def image_ingest_block(
    *,
    key_prefix: str,
    lookups: dict,
    submit_fn: Callable[..., dict],
    context: Context = "sensor",
    allow_folder: bool = False,
) -> None:
    """Render the image ingest UI and submit via ``submit_fn(**kwargs)``.

    ``allow_folder`` is reserved for Wave F3 (lab folder upload with replicate
    rows); currently a no-op for sensor.
    """
    del allow_folder  # reserved for Wave F3

    equipment_lookup = lookups["equipment"]
    parameters_lookup = lookups["parameters"]
    units_lookup = lookups["units"]
    _das_lookup = lookups.get("das", [])
    _tags_fn = lookups.get("tags_fn")

    with st.container(border=True):
        st.subheader("Channel Identity")

        img_mode = st.radio(
            "Ingest mode",
            ["Tagged (SCADA)", "Tagless (direct-connect)"],
            horizontal=True,
            key=f"{key_prefix}_ingest_mode",
        )

        col_das, col_id = st.columns(2)
        with col_das:
            if _das_lookup:
                _das_names = [d["name"] for d in _das_lookup]
                _sel_das = st.selectbox(
                    "DAS",
                    options=_das_names,
                    index=None,
                    placeholder="Select DAS...",
                    key=f"{key_prefix}_das",
                )
                img_das_name = _sel_das or ""
                _img_das_id = next(
                    (d["das_id"] for d in _das_lookup if d["name"] == _sel_das), None
                )
            else:
                img_das_name = st.text_input(
                    "DAS name", value="", placeholder="e.g. SCADA_OPC", key=f"{key_prefix}_das"
                )
                _img_das_id = None

        with col_id:
            if img_mode == "Tagged (SCADA)":
                if _das_lookup and _tags_fn and _img_das_id is not None:
                    _tag_cache_key = f"{key_prefix}_tags_cache_{_img_das_id}"
                    if _tag_cache_key not in st.session_state:
                        try:
                            st.session_state[_tag_cache_key] = [
                                t["name"] for t in _tags_fn(_img_das_id)
                            ]
                        except Exception:
                            st.session_state[_tag_cache_key] = []
                    img_tag = st.selectbox(
                        "Tag",
                        options=st.session_state[_tag_cache_key],
                        index=None,
                        placeholder="Select tag...",
                        key=f"{key_prefix}_tag",
                    )
                else:
                    img_tag = st.text_input(
                        "Tag", value="", placeholder="e.g. PLC1.cam", key=f"{key_prefix}_tag"
                    )
                img_equipment_name = None
            else:
                equipment_options = [
                    {"id": e["equipment_id"], "label": e["identifier"]} for e in equipment_lookup
                ]
                equipment_labels = [opt["label"] for opt in equipment_options]
                img_equipment_name = st.selectbox(
                    "Equipment",
                    options=equipment_labels,
                    index=None,
                    placeholder="Select equipment...",
                    key=f"{key_prefix}_equipment",
                    help="Physical instrument this channel is directly connected to",
                )
                img_tag = None

        col2, col3 = st.columns(2)
        with col2:
            parameter_labels = [p["parameter_name"] for p in parameters_lookup]
            img_parameter_name = st.selectbox(
                "Parameter",
                options=parameter_labels,
                index=None,
                placeholder="Select parameter...",
                key=f"{key_prefix}_parameter",
                help="Measured analyte or parameter (e.g. TSS, pH)",
            )
        with col3:
            unit_labels = [u["unit"] for u in units_lookup]
            img_unit_name = st.selectbox(
                "Unit",
                options=unit_labels,
                index=None,
                placeholder="Select unit...",
                key=f"{key_prefix}_unit",
                help="Unit of measurement (e.g. mg/L, NTU)",
            )

    with st.container(border=True):
        st.subheader("Timestamp")
        col1, col2 = st.columns(2)
        with col1:
            img_date = st.date_input("Measurement date", key=f"{key_prefix}_date")
        with col2:
            img_time = st.time_input("Measurement time", key=f"{key_prefix}_time")
        col_tz1, col_tz2 = st.columns([1, 3])
        with col_tz1:
            img_source_tz = _timezone_selector(
                key=f"{key_prefix}_timezone",
                label="Timezone",
                help="Timezone of the measurement time above. It will be converted to UTC on submit.",
            )
            img_timestamp = datetime.combine(img_date, img_time).replace(tzinfo=img_source_tz).astimezone(timezone.utc)
        with col_tz2:
            st.caption(" ")  # spacer

    with st.container(border=True):
        st.subheader("Image File")
        uploaded_image = st.file_uploader(
            "Select image file",
            type=["jpg", "jpeg", "png", "tif", "tiff", "bmp"],
            key=f"{key_prefix}_upload",
        )

        if uploaded_image is not None:
            image_bytes = uploaded_image.read()
            st.image(
                uploaded_image,
                caption=uploaded_image.name,
                use_container_width=False,
                width=300,
            )
            st.caption(f"File: {uploaded_image.name} | Size: {len(image_bytes) / 1024:.1f} KB")

            img_quality_code = st.number_input(
                "Quality code (optional)",
                value=None,
                min_value=0,
                step=1,
                key=f"{key_prefix}_qc",
            )

            if img_mode == "Tagged (SCADA)":
                img_has_required = all([img_das_name, img_tag, img_parameter_name, img_unit_name])
            else:
                img_has_required = all([img_das_name, img_equipment_name, img_parameter_name, img_unit_name])

            if st.button(
                "Upload Image",
                type="primary",
                key=f"{key_prefix}_submit",
                disabled=not img_has_required,
            ):
                try:
                    with st.spinner("Uploading..."):
                        result = submit_fn(
                            das_name=img_das_name,
                            tag=img_tag,
                            equipment_name=img_equipment_name,
                            channel_kind="value",
                            parameter_name=img_parameter_name or "",
                            unit_name=img_unit_name or "",
                            timestamp=img_timestamp.isoformat(),
                            image_bytes=image_bytes,
                            filename=uploaded_image.name,
                            quality_code=img_quality_code,
                            data_provenance_kind_id=1,
                        )
                    st.success(f"✅ Image stored at **{result['storage_path']}**")
                    st.info(
                        f"Channel ID: {result['channel_id']} | ValueImage ID: {result['value_image_id']}"
                    )
                except APIError as e:
                    st.error(f"Upload failed: {e.message}")
        else:
            st.info("Select an image file to upload.")
