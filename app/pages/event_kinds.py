"""Event Kinds — vocabulary admin page (generalised EventKind, PRD-2 S4)."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_event_kind,
    delete_event_kind,
    list_event_kinds,
    update_event_kind,
)
from app.auth import require_auth
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Event Kinds",
    pk_field="event_kind_id",
    form_fields=get_form_fields("event_kind"),
    list_fn=list_event_kinds,
    create_fn=create_event_kind,
    update_fn=update_event_kind,
    delete_fn=delete_event_kind,
    label_field="name",
)
