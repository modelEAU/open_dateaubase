"""Watersheds — entity admin page with map and GeoJSON support."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import folium
import streamlit as st
from streamlit_folium import st_folium

from app.api_client import (
    APIError,
    create_watershed,
    delete_watershed,
    get_land_use,
    list_watersheds,
    update_watershed,
    upsert_land_use,
)
from app.auth import require_auth
from app.components.geo_utils import maybe_prefill_area, normalize_geojson_for_folium, validate_geojson

require_auth()

_LAND_USE_FIELDS = [
    ("commercial", "Commercial"),
    ("green_spaces", "Green Spaces"),
    ("industrial", "Industrial"),
    ("institutional", "Institutional"),
    ("residential", "Residential"),
    ("agricultural", "Agricultural"),
    ("recreational", "Recreational"),
]

st.title("Watersheds")


def _render_map(geojson_data: dict | None, center: tuple[float, float] = (45.5, -73.6)) -> None:
    m = folium.Map(location=center, zoom_start=10, tiles="OpenStreetMap")
    if geojson_data:
        gj = folium.GeoJson(normalize_geojson_for_folium(geojson_data), name="Watershed boundary")
        gj.add_to(m)
    st_folium(m, height=350, use_container_width=True)


def _geojson_uploader(
    key: str,
    existing_geojson: str | None,
    *,
    area_target_key: str | None = None,
) -> tuple[str | None, dict | None]:
    """Render upload widget + current GeoJSON string display.

    Returns (geojson_str, parsed_dict) where both are None if no valid GeoJSON.

    When ``area_target_key`` is provided, the first time a given file is
    uploaded its geodesic surface area (ha) is written to that session-state
    key so the surface_area number_input picks it up on the next rerun.
    """
    uploaded = st.file_uploader(
        "Upload GeoJSON boundary",
        type=["geojson", "json"],
        key=f"{key}_uploader",
        help="Must contain only Polygon or MultiPolygon geometries.",
    )
    if uploaded is not None:
        raw = uploaded.read().decode("utf-8")
        parsed, err = validate_geojson(raw)
        if err:
            st.error(f"Invalid GeoJSON: {err}")
            return existing_geojson, None
        st.success("GeoJSON validated — Polygon/MultiPolygon geometry detected.")
        if area_target_key and parsed:
            if maybe_prefill_area(
                uploaded,
                parsed,
                target_key=area_target_key,
                sentinel_key=f"{key}_area_sentinel",
            ):
                st.rerun()
        return raw, parsed

    if existing_geojson:
        parsed, _ = validate_geojson(existing_geojson)
        return existing_geojson, parsed

    return None, None


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

try:
    items: list[dict] = list_watersheds()
except APIError as e:
    st.error(f"Cannot load watersheds: {e.message}")
    st.stop()

id_to_name = {w["watershed_id"]: w["name"] or f"#{w['watershed_id']}" for w in items}

# ---------------------------------------------------------------------------
# Create form
# ---------------------------------------------------------------------------

with st.expander("➕ Create new watershed", expanded=False):
    with st.form("ws_create_form", clear_on_submit=True):
        c_name = st.text_input("Name")
        c_desc = st.text_area("Description")
        c_surface = st.number_input(
            "Surface area (ha)",
            min_value=0.0,
            value=None,
            key="ws_create_surface",
            help="Auto-filled from uploaded GeoJSON; edit to override.",
        )
        c_conc = st.number_input("Concentration time (min)", min_value=0, step=1, value=None)
        c_imp = st.number_input("Impervious surface (%)", min_value=0.0, max_value=100.0, value=None)

        parent_labels = ["(none)"] + [f"{v} (#{k})" for k, v in id_to_name.items()]
        c_parent_label = st.selectbox("Parent watershed", parent_labels)

        st.subheader("Land Use (%)", divider=False)
        st.caption("Leave blank if unknown. Values represent percentage of watershed area.")
        c_land_use: dict[str, float | None] = {}
        lu_cols = st.columns(3)
        for i, (field, label) in enumerate(_LAND_USE_FIELDS):
            c_land_use[field] = lu_cols[i % 3].number_input(
                label, min_value=0.0, max_value=100.0, value=None, key=f"c_lu_{field}"
            )

        submitted = st.form_submit_button("Create")

    # GeoJSON upload lives outside the form (file_uploader + form = limitation)
    st.caption("Boundary (optional)")
    c_geojson_str, c_geojson_parsed = _geojson_uploader(
        "ws_create", None, area_target_key="ws_create_surface"
    )
    if c_geojson_parsed:
        _render_map(c_geojson_parsed)

    if submitted:
        parent_id: int | None = None
        if c_parent_label and c_parent_label != "(none)":
            pid_str = c_parent_label.rsplit("(#", 1)[-1].rstrip(")")
            try:
                parent_id = int(pid_str)
            except ValueError:
                parent_id = None
        try:
            new_ws = create_watershed(
                {
                    "name": c_name.strip() or None,
                    "description": c_desc.strip() or None,
                    "surface_area": c_surface,
                    "concentration_time": int(c_conc) if c_conc is not None else None,
                    "impervious_surface": c_imp,
                    "parent_watershed_id": parent_id,
                    "geometry_geojson": c_geojson_str,
                }
            )
            if any(v is not None for v in c_land_use.values()):
                upsert_land_use(new_ws["watershed_id"], c_land_use)
            st.success("Watershed created.")
            st.rerun()
        except APIError as e:
            st.error(f"Create failed: {e.message}")

# ---------------------------------------------------------------------------
# List + select for edit/delete
# ---------------------------------------------------------------------------

if not items:
    st.info("No watersheds yet.")
    st.stop()

import pandas as pd

from app.components.id_format import humanize_id_columns

id_to_name = {w["watershed_id"]: w["name"] for w in items}
df = pd.DataFrame(
    [
        {
            "ID": w["watershed_id"],
            "Name": w["name"] or "",
            "Surface (ha)": w["surface_area"],
            "Conc. time (min)": w["concentration_time"],
            "Impervious (%)": w["impervious_surface"],
            "parent_watershed_id": w["parent_watershed_id"],
            "Has boundary": w["geometry_geojson"] is not None,
        }
        for w in items
    ]
).sort_values("ID").reset_index(drop=True)

sel = st.dataframe(
    humanize_id_columns(df, resolvers={"parent_watershed_id": id_to_name}),
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
)
rows = (sel or {}).get("selection", {}).get("rows", [])
selected: dict | None = items[rows[0]] if rows else None

if selected is None:
    st.caption("Select a row to edit or view its boundary.")
    st.stop()

st.divider()
_ws_label = selected["name"] or f"Watershed #{selected['watershed_id']}"
st.subheader(f"Edit: {_ws_label}")

# Load existing land use (None if not yet set)
try:
    existing_land_use: dict | None = get_land_use(selected["watershed_id"])
except APIError:
    existing_land_use = None

# Map for currently stored geometry
existing_geojson_str: str | None = selected.get("geometry_geojson")
existing_parsed: dict | None = None
if existing_geojson_str:
    existing_parsed = json.loads(existing_geojson_str)

col_form, col_map = st.columns([1, 1])

with col_form:
    with st.form("ws_edit_form"):
        e_name = st.text_input("Name", value=selected.get("name") or "")
        e_desc = st.text_area("Description", value=selected.get("description") or "")
        e_surface_key = f"ws_edit_{selected['watershed_id']}_surface"
        e_surface = st.number_input(
            "Surface area (ha)",
            min_value=0.0,
            value=float(selected["surface_area"]) if selected["surface_area"] is not None else None,
            key=e_surface_key,
            help="Auto-filled when you upload a new GeoJSON; edit to override.",
        )
        e_conc = st.number_input(
            "Concentration time (min)",
            min_value=0,
            step=1,
            value=int(selected["concentration_time"]) if selected["concentration_time"] is not None else None,
        )
        e_imp = st.number_input(
            "Impervious surface (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(selected["impervious_surface"]) if selected["impervious_surface"] is not None else None,
        )

        # Parent watershed dropdown (exclude self)
        other_ws = {k: v for k, v in id_to_name.items() if k != selected["watershed_id"]}
        parent_opts = ["(none)"] + [f"{v} (#{k})" for k, v in other_ws.items()]
        current_parent = selected.get("parent_watershed_id")
        default_parent_idx = 0
        if current_parent and current_parent in other_ws:
            label = f"{other_ws[current_parent]} (#{current_parent})"
            if label in parent_opts:
                default_parent_idx = parent_opts.index(label)
        e_parent_label = st.selectbox("Parent watershed", parent_opts, index=default_parent_idx)

        st.subheader("Land Use (%)", divider=False)
        st.caption("Leave blank if unknown.")
        e_land_use: dict[str, float | None] = {}
        lu_edit_cols = st.columns(3)
        for i, (field, label) in enumerate(_LAND_USE_FIELDS):
            existing_val = existing_land_use.get(field) if existing_land_use else None
            e_land_use[field] = lu_edit_cols[i % 3].number_input(
                label,
                min_value=0.0,
                max_value=100.0,
                value=float(existing_val) if existing_val is not None else None,
                key=f"e_lu_{field}",
            )

        save_btn = st.form_submit_button("Save changes")
        del_btn = st.form_submit_button("🗑 Delete", type="secondary")

    # GeoJSON uploader (outside form)
    st.caption("Replace boundary (upload new GeoJSON, or leave blank to keep existing)")
    e_geojson_str, e_geojson_parsed = _geojson_uploader(
        f"ws_edit_{selected['watershed_id']}",
        existing_geojson_str,
        area_target_key=e_surface_key,
    )

with col_map:
    st.caption("Watershed boundary")
    display_geojson = e_geojson_parsed if e_geojson_parsed else existing_parsed
    _render_map(display_geojson)

# Handle save
if save_btn:
    e_parent_id: int | None = None
    if e_parent_label and e_parent_label != "(none)":
        pid_str = e_parent_label.rsplit("(#", 1)[-1].rstrip(")")
        try:
            e_parent_id = int(pid_str)
        except ValueError:
            e_parent_id = None

    # Keep existing GeoJSON if no new file was uploaded
    final_geojson = e_geojson_str if e_geojson_str is not None else existing_geojson_str

    try:
        update_watershed(
            selected["watershed_id"],
            {
                "name": e_name.strip() or None,
                "description": e_desc.strip() or None,
                "surface_area": e_surface,
                "concentration_time": int(e_conc) if e_conc is not None else None,
                "impervious_surface": e_imp,
                "parent_watershed_id": e_parent_id,
                "geometry_geojson": final_geojson,
            },
        )
        upsert_land_use(selected["watershed_id"], e_land_use)
        st.success("Saved.")
        st.rerun()
    except APIError as e:
        st.error(f"Save failed: {e.message}")

if del_btn:
    try:
        delete_watershed(selected["watershed_id"])
        st.success("Deleted.")
        st.rerun()
    except APIError as e:
        st.error(f"Delete failed: {e.message}")
