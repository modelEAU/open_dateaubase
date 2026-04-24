"""Campaign Types — vocabulary admin page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_campaign_type,
    delete_campaign_type,
    list_campaign_types,
    update_campaign_type,
)
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Campaign Types",
    pk_field="campaign_type_id",
    form_fields=[
        {"name": "name", "type": "text", "required": True, "label": "Name", "help": "Name of the campaign type"},
    ],
    list_fn=list_campaign_types,
    create_fn=create_campaign_type,
    update_fn=update_campaign_type,
    delete_fn=delete_campaign_type,
    label_field="name",
)
