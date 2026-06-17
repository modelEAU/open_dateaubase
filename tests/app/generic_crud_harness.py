"""Minimal Streamlit harness for generic_crud AppTest.

Not a test file — executed by AppTest.from_file() to provide a Streamlit
context. It reads a small config dict from session_state (seeded per test) and
calls render_crud_page with plain callables, so tests can exercise the shared
CRUD renderer's load/empty/error/unwrap branches without a live API.
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = str(Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.api_client import APIError
from app.components.generic_crud import render_crud_page

cfg = st.session_state.get("_crud_cfg", {})
behavior = cfg.get("list", "ok")
items = cfg.get("items", [{"widget_id": 1, "name": "Alpha"}, {"widget_id": 2, "name": "Beta"}])


def _list_fn():
    if behavior == "error":
        raise APIError(503, "backend down")
    if behavior == "empty":
        return []
    if behavior == "dict":
        return {"items": items}
    return items


render_crud_page(
    title="Widgets",
    pk_field="widget_id",
    form_fields=[{"name": "name", "type": "text", "required": True}],
    list_fn=_list_fn,
    create_fn=(lambda data: None) if cfg.get("create", True) else None,
    update_fn=(lambda pk, data: None) if cfg.get("update", True) else None,
    delete_fn=(lambda pk: None) if cfg.get("delete", True) else None,
    label_field="name",
    embedded=cfg.get("embedded", False),
)
