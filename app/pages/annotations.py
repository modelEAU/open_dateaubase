"""Annotations CRUD page with form-based editing."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from datetime import datetime
from typing import Any

import streamlit as st
import pandas as pd

from app.api_client import (
    APIError,
    create_annotation,
    delete_annotation,
    list_annotations,
    list_channels,
    update_annotation,
)
from app.components.form_dialog import create_form_dialog, edit_form_dialog
from app.components.form_specs import get_form_fields
from app.components.id_format import humanize_id_columns



st.title("Annotations")

# Load channels for dropdown (limited to first 100)
try:
    with st.spinner("Loading..."):
        channels_data = list_channels(page_size=100)
        channels = (
            channels_data.get("items", [])
            if isinstance(channels_data, dict)
            else channels_data
        )
except APIError as e:
    st.error(f"Cannot load channels: {e.message}")
    channels = []

# Prepare channel options for dropdown
channel_options = [
    {"id": c["channel_id"], "label": f"Channel {c['channel_id']}"} for c in channels
]

# Also try to get more descriptive labels if available
for i, opt in enumerate(channel_options):
    c = channels[i]
    # Build a more descriptive label if possible
    parts = []
    if c.get("parameter_name"):
        parts.append(c["parameter_name"])
    if c.get("equipment_identifier"):
        parts.append(f"({c['equipment_identifier']})")
    if parts:
        opt["label"] = " - ".join(parts)

# Load annotations
try:
    with st.spinner("Loading annotations..."):
        annotations_data = list_annotations()
        annotations = (
            annotations_data.get("items", [])
            if isinstance(annotations_data, dict)
            else annotations_data
        )
except APIError as e:
    st.error(f"Cannot load annotations: {e.message}")
    annotations = []


# Handler functions
def handle_create_annotation(data: dict) -> bool:
    # The page anchors annotations to a sensor Channel: its channel_id is the
    # Stream_ID, and the anchor arm is "channel". Lab series are not selectable
    # here, so anchor_kind is always "channel".
    stream_id = data.pop("channel_id", None)
    try:
        create_annotation(stream_id=stream_id, data=data, anchor_kind="channel")
        st.success("Annotation created successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to create annotation: {e.message}")
        return False


def handle_update_annotation(annotation_id: int, data: dict) -> bool:
    try:
        update_annotation(annotation_id, data)
        st.success("Annotation updated successfully!")
        return True
    except APIError as e:
        st.error(f"Failed to update annotation: {e.message}")
        return False


def handle_delete_annotation(annotation_id: int) -> None:
    try:
        delete_annotation(annotation_id)
        st.success("Annotation deleted successfully!")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete annotation: {e.message}")


# channel_id is the UI anchor (popped to stream_id on submit); the rest are the
# AnnotationCreate contract minus observation_id (set server-side from the anchor).
def _annotation_fields() -> list[dict]:
    return [
        {"name": "channel_id", "type": "select", "required": True, "options": channel_options},
        *get_form_fields("annotation"),
    ]


# Action buttons
col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=_annotation_fields(),
            on_submit=lambda data: handle_create_annotation(data),
            title="Create New Annotation",
        )

# Store selected row
if "selected_annotation_id" not in st.session_state:
    st.session_state.selected_annotation_id = None

# Display table
if annotations:
    df = pd.DataFrame(annotations)
    selected_indices = st.dataframe(
        humanize_id_columns(df, pk_field="annotation_id"),
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_indices and selected_indices.get("selection", {}).get("rows"):
        row_idx = selected_indices["selection"]["rows"][0]
        st.session_state.selected_annotation_id = df.iloc[row_idx]["annotation_id"]
        selected_item = annotations[row_idx]
    else:
        selected_item = None
        st.session_state.selected_annotation_id = None
else:
    st.info("No annotations found. Click 'New' to create one.")
    selected_item = None

with col2:
    if st.button("✏️ Edit", disabled=selected_item is None):
        if selected_item:
            edit_form_dialog(
                item_data=selected_item,
                fields=_annotation_fields(),
                on_submit=lambda data: handle_update_annotation(
                    selected_item["annotation_id"], data
                ),
                title=f"Edit Annotation: {selected_item.get('title', 'Untitled')}",
            )

with col3:
    if st.button("🗑️ Delete", disabled=selected_item is None, type="secondary"):
        if selected_item:
            handle_delete_annotation(selected_item["annotation_id"])
