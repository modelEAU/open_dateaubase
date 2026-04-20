"""Purposes — vocabulary admin page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_purpose,
    delete_purpose,
    list_purposes,
    update_purpose,
)
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Purposes",
    pk_field="purpose_id",
    form_fields=[
        {"name": "name", "type": "text", "required": False, "label": "Name", "help": "Name of the purpose"},
        {"name": "description", "type": "textarea", "required": False, "label": "Description", "help": "Description of the purpose"},
    ],
    list_fn=list_purposes,
    create_fn=create_purpose,
    update_fn=update_purpose,
    delete_fn=delete_purpose,
    label_field="name",
)
