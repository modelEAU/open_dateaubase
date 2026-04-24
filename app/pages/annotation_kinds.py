"""Annotation Types — managed via generic CRUD renderer."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.api_client import (
    create_annotation_type,
    delete_annotation_type,
    list_annotation_types,
    update_annotation_type,
)
from app.components.generic_crud import render_crud_page
from app.components.schema_registry import load_table

_schema = load_table("AnnotationType")

render_crud_page(
    title="Annotation Types",
    pk_field="id",  # AnnotationTypeResponse uses "id"
    form_fields=_schema.build_form_fields(),
    list_fn=list_annotation_types,
    create_fn=create_annotation_type,
    update_fn=update_annotation_type,
    delete_fn=delete_annotation_type,
)
