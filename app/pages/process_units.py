"""Process Units CRUD page — browse and manage the functional location hierarchy."""

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
    create_process_unit,
    delete_process_unit,
    list_process_unit_types,
    list_process_units,
    list_process_units_lookup,
    list_sites,
    update_process_unit,
)
from app.components.generic_crud import render_crud_page

st.set_page_config(page_title="Process Units", layout="wide")


# ---------------------------------------------------------------------------
# Site filter
# ---------------------------------------------------------------------------

try:
    sites = list_sites()
    sites_list: list[dict] = sites.get("items", sites) if isinstance(sites, dict) else sites
except APIError as e:
    st.error(f"Cannot load sites: {e.message}")
    st.stop()

site_options = {s["name"]: s["id"] for s in sites_list}

selected_site_name = st.selectbox(
    "Filter by site",
    options=["(all sites)"] + list(site_options.keys()),
    key="pu_site_filter",
    help="Show only process units belonging to this site",
)
selected_site_id: int | None = site_options.get(selected_site_name)  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
# Resolve FK option lists (site-scoped where applicable)
# ---------------------------------------------------------------------------

try:
    unit_types = list_process_unit_types()
    type_options = [{"id": t["process_unit_kind_id"], "label": t["name"]} for t in unit_types]
except APIError:
    unit_types = []
    type_options = []

try:
    parent_candidates = list_process_units_lookup(site_id=selected_site_id)
    parent_options = [{"id": u["id"], "label": f"{u['tag']} — {u['name']}"} for u in parent_candidates]
except APIError:
    parent_options = []

# ---------------------------------------------------------------------------
# CRUD page
# ---------------------------------------------------------------------------

form_fields = [
    {
        "name": "site_id",
        "label": "Site",
        "type": "select",
        "required": True,
        "options": [{"id": s["id"], "label": s["name"]} for s in sites_list],
        "help": "Foreign key to Site — scopes the unit to a single site",
    },
    {
        "name": "tag",
        "label": "P&ID Tag",
        "type": "text",
        "required": True,
        "help": "Stable functional identifier (e.g. R-210, BioLine1, 10-PL-102). Unique per site.",
    },
    {
        "name": "name",
        "label": "Name",
        "type": "text",
        "required": True,
        "help": "Human-readable name for the process unit",
    },
    {
        "name": "process_unit_kind_id",
        "label": "Type",
        "type": "select",
        "required": False,
        "options": type_options,
        "help": "Foreign key to ProcessUnitKind lookup",
    },
    {
        "name": "parent_id",
        "label": "Parent unit",
        "type": "select",
        "required": False,
        "options": parent_options,
        "help": "Self-reference to the parent ProcessUnit, enabling an unlimited-depth tree",
    },
    {
        "name": "description",
        "label": "Description",
        "type": "textarea",
        "required": False,
        "help": "Optional description of the process unit's role or function",
    },
]

render_crud_page(
    title="Process Units",
    pk_field="id",
    form_fields=form_fields,
    list_fn=lambda: list_process_units(site_id=selected_site_id),
    create_fn=lambda data: create_process_unit(data),
    update_fn=lambda pk, data: update_process_unit(pk, data),
    delete_fn=delete_process_unit,
    label_field="name",
)

# ---------------------------------------------------------------------------
# Read-only tree view
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Hierarchy tree")

if selected_site_id is None:
    st.info("Select a site above to display the hierarchy tree.")
else:
    try:
        flat_units = list_process_units(site_id=selected_site_id)
    except APIError as e:
        st.error(f"Cannot load units: {e.message}")
        flat_units = []

    if flat_units:
        # Build indented display by resolving parent depth
        nodes = {u["id"]: u for u in flat_units}
        depths: dict[int, int] = {}

        def _depth(uid: int) -> int:
            if uid in depths:
                return depths[uid]
            parent = nodes[uid].get("parent_id")
            d = 0 if parent is None or parent not in nodes else 1 + _depth(parent)
            depths[uid] = d
            return d

        rows = []
        for u in flat_units:
            indent = "\u00a0\u00a0\u00a0\u00a0" * _depth(u["id"])
            rows.append(
                {
                    "P&ID Tag": f"{indent}{u['tag']}",
                    "Name": u["name"],
                    "Type": u.get("process_unit_type_name") or "",
                    "Parent": u.get("parent_name") or "",
                    "Description": u.get("description") or "",
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No process units defined for this site yet.")
