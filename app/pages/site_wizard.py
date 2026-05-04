"""Site Setup Wizard — create a site with process units and sampling locations."""

from __future__ import annotations

import streamlit as st

from app.api_client import (
    APIError,
    create_process_unit,
    create_sampling_location,
    create_site,
    list_process_unit_types,
    list_process_units_lookup,
    list_site_kinds,
)
from app.components.location_picker import render_location_picker
from app.components.wizard_helpers import (
    clear_wizard,
    nav,
    render_wizard_header,
    resolve_id,
    restore_snapshot,
)

_WIZ = "site_wiz"

STEPS = [
    "Site",
    "Process Units",
    "Sampling Locations",
    "Review & Create",
]

_STEP_PREFIXES: dict[int, list[str]] = {
    0: [f"{_WIZ}_s0_", f"{_WIZ}_loc_"],
    1: [f"{_WIZ}_pu_"],
    2: [f"{_WIZ}_sl_"],
    3: [],
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
            "process_units": list_process_units_lookup(),
        }
    except APIError as e:
        st.error(f"Failed to load lookup data: {e.message}")
        return None


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def _step_site(lookups: dict) -> None:
    restore_snapshot(_WIZ, 0)

    kind_opts = [{"id": k["id"], "label": k["name"]} for k in lookups["site_kinds"]]
    kind_labels = ["(none)"] + [o["label"] for o in kind_opts]

    st.text_input("Site name *", key=f"{_WIZ}_s0_name")
    st.selectbox("Site type", kind_labels, key=f"{_WIZ}_s0_kind")
    st.text_area("Description", key=f"{_WIZ}_s0_description")
    st.markdown("#### Location")
    render_location_picker(key_prefix=f"{_WIZ}_loc")

    def on_next() -> list[str]:
        errors: list[str] = []
        if not (st.session_state.get(f"{_WIZ}_s0_name") or "").strip():
            errors.append("Site name is required.")
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

    kind_opts = [
        {"id": k["process_unit_kind_id"], "label": k["name"]}
        for k in lookups["pu_kinds"]
    ]
    kind_labels = ["(none)"] + [o["label"] for o in kind_opts]
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
            st.text_input("Name *", key=f"{_WIZ}_pu_{pu_id}_name")
            st.text_input("Tag", key=f"{_WIZ}_pu_{pu_id}_tag")
            if kind_labels:
                st.selectbox("Kind", kind_labels, key=f"{_WIZ}_pu_{pu_id}_kind")
            if st.button("Remove", key=f"{_WIZ}_pu_{pu_id}_remove_btn"):
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
    restore_snapshot(_WIZ, 2)

    # Build PU options: wizard-created PUs (from step 1) + existing DB PUs
    pu_ids: list[int] = st.session_state.get(f"{_WIZ}_pu_ids", [])
    wizard_pu_labels = [
        st.session_state.get(f"{_WIZ}_pu_{pid}_name") or f"Process Unit {pid + 1}"
        for pid in pu_ids
    ]
    existing_pu_labels = [p["name"] for p in lookups.get("process_units", [])]
    pu_label_options = ["(none)"] + wizard_pu_labels + existing_pu_labels

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
            st.text_input("Name *", key=f"{_WIZ}_sl_{sl_id}_name")
            st.text_area("Description", key=f"{_WIZ}_sl_{sl_id}_description")
            st.selectbox("Process Unit", pu_label_options, key=f"{_WIZ}_sl_{sl_id}_pu")
            if st.button("Remove", key=f"{_WIZ}_sl_{sl_id}_remove_btn"):
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
    site_name = st.session_state.get(f"{_WIZ}_s0_name", "")
    kind_label = st.session_state.get(f"{_WIZ}_s0_kind", "(none)")
    description = st.session_state.get(f"{_WIZ}_s0_description", "")
    lat = st.session_state.get(f"{_WIZ}_loc_lat_input")
    lng = st.session_state.get(f"{_WIZ}_loc_lng_input")
    city = st.session_state.get(f"{_WIZ}_loc_city_input", "")
    country = st.session_state.get(f"{_WIZ}_loc_country_input", "")

    st.markdown("### Site")
    st.write(f"**Name:** {site_name}")
    st.write(f"**Type:** {kind_label}")
    if description:
        st.write(f"**Description:** {description}")
    if lat and lng:
        st.write(f"**Location:** {lat:.5f}, {lng:.5f}  {city} {country}".strip())

    pu_ids = st.session_state.get(f"{_WIZ}_pu_ids", [])
    if pu_ids:
        st.markdown("### Process Units")
        for pu_id in pu_ids:
            name = st.session_state.get(f"{_WIZ}_pu_{pu_id}_name", "")
            tag = st.session_state.get(f"{_WIZ}_pu_{pu_id}_tag", "")
            kind = st.session_state.get(f"{_WIZ}_pu_{pu_id}_kind", "(none)")
            st.write(f"- **{name}** (tag: {tag or '—'}, kind: {kind})")

    sl_ids = st.session_state.get(f"{_WIZ}_sl_ids", [])
    if sl_ids:
        st.markdown("### Sampling Locations")
        for sl_id in sl_ids:
            name = st.session_state.get(f"{_WIZ}_sl_{sl_id}_name", "")
            pu_label = st.session_state.get(f"{_WIZ}_sl_{sl_id}_pu", "(none)")
            st.write(f"- **{name}** → process unit: {pu_label}")

    def on_next() -> list[str]:
        errors = _execute_creates(lookups)
        if not errors:
            st.toast("Site created successfully!", icon="✅")
            clear_wizard(_WIZ)
            st.rerun()
        return errors

    nav(
        wiz_id=_WIZ,
        step=3,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _execute_creates(lookups: dict) -> list[str]:
    for s in range(3):
        restore_snapshot(_WIZ, s)

    errors: list[str] = []
    pu_id_map: dict[int, int] = {}  # wiz_pu_id → DB ProcessUnit_ID

    kind_opts = [{"id": k["id"], "label": k["name"]} for k in lookups["site_kinds"]]
    pu_kind_opts = [
        {"id": k["process_unit_kind_id"], "label": k["name"]}
        for k in lookups["pu_kinds"]
    ]

    # 1. Create site
    site_kind_label = st.session_state.get(f"{_WIZ}_s0_kind") or None
    site_kind_id = (
        resolve_id(site_kind_label, kind_opts)
        if site_kind_label and site_kind_label != "(none)"
        else None
    )
    try:
        site = create_site(
            {
                "name": (st.session_state.get(f"{_WIZ}_s0_name") or "").strip(),
                "site_kind_id": site_kind_id,
                "description": st.session_state.get(f"{_WIZ}_s0_description") or None,
                "lat_wgs84": st.session_state.get(f"{_WIZ}_loc_lat_input"),
                "long_wgs84": st.session_state.get(f"{_WIZ}_loc_lng_input"),
                "city": st.session_state.get(f"{_WIZ}_loc_city_input") or None,
                "province": st.session_state.get(f"{_WIZ}_loc_province_input") or None,
                "country": st.session_state.get(f"{_WIZ}_loc_country_input") or None,
            }
        )
        site_id: int = site["id"]
    except APIError as e:
        errors.append(f"Site creation failed: {e.message}")
        return errors

    # 2. Create process units
    for pu_wiz_id in st.session_state.get(f"{_WIZ}_pu_ids", []):
        name = (st.session_state.get(f"{_WIZ}_pu_{pu_wiz_id}_name") or "").strip()
        tag = (st.session_state.get(f"{_WIZ}_pu_{pu_wiz_id}_tag") or "").strip()
        kind_label = st.session_state.get(f"{_WIZ}_pu_{pu_wiz_id}_kind") or None
        pu_kind_id = (
            resolve_id(kind_label, pu_kind_opts)
            if kind_label and kind_label != "(none)"
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
        except APIError as e:
            errors.append(f"Process unit '{name}': {e.message}")

    if errors:
        return errors

    # Build label → DB ID map for PU resolution in SLs
    pu_label_to_id: dict[str, int] = {}
    for pu_wiz_id, db_id in pu_id_map.items():
        wiz_name = (st.session_state.get(f"{_WIZ}_pu_{pu_wiz_id}_name") or "").strip()
        if wiz_name:
            pu_label_to_id[wiz_name] = db_id
    for pu in lookups.get("process_units", []):
        pu_label_to_id[pu["name"]] = pu["id"]

    # 3. Create sampling locations
    for sl_wiz_id in st.session_state.get(f"{_WIZ}_sl_ids", []):
        name = (st.session_state.get(f"{_WIZ}_sl_{sl_wiz_id}_name") or "").strip()
        if not name:
            continue
        pu_label = st.session_state.get(f"{_WIZ}_sl_{sl_wiz_id}_pu") or None
        pu_db_id = (
            pu_label_to_id.get(pu_label)
            if pu_label and pu_label != "(none)"
            else None
        )
        try:
            create_sampling_location(
                site_id,
                {
                    "name": name,
                    "description": st.session_state.get(f"{_WIZ}_sl_{sl_wiz_id}_description") or None,
                    "process_unit_id": pu_db_id,
                },
            )
        except APIError as e:
            errors.append(f"Sampling location '{name}': {e.message}")

    return errors


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
    }[step](lookups)


main()
