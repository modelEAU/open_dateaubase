"""Lab Panels management page."""

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
    create_lab_panel,
    delete_lab_panel,
    get_lab_panel,
    list_analysis_series_lookup,
    list_equipment_lookup,
    list_lab_panels,
    list_sample_collection_kinds,
    patch_lab_panel,
)
from app.components.form_dialog import create_form_dialog, edit_form_dialog

st.title("Lab Panels")

try:
    with st.spinner("Loading..."):
        _panels = list_lab_panels()
        _all_series = list_analysis_series_lookup()
        _collection_kinds = list_sample_collection_kinds()
        _equipment = list_equipment_lookup()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    st.stop()

_series_options = [
    {
        "id": s["analysis_series_id"],
        "label": f"{s['name']}  —  {s['parameter_name']} @ {s['sampling_point_label']}",
    }
    for s in _all_series
]

_ck_options = [{"id": None, "label": "— none —"}] + [
    {
        "id": c.get("sample_collection_kind_id") or c.get("id"),
        "label": c.get("name", ""),
    }
    for c in _collection_kinds
]

_eq_options = [{"id": None, "label": "— none —"}] + [
    {
        "id": e.get("equipment_id") or e.get("id"),
        "label": e.get("identifier", str(e)),
    }
    for e in _equipment
]

_fields = [
    {"name": "name", "type": "text", "required": True, "label": "Panel name"},
    {"name": "description", "type": "textarea", "required": False, "label": "Description"},
    {
        "name": "default_sample_collection_kind_id",
        "type": "select",
        "required": False,
        "label": "Default collection kind",
        "options": _ck_options,
    },
    {
        "name": "default_sample_equipment_id",
        "type": "select",
        "required": False,
        "label": "Default equipment",
        "options": _eq_options,
    },
    {
        "name": "series_ids",
        "type": "multiselect",
        "required": True,
        "label": "AnalysisSeries",
        "options": _series_options,
    },
]


def _handle_create(data: dict) -> bool:
    try:
        create_lab_panel(data)
        st.success("Panel created.")
        return True
    except APIError as e:
        st.error(f"Failed to create panel: {e.message}")
        return False


def _handle_patch(panel_id: int, data: dict) -> bool:
    try:
        patch_lab_panel(panel_id, data)
        st.success("Panel updated.")
        return True
    except APIError as e:
        st.error(f"Failed to update panel: {e.message}")
        return False


def _handle_delete(panel_id: int) -> None:
    try:
        delete_lab_panel(panel_id)
        st.success("Panel deleted.")
        st.rerun()
    except APIError as e:
        st.error(f"Failed to delete panel: {e.message}")


# ---------------------------------------------------------------------------
# Action buttons (New / Edit / Delete)
# ---------------------------------------------------------------------------

col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("➕ New", type="primary"):
        create_form_dialog(
            fields=_fields,
            on_submit=_handle_create,
            title="Create New Panel",
        )

# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

if _panels:
    df = pd.DataFrame(
        [
            {
                "lab_panel_id": p["lab_panel_id"],
                "name": p["name"],
                "description": p.get("description") or "",
                "series": p["series_count"],
            }
            for p in _panels
        ]
    )
    selection = st.dataframe(
        df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
    )
    if selection and selection.get("selection", {}).get("rows"):
        selected_item = _panels[selection["selection"]["rows"][0]]
    else:
        selected_item = None
else:
    st.info("No panels defined yet. Click '➕ New' to create one.")
    selected_item = None

with col2:
    if st.button("✏️ Edit", disabled=selected_item is None):
        if selected_item:
            try:
                detail = get_lab_panel(selected_item["lab_panel_id"])
                item_data = {
                    **selected_item,
                    "series_ids": [s["analysis_series_id"] for s in detail.get("series", [])],
                }
                edit_form_dialog(
                    item_data=item_data,
                    fields=_fields,
                    on_submit=lambda data: _handle_patch(
                        selected_item["lab_panel_id"], data
                    ),
                    title=f"Edit Panel: {selected_item['name']}",
                )
            except APIError as e:
                st.error(f"Cannot load panel detail: {e.message}")

with col3:
    if st.button("🗑️ Delete", disabled=selected_item is None, type="secondary"):
        if selected_item:
            _handle_delete(selected_item["lab_panel_id"])
