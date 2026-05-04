"""Equipment Model Associations — manage EquipmentModelHasParameter and EquipmentModelHasProcedures."""

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
    add_model_parameter,
    add_model_procedure,
    list_equipment_models,
    list_model_parameters,
    list_model_procedures,
    list_parameters_full,
    list_procedures,
    remove_model_parameter,
    remove_model_procedure,
)

st.title("Equipment Model Associations")

try:
    with st.spinner("Loading..."):
        all_models = list_equipment_models()
        all_parameters = list_parameters_full()
        all_procedures = list_procedures()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    all_models = []
    all_parameters = []
    all_procedures = []

if not all_models:
    st.info("No equipment models found.")
else:
    models_df = pd.DataFrame(all_models)
    display_cols = [c for c in ["model_id", "equipment_model", "manufacturer"] if c in models_df.columns]
    sel = st.dataframe(
        models_df[display_cols] if display_cols else models_df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="eq_model_sel",
    )

    selected_rows = sel.get("selection", {}).get("rows", []) if sel else []

    if not selected_rows:
        st.info("Select an equipment model above to manage its associations.")
    else:
        row_idx = selected_rows[0]
        model = all_models[row_idx]
        model_id = model["model_id"]
        model_label = f"{model.get('equipment_model', '')} ({model.get('manufacturer', '')})"

        st.markdown("---")
        st.subheader(model_label)

        tab_params, tab_procs = st.tabs(["Parameters", "Procedures"])

        with tab_params:
            try:
                current_params = list_model_parameters(model_id)
            except APIError as e:
                st.error(f"Failed to load parameters: {e.message}")
                current_params = []

            linked_param_ids = {r["parameter_id"] for r in current_params}
            unlinked_params = [p for p in all_parameters if p["parameter_id"] not in linked_param_ids]

            col_left, col_right = st.columns([6, 4])

            with col_left:
                st.markdown("**Current parameters**")
                if current_params:
                    params_df = pd.DataFrame(current_params)[["parameter_id", "parameter_name"]]
                    remove_sel = st.dataframe(
                        params_df,
                        use_container_width=True,
                        on_select="rerun",
                        selection_mode="multi-row",
                        key=f"remove_params_{model_id}",
                    )
                    remove_rows = remove_sel.get("selection", {}).get("rows", []) if remove_sel else []
                    if st.button("Remove selected", key=f"btn_remove_params_{model_id}", disabled=not remove_rows):
                        for ri in remove_rows:
                            pid = current_params[ri]["parameter_id"]
                            try:
                                remove_model_parameter(model_id, pid)
                            except APIError as e:
                                st.error(f"Failed to remove parameter {pid}: {e.message}")
                        st.rerun()
                else:
                    st.info("No parameters linked yet.")

            with col_right:
                st.markdown("**Add parameters**")
                if unlinked_params:
                    param_opts = {f"{p['parameter_name']} (#{p['parameter_id']})": p["parameter_id"] for p in unlinked_params}
                    selected_labels = st.multiselect(
                        "Select parameters to add",
                        options=list(param_opts.keys()),
                        key=f"add_params_select_{model_id}",
                    )
                    if st.button("Add selected", key=f"btn_add_params_{model_id}", disabled=not selected_labels):
                        for label in selected_labels:
                            pid = param_opts[label]
                            try:
                                add_model_parameter(model_id, pid)
                            except APIError as e:
                                st.error(f"Failed to add parameter: {e.message}")
                        st.rerun()
                else:
                    st.info("All parameters already linked.")

        with tab_procs:
            try:
                current_procs = list_model_procedures(model_id)
            except APIError as e:
                st.error(f"Failed to load procedures: {e.message}")
                current_procs = []

            linked_proc_ids = {r["procedure_id"] for r in current_procs}
            unlinked_procs = [p for p in all_procedures if p["procedure_id"] not in linked_proc_ids]

            col_left, col_right = st.columns([6, 4])

            with col_left:
                st.markdown("**Current procedures**")
                if current_procs:
                    procs_df = pd.DataFrame(current_procs)[["procedure_id", "procedure_name"]]
                    remove_sel = st.dataframe(
                        procs_df,
                        use_container_width=True,
                        on_select="rerun",
                        selection_mode="multi-row",
                        key=f"remove_procs_{model_id}",
                    )
                    remove_rows = remove_sel.get("selection", {}).get("rows", []) if remove_sel else []
                    if st.button("Remove selected", key=f"btn_remove_procs_{model_id}", disabled=not remove_rows):
                        for ri in remove_rows:
                            pid = current_procs[ri]["procedure_id"]
                            try:
                                remove_model_procedure(model_id, pid)
                            except APIError as e:
                                st.error(f"Failed to remove procedure {pid}: {e.message}")
                        st.rerun()
                else:
                    st.info("No procedures linked yet.")

            with col_right:
                st.markdown("**Add procedures**")
                if unlinked_procs:
                    proc_opts = {f"{p['procedure_name']} (#{p['procedure_id']})": p["procedure_id"] for p in unlinked_procs}
                    selected_labels = st.multiselect(
                        "Select procedures to add",
                        options=list(proc_opts.keys()),
                        key=f"add_procs_select_{model_id}",
                    )
                    if st.button("Add selected", key=f"btn_add_procs_{model_id}", disabled=not selected_labels):
                        for label in selected_labels:
                            pid = proc_opts[label]
                            try:
                                add_model_procedure(model_id, pid)
                            except APIError as e:
                                st.error(f"Failed to add procedure: {e.message}")
                        st.rerun()
                else:
                    st.info("All procedures already linked.")
