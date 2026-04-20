"""Generic CRUD page renderer.

Usage:
    render_crud_page(
        title="Units",
        pk_field="unit_id",
        form_fields=load_table("Unit").build_form_fields(),
        list_fn=list_units_lookup,
        create_fn=lambda data: create_unit(data["unit"]),
        update_fn=lambda item_id, data: update_unit(item_id, data["unit"]),
        delete_fn=delete_unit,
        label_field="unit",
    )
"""

from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st

import app.api_client as _api
from app.api_client import APIError
from app.components.form_dialog import create_form_dialog, edit_form_dialog


def render_crud_page(
    title: str,
    pk_field: str,
    form_fields: list[dict],
    list_fn: Callable,
    create_fn: Callable[[dict], object] | None = None,
    update_fn: Callable[[int, dict], object] | None = None,
    delete_fn: Callable[[int], None] | None = None,
    label_field: str = "name",
) -> None:
    """Render a standard list + create/edit/delete CRUD page.

    Parameters
    ----------
    title:       Page heading and entity name used in dialog titles.
    pk_field:    Key in each API response row that holds the primary key integer.
    form_fields: List of field dicts for form_dialog (type, required, help, …).
                 Fields with an ``options_fn`` key have that function resolved
                 against app.api_client at render time.
    list_fn:     Callable returning list[dict] or {"items": list[dict]}.
    create_fn:   Callable(data: dict) → any. Omit to hide the New button.
    update_fn:   Callable(pk: int, data: dict) → any. Omit to hide Edit.
    delete_fn:   Callable(pk: int) → None. Omit to hide Delete.
    label_field: Field name shown in the Edit dialog title (default "name").
    """
    st.title(title)

    resolved_fields = _resolve_fk_options(form_fields)

    try:
        with st.spinner("Loading…"):
            result = list_fn()
            items: list[dict] = result.get("items", result) if isinstance(result, dict) else result
    except APIError as e:
        st.error(f"Cannot load data: {e.message}")
        st.stop()
        return

    col_new, col_edit, col_del, _ = st.columns([2, 2, 2, 6])

    with col_new:
        if create_fn and st.button("➕ New", type="primary", use_container_width=True):
            create_form_dialog(
                fields=resolved_fields,
                on_submit=lambda data: _handle_create(create_fn, data, title),
                title=f"Create {title}",
            )

    session_key = f"_crud_sel_{pk_field}"
    if session_key not in st.session_state:
        st.session_state[session_key] = None

    selected: dict | None = None

    if items:
        df = pd.DataFrame(items)
        sel = st.dataframe(
            df,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
        )
        rows = (sel or {}).get("selection", {}).get("rows", [])
        if rows:
            idx = rows[0]
            st.session_state[session_key] = df.iloc[idx][pk_field]
            selected = items[idx]
        else:
            st.session_state[session_key] = None
    else:
        st.info(f"No {title.lower()} found. Click '➕ New' to create one.")

    item_label = selected.get(label_field, "") if selected else ""

    with col_edit:
        if update_fn and st.button("✏️ Edit", disabled=selected is None, use_container_width=True):
            if selected:
                edit_form_dialog(
                    item_data=selected,
                    fields=resolved_fields,
                    on_submit=lambda data: _handle_update(
                        update_fn, selected[pk_field], data, title
                    ),
                    title=f"Edit {title}: {item_label}",
                )

    with col_del:
        if delete_fn and st.button("🗑️ Delete", disabled=selected is None, type="secondary", use_container_width=True):
            if selected:
                try:
                    delete_fn(selected[pk_field])
                    st.success(f"{title} deleted.")
                    st.rerun()
                except APIError as e:
                    st.error(f"Delete failed: {e.message}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_fk_options(form_fields: list[dict]) -> list[dict]:
    """Replace ``options_fn`` keys with live ``options`` lists from api_client."""
    resolved = []
    for field in form_fields:
        f = dict(field)
        fn_name = f.pop("options_fn", None)
        if fn_name:
            fn = getattr(_api, fn_name, None)
            if fn:
                try:
                    f["options"] = _normalize_options(fn())
                except Exception:
                    f["options"] = []
            else:
                f["options"] = []
        resolved.append(f)
    return resolved


def _normalize_options(raw: list[dict]) -> list[dict]:
    """Coerce a lookup list to [{"id": …, "label": …}] for select fields."""
    if not raw:
        return []
    sample = raw[0]
    id_keys = [k for k in sample if k.endswith("_id")]
    label_keys = [k for k in sample if k in ("name", "label", "unit", "identifier", "code", "tag")]
    if id_keys and label_keys:
        return [{"id": r[id_keys[0]], "label": str(r[label_keys[0]])} for r in raw]
    keys = list(sample.keys())
    if len(keys) >= 2:
        return [{"id": r[keys[0]], "label": str(r[keys[1]])} for r in raw]
    return [{"id": r[keys[0]], "label": str(r[keys[0]])} for r in raw]


def _handle_create(fn: Callable, data: dict, title: str) -> bool:
    try:
        fn(data)
        st.success(f"{title} created.")
        return True
    except APIError as e:
        st.error(f"Create failed: {e.message}")
        return False


def _handle_update(fn: Callable, pk: int, data: dict, title: str) -> bool:
    try:
        fn(pk, data)
        st.success(f"{title} updated.")
        return True
    except APIError as e:
        st.error(f"Update failed: {e.message}")
        return False
