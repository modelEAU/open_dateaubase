"""Site Types — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_site_type,
    delete_site_type,
    list_site_types,
    update_site_type,
)
from app.components.generic_crud import render_crud_page
from app.components.schema_registry import load_table

_schema = load_table("SiteType")

render_crud_page(
    title="Site Types",
    pk_field="id",  # SiteTypeOut uses "id"
    form_fields=_schema.build_form_fields(),
    list_fn=list_site_types,
    create_fn=create_site_type,
    update_fn=update_site_type,
    delete_fn=delete_site_type,
)
