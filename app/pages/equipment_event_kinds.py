"""Equipment Event Types — vocabulary admin page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_equipment_event_type,
    delete_equipment_event_type,
    list_equipment_event_types,
    update_equipment_event_type,
)
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Equipment Event Types",
    pk_field="event_type_id",
    form_fields=[
        {"name": "name", "type": "text", "required": True, "label": "Name", "help": "Name of the event type"},
    ],
    list_fn=list_equipment_event_types,
    create_fn=create_equipment_event_type,
    update_fn=update_equipment_event_type,
    delete_fn=delete_equipment_event_type,
    label_field="event_type_name",
)
