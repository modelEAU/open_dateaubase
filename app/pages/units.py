"""Units — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import create_unit, delete_unit, list_units_lookup, update_unit
from app.components.generic_crud import render_crud_page
from app.components.schema_registry import load_table

_schema = load_table("Unit")

render_crud_page(
    title="Units",
    pk_field="unit_id",
    form_fields=_schema.build_form_fields(),
    list_fn=list_units_lookup,
    create_fn=lambda data: create_unit(data["unit"]),
    update_fn=lambda pk, data: update_unit(pk, data["unit"]),
    delete_fn=delete_unit,
    label_field="unit",
)
