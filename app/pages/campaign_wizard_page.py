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

    # Campaigns are multi-site: one repeatable block per site, each with its own
    # sampling-location multiselect. The campaign's sites are the union.
    block_ids: list[int] = st.session_state.get(f"{_WIZ}_s1_block_ids") or []
    if not block_ids:
        block_ids = [0]
        st.session_state[f"{_WIZ}_s1_block_ids"] = block_ids
        st.session_state[f"{_WIZ}_s1_next_block"] = 1

    st.caption(
        "Add each site this campaign covers and pick its sampling locations. "
        "The campaign's sites are derived from everything selected here."
    )

    for b in block_ids:
        with st.container(border=True):
            head, rm = st.columns([6, 1])
            with head:
                selected_site = st.selectbox(
                    "Site *", site_labels, key=f"{_WIZ}_s1_site_{b}"
                )
            with rm:
                st.write("")
                if len(block_ids) > 1 and st.button(
                    "✖", key=f"{_WIZ}_s1_site_{b}_remove", help="Remove this site"
                ):
                    st.session_state[f"{_WIZ}_s1_block_ids"] = [
                        i for i in block_ids if i != b
                    ]
                    st.rerun()

            site_record = next((s for s in sites if s["name"] == selected_site), None)
            site_id = site_record["site_id"] if site_record else None
            sls: list[dict] = []
            if site_id is not None:
                try:
                    sls = list_site_sampling_locations(site_id)
                except APIError as e:
                    st.error(f"Failed to load sampling locations: {e.message}")

            if not sls:
                st.info("This site has no sampling locations yet.")
            else:
                st.multiselect(
                    "Sampling locations in scope",
                    [sl["name"] for sl in sls],
                    key=f"{_WIZ}_s1_sls_{b}",
                )

    if st.button("➕ Add another site", key=f"{_WIZ}_s1_add_site"):
        nxt = st.session_state.get(f"{_WIZ}_s1_next_block", len(block_ids))
        st.session_state[f"{_WIZ}_s1_block_ids"] = block_ids + [nxt]
        st.session_state[f"{_WIZ}_s1_next_block"] = nxt + 1
        st.rerun()

    nav(
        wiz_id=_WIZ,
        step=1,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=lambda: [],
        on_cancel=_cancel,
    )


def _selected_sls(lookups: dict) -> list[dict]:
    """Union of sampling locations selected across all site blocks, each
    annotated with ``site_name``.

    Reads from the step-1 snapshot so it survives later-step reruns. SL ids are
    unique across sites; SL names may collide between sites, so resolution is
    per block (within a single site, names are unique)."""
    sites = lookups.get("sites", [])
    block_ids = snapshot_get(_WIZ, 1, f"{_WIZ}_s1_block_ids") or [0]
    out: list[dict] = []
    seen: set[int] = set()
    for b in block_ids:
        site_name = snapshot_get(_WIZ, 1, f"{_WIZ}_s1_site_{b}")
        site_record = next((s for s in sites if s["name"] == site_name), None)
        if not site_record:
            continue
        try:
            sls = list_site_sampling_locations(site_record["site_id"])
        except APIError:
            sls = []
        chosen = snapshot_get(_WIZ, 1, f"{_WIZ}_s1_sls_{b}") or []
        for sl in sls:
            if sl["name"] in chosen and sl["id"] not in seen:
                seen.add(sl["id"])
                out.append({**sl, "site_name": site_record["name"]})
    return out


def _step_equipment_deployments(lookups: dict) -> None:
    restore_snapshot(_WIZ, 2)

    # Sampling locations come from the step-1 snapshot (its widgets aren't
    # rendered here, so Streamlit drops their live keys on the rerun an
    # equipment selectbox triggers, which otherwise blanks this step).
    selected_sls = _selected_sls(lookups)

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
                    f"Equipment at **{sl['name']}** ({sl['site_name']})",
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
    # Re-inject earlier steps' snapshots: their widgets aren't rendered here, so
    # the live keys were dropped on the way to this step.
    for s in range(3):
        restore_snapshot(_WIZ, s)

    name = st.session_state.get(f"{_WIZ}_s0_name", "")
    kind_label = st.session_state.get(f"{_WIZ}_s0_kind", "")
    start = st.session_state.get(f"{_WIZ}_s0_start_date")
    end = st.session_state.get(f"{_WIZ}_s0_end_date")
    description = st.session_state.get(f"{_WIZ}_s0_description", "")

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

    selected_sls = _selected_sls(lookups)
    site_names = sorted({sl["site_name"] for sl in selected_sls})

    st.markdown("### Sites & Sampling Locations")
    if site_names:
        st.write(f"**Sites:** {', '.join(site_names)}")
    for sl in selected_sls:
        st.write(f"- {sl['name']} ({sl['site_name']})")

    # Show deployments
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
            st.write(f"- **{eq['identifier']}** at {sl['name']} ({sl['site_name']})")

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

    # 3. Create deployments (across every site block's selected locations)
    for sl in _selected_sls(lookups):
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
                created.append(
                    {"label": f"Deployment at {sl['name']} ({sl['site_name']})", "detail": eq_label}
                )
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
