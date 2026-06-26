"""Data Acquisition Systems — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_das,
    delete_das,
    list_das_lookup,
    update_das,
)
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

render_crud_page(
    title="Data Acquisition Systems",
    pk_field="das_id",
    form_fields=get_form_fields("das"),
    list_fn=list_das_lookup,
    create_fn=create_das,
    update_fn=update_das,
    delete_fn=delete_das,
)
