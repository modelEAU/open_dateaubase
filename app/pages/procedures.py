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
    list_procedure_kinds,
    list_procedures,
    update_procedure,
)
from app.auth import require_auth
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

require_auth()

try:
    _kind_options = [
        {"id": k["procedure_kind_id"], "label": k["name"]}
        for k in list_procedure_kinds()
    ]
except Exception:
    _kind_options = []


def _procedure_fields() -> list[dict]:
    """Schema-derived fields, with the kind FK wired to a live dropdown."""
    fields = []
    for f in get_form_fields("procedure"):
        f = dict(f)
        if f["name"] == "procedure_kind_id":
            f.pop("options_fn", None)
            f["type"] = "select"
            f["options"] = _kind_options
        fields.append(f)
    return fields


render_crud_page(
    title="Procedures",
    pk_field="procedure_id",
    form_fields=_procedure_fields(),
    list_fn=list_procedures,
    create_fn=create_procedure,
    update_fn=update_procedure,
    delete_fn=delete_procedure,
    label_field="procedure_name",
)
