"""Form dialog components for CRUD operations."""

from __future__ import annotations

import streamlit as st
from typing import Callable


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

    form_data = {}
    required_fields = []

    for field in fields:
        if field.get("required"):
            required_fields.append(field["name"])
        form_data[field["name"]] = render_form_field(
            field_name=field["name"],
            field_type=field["type"],
            required=field.get("required", False),
            options=field.get("options"),
            help_text=field.get("help"),
        )

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Validate", type="secondary"):
            errors = validate_required_fields(form_data, required_fields)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.success("All required fields filled!")
    with col2:
        if st.button("Send", type="primary"):
            errors = validate_required_fields(form_data, required_fields)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                success = on_submit(form_data)
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
            field_type=field["type"],
            value=current_value,
            required=field.get("required", False),
            options=field.get("options"),
            help_text=field.get("help"),
        )

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Validate", type="secondary"):
            errors = validate_required_fields(form_data, required_fields)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.success("All required fields filled!")
    with col2:
        if st.button("Send", type="primary"):
            errors = validate_required_fields(form_data, required_fields)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Include ID from original item
                form_data["id"] = item_data.get("id")
                success = on_submit(form_data)
                if success:
                    st.rerun()
    with col3:
        if st.button("Cancel", type="secondary"):
            st.rerun()
