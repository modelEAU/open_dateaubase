"""Procedures — admin page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_procedure,
    delete_procedure,
    list_procedures,
    update_procedure,
)
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Procedures",
    pk_field="procedure_id",
    form_fields=[
        {"name": "procedure_name", "type": "text", "required": False, "label": "Procedure Name", "help": "Title of the procedure"},
        {"name": "procedure_type", "type": "text", "required": False, "label": "Type", "help": "e.g. SOP, ISO method"},
        {"name": "description", "type": "textarea", "required": False, "label": "Description", "help": "Details of the procedure"},
        {"name": "procedure_location", "type": "text", "required": False, "label": "Location", "help": "Where the procedure document is stored"},
    ],
    list_fn=list_procedures,
    create_fn=create_procedure,
    update_fn=update_procedure,
    delete_fn=delete_procedure,
    label_field="procedure_name",
)
