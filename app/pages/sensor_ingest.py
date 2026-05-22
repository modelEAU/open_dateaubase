"""Sensor Data Ingest page with Scalar, Vector, Matrix, and Image tabs.

Thin caller around the reusable blocks in
``app.components.ingest_shapes``. Lab ingest (Wave F3) reuses the same blocks
with ``context="lab"`` and lab-specific submit fns.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from app.api_client import (
    APIError,
    ingest_sensor,
    ingest_sensor_image,
    ingest_sensor_matrix,
    ingest_sensor_tagless,
    ingest_sensor_vector,
    list_binning_axes_lookup,
    list_das_lookup,
    list_data_provenance_lookup,
    list_equipment_lookup,
    list_parameters_lookup,
    list_processing_kinds_lookup,
    list_tags_lookup,
    list_units_lookup,
)
from app.components.ingest_shapes import (
    image_ingest_block,
    matrix_ingest_block,
    scalar_ingest_block,
    vector_ingest_block,
)


st.title("Sensor Data Ingest")
st.markdown(
    "Upload or paste timestamped sensor measurements. The channel is "
    "created automatically if it does not yet exist."
)

try:
    with st.spinner("Loading lookup data..."):
        _lookups = {
            "equipment": list_equipment_lookup(),
            "parameters": list_parameters_lookup(),
            "units": list_units_lookup(),
            "provenance": list_data_provenance_lookup(),
            "processing_kinds": list_processing_kinds_lookup(),
            "binning_axes": list_binning_axes_lookup(),
            "das": list_das_lookup(),
            "tags_fn": list_tags_lookup,
        }
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()


def _scalar_submit(mode: str, payload: dict) -> dict:
    if mode == "tagless":
        return ingest_sensor_tagless(payload)
    return ingest_sensor(payload)


def _vector_submit(mode: str, payload: dict) -> dict:
    # The vector endpoint is the same for both modes; payload shape differs.
    del mode
    return ingest_sensor_vector(payload)


def _matrix_submit(mode: str, payload: dict) -> dict:
    del mode
    return ingest_sensor_matrix(payload)


tab_scalar, tab_vector, tab_matrix, tab_image = st.tabs(
    ["Scalar", "Vector", "Matrix", "Image"]
)

with tab_scalar:
    st.subheader("Scalar Sensor Ingest")
    st.markdown(
        "Upload or paste timestamped scalar measurements (one value per timestamp)."
    )
    scalar_ingest_block(
        key_prefix="scalar",
        lookups=_lookups,
        submit_fn=_scalar_submit,
        context="sensor",
    )

with tab_vector:
    st.subheader("Vector / Spectral Sensor Ingest")
    st.markdown(
        "Each row in the CSV is one observation (one spectrum or distribution). "
        "Columns: timestamp, then one column per bin in order of BinIndex."
    )
    vector_ingest_block(
        key_prefix="vector",
        lookups=_lookups,
        submit_fn=_vector_submit,
        context="sensor",
    )

with tab_matrix:
    st.subheader("Matrix / 2D Distribution Sensor Ingest")
    st.markdown(
        "Each observation is one 2D matrix at one timestamp. "
        "CSV format: first column is timestamp, then one column per (row_bin_index, col_bin_index) "
        "pair in row-major order — i.e., all col values for row 0, then all col values for row 1."
    )
    matrix_ingest_block(
        key_prefix="matrix",
        lookups=_lookups,
        submit_fn=_matrix_submit,
        context="sensor",
    )

with tab_image:
    st.subheader("Image / Camera Sensor Ingest")
    st.markdown(
        "Upload a single image captured by a sensor at a known timestamp. "
        "The file is stored on the server and linked to an auto-created image channel."
    )
    image_ingest_block(
        key_prefix="img",
        lookups=_lookups,
        submit_fn=ingest_sensor_image,
        context="sensor",
    )
