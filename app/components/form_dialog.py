"""Form dialog components for CRUD operations."""

from __future__ import annotations

import datetime
import streamlit as st
from typing import Callable


def _serialize_form_data(data: dict) -> dict:
    """Convert form data to JSON-serializable format.

    Handles datetime.date -> ISO format string conversion.
    """
    serialized = {}
    for key, value in data.items():
        if isinstance(value, datetime.date):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def _report(slot, errors: list[str]) -> None:
    """Render validation feedback into a placeholder above the fields."""
    with slot.container():
        if errors:
            for error in errors:
                st.error(error)
        else:
            st.success("All required fields filled!")


@st.dialog("Create New Item", width="large")
def create_form_dialog(
    fields: list[
        dict
    ],  # [{"name": "...", "type": "...", "required": bool, "options": [...]}]
    on_submit: Callable[[dict], bool],  # Returns True if successful
    title: str = "Create",
) -> None:
    """Display a create form dialog.

    Example fields:
    [
        {"name": "name", "type": "text", "required": True},
        {"name": "site_id", "type": "select", "required": True, "options": [{"id": 1, "label": "Site A"}]},
    ]
    """
    from app.components.crud_form import render_form_field, validate_required_fields

    st.write(f"### {title}")
    feedback = st.empty()  # errors belong beside the fields, not below Send

    form_data = {}
    required_fields = []

    for field in fields:
        if field.get("required"):
            required_fields.append(field["name"])
        form_data[field["name"]] = render_form_field(
            field_name=field["name"],
            field_type=field.get("type", "text"),
            required=field.get("required", False),
            options=field.get("options"),
            help_text=field.get("help"),
            label=field.get("label"),
            render_fn=field.get("render_fn"),
            max_length=field.get("max_length"),
            fk_table=field.get("fk_table"),
        )

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Validate", type="secondary"):
            errors = validate_required_fields(form_data, required_fields)
            _report(feedback, errors)
    with col2:
        if st.button("Send", type="primary"):
            errors = validate_required_fields(form_data, required_fields)
            if errors:
                _report(feedback, errors)
            else:
                serialized_data = _serialize_form_data(form_data)
                success = on_submit(serialized_data)
                if success:
                    st.rerun()
    with col3:
        if st.button("Cancel", type="secondary"):
            st.rerun()


@st.dialog("Edit Item", width="large")
def edit_form_dialog(
    item_data: dict,
    fields: list[dict],
    on_submit: Callable[[dict], bool],
    title: str = "Edit",
) -> None:
    """Display an edit form dialog pre-populated with item_data."""
    from app.components.crud_form import render_form_field, validate_required_fields

    st.write(f"### {title}")
    feedback = st.empty()  # errors belong beside the fields, not below Send

    form_data = {}
    required_fields = []

    for field in fields:
        field_name = field["name"]
        if field.get("required"):
            required_fields.append(field_name)

        # Get current value from item_data
        current_value = item_data.get(field_name)

        form_data[field_name] = render_form_field(
            field_name=field_name,
            field_type=field.get("type", "text"),
            value=current_value,
            required=field.get("required", False),
            options=field.get("options"),
            help_text=field.get("help"),
            label=field.get("label"),
            render_fn=field.get("render_fn"),
            max_length=field.get("max_length"),
            fk_table=field.get("fk_table"),
        )

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Validate", type="secondary"):
            errors = validate_required_fields(form_data, required_fields)
            _report(feedback, errors)
    with col2:
        if st.button("Send", type="primary"):
            errors = validate_required_fields(form_data, required_fields)
            if errors:
                _report(feedback, errors)
            else:
                # Include ID from original item and serialize dates
                form_data["id"] = item_data.get("id")
                serialized_data = _serialize_form_data(form_data)
                success = on_submit(serialized_data)
                if success:
                    st.rerun()
    with col3:
        if st.button("Cancel", type="secondary"):
            st.rerun()
