"""Sampling Locations CRUD page — filterable by site and process unit."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from app.api_client import (
    APIError,
    create_sampling_location,
    delete_sampling_location,
    list_all_sampling_locations,
    list_process_units_lookup,
    list_sites_lookup,
    update_sampling_location,
)
from app.components.form_specs import get_form_fields
from app.components.generic_crud import render_crud_page
from app.components.labels import ALL_LABEL

st.set_page_config(page_title="Sampling Locations", layout="wide")

# ---------------------------------------------------------------------------
# Load reference data for filters and form dropdowns
# ---------------------------------------------------------------------------

try:
    sites_list = list_sites_lookup()
except APIError as e:
    st.error(f"Cannot load sites: {e.message}")
    st.stop()

site_options = {s["name"]: s["id"] for s in sites_list}

col1, col2 = st.columns(2)

with col1:
    selected_site_name = st.selectbox(
        "Filter by site",
        options=[ALL_LABEL] + list(site_options.keys()),
        key="sl_site_filter",
        help="Show only the sampling locations at one site.",
    )
selected_site_id: int | None = site_options.get(selected_site_name)  # type: ignore[arg-type]

try:
    pu_candidates = list_process_units_lookup(site_id=selected_site_id)
    pu_options_map = {f"{u['tag']} — {u['name']}": u["id"] for u in pu_candidates}
except APIError:
    pu_candidates = []
    pu_options_map = {}

with col2:
    selected_pu_label = st.selectbox(
        "Filter by process unit",
        options=[ALL_LABEL] + list(pu_options_map.keys()),
        help="Show only the sampling locations on one process unit.",
        key="sl_pu_filter",
    )
selected_pu_id: int | None = pu_options_map.get(selected_pu_label)  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
# Form field definitions
# ---------------------------------------------------------------------------

site_form_options = [{"id": s["id"], "label": s["name"]} for s in sites_list]
pu_form_options = [{"id": u["id"], "label": f"{u['tag']} — {u['name']}"} for u in pu_candidates]

# site_id is a UI-only scope field (popped in _create); the rest are the
# SamplingLocationIn contract, sourced from form_specs and wired to live options.
_overlays = {
    "name": {"label": "Name", "help": 'e.g. "Inlet", "Outlet", "Effluent"'},
    "description": {"label": "Description"},
    "process_unit_id": {"options": pu_form_options, "label": "Process Unit"},
    "latitude": {"label": "Latitude (WGS84)"},
    "longitude": {"label": "Longitude (WGS84)"},
}
form_fields = [
    {
        "name": "site_id",
        "label": "Site",
        "type": "select",
        "required": True,
        "options": site_form_options,
        "help": "Site this sampling location belongs to",
    },
]
for _f in get_form_fields("sampling_location"):
    _f = {**_f, **_overlays.get(_f["name"], {})}
    form_fields.append(_f)


def _create(data: dict) -> dict:
    site_id = data.pop("site_id")
    return create_sampling_location(site_id, data)


def _update(pk: int, data: dict) -> dict:
    payload = {k: v for k, v in data.items() if k != "site_id"}
    return update_sampling_location(pk, payload)


render_crud_page(
    title="Sampling Locations",
    pk_field="id",
    form_fields=form_fields,
    list_fn=lambda: list_all_sampling_locations(
        site_id=selected_site_id,
        process_unit_id=selected_pu_id,
    ),
    create_fn=_create,
    update_fn=_update,
    delete_fn=delete_sampling_location,
    label_field="name",
)
