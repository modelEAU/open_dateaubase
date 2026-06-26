"""Annotation Types — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_annotation_kind,
    delete_annotation_kind,
    list_annotation_kinds,
    update_annotation_kind,
)
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page

render_crud_page(
    title="Annotation Types",
    pk_field="id",  # AnnotationKindResponse uses "id"
    form_fields=get_form_fields("annotation_kind"),
    list_fn=list_annotation_kinds,
    create_fn=create_annotation_kind,
    update_fn=update_annotation_kind,
    delete_fn=delete_annotation_kind,
)
