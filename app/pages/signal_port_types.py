"""Signal Port Types — read-only vocabulary page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import list_signal_port_types
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Signal Port Types",
    pk_field="signal_port_type_id",
    form_fields=[
        {"name": "name", "type": "text", "required": True, "label": "Name", "help": "Port type name"},
        {"name": "description", "type": "textarea", "required": False, "label": "Description", "help": "Explanation of the port type"},
    ],
    list_fn=list_signal_port_types,
    create_fn=None,
    update_fn=None,
    delete_fn=None,
)
