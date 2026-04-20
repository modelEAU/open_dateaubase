"""Watersheds — entity admin page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_watershed,
    delete_watershed,
    list_watersheds,
    update_watershed,
)
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Watersheds",
    pk_field="watershed_id",
    form_fields=[
        {"name": "name", "type": "text", "required": False, "label": "Name", "help": "Name of the watershed"},
        {"name": "description", "type": "textarea", "required": False, "label": "Description", "help": "Description of the watershed"},
        {"name": "surface_area", "type": "number", "required": False, "label": "Surface Area (ha)", "help": "Surface area in hectares"},
        {"name": "concentration_time", "type": "number", "required": False, "label": "Concentration Time (min)", "help": "Concentration time in minutes"},
        {"name": "impervious_surface", "type": "number", "required": False, "label": "Impervious Surface (%)", "help": "Percentage of impervious surface"},
    ],
    list_fn=list_watersheds,
    create_fn=create_watershed,
    update_fn=update_watershed,
    delete_fn=delete_watershed,
    label_field="name",
)
