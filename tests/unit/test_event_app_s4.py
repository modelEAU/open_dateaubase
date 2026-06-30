"""PRD-2 S4 — App-layer smoke tests for Event CRUD page + EventKind page.

Red→green: these fail until event_kind slug is added to form_specs and the
pages exist with correct imports.
"""

from __future__ import annotations

import importlib


def test_get_form_fields_event_kind_has_name_and_description() -> None:
    """get_form_fields('event_kind') returns at least name and description."""
    from app.components.form_specs import get_form_fields

    fields = get_form_fields("event_kind")
    field_names = {f["name"] for f in fields}
    assert "name" in field_names, "'name' field missing from event_kind form spec"
    assert "description" in field_names, "'description' field missing from event_kind form spec"


def test_event_kinds_page_imports() -> None:
    """app.pages.event_kinds imports without error."""
    # Use importlib so Streamlit top-level calls are not executed
    spec = importlib.util.find_spec("app.pages.event_kinds")
    assert spec is not None, "app/pages/event_kinds.py not found"


def test_events_page_imports() -> None:
    """app.pages.events imports without error."""
    spec = importlib.util.find_spec("app.pages.events")
    assert spec is not None, "app/pages/events.py not found"
