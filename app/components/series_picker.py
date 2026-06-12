"""Cascading filter widget for selecting and creating AnalysisSeries.

Designed to be injected into form_dialog via render_fn.
State is keyed by field_name so multiple pickers can coexist.
"""

from __future__ import annotations

import streamlit as st

_VALUE_KINDS = {1: "Scalar", 2: "Vector", 3: "Matrix", 4: "Image"}


def render_series_picker(
    ctx: dict,
    series_list: list[dict],
    campaigns: list[dict],
    parameters: list[dict],
    sampling_points: list[dict],
    units: list[dict],
) -> list[int]:
    """Cascading filter picker for AnalysisSeries.

    Args:
        ctx: Injected context from render_fn: {field_name, value, label, required}.
        series_list: All existing AnalysisSeries dicts (from list_analysis_series_lookup).
        campaigns: [{campaign_id, name}]
        parameters: [{parameter_id, parameter_name}]
        sampling_points: [{sampling_point_id, label}]
        units: [{unit_id, unit}]

    Returns:
        list[int] of selected analysis_series_ids.
    """
    from app.api_client import APIError, create_analysis_series

    field = ctx["field_name"]
    label = ctx["label"]
    sk_sel = f"spkr_{field}_selected"
    sk_creating = f"spkr_{field}_creating"

    # Initialise selected IDs from ctx["value"] on first render
    if sk_sel not in st.session_state:
        st.session_state[sk_sel] = list(ctx.get("value") or [])

    selected_ids: list[int] = st.session_state[sk_sel]

    st.markdown(f"**{label}**")

    # -----------------------------------------------------------------------
    # Selected chips
    # -----------------------------------------------------------------------
    id_to_series = {s["analysis_series_id"]: s for s in series_list}

    if selected_ids:
        cols = st.columns(min(len(selected_ids), 4))
        for i, sid in enumerate(list(selected_ids)):
            s = id_to_series.get(sid)
            chip_label = (
                f"{s['name']} @ {s['sampling_point_label']}"
                if s
                else f"Series {sid}"
            )
            with cols[i % 4]:
                if st.button(f"{chip_label} ×", key=f"spkr_{field}_rm_{sid}"):
                    st.session_state[sk_sel] = [x for x in selected_ids if x != sid]
    else:
        st.caption("No series selected yet.")

    st.divider()

    # -----------------------------------------------------------------------
    # Filter row
    # -----------------------------------------------------------------------
    col_c, col_p, col_sp = st.columns(3)

    with col_c:
        camp_opts = [{"id": None, "label": "— all campaigns —"}] + [
            {"id": c["campaign_id"], "label": c["name"]} for c in campaigns
        ]
        sel_camp_label = st.selectbox(
            "Campaign",
            [o["label"] for o in camp_opts],
            key=f"spkr_{field}_camp_sel",
        )
        filter_campaign_id = next(
            (o["id"] for o in camp_opts if o["label"] == sel_camp_label), None
        )

    with col_p:
        param_opts = [{"id": None, "label": "— all parameters —"}] + [
            {"id": p["parameter_id"], "label": p["parameter_name"]} for p in parameters
        ]
        sel_param_label = st.selectbox(
            "Parameter",
            [o["label"] for o in param_opts],
            key=f"spkr_{field}_param_sel",
        )
        filter_param_id = next(
            (o["id"] for o in param_opts if o["label"] == sel_param_label), None
        )

    with col_sp:
        sp_opts = [{"id": None, "label": "— all locations —"}] + [
            {"id": sp["sampling_point_id"], "label": sp["label"]} for sp in sampling_points
        ]
        sel_sp_label = st.selectbox(
            "Sampling point",
            [o["label"] for o in sp_opts],
            key=f"spkr_{field}_sp_sel",
        )
        filter_sp_id = next(
            (o["id"] for o in sp_opts if o["label"] == sel_sp_label), None
        )

    # -----------------------------------------------------------------------
    # Matching series
    # -----------------------------------------------------------------------
    matches = [
        s for s in series_list
        if s["analysis_series_id"] not in selected_ids
        and (filter_campaign_id is None or s.get("campaign_id") == filter_campaign_id)
        and (filter_param_id is None or s["parameter_id"] == filter_param_id)
        and (filter_sp_id is None or s["sampling_point_id"] == filter_sp_id)
    ]

    if matches:
        st.caption(f"{len(matches)} matching series:")
        for s in matches[:20]:
            camp_name = next(
                (c["name"] for c in campaigns if c["campaign_id"] == s.get("campaign_id")),
                "no campaign",
            )
            row_label = (
                f"{s['name']}  —  {s['parameter_name']} @ {s['sampling_point_label']}"
                f"  ({camp_name}, {s['unit_name']}, {_VALUE_KINDS.get(s['value_kind_id'], '?')})"
            )
            c1, c2 = st.columns([6, 1])
            with c1:
                st.write(row_label)
            with c2:
                if st.button("+ Add", key=f"spkr_{field}_add_{s['analysis_series_id']}"):
                    st.session_state[sk_sel] = selected_ids + [s["analysis_series_id"]]
        if len(matches) > 20:
            st.caption(f"…and {len(matches) - 20} more. Narrow your filters.")
    else:
        st.caption("No matching series found.")

    # -----------------------------------------------------------------------
    # Create new series
    # -----------------------------------------------------------------------
    creating = st.session_state.get(sk_creating, False)
    if st.button(
        "▲ Close create form" if creating else "▼ Create new series",
        key=f"spkr_{field}_toggle_create",
    ):
        st.session_state[sk_creating] = not creating

    if st.session_state.get(sk_creating, False):
        with st.container(border=True):
            st.caption("Create a new AnalysisSeries and add it to the selection.")
            cc1, cc2 = st.columns(2)
            with cc1:
                nc_camp_opts = [{"id": None, "label": "— none —"}] + [
                    {"id": c["campaign_id"], "label": c["name"]} for c in campaigns
                ]
                nc_camp_label = st.selectbox(
                    "Campaign", [o["label"] for o in nc_camp_opts],
                    key=f"spkr_{field}_nc_camp",
                )
                nc_campaign_id = next(
                    (o["id"] for o in nc_camp_opts if o["label"] == nc_camp_label), None
                )

                nc_param_opts = [{"id": None, "label": "— select —"}] + [
                    {"id": p["parameter_id"], "label": p["parameter_name"]} for p in parameters
                ]
                nc_param_label = st.selectbox(
                    "Parameter *", [o["label"] for o in nc_param_opts],
                    key=f"spkr_{field}_nc_param",
                )
                nc_param_id = next(
                    (o["id"] for o in nc_param_opts if o["label"] == nc_param_label), None
                )

                nc_sp_opts = [{"id": None, "label": "— select —"}] + [
                    {"id": sp["sampling_point_id"], "label": sp["label"]}
                    for sp in sampling_points
                ]
                nc_sp_label = st.selectbox(
                    "Sampling point *", [o["label"] for o in nc_sp_opts],
                    key=f"spkr_{field}_nc_sp",
                )
                nc_sp_id = next(
                    (o["id"] for o in nc_sp_opts if o["label"] == nc_sp_label), None
                )

            with cc2:
                nc_unit_opts = [{"id": None, "label": "— select —"}] + [
                    {"id": u["unit_id"], "label": u["unit"]} for u in units
                ]
                nc_unit_label = st.selectbox(
                    "Unit *", [o["label"] for o in nc_unit_opts],
                    key=f"spkr_{field}_nc_unit",
                )
                nc_unit_id = next(
                    (o["id"] for o in nc_unit_opts if o["label"] == nc_unit_label), None
                )

                nc_vk_label = st.selectbox(
                    "Value kind *", list(_VALUE_KINDS.values()),
                    key=f"spkr_{field}_nc_vk",
                )
                nc_vk_id = next(k for k, v in _VALUE_KINDS.items() if v == nc_vk_label)

            # Auto-generate name
            auto_name = ""
            if nc_param_id and nc_sp_id:
                p_name = next(
                    (p["parameter_name"] for p in parameters if p["parameter_id"] == nc_param_id),
                    "",
                )
                sp_name = next(
                    (sp["label"] for sp in sampling_points if sp["sampling_point_id"] == nc_sp_id),
                    "",
                )
                auto_name = f"{p_name} at {sp_name}"
            nc_name = st.text_input(
                "Series name *", value=auto_name, key=f"spkr_{field}_nc_name"
            )

            if st.button("Create & Add", type="primary", key=f"spkr_{field}_create_btn"):
                if not all([nc_param_id, nc_sp_id, nc_unit_id, nc_name.strip()]):
                    st.error("Parameter, Sampling Point, Unit, and Name are required.")
                else:
                    try:
                        result = create_analysis_series({
                            "name": nc_name.strip(),
                            "parameter_id": nc_param_id,
                            "sampling_point_id": nc_sp_id,
                            "unit_id": nc_unit_id,
                            "value_kind_id": nc_vk_id,
                            "campaign_id": nc_campaign_id,
                        })
                        new_id = result["analysis_series_id"]
                        st.session_state[sk_sel] = selected_ids + [new_id]
                        st.session_state[sk_creating] = False
                    except APIError as e:
                        st.error(f"Failed to create series: {e.message}")

    return list(st.session_state.get(sk_sel, []))
