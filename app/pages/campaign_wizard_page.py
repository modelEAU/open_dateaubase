"""Campaign Wizard — select existing site/equipment and create a campaign."""

from __future__ import annotations

import streamlit as st

from app.api_client import (
    APIError,
    create_campaign,
    create_campaign_deployment,
    create_person,
    list_campaign_kinds,
    list_equipment_lookup,
    list_persons_lookup,
    list_site_sampling_locations,
    list_sites_lookup,
)
from app.components.wizard_helpers import (
    clear_wizard,
    nav,
    render_wizard_header,
    render_wizard_result,
    resolve_id,
    restore_snapshot,
    snapshot_get,
)

_WIZ = "cmp_wiz"

STEPS = [
    "Campaign Details",
    "Site & Sampling Locations",
    "Equipment Deployments",
    "Review & Create",
    "Summary",
]

_STEP_PREFIXES: dict[int, list[str]] = {
    0: [f"{_WIZ}_s0_"],
    1: [f"{_WIZ}_s1_"],
    2: [f"{_WIZ}_s2_"],
    3: [],
    4: [],
}


def _init() -> None:
    defaults: dict = {f"{_WIZ}_step": 0}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _cancel() -> None:
    clear_wizard(_WIZ)


def _load_lookups() -> dict | None:
    try:
        return {
            "campaign_kinds": list_campaign_kinds(),
            "sites": list_sites_lookup(),
            "persons": list_persons_lookup(),
            "equipment": list_equipment_lookup(),
        }
    except APIError as e:
        st.error(f"Failed to load lookup data: {e.message}")
        return None


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def _render_prerequisites(lookups: dict) -> None:
    has_sites = bool(lookups.get("sites"))
    has_equipment = bool(lookups.get("equipment"))

    site_icon = "✅" if has_sites else "❌"
    eq_icon = "✅" if has_equipment else "❌"

    st.markdown("#### Before you start")
    st.markdown(
        f"{site_icon} **Site Setup Wizard** — at least one site with sampling locations\n\n"
        f"{eq_icon} **Field System Wizard** — at least one equipment item registered"
    )
    if not has_sites or not has_equipment:
        missing = []
        if not has_sites:
            missing.append("**Site Setup Wizard** (Workflows → Site Setup Wizard)")
        if not has_equipment:
            missing.append("**Field System Wizard** (Workflows → Field System Wizard)")
        st.warning("Complete the following first:\n\n" + "\n\n".join(f"- {m}" for m in missing))
    st.divider()


def _step_details(lookups: dict) -> None:
    restore_snapshot(_WIZ, 0)

    _render_prerequisites(lookups)

    kind_opts = [
        {"id": k["campaign_kind_id"], "label": k["name"]}
        for k in lookups["campaign_kinds"]
    ]
    kind_labels = [o["label"] for o in kind_opts]
    person_opts: list[dict] = lookups.get("persons", [])
    person_labels = [p["label"] for p in person_opts]

    st.text_input("Campaign name *", key=f"{_WIZ}_s0_name")
    if kind_labels:
        st.selectbox("Campaign type *", kind_labels, key=f"{_WIZ}_s0_kind")
    else:
        st.warning("No campaign types found — add one in Vocabulary → Campaign Kinds first.")
    col_start, col_end = st.columns(2)
    with col_start:
        st.date_input("Start date", key=f"{_WIZ}_s0_start_date", value=None)
    with col_end:
        st.date_input("End date", key=f"{_WIZ}_s0_end_date", value=None)
    st.text_area("Description", key=f"{_WIZ}_s0_description")

    person_mode = st.radio(
        "Responsible person *",
        ["Select existing", "Create new"],
        key=f"{_WIZ}_s0_person_mode",
        horizontal=True,
    )
    if person_mode == "Select existing":
        if person_labels:
            st.selectbox("Person *", person_labels, key=f"{_WIZ}_s0_person_label")
        else:
            st.info("No persons found. Switch to **Create new**.")
    else:
        col_fn, col_ln = st.columns(2)
        with col_fn:
            st.text_input("First name", key=f"{_WIZ}_s0_person_first_name")
        with col_ln:
            st.text_input("Last name", key=f"{_WIZ}_s0_person_last_name")
        st.text_input("Email", key=f"{_WIZ}_s0_person_email")
        col_role, col_org = st.columns(2)
        with col_role:
            st.text_input("Role", key=f"{_WIZ}_s0_person_role")
        with col_org:
            st.text_input("Organization", key=f"{_WIZ}_s0_person_org")
        st.text_input("Phone", key=f"{_WIZ}_s0_person_phone")

    def on_next() -> list[str]:
        errors: list[str] = []
        if not (st.session_state.get(f"{_WIZ}_s0_name") or "").strip():
            errors.append("Campaign name is required.")
        if not kind_labels:
            errors.append("No campaign types available — cannot proceed.")
        person_mode_ = st.session_state.get(f"{_WIZ}_s0_person_mode", "Select existing")
        if person_mode_ == "Select existing":
            if not person_labels:
                errors.append("No persons available — switch to Create new.")
            elif not st.session_state.get(f"{_WIZ}_s0_person_label"):
                errors.append("Responsible person is required.")
        else:
            fn = (st.session_state.get(f"{_WIZ}_s0_person_first_name") or "").strip()
            ln = (st.session_state.get(f"{_WIZ}_s0_person_last_name") or "").strip()
            if not fn and not ln:
                errors.append("Person: at least first name or last name is required.")
        return errors

    nav(
        wiz_id=_WIZ,
        step=0,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
    )


def _step_site_and_sls(lookups: dict) -> None:
    restore_snapshot(_WIZ, 1)

    sites = lookups.get("sites", [])
    site_labels = [s["name"] for s in sites]

    if not sites:
        st.warning(
            "No sites configured yet. "
            "Use the **Site Setup Wizard** in the Workflows sidebar section to create one first."
        )
        nav(
            wiz_id=_WIZ,
            step=1,
            steps=STEPS,
            step_prefixes=_STEP_PREFIXES,
            on_next=lambda: ["No site available — configure a site first."],
            on_cancel=_cancel,
        )
        return

    selected_site = st.selectbox("Site *", site_labels, key=f"{_WIZ}_s1_site")

    # Load sampling locations for the selected site
    site_record = next((s for s in sites if s["name"] == selected_site), None)
    site_id = site_record["site_id"] if site_record else None
    sampling_locations: list[dict] = []

    if site_id is not None:
        try:
            sampling_locations = list_site_sampling_locations(site_id)
        except APIError as e:
            st.error(f"Failed to load sampling locations: {e.message}")

    if not sampling_locations:
        st.info(
            "This site has no sampling locations yet. "
            "Use the **Site Setup Wizard** to add sampling locations, "
            "or proceed to create a campaign without deployments."
        )
    else:
        sl_labels = [sl["name"] for sl in sampling_locations]
        st.multiselect(
            "Sampling locations in scope",
            sl_labels,
            key=f"{_WIZ}_s1_sl_selected",
        )

    nav(
        wiz_id=_WIZ,
        step=1,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=lambda: [],
        on_cancel=_cancel,
    )


def _step_equipment_deployments(lookups: dict) -> None:
    restore_snapshot(_WIZ, 2)

    sites = lookups.get("sites", [])
    # Read step-1 selections from its snapshot: the step-1 widgets aren't
    # rendered here, so Streamlit drops their live keys on the rerun an
    # equipment selectbox triggers (which otherwise blanks this step).
    selected_site = snapshot_get(_WIZ, 1, f"{_WIZ}_s1_site")
    site_record = next((s for s in sites if s["name"] == selected_site), None)
    site_id = site_record["site_id"] if site_record else None

    sampling_locations: list[dict] = []
    if site_id is not None:
        try:
            sampling_locations = list_site_sampling_locations(site_id)
        except APIError:
            pass

    selected_sl_labels: list[str] = snapshot_get(_WIZ, 1, f"{_WIZ}_s1_sl_selected") or []
    selected_sls = [sl for sl in sampling_locations if sl["name"] in selected_sl_labels]

    equipment = lookups.get("equipment", [])
    eq_labels = [e["identifier"] for e in equipment]

    if not selected_sls:
        st.info(
            "No sampling locations selected. "
            "The campaign will be created without equipment deployments."
        )
    else:
        if not equipment:
            st.warning(
                "No equipment configured yet. "
                "Use the **Field System Wizard** to add equipment first."
            )
        else:
            st.info(
                "Select which equipment to deploy at each sampling location."
            )
            for sl in selected_sls:
                st.selectbox(
                    f"Equipment at **{sl['name']}**",
                    ["(none)"] + eq_labels,
                    key=f"{_WIZ}_s2_sl_{sl['id']}_eq",
                )

    nav(
        wiz_id=_WIZ,
        step=2,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=lambda: [],
        on_cancel=_cancel,
    )


def _step_review(lookups: dict) -> None:
    name = st.session_state.get(f"{_WIZ}_s0_name", "")
    kind_label = st.session_state.get(f"{_WIZ}_s0_kind", "")
    start = st.session_state.get(f"{_WIZ}_s0_start_date")
    end = st.session_state.get(f"{_WIZ}_s0_end_date")
    description = st.session_state.get(f"{_WIZ}_s0_description", "")
    selected_site = snapshot_get(_WIZ, 1, f"{_WIZ}_s1_site", "")
    selected_sl_labels: list[str] = snapshot_get(_WIZ, 1, f"{_WIZ}_s1_sl_selected") or []

    st.markdown("### Campaign")
    st.write(f"**Name:** {name}")
    st.write(f"**Type:** {kind_label}")
    if start:
        st.write(f"**Dates:** {start} → {end or '(open)'}")
    if description:
        st.write(f"**Description:** {description}")

    person_mode = st.session_state.get(f"{_WIZ}_s0_person_mode", "Select existing")
    if person_mode == "Select existing":
        st.write(f"**Responsible person:** {st.session_state.get(f'{_WIZ}_s0_person_label', '')}")
    else:
        fn = st.session_state.get(f"{_WIZ}_s0_person_first_name", "")
        ln = st.session_state.get(f"{_WIZ}_s0_person_last_name", "")
        st.write(f"**Responsible person (new):** {fn} {ln}".strip())

    st.markdown("### Site")
    st.write(f"**Site:** {selected_site}")
    if selected_sl_labels:
        st.write(f"**Sampling locations:** {', '.join(selected_sl_labels)}")

    # Show deployments
    sites = lookups.get("sites", [])
    site_record = next((s for s in sites if s["name"] == selected_site), None)
    site_id = site_record["site_id"] if site_record else None
    sampling_locations: list[dict] = []
    if site_id:
        try:
            sampling_locations = list_site_sampling_locations(site_id)
        except APIError:
            pass

    selected_sls = [sl for sl in sampling_locations if sl["name"] in selected_sl_labels]
    equipment = lookups.get("equipment", [])
    deployments = []
    for sl in selected_sls:
        eq_label = st.session_state.get(f"{_WIZ}_s2_sl_{sl['id']}_eq") or "(none)"
        eq_record = next((e for e in equipment if e["identifier"] == eq_label), None)
        if eq_record:
            deployments.append((sl, eq_record))

    if deployments:
        st.markdown("### Equipment Deployments")
        for sl, eq in deployments:
            st.write(f"- **{eq['identifier']}** at {sl['name']}")

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
        title="Campaign",
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

    kind_opts = [
        {"id": k["campaign_kind_id"], "label": k["name"]}
        for k in lookups["campaign_kinds"]
    ]
    person_opts: list[dict] = lookups.get("persons", [])
    sites = lookups.get("sites", [])
    equipment = lookups.get("equipment", [])
    eq_opts = [{"id": e["equipment_id"], "label": e["identifier"]} for e in equipment]

    # 1. Create person if new
    responsible_person_id: int | None = None
    person_mode = st.session_state.get(f"{_WIZ}_s0_person_mode", "Select existing")
    if person_mode == "Create new":
        fn = st.session_state.get(f"{_WIZ}_s0_person_first_name") or None
        ln = st.session_state.get(f"{_WIZ}_s0_person_last_name") or None
        if fn or ln:
            try:
                new_person = create_person(
                    {
                        "first_name": fn,
                        "last_name": ln,
                        "email": st.session_state.get(f"{_WIZ}_s0_person_email") or None,
                        "role": st.session_state.get(f"{_WIZ}_s0_person_role") or None,
                        "organization": st.session_state.get(f"{_WIZ}_s0_person_org") or None,
                        "phone": st.session_state.get(f"{_WIZ}_s0_person_phone") or None,
                    }
                )
                responsible_person_id = new_person["person_id"]
                created.append({"label": f"Person: {(fn or '')} {(ln or '')}".strip(), "detail": f"id={responsible_person_id}"})
            except APIError as e:
                errors.append(f"Person creation failed: {e.message}")
                return created, errors
    else:
        person_label = st.session_state.get(f"{_WIZ}_s0_person_label")
        if person_label:
            match = next((p for p in person_opts if p.get("label") == person_label), None)
            if match:
                responsible_person_id = match.get("person_id") or match.get("id")

    # 2. Create campaign
    kind_label = st.session_state.get(f"{_WIZ}_s0_kind") or None
    campaign_kind_id = resolve_id(kind_label, kind_opts) if kind_label else None
    start_date = st.session_state.get(f"{_WIZ}_s0_start_date")
    end_date = st.session_state.get(f"{_WIZ}_s0_end_date")
    try:
        campaign = create_campaign(
            {
                "name": (st.session_state.get(f"{_WIZ}_s0_name") or "").strip(),
                "campaign_kind_id": campaign_kind_id,
                "description": st.session_state.get(f"{_WIZ}_s0_description") or None,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "responsible_person_id": responsible_person_id,
            }
        )
        campaign_id: int = campaign["campaign_id"]
        created.append({"label": f"Campaign: {campaign.get('name', '')}", "detail": f"id={campaign_id}"})
    except APIError as e:
        errors.append(f"Campaign creation failed: {e.message}")
        return created, errors

    # 3. Create deployments
    selected_site = st.session_state.get(f"{_WIZ}_s1_site")
    site_record = next((s for s in sites if s["name"] == selected_site), None)
    site_id = site_record["site_id"] if site_record else None
    selected_sl_labels: list[str] = st.session_state.get(f"{_WIZ}_s1_sl_selected") or []

    if site_id and selected_sl_labels:
        try:
            sampling_locations = list_site_sampling_locations(site_id)
        except APIError:
            sampling_locations = []

        selected_sls = [sl for sl in sampling_locations if sl["name"] in selected_sl_labels]
        for sl in selected_sls:
            eq_label = st.session_state.get(f"{_WIZ}_s2_sl_{sl['id']}_eq") or "(none)"
            eq_id = resolve_id(eq_label, eq_opts) if eq_label != "(none)" else None
            if eq_id is not None:
                try:
                    create_campaign_deployment(
                        campaign_id,
                        {
                            "equipment_id": eq_id,
                            "sampling_point_id": sl["id"],
                        },
                    )
                    created.append({"label": f"Deployment at {sl['name']}", "detail": eq_label})
                except APIError as e:
                    errors.append(f"Deployment at '{sl['name']}': {e.message}")

    return created, errors


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def main() -> None:
    st.title("🪄 New Campaign")
    _init()

    with st.spinner("Loading lookup data…"):
        lookups = _load_lookups()
    if lookups is None:
        return

    step = st.session_state[f"{_WIZ}_step"]
    render_wizard_header(step, STEPS)

    {
        0: _step_details,
        1: _step_site_and_sls,
        2: _step_equipment_deployments,
        3: _step_review,
        4: _step_summary,
    }[step](lookups)


main()
