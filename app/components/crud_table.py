"""Reusable CRUD data editor component for Streamlit pages."""
from __future__ import annotations

import streamlit as st
import pandas as pd


def crud_data_editor(
    items: list[dict],
    column_config: dict,
    id_field: str,
    num_rows: str = "dynamic",
) -> tuple[list[dict], list[dict], list[int]]:
    """Render a st.data_editor and return (added_rows, changed_rows, deleted_ids).

    Parameters
    ----------
    items:         List of dicts from the API (each dict is one row).
    column_config: st.column_config mappings keyed by field name.
    id_field:      Name of the primary key field (e.g. "id", "equipment_id").
    num_rows:      "dynamic" allows add/delete; "fixed" disables them.

    Returns
    -------
    added_rows:   List of new row dicts (id_field absent or 0).
    changed_rows: List of dicts for rows whose values changed (id_field present).
    deleted_ids:  List of int IDs for rows that were deleted.
    """
    df_original = pd.DataFrame(items) if items else pd.DataFrame(columns=list(column_config.keys()))
    edited_df = st.data_editor(
        df_original,
        column_config=column_config,
        num_rows=num_rows,
        use_container_width=True,
        key=f"crud_editor_{id_field}",
    )

    added_rows: list[dict] = []
    changed_rows: list[dict] = []
    deleted_ids: list[int] = []

    if items:
        original_ids = set(df_original[id_field].tolist())
        edited_ids = set(edited_df[id_field].dropna().astype(int).tolist()) if id_field in edited_df.columns else set()

        # Deleted: in original but not in edited
        deleted_ids = [int(i) for i in original_ids - edited_ids]

        # Added: rows with no id_field value (NaN or 0)
        if id_field in edited_df.columns:
            added_mask = edited_df[id_field].isna() | (edited_df[id_field] == 0)
            added_rows = edited_df[added_mask].drop(columns=[id_field], errors="ignore").to_dict("records")

        # Changed: rows present in both, where values differ
        if not df_original.empty and not edited_df.empty and id_field in edited_df.columns:
            common_ids = original_ids & edited_ids
            for row_id in common_ids:
                orig_row = df_original[df_original[id_field] == row_id].iloc[0]
                new_row = edited_df[edited_df[id_field] == row_id].iloc[0]
                if not orig_row.equals(new_row):
                    changed_rows.append(new_row.to_dict())
    else:
        # All rows are new
        if not edited_df.empty:
            added_rows = edited_df.to_dict("records")

    return added_rows, changed_rows, deleted_ids
