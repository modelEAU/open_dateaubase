"""Lab Panels management page.

Lists existing panels with delete controls and a form to create new ones.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from app.api_client import (
    APIError,
    create_lab_panel,
    delete_lab_panel,
    list_analysis_series_lookup,
    list_lab_panels,
)

st.title("Lab Panels")
st.markdown(
    "Manage reusable bundles of AnalysisSeries. "
    "A panel can be loaded when starting a new lab experiment."
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

try:
    with st.spinner("Loading panels..."):
        _panels = list_lab_panels()
        _all_series = list_analysis_series_lookup()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    st.stop()

# ---------------------------------------------------------------------------
# Existing panels table
# ---------------------------------------------------------------------------

st.subheader("Existing panels")

if not _panels:
    st.caption("No panels defined yet. Create one below.")
else:
    for panel in _panels:
        col_name, col_count, col_del = st.columns([4, 1, 1])
        with col_name:
            st.write(
                f"**{panel['name']}**"
                + (f"  —  {panel['description']}" if panel.get("description") else "")
            )
        with col_count:
            st.caption(f"{panel['series_count']} series")
        with col_del:
            if st.button(
                "Delete",
                key=f"del_panel_{panel['lab_panel_id']}",
                type="secondary",
            ):
                st.session_state[f"confirm_del_{panel['lab_panel_id']}"] = True

        if st.session_state.get(f"confirm_del_{panel['lab_panel_id']}"):
            st.warning(f"Delete panel **{panel['name']}**? This cannot be undone.")
            c1, c2, _ = st.columns([1, 1, 5])
            with c1:
                if st.button(
                    "Confirm",
                    key=f"confirm_yes_{panel['lab_panel_id']}",
                    type="primary",
                ):
                    try:
                        delete_lab_panel(panel["lab_panel_id"])
                        st.success(f"Panel '{panel['name']}' deleted.")
                        del st.session_state[f"confirm_del_{panel['lab_panel_id']}"]
                        st.rerun()
                    except APIError as e:
                        st.error(f"Delete failed: {e.message}")
            with c2:
                if st.button("Cancel", key=f"confirm_no_{panel['lab_panel_id']}"):
                    del st.session_state[f"confirm_del_{panel['lab_panel_id']}"]
                    st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# New panel form
# ---------------------------------------------------------------------------

st.subheader("New panel")

new_name = st.text_input("Panel name *", key="new_panel_name")
new_desc = st.text_area("Description (optional)", key="new_panel_desc")

series_options = {
    s["analysis_series_id"]: (
        f"{s['name']}  —  {s['parameter_name']} @ {s['sampling_point_label']}"
    )
    for s in _all_series
}

selected_labels = st.multiselect(
    "AnalysisSeries *",
    options=list(series_options.values()),
    key="new_panel_series",
)
label_to_id = {v: k for k, v in series_options.items()}
selected_ids = [label_to_id[label] for label in selected_labels]

if st.button("Create panel", type="primary", key="create_panel_btn"):
    if not new_name.strip():
        st.error("Panel name is required.")
    elif not selected_ids:
        st.error("Select at least one AnalysisSeries.")
    else:
        try:
            result = create_lab_panel(
                {
                    "name": new_name.strip(),
                    "description": new_desc.strip() or None,
                    "series_ids": selected_ids,
                }
            )
            st.success(f"Panel created (ID {result['lab_panel_id']}).")
            st.rerun()
        except APIError as e:
            st.error(f"Create failed: {e.message}")
