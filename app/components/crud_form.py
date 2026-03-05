"""Reusable form components for CRUD operations."""

from __future__ import annotations

import streamlit as st
from typing import Any


def render_form_field(
    field_name: str,
    field_type: str,
    value: Any = None,
    required: bool = False,
    options: list[dict] | None = None,  # For dropdowns: [{"id": 1, "label": "Name"}]
    help_text: str | None = None,
) -> Any:
    """Render a single form field based on type.

    field_type: "text" | "number" | "select" | "date" | "textarea"
    """
    label = f"{field_name}{' *' if required else ''}"

    if field_type == "select" and options:
        # Map options to display labels, return ID
        option_map = {opt["label"]: opt["id"] for opt in options}
        labels = list(option_map.keys())
        current_label = next(
            (opt["label"] for opt in options if opt["id"] == value),
            labels[0] if labels else None,
        )
        selected = st.selectbox(
            label,
            options=labels,
            index=labels.index(current_label) if current_label in labels else 0,
            help=help_text,
        )
        return option_map[selected]
    elif field_type == "number":
        return st.number_input(label, value=value or 0, help=help_text)
    elif field_type == "date":
        return st.date_input(label, value=value, help=help_text)
    elif field_type == "textarea":
        return st.text_area(label, value=value or "", help=help_text)
    else:  # text
        return st.text_input(label, value=value or "", help=help_text)


def validate_required_fields(data: dict, required_fields: list[str]) -> list[str]:
    """Return list of validation errors for missing required fields."""
    errors = []
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field} is required")
    return errors
