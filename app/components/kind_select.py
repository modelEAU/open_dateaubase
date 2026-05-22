"""Reusable Kind-dropdown component.

`kind_select` renders a selectbox whose options come from a Kind-style lookup
list (rows with id/name/description fields). The selected row's long-form
description is shown as a caption beneath the selectbox so users see the
meaning of the Kind they pick.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


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
    allow_empty: If True, prepend a "(none)" choice that returns None.
    help: Help tooltip on the selectbox.

    Returns the selected id (or None if allow_empty and the empty row is chosen).
    """
    rows: list[dict[str, Any]] = list(options or [])

    sentinel: dict[str, Any] | None = None
    if allow_empty:
        sentinel = {id_field: None, name_field: "(none)", desc_field: ""}
        rows = [sentinel, *rows]

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
