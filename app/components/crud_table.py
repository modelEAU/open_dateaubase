"""Reusable CRUD data-table component built on st.data_editor."""

from __future__ import annotations

from typing import Any

import streamlit as st


def crud_table(
    rows: list[dict[str, Any]],
    *,
    key: str,
    column_config: dict[str, Any] | None = None,
    hide_columns: list[str] | None = None,
    num_rows: str = "fixed",
) -> list[dict[str, Any]]:
    """Render a data editor and return the edited rows.

    Args:
        rows: Current data as a list of dicts.
        key: Unique Streamlit widget key.
        column_config: Optional column configuration passed to st.data_editor.
        hide_columns: Column names to hide from the editor.
        num_rows: "fixed" to prevent adding/deleting rows, "dynamic" to allow it.

    Returns:
        The edited list of row dicts (only present when the user makes changes).
    """
    if not rows:
        st.caption("No records found.")
        return []

    import pandas as pd

    df = pd.DataFrame(rows)
    if hide_columns:
        column_order = [c for c in df.columns if c not in hide_columns]
    else:
        column_order = list(df.columns)

    edited = st.data_editor(
        df,
        key=key,
        column_config=column_config,
        column_order=column_order,
        use_container_width=True,
        num_rows=num_rows,
        hide_index=True,
    )

    return edited.to_dict(orient="records")
