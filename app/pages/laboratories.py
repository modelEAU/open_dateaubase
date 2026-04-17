"""Laboratories — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_laboratory,
    delete_laboratory,
    list_laboratories_lookup,
    update_laboratory,
)
from app.components.generic_crud import render_crud_page
from app.components.schema_registry import load_table

_schema = load_table("Laboratory")

render_crud_page(
    title="Laboratories",
    pk_field="laboratory_id",
    form_fields=_schema.build_form_fields(),
    list_fn=list_laboratories_lookup,
    create_fn=create_laboratory,
    update_fn=update_laboratory,
    delete_fn=delete_laboratory,
)
