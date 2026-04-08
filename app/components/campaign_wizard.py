"""Multi-step campaign creation wizard for open_datEAUbase."""

from __future__ import annotations

import streamlit as st

from app.api_client import (
    APIError,
    create_campaign,
    create_campaign_deployment,
    create_channel,
    create_equipment,
    create_signal_port,
    create_site,
    list_campaign_types,
    list_das_lookup,
    list_equipment_lookup,
    list_equipment_models_lookup,
    list_parameters_lookup,
    list_processing_degrees_lookup,
    list_signal_port_types_lookup,
    list_signal_ports,
    list_sites_lookup,
    list_sampling_points_lookup,
    register_equipment_at_port,
)
from app.components.location_picker import render_location_picker

STEPS = [
    "Campaign basics",
    "Site",
    "Equipment",
    "Channels",
    "Signal Ports",
    "Review & Create",
]

_VALUE_TYPES = [
    {"id": 1, "label": "Scalar"},
    {"id": 2, "label": "Vector"},
    {"id": 3, "label": "Matrix"},
    {"id": 4, "label": "Image"},
]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def init_wizard() -> None:
    """Ensure wizard session-state keys exist. Idempotent."""
    defaults: dict = {
        "wizard_step": 0,
        "wiz_eq_ids": [],
        "wiz_eq_next_id": 0,
        "wiz_ch_ids": [],
        "wiz_ch_next_id": 0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def clear_wizard() -> None:
    """Remove all wizard state from session_state."""
    to_del = [
        k
        for k in list(st.session_state.keys())
        if k.startswith("wiz_") or k in ("wizard_active", "wizard_step")
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
        2: _step_equipment,
        3: _step_channels,
        4: _step_signal_ports,
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
            "equipment": list_equipment_lookup(),
            "equipment_models": list_equipment_models_lookup(),
            "parameters": list_parameters_lookup(),
            "processing_degrees": list_processing_degrees_lookup(),
            "sampling_points": list_sampling_points_lookup(),
            "das": list_das_lookup(),
            "signal_port_types": list_signal_port_types_lookup(),
            "signal_ports_flat": signal_ports_flat,
        }
    except APIError as e:
        st.error(f"Failed to load lookup data: {e.message}")
        return None


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


def _eq_display_label(eq_wiz_id: int) -> str:
    mode = st.session_state.get(f"wiz_eq_{eq_wiz_id}_mode", "Existing")
    if mode == "Existing":
        return (
            st.session_state.get(f"wiz_eq_{eq_wiz_id}_eq_label")
            or f"Equipment {eq_wiz_id}"
        )
    return (
        st.session_state.get(f"wiz_eq_{eq_wiz_id}_identifier")
        or f"New equipment {eq_wiz_id}"
    )


def _ch_display_label(cid: int) -> str:
    eq_wiz_id = st.session_state.get(f"wiz_ch_{cid}_eq_id")
    param = st.session_state.get(f"wiz_ch_{cid}_parameter") or f"Channel {cid}"
    eq = _eq_display_label(eq_wiz_id) if eq_wiz_id is not None else "?"
    return f"{eq} – {param}"


# ---------------------------------------------------------------------------
# Step 0: Campaign basics
# ---------------------------------------------------------------------------


def _step_campaign(lookups: dict) -> None:
    type_opts = [
        {"id": t["campaign_type_id"], "label": t["name"]}
        for t in lookups["campaign_types"]
    ]
    type_labels = [o["label"] for o in type_opts]

    st.text_input("Campaign name *", key="wiz_s0_name")
    if type_labels:
        st.selectbox("Campaign type *", type_labels, key="wiz_s0_campaign_type")
    else:
        st.warning("No campaign types found in the database.")
    st.date_input("Start date", key="wiz_s0_start_date", value=None)
    st.date_input("End date", key="wiz_s0_end_date", value=None)
    st.text_area("Description", key="wiz_s0_description")

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
        st.text_input("Site type", key="wiz_s1_site_type")
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
# Step 2: Equipment
# ---------------------------------------------------------------------------


def _step_equipment(lookups: dict) -> None:
    eq_opts = [
        {"id": e["equipment_id"], "label": e["identifier"]}
        for e in lookups["equipment"]
    ]
    model_opts = [
        {"id": m["model_id"], "label": _model_label(m)}
        for m in lookups["equipment_models"]
    ]
    sp_opts = [
        {"id": s["sampling_point_id"], "label": s["label"]}
        for s in lookups["sampling_points"]
    ]

    eq_labels = [o["label"] for o in eq_opts]
    model_labels = [o["label"] for o in model_opts]
    sp_labels = [o["label"] for o in sp_opts]

    st.write("Add each piece of equipment that will be deployed in this campaign.")

    ids: list[int] = st.session_state.wiz_eq_ids
    for item_id in ids:
        with st.container(border=True):
            col_title, col_remove = st.columns([6, 1])
            with col_title:
                st.markdown(f"**Equipment item {item_id + 1}**")
            with col_remove:
                if st.button("✖ Remove", key=f"wiz_eq_{item_id}_remove"):
                    st.session_state.wiz_eq_ids = [i for i in ids if i != item_id]
                    st.rerun()

            mode = st.radio(
                "Add as",
                ["Existing", "New"],
                key=f"wiz_eq_{item_id}_mode",
                horizontal=True,
            )

            if mode == "Existing":
                if eq_labels:
                    st.selectbox(
                        "Select equipment *",
                        eq_labels,
                        key=f"wiz_eq_{item_id}_eq_label",
                    )
                else:
                    st.info("No existing equipment found. Switch to **New**.")
            else:
                if model_labels:
                    st.selectbox(
                        "Equipment model *",
                        model_labels,
                        key=f"wiz_eq_{item_id}_model",
                    )
                else:
                    st.warning("No equipment models found in the database.")
                st.text_input(
                    "Identifier / tag *", key=f"wiz_eq_{item_id}_identifier"
                )
                st.text_input("Serial number", key=f"wiz_eq_{item_id}_serial")

            if sp_labels:
                st.selectbox(
                    "Sampling point (optional)",
                    ["(none)"] + sp_labels,
                    key=f"wiz_eq_{item_id}_sp",
                )
            else:
                st.caption("No sampling points configured — deployment will be created without one.")

    if st.button("➕ Add equipment", key="wiz_eq_add"):
        new_id: int = st.session_state.wiz_eq_next_id
        st.session_state.wiz_eq_ids = ids + [new_id]
        st.session_state.wiz_eq_next_id += 1
        st.rerun()

    def on_next() -> list[str]:
        cur_ids: list[int] = st.session_state.wiz_eq_ids
        if not cur_ids:
            return ["Add at least one piece of equipment."]
        errors: list[str] = []
        for eid in cur_ids:
            m = st.session_state.get(f"wiz_eq_{eid}_mode", "Existing")
            if m == "Existing":
                if not st.session_state.get(f"wiz_eq_{eid}_eq_label"):
                    errors.append(f"Equipment item {eid + 1}: select an existing equipment.")
            else:
                if not st.session_state.get(f"wiz_eq_{eid}_model"):
                    errors.append(f"Equipment item {eid + 1}: model is required.")
                if not (st.session_state.get(f"wiz_eq_{eid}_identifier") or "").strip():
                    errors.append(f"Equipment item {eid + 1}: identifier is required.")
        return errors

    _nav(2, on_next)


# ---------------------------------------------------------------------------
# Step 3: Channels
# ---------------------------------------------------------------------------


def _step_channels(lookups: dict) -> None:
    param_opts = [
        {"id": p["parameter_id"], "label": p["parameter_name"]}
        for p in lookups["parameters"]
    ]
    pd_opts = [
        {"id": p["processing_degree_id"], "label": p["name"]}
        for p in lookups["processing_degrees"]
    ]
    param_labels = [o["label"] for o in param_opts]
    pd_labels = [o["label"] for o in pd_opts]
    vt_labels = [o["label"] for o in _VALUE_TYPES]

    st.write("Define measurement channels for each piece of equipment.")

    for eq_wiz_id in st.session_state.wiz_eq_ids:
        eq_label = _eq_display_label(eq_wiz_id)
        st.markdown(f"### {eq_label}")

        eq_ch_ids = [
            cid
            for cid in st.session_state.wiz_ch_ids
            if st.session_state.get(f"wiz_ch_{cid}_eq_id") == eq_wiz_id
        ]

        for cid in eq_ch_ids:
            with st.container(border=True):
                col_title, col_remove = st.columns([6, 1])
                with col_title:
                    st.markdown(f"Channel {cid + 1}")
                with col_remove:
                    if st.button("✖", key=f"wiz_ch_{cid}_remove"):
                        st.session_state.wiz_ch_ids = [
                            c for c in st.session_state.wiz_ch_ids if c != cid
                        ]
                        st.rerun()

                if param_labels:
                    st.selectbox(
                        "Parameter *", param_labels, key=f"wiz_ch_{cid}_parameter"
                    )
                else:
                    st.warning("No parameters found in the database.")
                st.selectbox(
                    "Value type *", vt_labels, key=f"wiz_ch_{cid}_value_type"
                )
                if pd_labels:
                    st.selectbox(
                        "Processing degree (optional)",
                        ["(none)"] + pd_labels,
                        key=f"wiz_ch_{cid}_processing_degree",
                    )

        if st.button(f"➕ Add channel for {eq_label}", key=f"wiz_ch_add_{eq_wiz_id}"):
            new_cid: int = st.session_state.wiz_ch_next_id
            st.session_state.wiz_ch_ids = st.session_state.wiz_ch_ids + [new_cid]
            st.session_state.wiz_ch_next_id += 1
            st.session_state[f"wiz_ch_{new_cid}_eq_id"] = eq_wiz_id
            st.rerun()

        st.divider()

    def on_next() -> list[str]:
        if not st.session_state.wiz_ch_ids:
            return ["Add at least one channel."]
        errors: list[str] = []
        for cid in st.session_state.wiz_ch_ids:
            if not param_labels:
                errors.append("No parameters available — cannot define channels.")
                break
            if not st.session_state.get(f"wiz_ch_{cid}_parameter"):
                errors.append(f"Channel {cid + 1}: parameter is required.")
        return errors

    _nav(3, on_next)


# ---------------------------------------------------------------------------
# Step 4: Signal Ports
# ---------------------------------------------------------------------------


def _step_signal_ports(lookups: dict) -> None:
    das_opts = [{"id": d["das_id"], "label": d["name"]} for d in lookups["das"]]
    sp_type_opts = [
        {"id": t["signal_port_type_id"], "label": t["name"]}
        for t in lookups["signal_port_types"]
    ]
    existing_sp_opts: list[dict] = lookups.get("signal_ports_flat", [])

    das_labels = [o["label"] for o in das_opts]
    sp_type_labels = [o["label"] for o in sp_type_opts]
    existing_sp_labels = [o["label"] for o in existing_sp_opts]

    st.write("Assign a DAS signal port to each measurement channel.")

    for cid in st.session_state.wiz_ch_ids:
        label = _ch_display_label(cid)
        with st.container(border=True):
            st.markdown(f"**{label}**")

            mode = st.radio(
                "Signal port",
                ["Create new", "Select existing"],
                key=f"wiz_sp_{cid}_mode",
                horizontal=True,
            )

            if mode == "Select existing":
                if existing_sp_labels:
                    st.selectbox(
                        "Signal port *",
                        existing_sp_labels,
                        key=f"wiz_sp_{cid}_existing_label",
                    )
                else:
                    st.info("No existing signal ports found. Switch to **Create new**.")
            else:
                if das_labels:
                    st.selectbox("DAS *", das_labels, key=f"wiz_sp_{cid}_das")
                else:
                    st.warning("No DAS systems found in the database.")
                if sp_type_labels:
                    st.selectbox(
                        "Port type *", sp_type_labels, key=f"wiz_sp_{cid}_type"
                    )
                else:
                    st.warning("No signal port types found in the database.")
                st.text_input(
                    "Tag *",
                    key=f"wiz_sp_{cid}_tag",
                    help="Unique identifier within the DAS (e.g. AI_01)",
                )
                st.text_input("Description", key=f"wiz_sp_{cid}_description")

    def on_next() -> list[str]:
        errors: list[str] = []
        for cid in st.session_state.wiz_ch_ids:
            m = st.session_state.get(f"wiz_sp_{cid}_mode", "Create new")
            ch = _ch_display_label(cid)
            if m == "Select existing":
                if not st.session_state.get(f"wiz_sp_{cid}_existing_label"):
                    errors.append(f"{ch}: select an existing signal port.")
            else:
                if not st.session_state.get(f"wiz_sp_{cid}_das"):
                    errors.append(f"{ch}: DAS is required.")
                if not st.session_state.get(f"wiz_sp_{cid}_type"):
                    errors.append(f"{ch}: port type is required.")
                if not (st.session_state.get(f"wiz_sp_{cid}_tag") or "").strip():
                    errors.append(f"{ch}: tag is required.")
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
        st.markdown(
            f"**Name:** {name}  \n**Type:** {type_label}  \n"
            f"**Start:** {start}  \n**End:** {end}  \n**Description:** {desc}"
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

    # Equipment
    eq_ids: list[int] = st.session_state.wiz_eq_ids
    with st.expander(f"Equipment ({len(eq_ids)} items)", expanded=True):
        for eid in eq_ids:
            mode = st.session_state.get(f"wiz_eq_{eid}_mode", "Existing")
            sp = st.session_state.get(f"wiz_eq_{eid}_sp") or "(none)"
            if mode == "Existing":
                lbl = st.session_state.get(f"wiz_eq_{eid}_eq_label", "—")
                st.markdown(f"- **{lbl}** *(existing)*, sampling point: {sp}")
            else:
                idf = st.session_state.get(f"wiz_eq_{eid}_identifier", "—")
                mdl = st.session_state.get(f"wiz_eq_{eid}_model", "—")
                st.markdown(
                    f"- **{idf}** *(new, model: {mdl})*, sampling point: {sp}"
                )

    # Channels
    ch_ids: list[int] = st.session_state.wiz_ch_ids
    with st.expander(f"Channels ({len(ch_ids)} items)", expanded=True):
        for cid in ch_ids:
            param = st.session_state.get(f"wiz_ch_{cid}_parameter", "—")
            vt = st.session_state.get(f"wiz_ch_{cid}_value_type", "—")
            pd_val = st.session_state.get(f"wiz_ch_{cid}_processing_degree") or "—"
            eq_wiz_id = st.session_state.get(f"wiz_ch_{cid}_eq_id")
            eq_lbl = (
                _eq_display_label(eq_wiz_id) if eq_wiz_id is not None else "?"
            )
            st.markdown(
                f"- **{param}** ({vt}) on *{eq_lbl}*, processing degree: {pd_val}"
            )

    # Signal Ports
    with st.expander(f"Signal Port assignments ({len(ch_ids)})", expanded=True):
        for cid in ch_ids:
            ch_lbl = _ch_display_label(cid)
            sp_mode = st.session_state.get(f"wiz_sp_{cid}_mode", "Create new")
            if sp_mode == "Select existing":
                sp_lbl = st.session_state.get(f"wiz_sp_{cid}_existing_label", "—")
                st.markdown(f"- **{ch_lbl}** → existing port: {sp_lbl}")
            else:
                das = st.session_state.get(f"wiz_sp_{cid}_das", "—")
                tag = st.session_state.get(f"wiz_sp_{cid}_tag", "—")
                sp_type = st.session_state.get(f"wiz_sp_{cid}_type", "—")
                st.markdown(
                    f"- **{ch_lbl}** → new port: tag=`{tag}`, DAS={das}, type={sp_type}"
                )

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
    eq_id_map: dict[int, int] = {}  # wiz_eq_id → actual DB equipment_id

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
    sp_opts = [
        {"id": s["sampling_point_id"], "label": s["label"]}
        for s in lookups["sampling_points"]
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

    # 1. Create site if new
    site_mode = st.session_state.get("wiz_s1_mode", "Use existing")
    if site_mode == "Create new":
        try:
            site = create_site(
                {
                    "name": st.session_state.get("wiz_s1_site_name", ""),
                    "type": st.session_state.get("wiz_s1_site_type") or None,
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

    # 2. Create campaign
    start_date = st.session_state.get("wiz_s0_start_date")
    end_date = st.session_state.get("wiz_s0_end_date")
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
            }
        )
        campaign_id: int = campaign["campaign_id"]
    except APIError as e:
        errors.append(f"Campaign creation failed: {e.message}")
        return errors

    # 3. Create equipment and deployments
    for eid in st.session_state.wiz_eq_ids:
        eq_mode = st.session_state.get(f"wiz_eq_{eid}_mode", "Existing")

        if eq_mode == "Existing":
            actual_eq_id = _resolve_id(
                st.session_state.get(f"wiz_eq_{eid}_eq_label"), eq_opts
            )
        else:
            try:
                eq = create_equipment(
                    {
                        "model_id": _resolve_id(
                            st.session_state.get(f"wiz_eq_{eid}_model"), model_opts
                        ),
                        "identifier": st.session_state.get(f"wiz_eq_{eid}_identifier")
                        or None,
                        "serial_number": st.session_state.get(f"wiz_eq_{eid}_serial")
                        or None,
                    }
                )
                actual_eq_id = eq["equipment_id"]
            except APIError as e:
                errors.append(f"Equipment item {eid + 1}: {e.message}")
                continue

        if actual_eq_id is None:
            errors.append(f"Equipment item {eid + 1}: could not resolve ID.")
            continue

        eq_id_map[eid] = actual_eq_id

        sp_label = st.session_state.get(f"wiz_eq_{eid}_sp")
        sampling_point_id = (
            _resolve_id(sp_label, sp_opts)
            if sp_label and sp_label != "(none)"
            else None
        )

        if sampling_point_id is not None:
            try:
                create_campaign_deployment(
                    campaign_id,
                    {
                        "equipment_id": actual_eq_id,
                        "sampling_point_id": sampling_point_id,
                    },
                )
            except APIError as e:
                errors.append(f"Deployment for equipment item {eid + 1}: {e.message}")

    # 4. Create signal ports, register equipment, create channels
    for cid in st.session_state.wiz_ch_ids:
        eq_wiz_id = st.session_state.get(f"wiz_ch_{cid}_eq_id")
        actual_eq_id = eq_id_map.get(eq_wiz_id) if eq_wiz_id is not None else None

        # Resolve signal port
        sp_mode = st.session_state.get(f"wiz_sp_{cid}_mode", "Create new")
        signal_port_id: int | None = None

        if sp_mode == "Select existing":
            signal_port_id = _resolve_id(
                st.session_state.get(f"wiz_sp_{cid}_existing_label"), existing_sp_opts
            )
        else:
            try:
                sp = create_signal_port(
                    {
                        "das_id": _resolve_id(
                            st.session_state.get(f"wiz_sp_{cid}_das"), das_opts
                        ),
                        "signal_port_type_id": _resolve_id(
                            st.session_state.get(f"wiz_sp_{cid}_type"), sp_type_opts
                        ),
                        "tag": (st.session_state.get(f"wiz_sp_{cid}_tag") or ""),
                        "description": st.session_state.get(
                            f"wiz_sp_{cid}_description"
                        )
                        or None,
                    }
                )
                signal_port_id = sp["signal_port_id"]
            except APIError as e:
                errors.append(
                    f"Signal port for {_ch_display_label(cid)}: {e.message}"
                )
                continue

        if signal_port_id is None:
            errors.append(
                f"Signal port for {_ch_display_label(cid)}: could not resolve port."
            )
            continue

        # Register equipment at port (best-effort — port may already have equipment)
        if actual_eq_id is not None:
            try:
                register_equipment_at_port(
                    signal_port_id, {"equipment_id": actual_eq_id}
                )
            except APIError as e:
                errors.append(
                    f"Equipment registration at port for {_ch_display_label(cid)}: "
                    f"{e.message}"
                )

        # Create channel
        param_label = st.session_state.get(f"wiz_ch_{cid}_parameter")
        vt_label = st.session_state.get(f"wiz_ch_{cid}_value_type")
        pd_label = st.session_state.get(f"wiz_ch_{cid}_processing_degree")
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
            errors.append(f"Channel {_ch_display_label(cid)}: {e.message}")

    return errors
