"""Signal Interface Types — vocabulary admin page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_signal_interface_type,
    delete_signal_interface_type,
    list_signal_interface_types,
    update_signal_interface_type,
)
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Signal Interface Types",
    pk_field="signal_interface_kind_id",
    form_fields=[
        {
            "name": "name",
            "type": "text",
            "required": True,
            "label": "Name",
            "help": "Name of the signal interface type",
        },
        {
            "name": "description",
            "type": "textarea",
            "required": False,
            "label": "Description",
            "help": "Explanation of the signal interface type",
        },
    ],
    list_fn=list_signal_interface_types,
    create_fn=lambda data: create_signal_interface_type(data),
    update_fn=lambda pk, data: update_signal_interface_type(pk, data),
    delete_fn=delete_signal_interface_type,
    label_field="name",
)
