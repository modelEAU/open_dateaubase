"""Equipment Models — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_equipment_model,
    delete_equipment_model,
    list_equipment_models,
    update_equipment_model,
)
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

render_crud_page(
    title="Equipment Models",
    pk_field="model_id",  # API uses model_id, not equipment_model_id
    form_fields=get_form_fields("equipment_model"),
    list_fn=list_equipment_models,
    create_fn=create_equipment_model,
    update_fn=update_equipment_model,
    delete_fn=delete_equipment_model,
    label_field="equipment_model",
)
