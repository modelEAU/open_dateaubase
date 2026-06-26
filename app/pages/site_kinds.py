"""Site Kinds — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_site_kind,
    delete_site_kind,
    list_site_kinds,
    update_site_kind,
)
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

render_crud_page(
    title="Site Kinds",
    pk_field="id",
    form_fields=get_form_fields("site_kind"),
    list_fn=list_site_kinds,
    create_fn=create_site_kind,
    update_fn=update_site_kind,
    delete_fn=delete_site_kind,
)
