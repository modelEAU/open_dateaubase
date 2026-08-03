"""Operation Kinds — read-only controlled-vocabulary page (ADR 0005).

OperationKind is a fixed, seeded 6-entry vocabulary (Unprocessed,
OutlierRemoval, DriftCorrection, FaultRemoval, Smoothing, Interpolation)
that classifies a ProcessingStep and feeds the per-channel ChannelTrait set.
It is seeded with the schema, so this page is read-only display — the backend
exposes no create/update/delete for it.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import list_operation_kinds
from app.auth import require_auth
from app.components.generic_crud import render_crud_page

require_auth()

render_crud_page(
    title="Operation Kinds",
    pk_field="operation_kind_id",
    form_fields=[
        {"name": "name", "type": "text", "required": True, "label": "Name", "help": "Operation kind name"},
    ],
    list_fn=list_operation_kinds,
    create_fn=None,
    update_fn=None,
    delete_fn=None,
    caption="Read-only: operation kinds are seeded with the schema, so there is nothing to add or edit here.",
)
