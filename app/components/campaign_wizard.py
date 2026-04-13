"""Multi-step campaign creation wizard for open_datEAUbase."""

from __future__ import annotations

import streamlit as st

from app.api_client import (
    APIError,
    create_campaign,
    create_campaign_deployment,
    create_channel,
    create_das,
    create_equipment,
    create_equipment_model,
    create_sampling_location,
    create_signal_port,
    create_site,
    list_campaign_types,
    list_das_lookup,
    list_equipment_lookup,
    list_equipment_models_lookup,
    list_parameters_lookup,
    list_persons_lookup,
    list_processing_degrees_lookup,
    list_signal_port_types_lookup,
    list_signal_ports,
    list_site_sampling_locations,
    list_site_types,
    list_sites_lookup,
    register_equipment_at_port,
)
from app.components.location_picker import render_location_picker

STEPS = [
    "Campaign basics",
    "Site",
    "Sampling Locations",
    "Data Acquisition Systems",
    "Equipment & Tags",
    "Review & Create",
]

_VALUE_TYPES = [
    {"id": 1, "label": "Scalar"},
    {"id": 2, "label": "Vector"},
    {"id": 3, "label": "Matrix"},
    {"id": 4, "label": "Image"},
]

# Session-state key prefixes that belong to each step (for snapshot/restore)
_STEP_PREFIXES: dict[int, list[str]] = {
    0: ["wiz_s0_"],
    1: ["wiz_s1_", "wiz_site_"],
    2: ["wiz_sl_"],
    3: ["wiz_das_"],
    4: ["wiz_eq_", "wiz_tag_"],
    5: [],
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def init_wizard() -> None:
    """Ensure wizard session-state keys exist. Idempotent."""
    defaults: dict = {
        "wizard_step": 0,
        "wiz_sl_ids": [],
        "wiz_sl_next_id": 0,
        "wiz_das_ids": [],
        "wiz_das_next_id": 0,
        "wiz_eq_ids": [],
        "wiz_eq_next_id": 0,
        "wiz_tag_ids": [],
        "wiz_tag_next_id": 0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def clear_wizard() -> None:
    """Remove all wizard state from session_state."""
    to_del = [
        k
        for k in list(st.session_state.keys())
        if k.startswith("wiz_")
        or k.startswith("_snap_s")
        or k in ("wizard_active", "wizard_step")
    ]
    for k in to_del:
        del st.session_state[k]


def render_wizard() -> None:
    """Render the campaign creation wizard (replaces full page content)."""
    init_wizard()
    with st.spinner("Loading lookup data…"):
        lookups = _load_lookups()
    if lookups is None:
        return

    step = st.session_state.wizard_step
    _render_header(step)

    {
        0: _step_campaign,
        1: _step_site,
        2: _step_sampling_locations,
        3: _step_das,
        4: _step_equipment_and_tags,
        5: _step_review,
    }[step](lookups)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def _load_lookups() -> dict | None:
    try:
        sp_data = list_signal_ports(page_size=500)
        signal_ports_flat = [
            {
                "id": sp["signal_port_id"],
                "label": f"{sp['tag']} ({sp.get('das_name', '')})",
            }
            for sp in sp_data.get("items", [])
        ]
        return {
            "campaign_types": list_campaign_types(),
            "sites": list_sites_lookup(),
            "site_types": list_site_types(),
            "equipment": list_equipment_lookup(),
            "equipment_models": list_equipment_models_lookup(),
            "parameters": list_parameters_lookup(),
            "processing_degrees": list_processing_degrees_lookup(),
            "das": list_das_lookup(),
            "signal_port_types": list_signal_port_types_lookup(),
            "signal_ports_flat": signal_ports_flat,
            "persons": list_persons_lookup(),
        }
    except APIError as e:
        st.error(f"Failed to load lookup data: {e.message}")
        return None


# ---------------------------------------------------------------------------
# Snapshot-based back navigation
# ---------------------------------------------------------------------------


def _save_snapshot(step: int) -> None:
    """Copy all session-state keys for this step into _snap_s{step}."""
    prefixes = _STEP_PREFIXES.get(step, [])
    snap: dict = {}
    for key, val in st.session_state.items():
        if any(key.startswith(p) for p in prefixes):
            snap[key] = val
    st.session_state[f"_snap_s{step}"] = snap


def _restore_snapshot(step: int) -> None:
    """Restore keys from _snap_s{step} for any that are not already present."""
    snap: dict = st.session_state.get(f"_snap_s{step}", {})
    for key, val in snap.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Header & navigation
# ---------------------------------------------------------------------------


def _render_header(step: int) -> None:
    fraction = step / max(len(STEPS) - 1, 1)
    st.progress(fraction)
    st.caption(f"Step {step + 1} / {len(STEPS)}: **{STEPS[step]}**")
    st.markdown(f"## {STEPS[step]}")


def _nav(step: int, on_next) -> None:
    """Render Cancel / Back / Next navigation row."""
    st.divider()
    col_cancel, col_back, _, col_next = st.columns([1, 1, 5, 2])

    with col_cancel:
        if st.button("✖ Cancel", key=f"wiz_cancel_{step}"):
            clear_wizard()
            st.rerun()

    with col_back:
        if st.button("◀ Back", key=f"wiz_back_{step}", disabled=step == 0):
            _save_snapshot(step)
            st.session_state.wizard_step -= 1
            st.rerun()

    with col_next:
        is_last = step == len(STEPS) - 1
        label = "Confirm & Create" if is_last else "Next ▶"
        if st.button(label, key=f"wiz_next_{step}", type="primary"):
            errors = on_next()
            if errors:
                for err in errors:
                    st.error(err)
            elif not is_last:
                _save_snapshot(step)
                st.session_state.wizard_step += 1
                st.rerun()
            # Last step: on_next calls st.rerun() on success itself


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_id(label: str | None, opts: list[dict]) -> int | None:
    """Return the `id` field for the first option whose `label` matches."""
    if not label:
        return None
    match = next((o for o in opts if o.get("label") == label), None)
    return match["id"] if match else None


def _model_label(m: dict) -> str:
    parts = [p for p in [m.get("manufacturer"), m.get("model_name")] if p]
    return " – ".join(parts) if parts else f"Model {m.get('model_id', '?')}"


def _sl_display_label(sl_wiz_id: int) -> str:
    mode = st.session_state.get(f"wiz_sl_{sl_wiz_id}_mode", "New")
    if mode == "Existing":
        return (
            st.session_state.get(f"wiz_sl_{sl_wiz_id}_existing_label")
            or f"Sampling point {sl_wiz_id}"
        )
    return (
        st.session_state.get(f"wiz_sl_{sl_wiz_id}_name")
        or f"New sampling point {sl_wiz_id}"
    )


def _das_display_label(das_wiz_id: int) -> str:
    mode = st.session_state.get(f"wiz_das_{das_wiz_id}_mode", "Existing")
    if mode == "Existing":
        return (
            st.session_state.get(f"wiz_das_{das_wiz_id}_das_label")
            or f"Data Acquisition System {das_wiz_id + 1}"
        )
    return (
        st.session_state.get(f"wiz_das_{das_wiz_id}_das_name")
        or f"New Data Acquisition System {das_wiz_id + 1}"
    )


def _eq_display_label(eq_wiz_id: int) -> str:
    mode = st.session_state.get(f"wiz_eq_{eq_wiz_id}_mode", "Existing")
    if mode == "Existing":
        return (
            st.session_state.get(f"wiz_eq_{eq_wiz_id}_eq_label")
            or f"Equipment {eq_wiz_id + 1}"
        )
    return (
        st.session_state.get(f"wiz_eq_{eq_wiz_id}_identifier")
        or f"New equipment {eq_wiz_id + 1}"
    )


# ---------------------------------------------------------------------------
# Step 0: Campaign basics
# ---------------------------------------------------------------------------


def _step_campaign(lookups: dict) -> None:
    _restore_snapshot(0)
    type_opts = [
        {"id": t["campaign_type_id"], "label": t["name"]}
        for t in lookups["campaign_types"]
    ]
    type_labels = [o["label"] for o in type_opts]
    person_opts: list[dict] = lookups.get("persons", [])
    person_labels = ["(none)"] + [p["label"] for p in person_opts]

    st.text_input("Campaign name *", key="wiz_s0_name")
    if type_labels:
        st.selectbox("Campaign type *", type_labels, key="wiz_s0_campaign_type")
    else:
        st.warning("No campaign types found in the database.")
    st.date_input("Start date", key="wiz_s0_start_date", value=None)
    st.date_input("End date", key="wiz_s0_end_date", value=None)
    st.text_area("Description", key="wiz_s0_description")
    st.selectbox(
        "Responsible person",
        person_labels,
        key="wiz_s0_responsible_person",
        help="Optional. Select the person responsible for this campaign.",
    )

    def on_next() -> list[str]:
        errors: list[str] = []
        if not (st.session_state.get("wiz_s0_name") or "").strip():
            errors.append("Campaign name is required.")
        if not type_labels:
            errors.append("No campaign types available — cannot proceed.")
        elif not st.session_state.get("wiz_s0_campaign_type"):
            errors.append("Campaign type is required.")
        return errors

    _nav(0, on_next)


# ---------------------------------------------------------------------------
# Step 1: Site
# ---------------------------------------------------------------------------


def _step_site(lookups: dict) -> None:
    _restore_snapshot(1)
    site_opts = [{"id": s["site_id"], "label": s["name"]} for s in lookups["sites"]]
    site_labels = [o["label"] for o in site_opts]

    mode = st.radio(
        "Site", ["Use existing", "Create new"], key="wiz_s1_mode", horizontal=True
    )

    if mode == "Use existing":
        if site_labels:
            st.selectbox("Select site *", site_labels, key="wiz_s1_site_label")
        else:
            st.info("No sites found. Switch to **Create new** to add one.")
    else:
        st.text_input("Site name *", key="wiz_s1_site_name")
        site_type_opts = [{"id": t["id"], "label": t["name"]} for t in lookups["site_types"]]
        site_type_labels = [""] + [o["label"] for o in site_type_opts]
        st.selectbox(
            "Site type",
            options=site_type_labels,
            index=0,
            key="wiz_s1_site_type_label",
        )
        st.text_area("Description", key="wiz_s1_site_description")
        st.divider()
        st.write("**Location**")
        render_location_picker(key_prefix="wiz_site")

    def on_next() -> list[str]:
        m = st.session_state.get("wiz_s1_mode", "Use existing")
        if m == "Use existing":
            if not site_labels:
                return ["No sites available. Create a new site instead."]
            if not st.session_state.get("wiz_s1_site_label"):
                return ["Select a site."]
        else:
            if not (st.session_state.get("wiz_s1_site_name") or "").strip():
                return ["Site name is required."]
        return []

    _nav(1, on_next)


# ---------------------------------------------------------------------------
# Step 2: Sampling Locations
# ---------------------------------------------------------------------------


def _step_sampling_locations(lookups: dict) -> None:
    _restore_snapshot(2)
    site_mode = st.session_state.get("wiz_s1_mode", "Use existing")
    site_opts = [{"id": s["site_id"], "label": s["name"]} for s in lookups["sites"]]

    existing_site_sls: list[dict] = []
    if site_mode == "Use existing":
        site_label = st.session_state.get("wiz_s1_site_label")
        site_id = _resolve_id(site_label, site_opts) if site_label else None
        if site_id:
            try:
                existing_site_sls = list_site_sampling_locations(site_id)
            except APIError:
                existing_site_sls = []
        can_pick_existing = bool(existing_site_sls)
    else:
        can_pick_existing = False

    st.write(
        "Define the sampling locations where equipment will be deployed. "
        "You can skip this step if you assign sampling points later."
    )

    ids: list[int] = st.session_state.wiz_sl_ids
    for sl_id in ids:
        with st.container(border=True):
            col_title, col_remove = st.columns([6, 1])
            with col_title:
                st.markdown(f"**Sampling location {sl_id + 1}**")
            with col_remove:
                confirm_key = f"wiz_sl_{sl_id}_remove_confirm"
                if st.session_state.get(confirm_key):
                    if st.button(
                        "Confirm remove",
                        key=f"wiz_sl_{sl_id}_remove_yes",
                        type="primary",
                    ):
                        st.session_state.wiz_sl_ids = [i for i in ids if i != sl_id]
                        del st.session_state[confirm_key]
                        st.rerun()
                else:
                    if st.button("✖ Remove", key=f"wiz_sl_{sl_id}_remove"):
                        st.session_state[confirm_key] = True
                        st.rerun()

            if st.session_state.get(f"wiz_sl_{sl_id}_remove_confirm"):
                cur_mode = st.session_state.get(f"wiz_sl_{sl_id}_mode", "New")
                note = (
                    " Note: removing an existing entry here does NOT delete the"
                    " record from the database."
                    if cur_mode == "Existing"
                    else ""
                )
                st.warning(f"Remove this sampling location?{note}")

            if can_pick_existing:
                mode = st.radio(
                    "Add as",
                    ["New", "Existing"],
                    key=f"wiz_sl_{sl_id}_mode",
                    horizontal=True,
                )
            else:
                mode = "New"

            if mode == "Existing":
                sl_labels = [s["name"] for s in existing_site_sls]
                st.selectbox(
                    "Sampling location *",
                    sl_labels,
                    key=f"wiz_sl_{sl_id}_existing_label",
                )
            else:
                st.text_input("Name *", key=f"wiz_sl_{sl_id}_name")
                st.text_area("Description", key=f"wiz_sl_{sl_id}_description")

    if st.button("➕ Add sampling location", key="wiz_sl_add"):
        new_id: int = st.session_state.wiz_sl_next_id
        st.session_state.wiz_sl_ids = ids + [new_id]
        st.session_state.wiz_sl_next_id += 1
        st.rerun()

    def on_next() -> list[str]:
        errors: list[str] = []
        for sl_id in st.session_state.wiz_sl_ids:
            m = st.session_state.get(f"wiz_sl_{sl_id}_mode", "New")
            if m == "Existing":
                if not st.session_state.get(f"wiz_sl_{sl_id}_existing_label"):
                    errors.append(
                        f"Sampling location {sl_id + 1}: select an existing location."
                    )
            else:
                if not (st.session_state.get(f"wiz_sl_{sl_id}_name") or "").strip():
                    errors.append(f"Sampling location {sl_id + 1}: name is required.")
        return errors

    _nav(2, on_next)


# ---------------------------------------------------------------------------
# Step 3: Data Acquisition Systems
# ---------------------------------------------------------------------------


def _step_das(lookups: dict) -> None:
    _restore_snapshot(3)
    das_opts = [{"id": d["das_id"], "label": d["name"]} for d in lookups["das"]]
    das_labels = [o["label"] for o in das_opts]

    st.write(
        "Add the Data Acquisition Systems used in this campaign. "
        "Select existing ones or create new ones inline."
    )

    ids: list[int] = st.session_state.wiz_das_ids
    for das_id in ids:
        with st.container(border=True):
            col_title, col_remove = st.columns([6, 1])
            with col_title:
                st.markdown(f"**Data Acquisition System {das_id + 1}**")
            with col_remove:
                if st.button("✖ Remove", key=f"wiz_das_{das_id}_remove"):
                    st.session_state.wiz_das_ids = [i for i in ids if i != das_id]
                    # Cascade: remove equipment and tags belonging to this DAS
                    eq_to_remove = [
                        eid
                        for eid in st.session_state.wiz_eq_ids
                        if st.session_state.get(f"wiz_eq_{eid}_das_wiz_id") == das_id
                    ]
                    for eid in eq_to_remove:
                        st.session_state.wiz_eq_ids = [
                            i for i in st.session_state.wiz_eq_ids if i != eid
                        ]
                        st.session_state.wiz_tag_ids = [
                            tid
                            for tid in st.session_state.wiz_tag_ids
                            if st.session_state.get(f"wiz_tag_{tid}_eq_wiz_id") != eid
                        ]
                    st.rerun()

            mode = st.radio(
                "Mode",
                ["Existing", "New"],
                key=f"wiz_das_{das_id}_mode",
                horizontal=True,
            )

            if mode == "Existing":
                if das_labels:
                    st.selectbox(
                        "Select Data Acquisition System *",
                        das_labels,
                        key=f"wiz_das_{das_id}_das_label",
                    )
                else:
                    st.info(
                        "No existing Data Acquisition Systems found. Switch to **New**."
                    )
            else:
                st.text_input(
                    "Name *",
                    key=f"wiz_das_{das_id}_das_name",
                    help="Name for the new Data Acquisition System",
                )

    if st.button("➕ Add Data Acquisition System", key="wiz_das_add"):
        new_id: int = st.session_state.wiz_das_next_id
        st.session_state.wiz_das_ids = ids + [new_id]
        st.session_state.wiz_das_next_id += 1
        st.rerun()

    def on_next() -> list[str]:
        if not st.session_state.wiz_das_ids:
            return ["Add at least one Data Acquisition System."]
        errors: list[str] = []
        for das_id in st.session_state.wiz_das_ids:
            m = st.session_state.get(f"wiz_das_{das_id}_mode", "Existing")
            if m == "Existing":
                if not das_labels:
                    errors.append(
                        f"Data Acquisition System {das_id + 1}: no existing systems available."
                    )
                elif not st.session_state.get(f"wiz_das_{das_id}_das_label"):
                    errors.append(
                        f"Data Acquisition System {das_id + 1}: select an existing system."
                    )
            else:
                if not (
                    st.session_state.get(f"wiz_das_{das_id}_das_name") or ""
                ).strip():
                    errors.append(
                        f"Data Acquisition System {das_id + 1}: name is required."
                    )
        return errors

    _nav(3, on_next)


# ---------------------------------------------------------------------------
# Step 4: Equipment & Tags
# ---------------------------------------------------------------------------


def _step_equipment_and_tags(lookups: dict) -> None:
    _restore_snapshot(4)
    eq_opts = [
        {"id": e["equipment_id"], "label": e["identifier"]}
        for e in lookups["equipment"]
    ]
    model_opts = [
        {"id": m["model_id"], "label": _model_label(m)}
        for m in lookups["equipment_models"]
    ]
    eq_labels = [o["label"] for o in eq_opts]
    model_labels = [o["label"] for o in model_opts]

    sp_type_opts = [
        {"id": t["signal_port_type_id"], "label": t["name"]}
        for t in lookups["signal_port_types"]
    ]
    param_opts = [
        {"id": p["parameter_id"], "label": p["parameter_name"]}
        for p in lookups["parameters"]
    ]
    pd_opts = [
        {"id": p["processing_degree_id"], "label": p["name"]}
        for p in lookups["processing_degrees"]
    ]
    sp_type_labels = [o["label"] for o in sp_type_opts]
    param_labels = [o["label"] for o in param_opts]
    pd_labels = [o["label"] for o in pd_opts]
    vt_labels = [o["label"] for o in _VALUE_TYPES]
    existing_sp_opts: list[dict] = lookups.get("signal_ports_flat", [])
    existing_sp_labels = [o["label"] for o in existing_sp_opts]

    # Sampling location labels from step 2
    sl_wiz_ids: list[int] = st.session_state.wiz_sl_ids
    sl_named_ids = [
        sl_id
        for sl_id in sl_wiz_ids
        if (
            st.session_state.get(f"wiz_sl_{sl_id}_mode", "New") == "Existing"
            and st.session_state.get(f"wiz_sl_{sl_id}_existing_label")
        )
        or (
            st.session_state.get(f"wiz_sl_{sl_id}_mode", "New") == "New"
            and (st.session_state.get(f"wiz_sl_{sl_id}_name") or "").strip()
        )
    ]
    sl_labels = [_sl_display_label(sl_id) for sl_id in sl_named_ids]

    st.write("Add equipment and signal port tags for each Data Acquisition System.")

    for das_wiz_id in st.session_state.wiz_das_ids:
        das_label = _das_display_label(das_wiz_id)
        st.markdown(f"### {das_label}")

        das_eq_ids = [
            eid
            for eid in st.session_state.wiz_eq_ids
            if st.session_state.get(f"wiz_eq_{eid}_das_wiz_id") == das_wiz_id
        ]

        for item_id in das_eq_ids:
            with st.container(border=True):
                col_title, col_remove = st.columns([6, 1])
                with col_title:
                    st.markdown(f"**Equipment: {_eq_display_label(item_id)}**")
                with col_remove:
                    if st.button("✖ Remove", key=f"wiz_eq_{item_id}_remove"):
                        st.session_state.wiz_eq_ids = [
                            i for i in st.session_state.wiz_eq_ids if i != item_id
                        ]
                        st.session_state.wiz_tag_ids = [
                            tid
                            for tid in st.session_state.wiz_tag_ids
                            if st.session_state.get(f"wiz_tag_{tid}_eq_wiz_id") != item_id
                        ]
                        st.rerun()

                eq_mode = st.radio(
                    "Add as",
                    ["Existing", "New"],
                    key=f"wiz_eq_{item_id}_mode",
                    horizontal=True,
                )

                if eq_mode == "Existing":
                    if eq_labels:
                        st.selectbox(
                            "Select equipment *",
                            eq_labels,
                            key=f"wiz_eq_{item_id}_eq_label",
                        )
                    else:
                        st.info("No existing equipment found. Switch to **New**.")
                else:
                    model_mode = st.radio(
                        "Equipment model",
                        ["Select existing", "Create new"],
                        key=f"wiz_eq_{item_id}_model_mode",
                        horizontal=True,
                    )
                    if model_mode == "Select existing":
                        if model_labels:
                            st.selectbox(
                                "Equipment model *",
                                model_labels,
                                key=f"wiz_eq_{item_id}_model",
                            )
                        else:
                            st.warning(
                                "No equipment models found. Switch to **Create new**."
                            )
                    else:
                        st.text_input(
                            "Manufacturer", key=f"wiz_eq_{item_id}_model_manufacturer"
                        )
                        st.text_input(
                            "Model name *", key=f"wiz_eq_{item_id}_model_name_new"
                        )
                    st.text_input(
                        "Identifier / tag *", key=f"wiz_eq_{item_id}_identifier"
                    )
                    st.text_input("Serial number", key=f"wiz_eq_{item_id}_serial")

                if sl_labels:
                    st.selectbox(
                        "Sampling location *",
                        sl_labels,
                        key=f"wiz_eq_{item_id}_sp",
                    )
                else:
                    st.warning(
                        "No sampling locations defined — go back to step 2 and add"
                        " at least one."
                    )

                # Tags (signal ports) for this equipment
                st.markdown("**Signal port tags**")
                eq_tag_ids = [
                    tid
                    for tid in st.session_state.wiz_tag_ids
                    if st.session_state.get(f"wiz_tag_{tid}_eq_wiz_id") == item_id
                ]

                for tid in eq_tag_ids:
                    with st.container(border=True):
                        col_t, col_tr = st.columns([6, 1])
                        with col_t:
                            tag_val = (
                                st.session_state.get(f"wiz_tag_{tid}_tag")
                                or f"Tag {tid + 1}"
                            )
                            st.markdown(f"*{tag_val}*")
                        with col_tr:
                            if st.button("✖", key=f"wiz_tag_{tid}_remove"):
                                st.session_state.wiz_tag_ids = [
                                    i
                                    for i in st.session_state.wiz_tag_ids
                                    if i != tid
                                ]
                                st.rerun()

                        tag_mode = st.radio(
                            "Port",
                            ["New", "Existing"],
                            key=f"wiz_tag_{tid}_mode",
                            horizontal=True,
                        )

                        if tag_mode == "Existing":
                            if existing_sp_labels:
                                st.selectbox(
                                    "Signal port *",
                                    existing_sp_labels,
                                    key=f"wiz_tag_{tid}_existing_label",
                                )
                            else:
                                st.info(
                                    "No existing signal ports found. Switch to **New**."
                                )
                        else:
                            st.text_input(
                                "Tag *",
                                key=f"wiz_tag_{tid}_tag",
                                help="Unique identifier within the Data Acquisition"
                                " System (e.g. AI_01)",
                            )
                            if sp_type_labels:
                                st.selectbox(
                                    "Port type *",
                                    sp_type_labels,
                                    key=f"wiz_tag_{tid}_port_type",
                                )
                            else:
                                st.warning("No signal port types found in the database.")
                            if param_labels:
                                st.selectbox(
                                    "Parameter *",
                                    param_labels,
                                    key=f"wiz_tag_{tid}_parameter",
                                )
                            else:
                                st.warning("No parameters found in the database.")
                            st.selectbox(
                                "Value type *",
                                vt_labels,
                                key=f"wiz_tag_{tid}_value_type",
                            )
                            if pd_labels:
                                st.selectbox(
                                    "Processing degree",
                                    ["(none)"] + pd_labels,
                                    key=f"wiz_tag_{tid}_processing_degree",
                                )

                if st.button("➕ Add tag", key=f"wiz_tag_add_{item_id}"):
                    new_tid: int = st.session_state.wiz_tag_next_id
                    st.session_state.wiz_tag_ids = st.session_state.wiz_tag_ids + [
                        new_tid
                    ]
                    st.session_state.wiz_tag_next_id += 1
                    st.session_state[f"wiz_tag_{new_tid}_eq_wiz_id"] = item_id
                    st.rerun()

        if st.button(
            f"➕ Add equipment to {das_label}",
            key=f"wiz_eq_add_{das_wiz_id}",
        ):
            new_eid: int = st.session_state.wiz_eq_next_id
            st.session_state.wiz_eq_ids = st.session_state.wiz_eq_ids + [new_eid]
            st.session_state.wiz_eq_next_id += 1
            st.session_state[f"wiz_eq_{new_eid}_das_wiz_id"] = das_wiz_id
            st.rerun()

        st.divider()

    def on_next() -> list[str]:
        errors: list[str] = []
        cur_eq_ids: list[int] = st.session_state.wiz_eq_ids
        if not cur_eq_ids:
            errors.append("Add at least one piece of equipment.")
        for eid in cur_eq_ids:
            m = st.session_state.get(f"wiz_eq_{eid}_mode", "Existing")
            if m == "Existing":
                if not st.session_state.get(f"wiz_eq_{eid}_eq_label"):
                    errors.append(
                        f"Equipment {_eq_display_label(eid)}: select an existing"
                        " equipment."
                    )
            else:
                mm = st.session_state.get(f"wiz_eq_{eid}_model_mode", "Select existing")
                if mm == "Select existing":
                    if not st.session_state.get(f"wiz_eq_{eid}_model"):
                        errors.append(
                            f"Equipment {_eq_display_label(eid)}: model is required."
                        )
                else:
                    if not (
                        st.session_state.get(f"wiz_eq_{eid}_model_name_new") or ""
                    ).strip():
                        errors.append(
                            f"Equipment {_eq_display_label(eid)}: model name is"
                            " required."
                        )
                if not (
                    st.session_state.get(f"wiz_eq_{eid}_identifier") or ""
                ).strip():
                    errors.append(
                        f"Equipment {_eq_display_label(eid)}: identifier is required."
                    )
            if sl_labels and not st.session_state.get(f"wiz_eq_{eid}_sp"):
                errors.append(
                    f"Equipment {_eq_display_label(eid)}: sampling location is"
                    " required."
                )
        if not sl_labels and cur_eq_ids:
            errors.append(
                "Define at least one sampling location in step 2 before adding"
                " equipment."
            )

        for tid in st.session_state.wiz_tag_ids:
            tmode = st.session_state.get(f"wiz_tag_{tid}_mode", "New")
            if tmode == "Existing":
                if not st.session_state.get(f"wiz_tag_{tid}_existing_label"):
                    errors.append(f"Tag {tid + 1}: select an existing signal port.")
            else:
                if not (
                    st.session_state.get(f"wiz_tag_{tid}_tag") or ""
                ).strip():
                    errors.append(f"Tag {tid + 1}: tag string is required.")
                if not st.session_state.get(f"wiz_tag_{tid}_port_type"):
                    errors.append(f"Tag {tid + 1}: port type is required.")
                if not st.session_state.get(f"wiz_tag_{tid}_parameter"):
                    errors.append(f"Tag {tid + 1}: parameter is required.")
        return errors

    _nav(4, on_next)


# ---------------------------------------------------------------------------
# Step 5: Review & Create
# ---------------------------------------------------------------------------


def _step_review(lookups: dict) -> None:
    st.write(
        "Review the entities below. Click **Confirm & Create** to write everything "
        "to the database in one go."
    )

    # Campaign
    with st.expander("Campaign", expanded=True):
        name = st.session_state.get("wiz_s0_name", "—")
        type_label = st.session_state.get("wiz_s0_campaign_type", "—")
        start = st.session_state.get("wiz_s0_start_date") or "—"
        end = st.session_state.get("wiz_s0_end_date") or "—"
        desc = st.session_state.get("wiz_s0_description") or "—"
        resp = st.session_state.get("wiz_s0_responsible_person") or "—"
        st.markdown(
            f"**Name:** {name}  \n**Type:** {type_label}  \n"
            f"**Start:** {start}  \n**End:** {end}  \n**Description:** {desc}  \n"
            f"**Responsible person:** {resp}"
        )

    # Site
    with st.expander("Site", expanded=True):
        m = st.session_state.get("wiz_s1_mode", "Use existing")
        if m == "Use existing":
            st.markdown(
                f"**Using existing:** {st.session_state.get('wiz_s1_site_label', '—')}"
            )
        else:
            st.markdown(
                f"**Creating new:** {st.session_state.get('wiz_s1_site_name', '—')}"
            )

    # Sampling Locations
    sl_ids: list[int] = st.session_state.wiz_sl_ids
    with st.expander(f"Sampling Locations ({len(sl_ids)} items)", expanded=True):
        if sl_ids:
            new_sls = [
                sl_id
                for sl_id in sl_ids
                if st.session_state.get(f"wiz_sl_{sl_id}_mode", "New") == "New"
            ]
            exist_sls = [
                sl_id
                for sl_id in sl_ids
                if st.session_state.get(f"wiz_sl_{sl_id}_mode", "New") == "Existing"
            ]
            if new_sls:
                st.markdown("**Will be created:**")
                for sl_id in new_sls:
                    st.markdown(f"- {_sl_display_label(sl_id)}")
            if exist_sls:
                st.markdown("**Already exists / will be linked:**")
                for sl_id in exist_sls:
                    st.markdown(f"- {_sl_display_label(sl_id)}")
        else:
            st.caption("No sampling locations defined — you can add them later.")

    # Data Acquisition Systems
    das_ids: list[int] = st.session_state.wiz_das_ids
    with st.expander(
        f"Data Acquisition Systems ({len(das_ids)} items)", expanded=True
    ):
        new_das = [
            d
            for d in das_ids
            if st.session_state.get(f"wiz_das_{d}_mode", "Existing") == "New"
        ]
        exist_das = [
            d
            for d in das_ids
            if st.session_state.get(f"wiz_das_{d}_mode", "Existing") == "Existing"
        ]
        if new_das:
            st.markdown("**Will be created:**")
            for d in new_das:
                st.markdown(f"- {_das_display_label(d)}")
        if exist_das:
            st.markdown("**Already exists / will be linked:**")
            for d in exist_das:
                st.markdown(f"- {_das_display_label(d)}")

    # Equipment
    eq_ids: list[int] = st.session_state.wiz_eq_ids
    with st.expander(f"Equipment ({len(eq_ids)} items)", expanded=True):
        new_eq = [
            e
            for e in eq_ids
            if st.session_state.get(f"wiz_eq_{e}_mode", "Existing") == "New"
        ]
        exist_eq = [
            e
            for e in eq_ids
            if st.session_state.get(f"wiz_eq_{e}_mode", "Existing") == "Existing"
        ]
        if new_eq:
            st.markdown("**Will be created:**")
            for eid in new_eq:
                sp = st.session_state.get(f"wiz_eq_{eid}_sp") or "(none)"
                das_wid = st.session_state.get(f"wiz_eq_{eid}_das_wiz_id")
                das_lbl = (
                    _das_display_label(das_wid) if das_wid is not None else "?"
                )
                st.markdown(
                    f"- **{_eq_display_label(eid)}** (Data Acquisition System:"
                    f" {das_lbl}, sampling point: {sp})"
                )
        if exist_eq:
            st.markdown("**Already exists / will be linked:**")
            for eid in exist_eq:
                sp = st.session_state.get(f"wiz_eq_{eid}_sp") or "(none)"
                st.markdown(
                    f"- **{_eq_display_label(eid)}** (sampling point: {sp})"
                )

    # Tags
    tag_ids: list[int] = st.session_state.wiz_tag_ids
    with st.expander(f"Signal Port Tags ({len(tag_ids)} items)", expanded=True):
        new_tags = [
            tid
            for tid in tag_ids
            if st.session_state.get(f"wiz_tag_{tid}_mode", "New") == "New"
        ]
        exist_tags = [
            tid
            for tid in tag_ids
            if st.session_state.get(f"wiz_tag_{tid}_mode", "New") == "Existing"
        ]
        if new_tags:
            st.markdown("**Will be created:**")
            for tid in new_tags:
                tag_str = st.session_state.get(f"wiz_tag_{tid}_tag", "—")
                ptype = st.session_state.get(f"wiz_tag_{tid}_port_type", "—")
                param = st.session_state.get(f"wiz_tag_{tid}_parameter", "—")
                vt = st.session_state.get(f"wiz_tag_{tid}_value_type", "—")
                eq_wid = st.session_state.get(f"wiz_tag_{tid}_eq_wiz_id")
                eq_lbl = _eq_display_label(eq_wid) if eq_wid is not None else "?"
                st.markdown(
                    f"- `{tag_str}` ({ptype}, {param}, {vt}) on *{eq_lbl}*"
                )
        if exist_tags:
            st.markdown("**Already exists / will be linked:**")
            for tid in exist_tags:
                sp_lbl = st.session_state.get(
                    f"wiz_tag_{tid}_existing_label", "—"
                )
                st.markdown(f"- {sp_lbl}")
        if not tag_ids:
            st.caption("No signal port tags defined.")

    def on_next() -> list[str]:
        errors = _execute_creates(lookups)
        if not errors:
            st.toast("Campaign and all entities created successfully!", icon="✅")
            clear_wizard()
            st.rerun()
        return errors

    _nav(5, on_next)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _execute_creates(lookups: dict) -> list[str]:
    """Create all entities in dependency order. Returns list of error strings."""
    errors: list[str] = []
    eq_id_map: dict[int, int] = {}   # wiz_eq_id  → DB equipment_id
    sl_id_map: dict[int, int] = {}   # wiz_sl_id  → DB SamplingPoint_ID
    das_id_map: dict[int, int] = {}  # wiz_das_id → DB DAS_ID

    type_opts = [
        {"id": t["campaign_type_id"], "label": t["name"]}
        for t in lookups["campaign_types"]
    ]
    site_opts = [{"id": s["site_id"], "label": s["name"]} for s in lookups["sites"]]
    eq_opts = [
        {"id": e["equipment_id"], "label": e["identifier"]}
        for e in lookups["equipment"]
    ]
    model_opts = [
        {"id": m["model_id"], "label": _model_label(m)}
        for m in lookups["equipment_models"]
    ]
    param_opts = [
        {"id": p["parameter_id"], "label": p["parameter_name"]}
        for p in lookups["parameters"]
    ]
    pd_opts = [
        {"id": p["processing_degree_id"], "label": p["name"]}
        for p in lookups["processing_degrees"]
    ]
    das_opts = [{"id": d["das_id"], "label": d["name"]} for d in lookups["das"]]
    sp_type_opts = [
        {"id": t["signal_port_type_id"], "label": t["name"]}
        for t in lookups["signal_port_types"]
    ]
    existing_sp_opts: list[dict] = lookups.get("signal_ports_flat", [])
    person_opts: list[dict] = lookups.get("persons", [])

    # 1. Create site if new
    site_mode = st.session_state.get("wiz_s1_mode", "Use existing")
    if site_mode == "Create new":
        site_type_opts = [
            {"id": t["id"], "label": t["name"]} for t in lookups["site_types"]
        ]
        selected_type_label = st.session_state.get("wiz_s1_site_type_label") or None
        site_type_id = (
            _resolve_id(selected_type_label, site_type_opts)
            if selected_type_label
            else None
        )
        try:
            site = create_site(
                {
                    "name": st.session_state.get("wiz_s1_site_name", ""),
                    "site_type_id": site_type_id,
                    "description": st.session_state.get("wiz_s1_site_description")
                    or None,
                    "lat_wgs84": st.session_state.get("wiz_site_lat_input"),
                    "long_wgs84": st.session_state.get("wiz_site_lng_input"),
                    "city": st.session_state.get("wiz_site_city_input") or None,
                    "province": st.session_state.get("wiz_site_province_input") or None,
                    "country": st.session_state.get("wiz_site_country_input") or None,
                }
            )
            campaign_site_id: int | None = site["site_id"]
        except APIError as e:
            errors.append(f"Site creation failed: {e.message}")
            return errors
    else:
        campaign_site_id = _resolve_id(
            st.session_state.get("wiz_s1_site_label"), site_opts
        )

    # 2. Resolve / create sampling locations
    if site_mode == "Use existing" and campaign_site_id:
        try:
            existing_site_sls = list_site_sampling_locations(campaign_site_id)
        except APIError:
            existing_site_sls = []
    else:
        existing_site_sls = []

    for sl_wiz_id in st.session_state.get("wiz_sl_ids", []):
        sl_mode = st.session_state.get(f"wiz_sl_{sl_wiz_id}_mode", "New")
        if sl_mode == "Existing":
            label = st.session_state.get(f"wiz_sl_{sl_wiz_id}_existing_label")
            match = next(
                (s for s in existing_site_sls if s["name"] == label), None
            )
            if match:
                sl_id_map[sl_wiz_id] = match["id"]
            else:
                errors.append(
                    f"Sampling location '{label}': could not resolve ID."
                )
        else:
            name = (
                st.session_state.get(f"wiz_sl_{sl_wiz_id}_name") or ""
            ).strip()
            if name and campaign_site_id is not None:
                try:
                    sl = create_sampling_location(
                        campaign_site_id,
                        {
                            "name": name,
                            "description": st.session_state.get(
                                f"wiz_sl_{sl_wiz_id}_description"
                            )
                            or None,
                            "latitude": None,
                            "longitude": None,
                        },
                    )
                    sl_id_map[sl_wiz_id] = sl["id"]
                except APIError as e:
                    errors.append(f"Sampling location '{name}': {e.message}")

    if errors:
        return errors

    # 3. Create campaign (with responsible_person_id)
    start_date = st.session_state.get("wiz_s0_start_date")
    end_date = st.session_state.get("wiz_s0_end_date")
    resp_label = st.session_state.get("wiz_s0_responsible_person")
    responsible_person_id: int | None = None
    if resp_label and resp_label != "(none)":
        matched_person = next(
            (p for p in person_opts if p["label"] == resp_label), None
        )
        if matched_person:
            responsible_person_id = matched_person["person_id"]
    try:
        campaign = create_campaign(
            {
                "name": st.session_state.get("wiz_s0_name"),
                "campaign_type_id": _resolve_id(
                    st.session_state.get("wiz_s0_campaign_type"), type_opts
                ),
                "site_id": campaign_site_id,
                "description": st.session_state.get("wiz_s0_description") or None,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "responsible_person_id": responsible_person_id,
            }
        )
        campaign_id: int = campaign["campaign_id"]
    except APIError as e:
        errors.append(f"Campaign creation failed: {e.message}")
        return errors

    # 4. Create DASes
    for das_wiz_id in st.session_state.get("wiz_das_ids", []):
        das_mode = st.session_state.get(f"wiz_das_{das_wiz_id}_mode", "Existing")
        if das_mode == "Existing":
            actual_das_id = _resolve_id(
                st.session_state.get(f"wiz_das_{das_wiz_id}_das_label"), das_opts
            )
            if actual_das_id is None:
                errors.append(
                    f"Data Acquisition System {das_wiz_id + 1}: could not resolve ID."
                )
                continue
        else:
            das_name = (
                st.session_state.get(f"wiz_das_{das_wiz_id}_das_name") or ""
            ).strip()
            try:
                new_das_obj = create_das({"name": das_name})
                actual_das_id = new_das_obj["das_id"]
            except APIError as e:
                errors.append(
                    f"Data Acquisition System '{das_name}': {e.message}"
                )
                continue
        das_id_map[das_wiz_id] = actual_das_id

    if errors:
        return errors

    # 5. Create equipment models (if needed), equipment, and deployments
    for eid in st.session_state.get("wiz_eq_ids", []):
        eq_mode = st.session_state.get(f"wiz_eq_{eid}_mode", "Existing")

        if eq_mode == "Existing":
            actual_eq_id = _resolve_id(
                st.session_state.get(f"wiz_eq_{eid}_eq_label"), eq_opts
            )
        else:
            model_mode = st.session_state.get(
                f"wiz_eq_{eid}_model_mode", "Select existing"
            )
            if model_mode == "Create new":
                try:
                    new_model = create_equipment_model(
                        {
                            "equipment_model": st.session_state.get(
                                f"wiz_eq_{eid}_model_name_new"
                            )
                            or None,
                            "manufacturer": st.session_state.get(
                                f"wiz_eq_{eid}_model_manufacturer"
                            )
                            or None,
                        }
                    )
                    resolved_model_id = new_model["model_id"]
                except APIError as e:
                    errors.append(
                        f"Equipment {_eq_display_label(eid)} model: {e.message}"
                    )
                    continue
            else:
                resolved_model_id = _resolve_id(
                    st.session_state.get(f"wiz_eq_{eid}_model"), model_opts
                )

            try:
                eq = create_equipment(
                    {
                        "model_id": resolved_model_id,
                        "identifier": st.session_state.get(
                            f"wiz_eq_{eid}_identifier"
                        )
                        or None,
                        "serial_number": st.session_state.get(
                            f"wiz_eq_{eid}_serial"
                        )
                        or None,
                    }
                )
                actual_eq_id = eq["equipment_id"]
            except APIError as e:
                errors.append(f"Equipment {_eq_display_label(eid)}: {e.message}")
                continue

        if actual_eq_id is None:
            errors.append(
                f"Equipment {_eq_display_label(eid)}: could not resolve ID."
            )
            continue

        eq_id_map[eid] = actual_eq_id

        # Resolve sampling point
        sp_label = st.session_state.get(f"wiz_eq_{eid}_sp")
        sampling_point_id: int | None = None
        if sp_label and sp_label != "(none)":
            matched_wiz_sl_id = next(
                (
                    sl_id
                    for sl_id in st.session_state.wiz_sl_ids
                    if _sl_display_label(sl_id) == sp_label
                ),
                None,
            )
            sampling_point_id = (
                sl_id_map.get(matched_wiz_sl_id)
                if matched_wiz_sl_id is not None
                else None
            )

        if sampling_point_id is None:
            errors.append(
                f"Equipment {_eq_display_label(eid)}: sampling location could"
                " not be resolved."
            )
            continue
        try:
            create_campaign_deployment(
                campaign_id,
                {
                    "equipment_id": actual_eq_id,
                    "sampling_point_id": sampling_point_id,
                },
            )
        except APIError as e:
            errors.append(
                f"Deployment for {_eq_display_label(eid)}: {e.message}"
            )

    if errors:
        return errors

    # 6. Create signal ports (tags), register equipment at port, create channels
    for tid in st.session_state.get("wiz_tag_ids", []):
        eq_wiz_id = st.session_state.get(f"wiz_tag_{tid}_eq_wiz_id")
        actual_eq_id = eq_id_map.get(eq_wiz_id) if eq_wiz_id is not None else None

        das_wiz_id = (
            st.session_state.get(f"wiz_eq_{eq_wiz_id}_das_wiz_id")
            if eq_wiz_id is not None
            else None
        )
        actual_das_id = (
            das_id_map.get(das_wiz_id) if das_wiz_id is not None else None
        )

        tag_mode = st.session_state.get(f"wiz_tag_{tid}_mode", "New")
        signal_port_id: int | None = None

        if tag_mode == "Existing":
            signal_port_id = _resolve_id(
                st.session_state.get(f"wiz_tag_{tid}_existing_label"),
                existing_sp_opts,
            )
        else:
            sp_type_id = _resolve_id(
                st.session_state.get(f"wiz_tag_{tid}_port_type"), sp_type_opts
            )
            try:
                sp = create_signal_port(
                    {
                        "das_id": actual_das_id,
                        "signal_port_type_id": sp_type_id,
                        "tag": st.session_state.get(f"wiz_tag_{tid}_tag") or "",
                    }
                )
                signal_port_id = sp["signal_port_id"]
            except APIError as e:
                tag_str = st.session_state.get(f"wiz_tag_{tid}_tag", f"tag {tid + 1}")
                errors.append(f"Signal port '{tag_str}': {e.message}")
                continue

        if signal_port_id is None:
            errors.append(f"Tag {tid + 1}: could not resolve signal port.")
            continue

        # Register equipment at port
        if actual_eq_id is not None:
            try:
                register_equipment_at_port(
                    signal_port_id, {"equipment_id": actual_eq_id}
                )
            except APIError as e:
                tag_str = st.session_state.get(f"wiz_tag_{tid}_tag", f"tag {tid + 1}")
                errors.append(
                    f"Equipment registration at port '{tag_str}': {e.message}"
                )

        # Create channel
        param_label = st.session_state.get(f"wiz_tag_{tid}_parameter")
        vt_label = st.session_state.get(f"wiz_tag_{tid}_value_type")
        pd_label = st.session_state.get(f"wiz_tag_{tid}_processing_degree")
        pd_id = (
            _resolve_id(pd_label, pd_opts)
            if pd_label and pd_label != "(none)"
            else None
        )
        try:
            create_channel(
                {
                    "signal_port_id": signal_port_id,
                    "parameter_id": _resolve_id(param_label, param_opts),
                    "value_type_id": _resolve_id(vt_label, _VALUE_TYPES),
                    "processing_degree_id": pd_id,
                }
            )
        except APIError as e:
            tag_str = st.session_state.get(f"wiz_tag_{tid}_tag", f"tag {tid + 1}")
            errors.append(f"Channel for '{tag_str}': {e.message}")

    return errors
