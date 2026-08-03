"""Site Setup Wizard — create a site with process units and sampling locations."""

from __future__ import annotations

import json

import folium
import streamlit as st
from streamlit_folium import st_folium

from app.api_client import (
    APIError,
    create_process_unit,
    create_sampling_location,
    create_site,
    create_watershed,
    list_process_unit_types,
    list_site_kinds,
    list_watersheds,
)
from app.components.geo_utils import geojson_area_ha, geojson_bounds, normalize_geojson_for_folium, validate_geojson
from app.components.location_picker import render_location_picker
from app.components.kind_select import kind_caption, kind_options
from app.components.labels import NONE_LABEL
from app.components.schema_registry import describe
from app.components.wizard_helpers import (
    clear_wizard,
    nav,
    render_wizard_header,
    render_wizard_result,
    resolve_id,
    restore_snapshot,
)

def _validate_ws_geojson(raw: str) -> tuple[dict | None, str | None]:
    """Validate a watershed GeoJSON string. Returns (parsed, error)."""
    return validate_geojson(raw)


def _on_ws_geojson_upload() -> None:
    # ponytail: callback runs pre-rerun so session_state writes are safe here
    uploaded = st.session_state.get(f"{_WIZ}_ws_new_geojson_upload")
    geojson_key = f"{_WIZ}_ws_new_geojson"
    err_key = f"{_WIZ}_ws_new_geojson_error"
    sentinel_key = f"{_WIZ}_ws_new_geojson_area_sentinel"
    area_key = f"{_WIZ}_ws_new_surface_area"

    if uploaded is None:
        st.session_state.pop(geojson_key, None)
        st.session_state.pop(err_key, None)
        return

    raw = uploaded.read().decode("utf-8")
    parsed, err = _validate_ws_geojson(raw)
    if err or parsed is None:
        st.session_state[err_key] = err
        st.session_state.pop(geojson_key, None)
        return

    st.session_state.pop(err_key, None)
    st.session_state[geojson_key] = raw

    file_id = getattr(uploaded, "file_id", None) or (uploaded.name, uploaded.size)
    if st.session_state.get(sentinel_key) != file_id:
        try:
            st.session_state[area_key] = round(geojson_area_ha(parsed), 2)
            st.session_state[sentinel_key] = file_id
        except Exception:
            pass


def _render_ws_map(geojson_data: dict | None) -> None:
    bounds = geojson_bounds(geojson_data) if geojson_data else None
    if bounds:
        center = [(bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2]
        m = folium.Map(location=center, zoom_start=16, tiles="OpenStreetMap")
    else:
        m = folium.Map(location=[45.5, -73.6], zoom_start=10, tiles="OpenStreetMap")
    if geojson_data:
        folium.GeoJson(normalize_geojson_for_folium(geojson_data), name="Watershed boundary").add_to(m)
    st_folium(m, height=400, use_container_width=True, returned_objects=[])


_WIZ = "site_wiz"

STEPS = [
    "Site",
    "Process Units",
    "Sampling Locations",
    "Review & Create",
    "Summary",
]

_STEP_PREFIXES: dict[int, list[str]] = {
    0: [f"{_WIZ}_s0_", f"{_WIZ}_loc_", f"{_WIZ}_ws_"],
    1: [f"{_WIZ}_pu_"],
    2: [f"{_WIZ}_sl_"],
    3: [],
    4: [],
}


def _init() -> None:
    defaults: dict = {
        f"{_WIZ}_step": 0,
        f"{_WIZ}_pu_ids": [],
        f"{_WIZ}_pu_next_id": 0,
        f"{_WIZ}_sl_ids": [],
        f"{_WIZ}_sl_next_id": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _cancel() -> None:
    clear_wizard(_WIZ)


def _load_lookups() -> dict | None:
    try:
        return {
            "site_kinds": list_site_kinds(),
            "pu_kinds": list_process_unit_types(),
            "watersheds": list_watersheds(),
        }
    except APIError as e:
        st.error(f"Failed to load lookup data: {e.message}")
        return None


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def _step_site(lookups: dict) -> None:
    restore_snapshot(_WIZ, 0)

    kind_opts = kind_options(lookups["site_kinds"], "id")
    kind_labels = [NONE_LABEL] + [o["label"] for o in kind_opts]

    st.text_input("Site name *", key=f"{_WIZ}_s0_name", help=describe("Site", "Name"))
    st.selectbox(
        "Site type",
        kind_labels,
        key=f"{_WIZ}_s0_kind",
        help=describe("Site", "SiteKind_ID"),
    )
    kind_caption(kind_opts, st.session_state.get(f"{_WIZ}_s0_kind"))
    st.text_area(
        "Description",
        key=f"{_WIZ}_s0_description",
        help=describe("Site", "Description"),
    )
    st.markdown("#### Location")
    render_location_picker(key_prefix=f"{_WIZ}_loc")

    st.markdown("#### Watershed (optional)")
    st.caption("Does this site drain into a watershed you want to track?")
    ws_mode = st.radio(
        "Watershed",
        ["None", "Select existing", "Create new"],
        key=f"{_WIZ}_ws_mode",
        label_visibility="collapsed",
        help=(
            "None leaves the site unlinked; Select existing attaches it to a watershed "
            "already in the database; Create new adds a watershed record (name, boundary, "
            "area) and attaches the site to it."
        ),
    )

    if ws_mode == "Select existing":
        ws_opts = [{"id": w["watershed_id"], "label": w["name"]} for w in lookups["watersheds"]]
        ws_labels = [NONE_LABEL] + [o["label"] for o in ws_opts]
        st.selectbox(
            "Watershed",
            ws_labels,
            key=f"{_WIZ}_ws_select",
            help=describe("Site", "Watershed_ID"),
        )
    elif ws_mode == "Create new":
        st.text_input(
            "Watershed name *",
            key=f"{_WIZ}_ws_new_name",
            help=describe("Watershed", "Name"),
        )
        st.text_area(
            "Description",
            key=f"{_WIZ}_ws_new_description",
            help=describe("Watershed", "Description"),
        )
        st.caption("Boundary (optional)")
        uploaded = st.file_uploader(
            "Upload GeoJSON boundary",
            type=["geojson", "json"],
            key=f"{_WIZ}_ws_new_geojson_upload",
            on_change=_on_ws_geojson_upload,
            help="Must contain only Polygon or MultiPolygon geometries.",
        )
        if uploaded is not None:
            if err := st.session_state.get(f"{_WIZ}_ws_new_geojson_error"):
                st.error(err)
            else:
                st.success("GeoJSON validated.")
        st.number_input(
            "Surface area (ha)",
            min_value=0.0,
            key=f"{_WIZ}_ws_new_surface_area",
            help="Auto-filled from uploaded GeoJSON; edit to override.",
        )
        st.number_input(
            "Concentration time (min)",
            min_value=0,
            step=1,
            key=f"{_WIZ}_ws_new_concentration_time",
            help=describe("Watershed", "concentration_time"),
        )
        st.number_input(
            "Impervious surface (%)",
            min_value=0.0,
            max_value=100.0,
            key=f"{_WIZ}_ws_new_impervious_surface",
            help=describe("Watershed", "impervious_surface"),
        )
        if st.session_state.get(f"{_WIZ}_ws_new_geojson"):
            _render_ws_map(json.loads(st.session_state[f"{_WIZ}_ws_new_geojson"]))

    def on_next() -> list[str]:
        errors: list[str] = []
        if not (st.session_state.get(f"{_WIZ}_s0_name") or "").strip():
            errors.append("Site name is required.")
        if st.session_state.get(f"{_WIZ}_ws_mode") == "Create new":
            if not (st.session_state.get(f"{_WIZ}_ws_new_name") or "").strip():
                errors.append("Watershed name is required when creating a new watershed.")
        return errors

    nav(
        wiz_id=_WIZ,
        step=0,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
    )


def _step_process_units(lookups: dict) -> None:
    restore_snapshot(_WIZ, 1)

    kind_opts = kind_options(lookups["pu_kinds"], "process_unit_kind_id")
    kind_labels = [NONE_LABEL] + [o["label"] for o in kind_opts]
    pu_ids: list[int] = st.session_state[f"{_WIZ}_pu_ids"]

    st.info("Add process units at this site (optional — click Next to skip).")

    if st.button("+ Add Process Unit", key=f"{_WIZ}_pu_add_btn"):
        nid = st.session_state[f"{_WIZ}_pu_next_id"]
        st.session_state[f"{_WIZ}_pu_ids"].append(nid)
        st.session_state[f"{_WIZ}_pu_next_id"] = nid + 1
        st.rerun()

    for pu_id in list(pu_ids):
        label = st.session_state.get(f"{_WIZ}_pu_{pu_id}_name") or f"Process Unit {pu_id + 1}"
        with st.expander(label, expanded=True):
            st.text_input(
                "Name *",
                key=f"{_WIZ}_pu_{pu_id}_name",
                help=describe("ProcessUnit", "name"),
            )
            st.text_input(
                "P&ID Tag",
                key=f"{_WIZ}_pu_{pu_id}_tag",
                help=describe("ProcessUnit", "tag"),
            )
            if kind_labels:
                st.selectbox(
                    "Kind",
                    kind_labels,
                    key=f"{_WIZ}_pu_{pu_id}_kind",
                    help=describe("ProcessUnit", "process_unit_kind_id"),
                )
                kind_caption(kind_opts, st.session_state.get(f"{_WIZ}_pu_{pu_id}_kind"))
            if st.button("Remove", key=f"{_WIZ}_pu_{pu_id}_remove"):
                st.session_state[f"{_WIZ}_pu_ids"].remove(pu_id)
                st.rerun()

    def on_next() -> list[str]:
        errors: list[str] = []
        for pu_id in st.session_state[f"{_WIZ}_pu_ids"]:
            if not (st.session_state.get(f"{_WIZ}_pu_{pu_id}_name") or "").strip():
                errors.append(f"Process Unit {pu_id + 1}: name is required.")
        return errors

    nav(
        wiz_id=_WIZ,
        step=1,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
    )


def _step_sampling_locations(lookups: dict) -> None:
    restore_snapshot(_WIZ, 1)  # Streamlit clears widget keys when not rendered; restore PU names
    restore_snapshot(_WIZ, 2)

    # Build PU options: only process units created earlier in this wizard —
    # this site doesn't exist yet, so no other site's process units apply.
    pu_ids: list[int] = st.session_state.get(f"{_WIZ}_pu_ids", [])
    wizard_pu_labels = [
        st.session_state.get(f"{_WIZ}_pu_{pid}_name") or f"Process Unit {pid + 1}"
        for pid in pu_ids
    ]
    pu_label_options = [NONE_LABEL] + wizard_pu_labels

    sl_ids: list[int] = st.session_state[f"{_WIZ}_sl_ids"]

    st.info("Add sampling locations at this site (optional — click Next to skip).")

    if st.button("+ Add Sampling Location", key=f"{_WIZ}_sl_add_btn"):
        nid = st.session_state[f"{_WIZ}_sl_next_id"]
        st.session_state[f"{_WIZ}_sl_ids"].append(nid)
        st.session_state[f"{_WIZ}_sl_next_id"] = nid + 1
        st.rerun()

    for sl_id in list(sl_ids):
        label = st.session_state.get(f"{_WIZ}_sl_{sl_id}_name") or f"Sampling Location {sl_id + 1}"
        with st.expander(label, expanded=True):
            st.text_input(
                "Name *",
                key=f"{_WIZ}_sl_{sl_id}_name",
                help=describe("SamplingPoint", "sampling_point"),
            )
            st.text_area(
                "Description",
                key=f"{_WIZ}_sl_{sl_id}_description",
                help=describe("SamplingPoint", "description"),
            )
            st.selectbox(
                "Process Unit",
                pu_label_options,
                key=f"{_WIZ}_sl_{sl_id}_pu",
                help=describe("SamplingPoint", "process_unit_id"),
            )
            if st.button("Remove", key=f"{_WIZ}_sl_{sl_id}_remove"):
                st.session_state[f"{_WIZ}_sl_ids"].remove(sl_id)
                st.rerun()

    def on_next() -> list[str]:
        errors: list[str] = []
        for sl_id in st.session_state[f"{_WIZ}_sl_ids"]:
            if not (st.session_state.get(f"{_WIZ}_sl_{sl_id}_name") or "").strip():
                errors.append(f"Sampling Location {sl_id + 1}: name is required.")
        return errors

    nav(
        wiz_id=_WIZ,
        step=2,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
    )


def _step_review(lookups: dict) -> None:
    # Streamlit clears widget-bound session_state keys for widgets not
    # rendered in the current run; restore them before reading.
    for s in range(3):
        restore_snapshot(_WIZ, s)

    site_name = st.session_state.get(f"{_WIZ}_s0_name", "")
    kind_label = st.session_state.get(f"{_WIZ}_s0_kind", NONE_LABEL)
    description = st.session_state.get(f"{_WIZ}_s0_description", "")
    lat = st.session_state.get(f"{_WIZ}_loc_lat_input")
    lng = st.session_state.get(f"{_WIZ}_loc_lng_input")
    city = st.session_state.get(f"{_WIZ}_loc_city_input", "")
    country = st.session_state.get(f"{_WIZ}_loc_country_input", "")
    ws_mode = st.session_state.get(f"{_WIZ}_ws_mode", "None")

    st.markdown("### Site")
    st.write(f"**Name:** {site_name}")
    st.write(f"**Type:** {kind_label}")
    if description:
        st.write(f"**Description:** {description}")
    if lat and lng:
        st.write(f"**Location:** {lat:.5f}, {lng:.5f}  {city} {country}".strip())
    if ws_mode == "Select existing":
        ws_label = st.session_state.get(f"{_WIZ}_ws_select", NONE_LABEL)
        st.write(f"**Watershed:** {ws_label}")
    elif ws_mode == "Create new":
        ws_name = st.session_state.get(f"{_WIZ}_ws_new_name", "")
        st.write(f"**Watershed:** {ws_name} (new)")

    pu_ids = st.session_state.get(f"{_WIZ}_pu_ids", [])
    if pu_ids:
        st.markdown("### Process Units")
        for pu_id in pu_ids:
            name = st.session_state.get(f"{_WIZ}_pu_{pu_id}_name", "")
            tag = st.session_state.get(f"{_WIZ}_pu_{pu_id}_tag", "")
            kind = st.session_state.get(f"{_WIZ}_pu_{pu_id}_kind", NONE_LABEL)
            st.write(f"- **{name}** (P&ID Tag: {tag or '—'}, kind: {kind})")

    sl_ids = st.session_state.get(f"{_WIZ}_sl_ids", [])
    if sl_ids:
        st.markdown("### Sampling Locations")
        for sl_id in sl_ids:
            name = st.session_state.get(f"{_WIZ}_sl_{sl_id}_name", "")
            pu_label = st.session_state.get(f"{_WIZ}_sl_{sl_id}_pu", NONE_LABEL)
            st.write(f"- **{name}** → process unit: {pu_label}")

    def on_next() -> list[str]:
        created, errors = _execute_creates(lookups)
        st.session_state[f"_{_WIZ}_created"] = created
        st.session_state[f"_{_WIZ}_errors"] = errors
        return []

    nav(
        wiz_id=_WIZ,
        step=3,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
        next_label="Confirm & Create",
    )


def _step_summary(lookups: dict) -> None:
    render_wizard_result(
        wiz_id=_WIZ,
        title="Site",
        created=st.session_state.get(f"_{_WIZ}_created", []),
        errors=st.session_state.get(f"_{_WIZ}_errors", []),
        on_restart=lambda: clear_wizard(_WIZ),
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _execute_creates(lookups: dict) -> tuple[list[dict], list[str]]:
    for s in range(3):
        restore_snapshot(_WIZ, s)

    created: list[dict] = []
    errors: list[str] = []
    pu_id_map: dict[int, int] = {}  # wiz_pu_id → DB ProcessUnit_ID

    kind_opts = [{"id": k["id"], "label": k["name"]} for k in lookups["site_kinds"]]
    pu_kind_opts = [
        {"id": k["process_unit_kind_id"], "label": k["name"]}
        for k in lookups["pu_kinds"]
    ]
    ws_opts = [{"id": w["watershed_id"], "label": w["name"]} for w in lookups["watersheds"]]

    # 1. Resolve watershed
    watershed_id: int | None = None
    ws_mode = st.session_state.get(f"{_WIZ}_ws_mode", "None")
    if ws_mode == "Create new":
        try:
            ws = create_watershed(
                {
                    "name": (st.session_state.get(f"{_WIZ}_ws_new_name") or "").strip(),
                    "description": st.session_state.get(f"{_WIZ}_ws_new_description") or None,
                    "surface_area": st.session_state.get(f"{_WIZ}_ws_new_surface_area") or None,
                    "concentration_time": st.session_state.get(f"{_WIZ}_ws_new_concentration_time") or None,
                    "impervious_surface": st.session_state.get(f"{_WIZ}_ws_new_impervious_surface") or None,
                    "geometry_geojson": st.session_state.get(f"{_WIZ}_ws_new_geojson") or None,
                }
            )
            watershed_id = ws["watershed_id"]
            created.append({"label": f"Watershed: {ws['name']}", "detail": f"id={watershed_id}"})
        except APIError as e:
            errors.append(f"Watershed creation failed: {e.message}")
            return created, errors
    elif ws_mode == "Select existing":
        ws_label = st.session_state.get(f"{_WIZ}_ws_select") or None
        if ws_label and ws_label != NONE_LABEL:
            watershed_id = resolve_id(ws_label, ws_opts)

    # 2. Create site
    site_kind_label = st.session_state.get(f"{_WIZ}_s0_kind") or None
    site_kind_id = (
        resolve_id(site_kind_label, kind_opts)
        if site_kind_label and site_kind_label != NONE_LABEL
        else None
    )
    try:
        site = create_site(
            {
                "name": (st.session_state.get(f"{_WIZ}_s0_name") or "").strip(),
                "site_kind_id": site_kind_id,
                "watershed_id": watershed_id,
                "description": st.session_state.get(f"{_WIZ}_s0_description") or None,
                "lat_wgs84": st.session_state.get(f"{_WIZ}_loc_lat_input"),
                "long_wgs84": st.session_state.get(f"{_WIZ}_loc_lng_input"),
                "city": st.session_state.get(f"{_WIZ}_loc_city_input") or None,
                "province": st.session_state.get(f"{_WIZ}_loc_province_input") or None,
                "country": st.session_state.get(f"{_WIZ}_loc_country_input") or None,
            }
        )
        site_id: int = site["id"]
        created.append({"label": f"Site: {site['name']}", "detail": f"id={site_id}"})
    except APIError as e:
        errors.append(f"Site creation failed: {e.message}")
        return created, errors

    # 3. Create process units
    for pu_wiz_id in st.session_state.get(f"{_WIZ}_pu_ids", []):
        name = (st.session_state.get(f"{_WIZ}_pu_{pu_wiz_id}_name") or "").strip()
        tag = (st.session_state.get(f"{_WIZ}_pu_{pu_wiz_id}_tag") or "").strip()
        kind_label = st.session_state.get(f"{_WIZ}_pu_{pu_wiz_id}_kind") or None
        pu_kind_id = (
            resolve_id(kind_label, pu_kind_opts)
            if kind_label and kind_label != NONE_LABEL
            else None
        )
        if not name:
            continue
        try:
            pu = create_process_unit(
                {
                    "site_id": site_id,
                    "name": name,
                    "tag": tag or name,
                    "process_unit_kind_id": pu_kind_id,
                }
            )
            pu_id_map[pu_wiz_id] = pu["id"]
            created.append({"label": f"Process unit: {name}", "detail": f"id={pu['id']}"})
        except APIError as e:
            errors.append(f"Process unit '{name}': {e.message}")

    if errors:
        return created, errors

    # Build label → DB ID map for PU resolution in SLs
    pu_label_to_id: dict[str, int] = {}
    for pu_wiz_id, db_id in pu_id_map.items():
        wiz_name = (st.session_state.get(f"{_WIZ}_pu_{pu_wiz_id}_name") or "").strip()
        if wiz_name:
            pu_label_to_id[wiz_name] = db_id
    # 4. Create sampling locations
    for sl_wiz_id in st.session_state.get(f"{_WIZ}_sl_ids", []):
        name = (st.session_state.get(f"{_WIZ}_sl_{sl_wiz_id}_name") or "").strip()
        if not name:
            continue
        pu_label = st.session_state.get(f"{_WIZ}_sl_{sl_wiz_id}_pu") or None
        pu_db_id = (
            pu_label_to_id.get(pu_label)
            if pu_label and pu_label != NONE_LABEL
            else None
        )
        try:
            sl = create_sampling_location(
                site_id,
                {
                    "name": name,
                    "description": st.session_state.get(f"{_WIZ}_sl_{sl_wiz_id}_description") or None,
                    "process_unit_id": pu_db_id,
                },
            )
            sl_id = sl.get("id") if isinstance(sl, dict) else None
            created.append({"label": f"Sampling location: {name}", "detail": f"id={sl_id}" if sl_id else None})
        except APIError as e:
            errors.append(f"Sampling location '{name}': {e.message}")

    return created, errors


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def main() -> None:
    st.title("🏭 Site Setup Wizard")
    _init()

    with st.spinner("Loading lookup data…"):
        lookups = _load_lookups()
    if lookups is None:
        return

    step = st.session_state[f"{_WIZ}_step"]
    render_wizard_header(step, STEPS)

    {
        0: _step_site,
        1: _step_process_units,
        2: _step_sampling_locations,
        3: _step_review,
        4: _step_summary,
    }[step](lookups)


main()
