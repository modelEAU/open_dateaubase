"""Multi-step campaign creation wizard for open_datEAUbase."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from app.api_client import (
    APIError,
    create_campaign,
    create_campaign_deployment,
    create_channel,
    create_das,
    create_equipment,
    create_equipment_model,
    create_person,
    create_process_unit,
    create_sampling_location,
    create_signal_interface,
    create_site,
    deploy_das,
    get_das_conflict,
    list_campaign_kinds,
    list_das_lookup,
    list_equipment_lookup,
    list_equipment_models_lookup,
    list_parameters_lookup,
    list_operation_kinds_lookup,
    list_persons_lookup,
    list_signal_interfaces_lookup,
    list_site_sampling_locations,
    list_site_kinds,
    list_sites_lookup,
    list_process_units_lookup,
    register_equipment_at_interface,
)
from app.components.location_picker import render_location_picker

STEPS = [
    "Campaign basics",
    "Site",
    "Sampling Locations",
    "Data Acquisition Systems",
    "Equipment & Tags",
    "Review & Create",
    "Summary",
]

_VALUE_TYPES = [
    {"id": 1, "label": "Scalar"},
    {"id": 2, "label": "Vector"},
    {"id": 3, "label": "Matrix"},
    {"id": 4, "label": "Image"},
]

# Session-state key prefixes that belong to each step (for snapshot/restore)
_STEP_PREFIXES: dict[int, list[str]] = {
    0: ["wiz_s0_", "wiz_s0_person_"],  # Campaign basics + person creation fields
    1: ["wiz_s1_", "wiz_site_"],
    2: ["wiz_sl_"],  # Snapshot captures all SL keys including _store
    3: ["wiz_das_"],
    4: ["wiz_eq_", "wiz_tag_", "wiz_eq__model_params"],  # Equipment, tags, model params
    5: [],
    6: [],
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
        6: _step_summary,
    }[step](lookups)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def _load_lookups() -> dict | None:
    try:
        si_data = list_signal_interfaces_lookup()
        signal_interfaces_flat = [
            {
                "id": si["signal_interface_id"],
                "label": f"{si.get('das_name', '?')} › {si.get('name', '')}",
            }
            for si in si_data
        ]
        return {
            "campaign_kinds": list_campaign_kinds(),
            "sites": list_sites_lookup(),
            "site_kinds": list_site_kinds(),
            "equipment": list_equipment_lookup(),
            "equipment_models": list_equipment_models_lookup(),
            "parameters": list_parameters_lookup(),
            "operation_kinds": list_operation_kinds_lookup(),
            "das": list_das_lookup(),
            "signal_interfaces_flat": signal_interfaces_flat,
            "persons": list_persons_lookup(),
            "process_units": list_process_units_lookup(),
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
        if isinstance(key, str) and any(key.startswith(p) for p in prefixes):
            # Skip button keys - they can't be restored and cause errors
            if (
                key.endswith("_remove")
                or key.endswith("_remove_confirm")
                or key.endswith("_remove_yes")
                or key.endswith("_add")
                or "_add_" in key
            ):
                continue
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


def _nav(step: int, on_next, *, next_label: str | None = None) -> None:
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
        label = next_label or ("Confirm & Create" if is_last else "Next ▶")
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


def _sl_mode(sl_wiz_id: int) -> str:
    """Read SL mode preferring the snapshot-stable _store key (BUG-4).

    Streamlit drops the radio widget key once the user leaves step 2, so reads
    in later steps must use the store key (set in step-2 on_next).
    """
    return (
        st.session_state.get(f"wiz_sl_{sl_wiz_id}_mode_store")
        or st.session_state.get(f"wiz_sl_{sl_wiz_id}_mode", "New")
    )


def _model_label(m: dict) -> str:
    parts = [p for p in [m.get("manufacturer"), m.get("model_name")] if p]
    return " – ".join(parts) if parts else f"Model {m.get('model_id', '?')}"


def _sl_display_label(sl_wiz_id: int) -> str:
    mode = _sl_mode(sl_wiz_id)
    if mode == "Existing":
        # Read from _store key which persists across steps
        return (
            st.session_state.get(f"wiz_sl_{sl_wiz_id}_existing_label_store")
            or st.session_state.get(f"wiz_sl_{sl_wiz_id}_existing_label")
            or f"Sampling point {sl_wiz_id}"
        )
    # Read from _store key which persists across steps
    return (
        st.session_state.get(f"wiz_sl_{sl_wiz_id}_name_store")
        or st.session_state.get(f"wiz_sl_{sl_wiz_id}_name")
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
        {"id": t["campaign_kind_id"], "label": t["name"]}
        for t in lookups["campaign_kinds"]
    ]
    type_labels = [o["label"] for o in type_opts]
    person_opts: list[dict] = lookups.get("persons", [])
    person_labels = [p["label"] for p in person_opts]

    st.text_input("Campaign name *", key="wiz_s0_name")
    if type_labels:
        st.selectbox("Campaign type *", type_labels, key="wiz_s0_campaign_type")
    else:
        st.warning("No campaign types found in the database.")
    st.date_input("Start date", key="wiz_s0_start_date", value=None)
    st.date_input("End date", key="wiz_s0_end_date", value=None)
    st.text_area("Description", key="wiz_s0_description")

    # Responsible person — required
    person_mode = st.radio(
        "Responsible person *",
        ["Select existing", "Create new"],
        key="wiz_s0_person_mode",
        horizontal=True,
    )
    if person_mode == "Select existing":
        if person_labels:
            st.selectbox(
                "Select person *",
                person_labels,
                key="wiz_s0_responsible_person",
            )
        else:
            st.info("No persons found. Switch to **Create new** to add one.")
    else:
        col_fn, col_ln = st.columns(2)
        with col_fn:
            st.text_input("First name", key="wiz_s0_person_first_name")
        with col_ln:
            st.text_input("Last name", key="wiz_s0_person_last_name")
        st.text_input("Email", key="wiz_s0_person_email")
        st.text_input("Role / function", key="wiz_s0_person_role")
        col_org, col_ph = st.columns(2)
        with col_org:
            st.text_input("Organization", key="wiz_s0_person_organization")
        with col_ph:
            st.text_input("Phone", key="wiz_s0_person_phone")

    def on_next() -> list[str]:
        errors: list[str] = []
        if not (st.session_state.get("wiz_s0_name") or "").strip():
            errors.append("Campaign name is required.")
        if not type_labels:
            errors.append("No campaign types available — cannot proceed.")
        elif not st.session_state.get("wiz_s0_campaign_type"):
            errors.append("Campaign type is required.")
        # Responsible person is mandatory
        mode = st.session_state.get("wiz_s0_person_mode", "Select existing")
        if mode == "Select existing":
            if not person_labels:
                errors.append("No persons available — switch to Create new.")
            elif not st.session_state.get("wiz_s0_responsible_person"):
                errors.append("Responsible person is required.")
        else:
            fn = (st.session_state.get("wiz_s0_person_first_name") or "").strip()
            ln = (st.session_state.get("wiz_s0_person_last_name") or "").strip()
            if not fn and not ln:
                errors.append("Person: at least first name or last name is required.")
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

    def _sync_site_label() -> None:
        st.session_state["wiz_s1_site_label_store"] = st.session_state.get(
            "wiz_s1_site_label"
        )

    def _sync_site_name() -> None:
        st.session_state["wiz_s1_site_name_store"] = st.session_state.get(
            "wiz_s1_site_name"
        )

    if mode == "Use existing":
        if site_labels:
            st.selectbox(
                "Select site *",
                site_labels,
                key="wiz_s1_site_label",
                on_change=_sync_site_label,
            )
            # Initialize store if absent (covers first render before on_change).
            if "wiz_s1_site_label_store" not in st.session_state:
                st.session_state["wiz_s1_site_label_store"] = st.session_state.get(
                    "wiz_s1_site_label"
                )
        else:
            st.info("No sites found. Switch to **Create new** to add one.")
    else:
        st.text_input(
            "Site name *", key="wiz_s1_site_name", on_change=_sync_site_name
        )
        if "wiz_s1_site_name_store" not in st.session_state:
            st.session_state["wiz_s1_site_name_store"] = st.session_state.get(
                "wiz_s1_site_name"
            )
        site_type_opts = [
            {"id": t["id"], "label": t["name"]} for t in lookups["site_kinds"]
        ]
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

                def _sync_existing(sl_id=sl_id):
                    st.session_state[f"wiz_sl_{sl_id}_existing_label_store"] = (
                        st.session_state[f"wiz_sl_{sl_id}_existing_label"]
                    )

                st.selectbox(
                    "Sampling location *",
                    sl_labels,
                    key=f"wiz_sl_{sl_id}_existing_label",
                    on_change=_sync_existing,
                )
                # Initialize store if needed
                if f"wiz_sl_{sl_id}_existing_label_store" not in st.session_state:
                    st.session_state[f"wiz_sl_{sl_id}_existing_label_store"] = (
                        st.session_state.get(f"wiz_sl_{sl_id}_existing_label")
                    )
            else:

                def _sync_name(sl_id=sl_id):
                    st.session_state[f"wiz_sl_{sl_id}_name_store"] = st.session_state[
                        f"wiz_sl_{sl_id}_name"
                    ]

                def _sync_desc(sl_id=sl_id):
                    st.session_state[f"wiz_sl_{sl_id}_description_store"] = (
                        st.session_state[f"wiz_sl_{sl_id}_description"]
                    )

                st.text_input(
                    "Name *", key=f"wiz_sl_{sl_id}_name", on_change=_sync_name
                )
                st.text_area(
                    "Description",
                    key=f"wiz_sl_{sl_id}_description",
                    on_change=_sync_desc,
                )

                # Process unit — Existing or New
                pu_mode = st.radio(
                    "Process unit",
                    ["None", "Existing", "New"],
                    key=f"wiz_sl_{sl_id}_pu_mode",
                    horizontal=True,
                )
                if pu_mode == "Existing":
                    pu_opts = lookups.get("process_units", [])
                    if pu_opts:
                        st.selectbox(
                            "Select process unit *",
                            [p["name"] for p in pu_opts],
                            key=f"wiz_sl_{sl_id}_pu_existing",
                        )
                    else:
                        st.info("No process units found. Switch to **New**.")
                elif pu_mode == "New":
                    st.text_input("Process unit name *", key=f"wiz_sl_{sl_id}_pu_name")
                    st.text_input(
                        "P&ID Tag *",
                        key=f"wiz_sl_{sl_id}_pu_tag",
                        help="Short identifier, e.g. PU-001",
                    )

                st.file_uploader(
                    "Photo (optional)",
                    type=["jpg", "jpeg", "png"],
                    key=f"wiz_sl_{sl_id}_photo",
                    help="Reference photo of the sampling location",
                )

                # Initialize stores if needed
                if f"wiz_sl_{sl_id}_name_store" not in st.session_state:
                    st.session_state[f"wiz_sl_{sl_id}_name_store"] = (
                        st.session_state.get(f"wiz_sl_{sl_id}_name", "")
                    )
                if f"wiz_sl_{sl_id}_description_store" not in st.session_state:
                    st.session_state[f"wiz_sl_{sl_id}_description_store"] = (
                        st.session_state.get(f"wiz_sl_{sl_id}_description", "")
                    )

    if st.button("➕ Add sampling location", key="wiz_sl_add"):
        new_id: int = st.session_state.wiz_sl_next_id
        st.session_state.wiz_sl_ids = ids + [new_id]
        st.session_state.wiz_sl_next_id += 1
        st.rerun()

    def on_next() -> list[str]:
        # Sync widget values to store keys before validation. The mode store
        # is critical: Streamlit drops the radio widget key when step 2 is
        # left, so without _mode_store the SL filter in step 4 reads "New"
        # by default and SLs created as "Existing" silently disappear.
        for sl_id in st.session_state.wiz_sl_ids:
            m = st.session_state.get(f"wiz_sl_{sl_id}_mode", "New")
            st.session_state[f"wiz_sl_{sl_id}_mode_store"] = m
            if m == "Existing":
                st.session_state[f"wiz_sl_{sl_id}_existing_label_store"] = (
                    st.session_state.get(f"wiz_sl_{sl_id}_existing_label", "")
                )
            else:
                st.session_state[f"wiz_sl_{sl_id}_name_store"] = st.session_state.get(
                    f"wiz_sl_{sl_id}_name", ""
                )
                st.session_state[f"wiz_sl_{sl_id}_description_store"] = (
                    st.session_state.get(f"wiz_sl_{sl_id}_description", "")
                )

        errors: list[str] = []
        for sl_id in st.session_state.wiz_sl_ids:
            m = st.session_state.get(f"wiz_sl_{sl_id}_mode", "New")
            if m == "Existing":
                if not st.session_state.get(f"wiz_sl_{sl_id}_existing_label_store"):
                    errors.append(
                        f"Sampling location {sl_id + 1}: select an existing location."
                    )
            else:
                pu_mode = st.session_state.get(f"wiz_sl_{sl_id}_pu_mode", "None")
                if pu_mode == "New":
                    if not (
                        st.session_state.get(f"wiz_sl_{sl_id}_pu_name") or ""
                    ).strip():
                        errors.append(
                            f"Sampling location {sl_id + 1}: process unit name is required."
                        )
                    if not (
                        st.session_state.get(f"wiz_sl_{sl_id}_pu_tag") or ""
                    ).strip():
                        errors.append(
                            f"Sampling location {sl_id + 1}: process unit tag is required."
                        )
                if not (
                    st.session_state.get(f"wiz_sl_{sl_id}_name_store") or ""
                ).strip():
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

    # Resolve the site chosen in step 1 so we can run conflict checks.
    site_opts = [{"id": s["site_id"], "label": s["name"]} for s in lookups["sites"]]
    site_mode = st.session_state.get("wiz_s1_mode", "Use existing")
    current_site_id: int | None = None
    if site_mode == "Use existing":
        site_label = st.session_state.get("wiz_s1_site_label")
        if site_label:
            current_site_id = _resolve_id(site_label, site_opts)

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
                    # Conflict check: warn if this DAS is currently active at a different site.
                    selected_label = st.session_state.get(f"wiz_das_{das_id}_das_label")
                    resolved_das_id = _resolve_id(selected_label, das_opts) if selected_label else None
                    if resolved_das_id is not None and current_site_id is not None:
                        try:
                            conflict = get_das_conflict(resolved_das_id, current_site_id)
                        except APIError:
                            conflict = None
                        if conflict:
                            other_site = conflict.get("conflicting_site_name") or f"site ID {conflict.get('conflicting_site_id')}"
                            other_campaign = conflict.get("conflicting_campaign_name")
                            msg = (
                                f"This DAS is currently active at **{other_site}**"
                                + (f" (campaign: {other_campaign})" if other_campaign else "")
                                + ". You can still proceed if it will be physically moved here, "
                                "but make sure the other campaign is aware."
                            )
                            st.warning(msg)
                        st.session_state[f"wiz_das_{das_id}_conflict"] = conflict
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
    _restore_snapshot(
        3
    )  # DAS labels/names cleaned up by Streamlit after leaving step 3
    _restore_snapshot(2)  # SL modes cleaned up after leaving step 2
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

    param_opts = [
        {"id": p["parameter_id"], "label": p["parameter_name"]}
        for p in lookups["parameters"]
    ]
    pd_opts = [
        {"id": p["operation_kind_id"], "label": p["name"]}
        for p in lookups["operation_kinds"]
    ]
    param_labels = [o["label"] for o in param_opts]
    pd_labels = [o["label"] for o in pd_opts]
    vt_labels = [o["label"] for o in _VALUE_TYPES]
    existing_si_opts: list[dict] = lookups.get("signal_interfaces_flat", [])
    existing_si_labels = [o["label"] for o in existing_si_opts]

    # Sampling location labels from step 2
    sl_wiz_ids: list[int] = st.session_state.wiz_sl_ids

    # Read from _store keys which persist across steps
    sl_named_ids = [
        sl_id
        for sl_id in sl_wiz_ids
        if (
            _sl_mode(sl_id) == "Existing"
            and st.session_state.get(f"wiz_sl_{sl_id}_existing_label_store")
        )
        or (
            _sl_mode(sl_id) == "New"
            and (st.session_state.get(f"wiz_sl_{sl_id}_name_store") or "").strip()
        )
    ]
    sl_labels = [_sl_display_label(sl_id) for sl_id in sl_named_ids]

    st.write(
        "Add equipment and/or channels for each Data Acquisition System. "
        "You can add equipment with a sampling location, or standalone channels."
    )

    for das_wiz_id in st.session_state.wiz_das_ids:
        das_label = _das_display_label(das_wiz_id)
        st.markdown(f"### {das_label}")

        # Get equipment for this DAS
        das_eq_ids = [
            eid
            for eid in st.session_state.wiz_eq_ids
            if st.session_state.get(f"wiz_eq_{eid}_das_wiz_id") == das_wiz_id
        ]

        # Get standalone tags for this DAS (not associated with equipment)
        das_tag_ids = [
            tid
            for tid in st.session_state.wiz_tag_ids
            if st.session_state.get(f"wiz_tag_{tid}_das_wiz_id") == das_wiz_id
            and st.session_state.get(f"wiz_tag_{tid}_eq_wiz_id") is None
        ]

        # Render equipment items
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
                        # Measurable parameters for new equipment model
                        if param_labels:
                            st.multiselect(
                                "Measurable parameters",
                                param_labels,
                                key=f"wiz_eq_{item_id}_model_params",
                                help="Select the parameters this equipment model can measure",
                            )
                    st.text_input(
                        "Identifier / tag *", key=f"wiz_eq_{item_id}_identifier"
                    )
                    st.text_input("Serial number", key=f"wiz_eq_{item_id}_serial")

                if sl_named_ids:
                    # Build label->ID mapping for reliable selection
                    sl_options = {
                        sl_id: _sl_display_label(sl_id) for sl_id in sl_named_ids
                    }
                    sl_index_map = list(sl_options.keys())
                    sl_label_list = list(sl_options.values())

                    # Ensure ID is always set before rendering selectbox
                    id_key = f"wiz_eq_{item_id}_sp_id"
                    current_sl_id = st.session_state.get(id_key)
                    default_index = 0
                    if current_sl_id in sl_index_map:
                        default_index = sl_index_map.index(current_sl_id)
                    else:
                        # Initialize with first option and sync immediately
                        default_index = 0
                        st.session_state[id_key] = sl_index_map[0]

                    selected_label = st.selectbox(
                        "Sampling location *",
                        sl_label_list,
                        index=default_index,
                        key=f"wiz_eq_{item_id}_sp_label",
                    )
                    # Always sync the ID from the selected label
                    selected_idx = sl_label_list.index(selected_label)
                    st.session_state[id_key] = sl_index_map[selected_idx]
                else:
                    st.warning(
                        "No sampling locations defined — go back to step 2 and add"
                        " at least one."
                    )

        # Render standalone channels for this DAS
        for tid in das_tag_ids:
            with st.container(border=True):
                col_t, col_tr = st.columns([6, 1])
                with col_t:
                    tag_val = (
                        st.session_state.get(f"wiz_tag_{tid}_tag")
                        or f"Channel {tid + 1}"
                    )
                    st.markdown(f"**Standalone Channel: {tag_val}**")
                with col_tr:
                    if st.button("✖", key=f"wiz_tag_{tid}_remove"):
                        st.session_state.wiz_tag_ids = [
                            i for i in st.session_state.wiz_tag_ids if i != tid
                        ]
                        st.rerun()

                tag_mode = st.radio(
                    "Signal Interface",
                    ["Existing", "New"],
                    key=f"wiz_tag_{tid}_mode",
                    horizontal=True,
                )

                if tag_mode == "Existing":
                    if existing_si_labels:
                        st.selectbox(
                            "Signal Interface *",
                            existing_si_labels,
                            key=f"wiz_tag_{tid}_existing_label",
                        )
                    else:
                        st.info(
                            "No existing signal interfaces found. Switch to **New**."
                        )
                else:
                    st.text_input(
                        "Tag / Interface Name *",
                        key=f"wiz_tag_{tid}_tag",
                        help="Name for the new Signal Interface and Channel"
                        " (e.g. AI_01)",
                    )
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
                        _pd_all = ["(none)"] + pd_labels
                        _pd_key = f"wiz_tag_{tid}_operation_kind"
                        if _pd_key not in st.session_state:
                            # Pre-seed "Unprocessed" as default without using
                            # index= (index= conflicts with session-state restore)
                            _raw = next(
                                (
                                    l
                                    for l in _pd_all
                                    if l.lower() in ("unprocessed", "raw")
                                ),
                                _pd_all[0],
                            )
                            st.session_state[_pd_key] = _raw
                        st.selectbox(
                            "Operation kind",
                            _pd_all,
                            key=_pd_key,
                        )

        # Add buttons row - mutually exclusive choice
        col_eq, col_tag = st.columns(2)
        with col_eq:
            if st.button(
                f"➕ Add equipment to {das_label}",
                key=f"wiz_eq_add_{das_wiz_id}",
            ):
                new_eid: int = st.session_state.wiz_eq_next_id
                st.session_state.wiz_eq_ids = st.session_state.wiz_eq_ids + [new_eid]
                st.session_state.wiz_eq_next_id += 1
                st.session_state[f"wiz_eq_{new_eid}_das_wiz_id"] = das_wiz_id
                st.rerun()

        with col_tag:
            if st.button(
                f"➕ Add standalone channel to {das_label}",
                key=f"wiz_tag_add_{das_wiz_id}",
            ):
                new_tid: int = st.session_state.wiz_tag_next_id
                st.session_state.wiz_tag_ids = st.session_state.wiz_tag_ids + [new_tid]
                st.session_state.wiz_tag_next_id += 1
                st.session_state[f"wiz_tag_{new_tid}_das_wiz_id"] = das_wiz_id
                # Explicitly set eq_wiz_id to None for standalone tags
                st.session_state[f"wiz_tag_{new_tid}_eq_wiz_id"] = None
                st.rerun()

        st.divider()

    def on_next() -> list[str]:
        # Sync equipment sampling location selections before validation
        for eid in st.session_state.wiz_eq_ids:
            label_key = f"wiz_eq_{eid}_sp_label"
            id_key = f"wiz_eq_{eid}_sp_id"
            # If label exists, sync from label->ID; if not but ID exists with no label,
            # derive label from ID to ensure consistency
            if label_key in st.session_state:
                selected_label = st.session_state[label_key]
                for sl_id in sl_named_ids:
                    if _sl_display_label(sl_id) == selected_label:
                        st.session_state[id_key] = sl_id
                        break
            elif id_key not in st.session_state and sl_named_ids:
                # Neither label nor ID set - default to first sampling location
                st.session_state[id_key] = sl_named_ids[0]

        errors: list[str] = []
        cur_eq_ids: list[int] = st.session_state.wiz_eq_ids
        cur_tag_ids: list[int] = st.session_state.wiz_tag_ids

        # At least one equipment OR channel is required
        if not cur_eq_ids and not cur_tag_ids:
            errors.append("Add at least one piece of equipment or one channel.")

        # Validate equipment
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
                if not (st.session_state.get(f"wiz_eq_{eid}_identifier") or "").strip():
                    errors.append(
                        f"Equipment {_eq_display_label(eid)}: identifier is required."
                    )
            if sl_named_ids and st.session_state.get(f"wiz_eq_{eid}_sp_id") is None:
                errors.append(
                    f"Equipment {_eq_display_label(eid)}: sampling location is"
                    " required."
                )

        if not sl_named_ids and cur_eq_ids:
            errors.append(
                "Define at least one sampling location in step 2 before adding"
                " equipment."
            )

        # Validate standalone channels
        for tid in cur_tag_ids:
            tmode = st.session_state.get(f"wiz_tag_{tid}_mode", "New")
            if tmode == "Existing":
                if not st.session_state.get(f"wiz_tag_{tid}_existing_label"):
                    errors.append(
                        f"Channel {tid + 1}: select an existing signal interface."
                    )
            else:
                if not (st.session_state.get(f"wiz_tag_{tid}_tag") or "").strip():
                    errors.append(
                        f"Channel {tid + 1}: tag / interface name is required."
                    )
                if not st.session_state.get(f"wiz_tag_{tid}_parameter"):
                    errors.append(f"Channel {tid + 1}: parameter is required.")

        return errors

    _nav(4, on_next)


# ---------------------------------------------------------------------------
# Step 5: Review & Create
# ---------------------------------------------------------------------------


def _step_review(lookups: dict) -> None:
    # Widget keys from previous steps are cleaned up by Streamlit once those
    # widgets stop being rendered.  Restore all step snapshots so we can read
    # every field that was captured when the user clicked "Next" on each step.
    for s in range(5):
        _restore_snapshot(s)

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
        person_mode = st.session_state.get("wiz_s0_person_mode", "Select existing")
        if person_mode == "Select existing":
            resp = st.session_state.get("wiz_s0_responsible_person") or "—"
        else:
            first = st.session_state.get("wiz_s0_person_first_name") or ""
            last = st.session_state.get("wiz_s0_person_last_name") or ""
            role_v = st.session_state.get("wiz_s0_person_role") or ""
            org_v = st.session_state.get("wiz_s0_person_organization") or ""
            name_part = f"{first} {last}".strip() or "—"
            extra = ", ".join(p for p in [role_v, org_v] if p)
            resp = f"(New: {name_part}{f' — {extra}' if extra else ''})"
        st.markdown(
            f"**Name:** {name}  \n**Type:** {type_label}  \n"
            f"**Start:** {start}  \n**End:** {end}  \n**Description:** {desc}  \n"
            f"**Responsible person:** {resp}"
        )

    # Site
    with st.expander("Site", expanded=True):
        m = st.session_state.get("wiz_s1_mode", "Use existing")
        if m == "Use existing":
            site_label_display = (
                st.session_state.get("wiz_s1_site_label_store")
                or st.session_state.get("wiz_s1_site_label")
                or "—"
            )
            st.markdown(f"**Using existing:** {site_label_display}")
        else:
            site_name_display = (
                st.session_state.get("wiz_s1_site_name_store")
                or st.session_state.get("wiz_s1_site_name")
                or "—"
            )
            st.markdown(f"**Creating new:** {site_name_display}")

    # Sampling Locations
    sl_ids: list[int] = st.session_state.wiz_sl_ids
    with st.expander(f"Sampling Locations ({len(sl_ids)} items)", expanded=True):
        if sl_ids:
            new_sls = [sl_id for sl_id in sl_ids if _sl_mode(sl_id) == "New"]
            exist_sls = [sl_id for sl_id in sl_ids if _sl_mode(sl_id) == "Existing"]
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
    with st.expander(f"Data Acquisition Systems ({len(das_ids)} items)", expanded=True):
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
                sp_wid = st.session_state.get(f"wiz_eq_{eid}_sp_id")
                sp = _sl_display_label(sp_wid) if sp_wid is not None else "(none)"
                das_wid = st.session_state.get(f"wiz_eq_{eid}_das_wiz_id")
                das_lbl = _das_display_label(das_wid) if das_wid is not None else "?"
                st.markdown(
                    f"- **{_eq_display_label(eid)}** (Data Acquisition System:"
                    f" {das_lbl}, sampling point: {sp})"
                )
        if exist_eq:
            st.markdown("**Already exists / will be linked:**")
            for eid in exist_eq:
                sp_wid = st.session_state.get(f"wiz_eq_{eid}_sp_id")
                sp = _sl_display_label(sp_wid) if sp_wid is not None else "(none)"
                st.markdown(f"- **{_eq_display_label(eid)}** (sampling point: {sp})")

    # Channels (standalone)
    tag_ids: list[int] = st.session_state.wiz_tag_ids
    with st.expander(f"Channels ({len(tag_ids)} items)", expanded=True):
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
                param = st.session_state.get(f"wiz_tag_{tid}_parameter", "—")
                vt = st.session_state.get(f"wiz_tag_{tid}_value_type", "—")
                st.markdown(f"- `{tag_str}` ({param}, {vt})")
        if exist_tags:
            st.markdown("**Already exists / will be linked:**")
            for tid in exist_tags:
                si_lbl = st.session_state.get(f"wiz_tag_{tid}_existing_label", "—")
                st.markdown(f"- {si_lbl}")
        if not tag_ids:
            st.caption("No standalone channels defined.")

    def on_next() -> list[str]:
        created, errors = _execute_creates(lookups)
        st.session_state["_wiz_created"] = created
        st.session_state["_wiz_errors"] = errors
        return []

    _nav(5, on_next, next_label="Confirm & Create")


def _step_summary(lookups: dict) -> None:
    from app.components.wizard_helpers import render_wizard_result

    render_wizard_result(
        wiz_id="wiz",
        title="Campaign",
        created=st.session_state.get("_wiz_created", []),
        errors=st.session_state.get("_wiz_errors", []),
        on_restart=lambda: clear_wizard(),
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _execute_creates(lookups: dict) -> tuple[list[dict], list[str]]:
    """Create all entities in dependency order. Returns (created, errors)."""
    # Ensure all step snapshots are restored; Streamlit removes widget keys
    # when their step is not rendered, so we need the captured values here.
    for s in range(5):
        _restore_snapshot(s)

    created: list[dict] = []
    errors: list[str] = []
    eq_id_map: dict[int, int] = {}  # wiz_eq_id  → DB equipment_id
    sl_id_map: dict[int, int] = {}  # wiz_sl_id  → DB SamplingPoint_ID
    das_id_map: dict[int, int] = {}  # wiz_das_id → DB DAS_ID

    type_opts = [
        {"id": t["campaign_kind_id"], "label": t["name"]}
        for t in lookups["campaign_kinds"]
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
    das_opts = [{"id": d["das_id"], "label": d["name"]} for d in lookups["das"]]
    existing_si_opts: list[dict] = lookups.get("signal_interfaces_flat", [])
    person_opts: list[dict] = lookups.get("persons", [])

    # 1. Create site if new
    site_mode = st.session_state.get("wiz_s1_mode", "Use existing")
    if site_mode == "Create new":
        site_type_opts = [
            {"id": t["id"], "label": t["name"]} for t in lookups["site_kinds"]
        ]
        selected_type_label = st.session_state.get("wiz_s1_site_type_label") or None
        site_kind_id = (
            _resolve_id(selected_type_label, site_type_opts)
            if selected_type_label
            else None
        )
        # Prefer the snapshot-stable _store key (survives Streamlit dropping
        # widget keys across step transitions); fall back to widget key.
        site_name_to_create = (
            st.session_state.get("wiz_s1_site_name_store")
            or st.session_state.get("wiz_s1_site_name")
            or ""
        )
        try:
            site = create_site(
                {
                    "name": site_name_to_create,
                    "site_kind_id": site_kind_id,
                    "description": st.session_state.get("wiz_s1_site_description")
                    or None,
                    "lat_wgs84": st.session_state.get("wiz_site_lat_input"),
                    "long_wgs84": st.session_state.get("wiz_site_lng_input"),
                    "city": st.session_state.get("wiz_site_city_input") or None,
                    "province": st.session_state.get("wiz_site_province_input") or None,
                    "country": st.session_state.get("wiz_site_country_input") or None,
                }
            )
            campaign_site_id: int | None = site["id"]
            created.append({"label": f"Site: {site_name_to_create}", "detail": f"id={campaign_site_id}"})
        except APIError as e:
            errors.append(f"Site creation failed: {e.message}")
            return created, errors
    else:
        # Prefer the snapshot-stable _store key; Streamlit drops the widget
        # key once step 1 is left, but the store key survives.
        site_label_for_lookup = st.session_state.get(
            "wiz_s1_site_label_store"
        ) or st.session_state.get("wiz_s1_site_label")
        campaign_site_id = _resolve_id(site_label_for_lookup, site_opts)
        if campaign_site_id is None:
            errors.append(
                "No site selected — go back to step 'Site' and pick or create one."
            )
            return created, errors

    # 2. Resolve / create sampling locations
    if site_mode == "Use existing" and campaign_site_id:
        try:
            existing_site_sls = list_site_sampling_locations(campaign_site_id)
        except APIError:
            existing_site_sls = []
    else:
        existing_site_sls = []

    for sl_wiz_id in st.session_state.get("wiz_sl_ids", []):
        sl_mode = _sl_mode(sl_wiz_id)
        if sl_mode == "Existing":
            # Use _store key which persists across steps
            label = st.session_state.get(f"wiz_sl_{sl_wiz_id}_existing_label_store")
            match = next((s for s in existing_site_sls if s["name"] == label), None)
            if match:
                sl_id_map[sl_wiz_id] = match["id"]
            else:
                errors.append(f"Sampling location '{label}': could not resolve ID.")
        else:
            # Use _store key which persists across steps
            name = (
                st.session_state.get(f"wiz_sl_{sl_wiz_id}_name_store") or ""
            ).strip()
            if name and campaign_site_id is not None:
                try:
                    pu_mode = st.session_state.get(
                        f"wiz_sl_{sl_wiz_id}_pu_mode", "None"
                    )
                    pu_id = None
                    if pu_mode == "Existing":
                        pu_label = st.session_state.get(
                            f"wiz_sl_{sl_wiz_id}_pu_existing"
                        )
                        pu_id = next(
                            (
                                p["process_unit_id"]
                                for p in lookups.get("process_units", [])
                                if p["name"] == pu_label
                            ),
                            None,
                        )
                    elif pu_mode == "New" and campaign_site_id is not None:
                        pu_name = (
                            st.session_state.get(f"wiz_sl_{sl_wiz_id}_pu_name") or ""
                        ).strip()
                        pu_tag = (
                            st.session_state.get(f"wiz_sl_{sl_wiz_id}_pu_tag") or ""
                        ).strip()
                        if pu_name and pu_tag:
                            try:
                                new_pu = create_process_unit(
                                    {
                                        "site_id": campaign_site_id,
                                        "name": pu_name,
                                        "tag": pu_tag,
                                    }
                                )
                                pu_id = new_pu["id"]
                            except APIError as e:
                                errors.append(f"Process unit '{pu_name}': {e.message}")
                    sl = create_sampling_location(
                        campaign_site_id,
                        {
                            "name": name,
                            "description": st.session_state.get(
                                f"wiz_sl_{sl_wiz_id}_description_store"
                            )
                            or None,
                            "latitude": None,
                            "longitude": None,
                            "process_unit_id": pu_id,
                        },
                    )
                    sl_id_map[sl_wiz_id] = sl["id"]
                    created.append({"label": f"Sampling location: {name}", "detail": f"id={sl['id']}"})
                    photo_file = st.session_state.get(f"wiz_sl_{sl_wiz_id}_photo")
                    if photo_file is not None:
                        try:
                            from app.api_client import upload_sampling_point_picture

                            upload_sampling_point_picture(
                                campaign_site_id,
                                sl["id"],
                                photo_file.read(),
                                photo_file.name,
                            )
                        except APIError:
                            errors.append(
                                f"Photo for '{name}' could not be uploaded (location was created)."
                            )
                except APIError as e:
                    errors.append(f"Sampling location '{name}': {e.message}")

    if errors:
        return created, errors

    # 3. Create person if needed, then create campaign
    start_date = st.session_state.get("wiz_s0_start_date")
    end_date = st.session_state.get("wiz_s0_end_date")
    person_mode = st.session_state.get("wiz_s0_person_mode", "Select existing")
    responsible_person_id: int | None = None
    if person_mode == "Create new":
        first_name = st.session_state.get("wiz_s0_person_first_name") or None
        last_name = st.session_state.get("wiz_s0_person_last_name") or None
        email = st.session_state.get("wiz_s0_person_email") or None
        role = st.session_state.get("wiz_s0_person_role") or None
        organization = st.session_state.get("wiz_s0_person_organization") or None
        phone = st.session_state.get("wiz_s0_person_phone") or None
        if first_name or last_name:
            try:
                new_person = create_person(
                    {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "role": role,
                        "organization": organization,
                        "phone": phone,
                    }
                )
                responsible_person_id = new_person["person_id"]
                created.append({"label": f"Person: {(first_name or '')} {(last_name or '')}".strip(), "detail": f"id={responsible_person_id}"})
            except APIError as e:
                errors.append(f"Person creation failed: {e.message}")
                return created, errors
    else:
        resp_label = st.session_state.get("wiz_s0_responsible_person")
        if resp_label:
            matched_person = next(
                (p for p in person_opts if p["label"] == resp_label), None
            )
            if matched_person:
                responsible_person_id = matched_person["person_id"]
    try:
        campaign = create_campaign(
            {
                "name": st.session_state.get("wiz_s0_name"),
                "campaign_kind_id": _resolve_id(
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
        created.append({"label": f"Campaign: {campaign.get('name') or st.session_state.get('wiz_s0_name', '')}", "detail": f"id={campaign_id}"})
    except APIError as e:
        errors.append(f"Campaign creation failed: {e.message}")
        return created, errors

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
                created.append({"label": f"DAS: {das_name}", "detail": f"id={actual_das_id}"})
            except APIError as e:
                errors.append(f"Data Acquisition System '{das_name}': {e.message}")
                continue
        das_id_map[das_wiz_id] = actual_das_id

        # Record the DAS deployment against the campaign site and start date.
        if campaign_site_id is not None:
            deploy_valid_from = (
                datetime(start_date.year, start_date.month, start_date.day).isoformat()
                if start_date
                else datetime.now(timezone.utc).isoformat()
            )
            try:
                deploy_das(
                    actual_das_id,
                    site_id=campaign_site_id,
                    valid_from=deploy_valid_from,
                    campaign_id=campaign_id,
                )
            except APIError as e:
                errors.append(
                    f"Data Acquisition System {das_wiz_id + 1}: "
                    f"could not record deployment: {e.message}"
                )

    if errors:
        return created, errors

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
                        "identifier": st.session_state.get(f"wiz_eq_{eid}_identifier")
                        or None,
                        "serial_number": st.session_state.get(f"wiz_eq_{eid}_serial")
                        or None,
                    }
                )
                actual_eq_id = eq["equipment_id"]
                created.append({"label": f"Equipment: {_eq_display_label(eid)}", "detail": f"id={actual_eq_id}"})
            except APIError as e:
                errors.append(f"Equipment {_eq_display_label(eid)}: {e.message}")
                continue

        if actual_eq_id is None:
            errors.append(f"Equipment {_eq_display_label(eid)}: could not resolve ID.")
            continue

        eq_id_map[eid] = actual_eq_id

        # Resolve sampling point using stored wizard ID (not label)
        sp_wiz_id = st.session_state.get(f"wiz_eq_{eid}_sp_id")
        sampling_point_id: int | None = (
            sl_id_map.get(sp_wiz_id) if sp_wiz_id is not None else None
        )

        if sampling_point_id is None:
            errors.append(
                f"Equipment {_eq_display_label(eid)}: sampling location could"
                " not be resolved."
            )
            continue
        # valid_from defaults to campaign start_date when available, else
        # the server fills in current UTC time. This timestamps the
        # EquipmentLocationHistory row created by create_campaign_deployment.
        deployment_payload: dict = {
            "equipment_id": actual_eq_id,
            "sampling_point_id": sampling_point_id,
        }
        if start_date:
            deployment_payload["valid_from"] = start_date.isoformat()
        try:
            create_campaign_deployment(campaign_id, deployment_payload)
            created.append({"label": f"Deployment for {_eq_display_label(eid)}", "detail": None})
        except APIError as e:
            errors.append(f"Deployment for {_eq_display_label(eid)}: {e.message}")

    if errors:
        return created, errors

    # 6. Create signal interfaces, wire equipment, create channels
    for tid in st.session_state.get("wiz_tag_ids", []):
        eq_wiz_id = st.session_state.get(f"wiz_tag_{tid}_eq_wiz_id")
        actual_eq_id = eq_id_map.get(eq_wiz_id) if eq_wiz_id is not None else None

        # Get DAS: either from equipment (if associated) or directly from tag
        if eq_wiz_id is not None:
            das_wiz_id = st.session_state.get(f"wiz_eq_{eq_wiz_id}_das_wiz_id")
        else:
            das_wiz_id = st.session_state.get(f"wiz_tag_{tid}_das_wiz_id")

        actual_das_id = das_id_map.get(das_wiz_id) if das_wiz_id is not None else None

        tag_mode = st.session_state.get(f"wiz_tag_{tid}_mode", "New")
        signal_interface_id: int | None = None

        if tag_mode == "Existing":
            signal_interface_id = _resolve_id(
                st.session_state.get(f"wiz_tag_{tid}_existing_label"),
                existing_si_opts,
            )
        else:
            tag_str = st.session_state.get(f"wiz_tag_{tid}_tag") or ""
            try:
                si = create_signal_interface(
                    {
                        "data_acquisition_system_id": actual_das_id,
                        "name": tag_str,
                    }
                )
                signal_interface_id = si["signal_interface_id"]
                created.append({"label": f"Signal interface: {tag_str}", "detail": f"id={signal_interface_id}"})
            except APIError as e:
                errors.append(f"Signal interface '{tag_str}': {e.message}")
                continue

        if signal_interface_id is None:
            errors.append(f"Channel {tid + 1}: could not resolve signal interface.")
            continue

        # Wire equipment to interface (only if tag is associated with equipment)
        if actual_eq_id is not None:
            try:
                register_equipment_at_interface(
                    actual_eq_id,
                    {
                        "signal_interface_id": signal_interface_id,
                        "valid_from": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except APIError as e:
                tag_str = st.session_state.get(
                    f"wiz_tag_{tid}_tag", f"channel {tid + 1}"
                )
                errors.append(f"Equipment wiring to interface '{tag_str}': {e.message}")

        # Create channel. The channel's operation kind is not part of the
        # Channel identity (set later via the lineage/processing step), so the
        # operation-kind selection here is informational only.
        param_label = st.session_state.get(f"wiz_tag_{tid}_parameter")
        vt_label = st.session_state.get(f"wiz_tag_{tid}_value_type")
        try:
            create_channel(
                {
                    "signal_interface_id": signal_interface_id,
                    "tag_name": st.session_state.get(f"wiz_tag_{tid}_tag") or "",
                    "parameter_id": _resolve_id(param_label, param_opts),
                    "value_kind_id": _resolve_id(vt_label, _VALUE_TYPES),
                }
            )
            tag_str = st.session_state.get(f"wiz_tag_{tid}_tag", f"channel {tid + 1}")
            created.append({"label": f"Channel: {tag_str}", "detail": None})
        except APIError as e:
            tag_str = st.session_state.get(f"wiz_tag_{tid}_tag", f"channel {tid + 1}")
            errors.append(f"Channel for '{tag_str}': {e.message}")
            continue

    return created, errors
