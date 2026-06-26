"""Units — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import create_unit, delete_unit, list_units_lookup, update_unit
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

render_crud_page(
    title="Units",
    pk_field="unit_id",
    form_fields=get_form_fields("unit"),
    list_fn=list_units_lookup,
    create_fn=create_unit,
    update_fn=update_unit,
    delete_fn=delete_unit,
    label_field="unit",
)
