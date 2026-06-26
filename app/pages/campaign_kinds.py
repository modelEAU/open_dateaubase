"""Campaign Types — vocabulary admin page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_campaign_kind,
    delete_campaign_kind,
    list_campaign_kinds,
    update_campaign_kind,
)
from app.auth import require_auth
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Campaign Types",
    pk_field="campaign_kind_id",
    form_fields=get_form_fields("campaign_kind"),
    list_fn=list_campaign_kinds,
    create_fn=create_campaign_kind,
    update_fn=update_campaign_kind,
    delete_fn=delete_campaign_kind,
    label_field="name",
)
