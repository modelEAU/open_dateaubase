"""Sample Methods — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_sample_method,
    delete_sample_method,
    list_sample_methods,
    update_sample_method,
)
from app.components.generic_crud import render_crud_page
from app.components.schema_registry import load_table

_schema = load_table("SampleMethod")

render_crud_page(
    title="Sample Methods",
    pk_field="sample_method_id",
    form_fields=_schema.build_form_fields(),
    list_fn=list_sample_methods,
    create_fn=create_sample_method,
    update_fn=update_sample_method,
    delete_fn=delete_sample_method,
)
