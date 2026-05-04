"""Parameter Units — manage ParameterHasUnit associations."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app.api_client import (
    APIError,
    add_parameter_unit,
    list_parameter_units,
    list_parameters_full,
    list_units_lookup,
    remove_parameter_unit,
)

st.title("Parameter Units")

try:
    with st.spinner("Loading..."):
        all_parameters = list_parameters_full()
        all_units = list_units_lookup()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    all_parameters = []
    all_units = []

if not all_parameters:
    st.info("No parameters found.")
else:
    params_df = pd.DataFrame(all_parameters)
    display_cols = [c for c in ["parameter_id", "parameter_name", "description"] if c in params_df.columns]
    sel = st.dataframe(
        params_df[display_cols] if display_cols else params_df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="param_units_sel",
    )

    selected_rows = sel.get("selection", {}).get("rows", []) if sel else []

    if not selected_rows:
        st.info("Select a parameter above to manage its valid units.")
    else:
        row_idx = selected_rows[0]
        param = all_parameters[row_idx]
        parameter_id = param["parameter_id"]
        param_label = param.get("parameter_name", str(parameter_id))

        st.markdown("---")
        st.subheader(param_label)
        st.info(
            "ParameterHasUnit rows are auto-generated from QUDT at build time. "
            "Manual edits may be overwritten on next build."
        )

        try:
            current_units = list_parameter_units(parameter_id)
        except APIError as e:
            st.error(f"Failed to load units: {e.message}")
            current_units = []

        linked_unit_ids = {u["unit_id"] for u in current_units}
        unlinked_units = [u for u in all_units if u["unit_id"] not in linked_unit_ids]

        col_left, col_right = st.columns([6, 4])

        with col_left:
            st.markdown("**Current units**")
            if current_units:
                units_df = pd.DataFrame(current_units)[["unit_id", "unit"]]
                remove_sel = st.dataframe(
                    units_df,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="multi-row",
                    key=f"remove_units_{parameter_id}",
                )
                remove_rows = remove_sel.get("selection", {}).get("rows", []) if remove_sel else []
                if st.button("Remove selected", key=f"btn_remove_units_{parameter_id}", disabled=not remove_rows):
                    for ri in remove_rows:
                        uid = current_units[ri]["unit_id"]
                        try:
                            remove_parameter_unit(parameter_id, uid)
                        except APIError as e:
                            st.error(f"Failed to remove unit {uid}: {e.message}")
                    st.rerun()
            else:
                st.info("No units linked yet.")

        with col_right:
            st.markdown("**Add units**")
            if unlinked_units:
                unit_opts = {f"{u['unit']} (#{u['unit_id']})": u["unit_id"] for u in unlinked_units}
                selected_labels = st.multiselect(
                    "Select units to add",
                    options=list(unit_opts.keys()),
                    key=f"add_units_select_{parameter_id}",
                )
                if st.button("Add selected", key=f"btn_add_units_{parameter_id}", disabled=not selected_labels):
                    for label in selected_labels:
                        uid = unit_opts[label]
                        try:
                            add_parameter_unit(parameter_id, uid)
                        except APIError as e:
                            st.error(f"Failed to add unit: {e.message}")
                    st.rerun()
            else:
                st.info("All units already linked.")
