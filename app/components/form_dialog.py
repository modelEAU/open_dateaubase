"""Form dialog components for CRUD operations."""

from __future__ import annotations

import datetime
import streamlit as st
from typing import Callable

# Sentinel label appended to selects that support inline item creation
_ADD_NEW_LABEL = "➕ Add new..."

# Session-state keys for sub-form state (single modal at a time is fine)
_SF_ACTIVE = "_sf_active"
_SF_FIELD = "_sf_field"


def _extra_opts_key(field_name: str) -> str:
    return f"_sf_extra_opts_{field_name}"


def _preselect_key(field_name: str) -> str:
    return f"_sf_preselect_{field_name}"


def _serialize_form_data(data: dict) -> dict:
    """Convert form data to JSON-serializable format."""
    serialized = {}
    for key, value in data.items():
        if isinstance(value, datetime.date):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def _cleanup_sf_state(fields: list[dict]) -> None:
    """Remove all sub-form session-state keys for the given fields."""
    st.session_state.pop(_SF_ACTIVE, None)
    st.session_state.pop(_SF_FIELD, None)
    for field in fields:
        if "add_new" in field:
            st.session_state.pop(_extra_opts_key(field["name"]), None)
            st.session_state.pop(_preselect_key(field["name"]), None)


def _render_select_with_add_new(field: dict, current_value=None) -> int | None:
    """Render a select field that supports inline creation of new options.

    Returns the selected id, or None if nothing is selected.
    If the user picks the add-new sentinel, sets session state and reruns.
    """
    field_name = field["name"]
    required = field.get("required", False)
    label = f"{field_name}{' *' if required else ''}"

    # Merge base options with any newly-created extras
    base_options: list[dict] = list(field.get("options") or [])
    extra: list[dict] = list(st.session_state.get(_extra_opts_key(field_name), []))
    all_options = base_options + extra

    # Check if there is a freshly-created pre-selection
    preselect_id = st.session_state.pop(_preselect_key(field_name), None)
    effective_value = preselect_id if preselect_id is not None else current_value

    option_map = {opt["label"]: opt["id"] for opt in all_options}
    labels = list(option_map.keys()) + [_ADD_NEW_LABEL]

    current_label = next(
        (opt["label"] for opt in all_options if opt["id"] == effective_value),
        labels[0] if labels[:-1] else None,
    )
    idx = labels.index(current_label) if current_label in labels else 0

    selected_label = st.selectbox(label, options=labels, index=idx, help=field.get("help"))

    if selected_label == _ADD_NEW_LABEL:
        st.session_state[_SF_ACTIVE] = True
        st.session_state[_SF_FIELD] = field_name
        st.rerun()

    return option_map.get(selected_label)


def _render_main_form(fields: list[dict], initial_values: dict | None = None):
    """Render all fields of the main form. Returns (form_data, required_fields)."""
    from app.components.crud_form import render_form_field

    form_data = {}
    required_fields = []
    initial_values = initial_values or {}

    for field in fields:
        field_name = field["name"]
        if field.get("required"):
            required_fields.append(field_name)
        current_value = initial_values.get(field_name)

        if field["type"] == "select" and "add_new" in field:
            form_data[field_name] = _render_select_with_add_new(field, current_value)
        else:
            form_data[field_name] = render_form_field(
                field_name=field_name,
                field_type=field["type"],
                value=current_value,
                required=field.get("required", False),
                options=field.get("options"),
                help_text=field.get("help"),
            )

    return form_data, required_fields


def _render_sub_form(fields: list[dict]) -> None:
    """Render the inline sub-form for creating a new linked item."""
    from app.components.crud_form import render_form_field, validate_required_fields

    active_field_name = st.session_state.get(_SF_FIELD)
    active_field = next((f for f in fields if f["name"] == active_field_name), None)
    if active_field is None:
        st.session_state.pop(_SF_ACTIVE, None)
        st.session_state.pop(_SF_FIELD, None)
        st.rerun()

    add_new_cfg = active_field["add_new"]
    st.write(f"### {add_new_cfg.get('title', 'Add New')}")

    sub_data: dict = {}
    sub_required: list[str] = []

    for sf in add_new_cfg.get("fields", []):
        if sf.get("required"):
            sub_required.append(sf["name"])
        sub_data[sf["name"]] = render_form_field(
            field_name=sf["name"],
            field_type=sf["type"],
            required=sf.get("required", False),
            options=sf.get("options"),
            help_text=sf.get("help"),
        )

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("← Back", type="secondary"):
            st.session_state.pop(_SF_ACTIVE, None)
            st.session_state.pop(_SF_FIELD, None)
            st.rerun()
    with col2:
        if st.button("OK", type="primary"):
            errors = validate_required_fields(sub_data, sub_required)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                on_create = add_new_cfg.get("on_create")
                new_option = on_create(sub_data) if on_create else None
                if new_option:
                    key = _extra_opts_key(active_field_name)
                    existing = list(st.session_state.get(key, []))
                    existing.append(new_option)
                    st.session_state[key] = existing
                    st.session_state[_preselect_key(active_field_name)] = new_option["id"]
                    st.session_state.pop(_SF_ACTIVE, None)
                    st.session_state.pop(_SF_FIELD, None)
                    st.rerun()


@st.dialog("Create New Item", width="large")
def create_form_dialog(
    fields: list[dict],
    on_submit: Callable[[dict], bool],
    title: str = "Create",
) -> None:
    """Display a create form dialog.

    Select fields may include an ``add_new`` config for inline item creation::

        {
            "name": "unit_id",
            "type": "select",
            "options": [...],
            "add_new": {
                "title": "Add New Unit",
                "fields": [{"name": "unit", "type": "text", "required": True}],
                "on_create": callable,  # fn(data) -> {"id": int, "label": str} | None
            },
        }
    """
    from app.components.crud_form import validate_required_fields

    st.write(f"### {title}")

    if st.session_state.get(_SF_ACTIVE):
        _render_sub_form(fields)
        return

    form_data, required_fields = _render_main_form(fields)

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
                serialized_data = _serialize_form_data(form_data)
                success = on_submit(serialized_data)
                if success:
                    _cleanup_sf_state(fields)
                    st.rerun()
    with col3:
        if st.button("Cancel", type="secondary"):
            _cleanup_sf_state(fields)
            st.rerun()


@st.dialog("Edit Item", width="large")
def edit_form_dialog(
    item_data: dict,
    fields: list[dict],
    on_submit: Callable[[dict], bool],
    title: str = "Edit",
) -> None:
    """Display an edit form dialog pre-populated with item_data.

    Supports the same ``add_new`` config on select fields as :func:`create_form_dialog`.
    """
    from app.components.crud_form import validate_required_fields

    st.write(f"### {title}")

    if st.session_state.get(_SF_ACTIVE):
        _render_sub_form(fields)
        return

    form_data, required_fields = _render_main_form(fields, initial_values=item_data)

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
                form_data["id"] = item_data.get("id")
                serialized_data = _serialize_form_data(form_data)
                success = on_submit(serialized_data)
                if success:
                    _cleanup_sf_state(fields)
                    st.rerun()
    with col3:
        if st.button("Cancel", type="secondary"):
            _cleanup_sf_state(fields)
            st.rerun()
