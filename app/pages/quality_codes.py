"""Quality Codes — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_quality_code,
    delete_quality_code,
    list_quality_codes,
    update_quality_code,
)
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

render_crud_page(
    title="Quality Codes",
    pk_field="quality_code_id",
    form_fields=get_form_fields("quality_code"),
    list_fn=list_quality_codes,
    create_fn=create_quality_code,
    update_fn=update_quality_code,
    delete_fn=delete_quality_code,
)
