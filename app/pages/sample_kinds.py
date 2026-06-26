"""Sample Types — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_sample_kind,
    delete_sample_kind,
    list_sample_kinds,
    update_sample_kind,
)
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

render_crud_page(
    title="Sample Types",
    pk_field="sample_kind_id",
    form_fields=get_form_fields("sample_kind"),
    list_fn=list_sample_kinds,
    create_fn=create_sample_kind,
    update_fn=update_sample_kind,
    delete_fn=delete_sample_kind,
)
