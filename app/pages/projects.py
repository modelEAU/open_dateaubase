"""Projects — entity admin page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_project,
    delete_project,
    list_projects,
    update_project,
)
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Projects",
    pk_field="project_id",
    form_fields=[
        {"name": "name", "type": "text", "required": False, "label": "Name", "help": "Name of the project"},
        {"name": "description", "type": "textarea", "required": False, "label": "Description", "help": "Description of the project"},
    ],
    list_fn=list_projects,
    create_fn=create_project,
    update_fn=update_project,
    delete_fn=delete_project,
    label_field="name",
)
