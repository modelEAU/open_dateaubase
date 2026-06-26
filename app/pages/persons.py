"""Persons — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_person,
    delete_person,
    list_persons,
    update_person,
)
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

render_crud_page(
    title="Persons",
    pk_field="person_id",
    form_fields=get_form_fields("person"),
    list_fn=list_persons,
    create_fn=create_person,
    update_fn=update_person,
    delete_fn=delete_person,
    label_field="last_name",
)
