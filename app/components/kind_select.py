"""Reusable Kind-dropdown component.

`kind_select` renders a selectbox whose options come from a Kind-style lookup
list (rows with id/name/description fields). The selected row's long-form
description is shown as a caption beneath the selectbox so users see the
meaning of the Kind they pick.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.labels import NONE_LABEL

__all__ = [
    "NONE_LABEL",
    "kind_caption",
    "kind_options",
    "kind_select",
    "select_or_none",
]


def kind_caption(options: list[dict], selected_label: str | None) -> None:
    """Show the picked Kind's definition under a label-driven selectbox.

    Some selectboxes (the wizards) take plain label strings because
    ``session_state`` stores the label and a later step resolves it back to an
    id, so they can't go through ``kind_select``. Options built with
    ``kind_options`` still carry the vocabulary term's definition; this renders
    it the same way ``kind_select`` does, so a Kind explains itself either way.
    """
    desc = next(
        (o.get("description") for o in options if o.get("label") == selected_label), ""
    )
    if desc:
        st.caption(desc)


def kind_options(rows: list[dict], id_key: str, *, name_key: str = "name") -> list[dict]:
    """Build dropdown options from a Kind lookup, keeping the definition.

    A Kind row is a controlled-vocabulary term, and its ``Description`` is the
    definition users need in order to pick correctly. Building options by hand
    as ``{"id": ..., "label": ...}`` throws that away and yields a dropdown of
    bare words; carrying ``description`` makes ``crud_form``/``kind_select``
    render it as a caption under the select.
    """
    return [
        {
            "id": r.get(id_key) or r.get("id"),
            "label": r.get(name_key, ""),
            "description": r.get("description") or "",
        }
        for r in rows
    ]


def select_or_none(
    label: str,
    options: list[str],
    *,
    key: str,
    help: str | None = None,
) -> str | None:
    """Selectbox over plain string options, with the house NONE_LABEL row.

    Returns the picked option, or None when nothing is picked — so callers keep
    "None means unset" while the empty choice looks like every other dropdown.
    A selection that is no longer on offer (a narrowed list) is dropped, since
    Streamlit raises on a session value outside ``options``.
    """
    rows = [NONE_LABEL, *options]
    if st.session_state.get(key) not in rows:
        st.session_state.pop(key, None)
    picked = st.selectbox(label, options=rows, key=key, help=help)
    return None if picked == NONE_LABEL else picked


def kind_select(
    label: str,
    options: list[dict],
    *,
    key: str | None = None,
    id_field: str = "id",
    name_field: str = "name",
    desc_field: str = "description",
    default_id: int | None = None,
    allow_empty: bool = False,
    help: str | None = None,
) -> int | None:
    """Render a Kind selectbox with description caption.

    Parameters
    ----------
    label: Label for the selectbox.
    options: List of dicts containing id/name/description keys (configurable).
    key: Streamlit widget key.
    id_field, name_field, desc_field: Keys to read from each option row.
    default_id: Pre-selected id; ignored if not present in options.
    allow_empty: If True, prepend a NONE_LABEL choice that returns None.
    help: Help tooltip on the selectbox.

    Returns the selected id (or None if allow_empty and the empty row is chosen).
    """
    # Drop any empty row a caller prepended; the sentinel is ours to add.
    rows: list[dict[str, Any]] = [
        r for r in (options or []) if r.get(id_field) is not None
    ]

    if allow_empty:
        rows = [{id_field: None, name_field: NONE_LABEL, desc_field: ""}, *rows]

    if not rows:
        st.selectbox(label, options=["(no options)"], disabled=True, key=key, help=help)
        return None

    default_index = 0
    if default_id is not None:
        for i, row in enumerate(rows):
            if row.get(id_field) == default_id:
                default_index = i
                break

    selected = st.selectbox(
        label,
        options=rows,
        index=default_index,
        format_func=lambda r: str(r.get(name_field, "")),
        key=key,
        help=help,
    )

    desc = (selected or {}).get(desc_field) or ""
    if desc:
        st.caption(desc)

    return selected.get(id_field) if selected else None
