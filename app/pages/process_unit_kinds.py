"""Process Unit Types — vocabulary admin page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_process_unit_type,
    delete_process_unit_type,
    list_process_unit_types,
    update_process_unit_type,
)
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Process Unit Types",
    pk_field="process_unit_kind_id",
    form_fields=[
        {"name": "name", "type": "text", "required": True, "label": "Name", "help": "Name of the process unit type"},
        {"name": "description", "type": "textarea", "required": False, "label": "Description", "help": "Explanation of the process unit type"},
    ],
    list_fn=list_process_unit_types,
    create_fn=create_process_unit_type,
    update_fn=update_process_unit_type,
    delete_fn=delete_process_unit_type,
    label_field="name",
)
