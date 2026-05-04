"""Processing Degrees — read-only vocabulary page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import list_processing_kinds
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Processing Degrees",
    pk_field="processing_kind_id",
    form_fields=[
        {"name": "name", "type": "text", "required": True, "label": "Name", "help": "Processing degree name"},
    ],
    list_fn=list_processing_kinds,
    create_fn=None,
    update_fn=None,
    delete_fn=None,
)
