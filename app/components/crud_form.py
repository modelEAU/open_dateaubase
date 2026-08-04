"""Reusable form components for CRUD operations."""

from __future__ import annotations

import datetime
from typing import Any, Callable

import streamlit as st


def _offer_add_new(field_name: str, fk_table: str) -> int | None:
    """"+ Add new" affordance for a vocabulary-backed select.

    Reuses the entity's own CRUD form via ``entity_picker`` — same registry the
    sheet-mapper's inline create uses — so a value missing from the vocabulary
    doesn't force a detour to its admin page. Local import: ``entity_picker``
    imports this module, so importing it at module scope would be circular.
    """
    from app.components.entity_picker import can_create_from_name, create_from_name
    from app.components.schema_registry import fk_lookup_fn

    if not can_create_from_name(fk_table):
        return None
    open_key = f"_offer_add_new::{field_name}"
    if st.button(f"＋ Add new {fk_table}…", key=f"{open_key}::toggle"):
        st.session_state[open_key] = not st.session_state.get(open_key, False)
    if not st.session_state.get(open_key):
        return None
    new_name = st.text_input(
        f"New {fk_table} name",
        key=f"{open_key}::name",
        help=f"Creates a {fk_table} row and selects it for this field.",
    )
    if not st.button("Create", key=f"{open_key}::create"):
        return None
    if not new_name.strip():
        st.error("Name is required.")
        return None

    def _lookup(table: str) -> list[dict]:
        import app.api_client as api

        return getattr(api, fk_lookup_fn(table))()

    new_id = create_from_name(fk_table, new_name.strip(), _lookup)
    st.session_state[open_key] = False
    return new_id


def render_form_field(
    field_name: str,
    field_type: str = "text",
    value: Any = None,
    required: bool = False,
    options: list[dict] | None = None,  # For dropdowns: [{"id": 1, "label": "Name"}]
    help_text: str | None = None,
    label: str | None = None,
    render_fn: Callable[[dict], Any] | None = None,
    max_length: int | None = None,
    fk_table: str | None = None,
) -> Any:
    """Render a single form field based on type.

    field_type: "text" | "number" | "select" | "date" | "datetime" | "textarea"
    """
    display_name = label if label else field_name
    label_str = f"{display_name}{' *' if required else ''}"

    if render_fn is not None:
        return render_fn(
            {"field_name": field_name, "value": value, "label": label_str, "required": required}
        )

    label = label_str

    if field_type == "multiselect" and options:
        option_map = {opt["label"]: opt["id"] for opt in options}
        labels = list(option_map.keys())
        current_labels = [opt["label"] for opt in options if opt["id"] in (value or [])]
        selected = st.multiselect(label, options=labels, default=current_labels, help=help_text)
        return [option_map[lbl] for lbl in selected]
    elif field_type == "select":
        from app.components.kind_select import NONE_LABEL, kind_select

        # This widget owns the empty choice; drop any sentinel row the caller
        # prepended so it can't show up twice.
        options = [opt for opt in (options or []) if opt.get("id") is not None]

        if fk_table:
            new_id = _offer_add_new(field_name, fk_table)
            if new_id is not None:
                return new_id

        # If any option carries a description, route through kind_select so the
        # long-form description renders as a caption beneath the selectbox.
        if any(opt.get("description") for opt in options):
            return kind_select(
                label,
                options,
                id_field="id",
                name_field="label",
                desc_field="description",
                default_id=value if isinstance(value, int) else None,
                allow_empty=not required,
                help=help_text,
            )

        # Map options to display labels, return ID. Optional fields get the
        # NONE_LABEL sentinel so an unset FK isn't silently defaulted to
        # whatever option happens to be first in the list.
        none_label = NONE_LABEL
        option_map = {opt["label"]: opt["id"] for opt in options}
        labels = list(option_map.keys())
        if not required:
            option_map[none_label] = None
            labels = [none_label] + labels
        fallback = none_label if not required else (labels[0] if labels else none_label)
        current_label = next(
            (opt["label"] for opt in options if opt["id"] == value),
            fallback,
        )
        selected = st.selectbox(
            label,
            options=labels,
            index=labels.index(current_label) if current_label in labels else 0,
            help=help_text,
        )
        # A required select with no options leaves `labels` empty, so the widget
        # returns None rather than a label.
        return option_map.get(selected)
    elif field_type == "number":
        return st.number_input(label, value=value or 0, help=help_text)
    elif field_type == "date":
        return st.date_input(label, value=value, help=help_text)
    elif field_type == "datetime":
        # Handle datetime fields - combine date and time inputs
        if isinstance(value, str):
            try:
                value = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                value = None
        date_val = st.date_input(f"{label} (date)", value=value, help=help_text)
        time_val = st.time_input(
            f"{label} (time)", value=value or datetime.time(0, 0), help=help_text
        )
        # Handle case where date_input returns None (no value selected)
        if date_val is None:
            return None
        return datetime.datetime.combine(date_val, time_val)
    elif field_type == "checkbox":
        return st.checkbox(label, value=bool(value), help=help_text)
    elif field_type == "textarea":
        return st.text_area(label, value=value or "", help=help_text, max_chars=max_length)
    else:  # text
        return st.text_input(label, value=value or "", help=help_text, max_chars=max_length)


def validate_required_fields(data: dict, required_fields: list[str]) -> list[str]:
    """Return list of validation errors for missing required fields."""
    errors = []
    for field in required_fields:
        value = data.get(field)
        # Booleans are always valid; flag None, empty strings, and empty lists
        if (
            value is None
            or (isinstance(value, str) and not value.strip())
            or (isinstance(value, list) and not value)
        ):
            errors.append(f"{field} is required")
    return errors
