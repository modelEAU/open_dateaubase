"""Cascading filter widget for selecting and creating AnalysisSeries.

Designed to be injected into form_dialog via render_fn.
State is keyed by field_name so multiple pickers can coexist.
"""

from __future__ import annotations

import streamlit as st
from streamlit.errors import StreamlitAPIException

from app.components.kind_select import select_or_none
from app.components.labels import ALL_LABEL
from app.components.param_unit import unit_select
from app.components.schema_registry import describe

_VALUE_KINDS = {1: "Scalar", 2: "Vector", 3: "Matrix", 4: "Image"}


def _sampling_points_for_campaign(campaign_id: int) -> list[dict]:
    from app.api_client import APIError, list_sampling_points_lookup

    try:
        return list_sampling_points_lookup(campaign_id=campaign_id)
    except APIError:
        return []


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
    sk_new = f"spkr_{field}_created"

    # Initialise selected IDs from ctx["value"] on first render
    if sk_sel not in st.session_state:
        st.session_state[sk_sel] = list(ctx.get("value") or [])

    selected_ids: list[int] = st.session_state[sk_sel]

    # Series created from this picker are not in the caller's `series_list`
    # until the page re-fetches, so carry them here until it catches up.
    known = {s["analysis_series_id"] for s in series_list}
    series_list = series_list + [
        s
        for s in st.session_state.get(sk_new, [])
        if s["analysis_series_id"] not in known
    ]

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
    filter_box = st.container(border=True)
    filter_box.caption("Search existing series")
    with filter_box:
        col_c, col_p, col_sp = st.columns(3)

    with col_c:
        camp_opts = [{"id": None, "label": ALL_LABEL}] + [
            {"id": c["campaign_id"], "label": c["name"]} for c in campaigns
        ]
        sel_camp_label = st.selectbox(
            "Campaign",
            [o["label"] for o in camp_opts],
            key=f"spkr_{field}_camp_sel",
            help="Narrow the list below to series belonging to one campaign.",
        )
        filter_campaign_id = next(
            (o["id"] for o in camp_opts if o["label"] == sel_camp_label), None
        )

    with col_p:
        param_opts = [{"id": None, "label": ALL_LABEL}] + [
            {"id": p["parameter_id"], "label": p["parameter_name"]} for p in parameters
        ]
        sel_param_label = st.selectbox(
            "Parameter",
            [o["label"] for o in param_opts],
            key=f"spkr_{field}_param_sel",
            help="Narrow the list below to series measuring one parameter.",
        )
        filter_param_id = next(
            (o["id"] for o in param_opts if o["label"] == sel_param_label), None
        )

    with col_sp:
        filter_sampling_points = (
            sampling_points
            if filter_campaign_id is None
            else _sampling_points_for_campaign(filter_campaign_id)
        )
        sp_opts = [{"id": None, "label": ALL_LABEL}] + [
            {"id": sp["sampling_point_id"], "label": sp["label"]} for sp in filter_sampling_points
        ]
        sel_sp_label = st.selectbox(
            "Sampling point",
            [o["label"] for o in sp_opts],
            key=f"spkr_{field}_sp_sel",
            help="Narrow the list below to series from one sampling point.",
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
        if not creating:
            # Opening the form: inherit whatever the filter row above is showing,
            # since that is the series the user just failed to find.
            for wkey, seeded in (
                (f"spkr_{field}_nc_camp", sel_camp_label),
                (f"spkr_{field}_nc_param", sel_param_label),
                (f"spkr_{field}_nc_sp", sel_sp_label),
            ):
                if seeded != ALL_LABEL:
                    st.session_state[wkey] = seeded

    if st.session_state.get(sk_creating, False):
        with st.container(border=True):
            st.caption("Create a new AnalysisSeries and add it to the selection.")
            cc1, cc2 = st.columns(2)
            with cc1:
                nc_camp_ids = {c["name"]: c["campaign_id"] for c in campaigns}
                nc_camp_label = select_or_none(
                    "Campaign",
                    list(nc_camp_ids),
                    key=f"spkr_{field}_nc_camp",
                    help=describe("AnalysisSeries", "campaign_id"),
                )
                nc_campaign_id = nc_camp_ids.get(nc_camp_label or "")

                nc_param_ids = {
                    p["parameter_name"]: p["parameter_id"] for p in parameters
                }
                nc_param_label = select_or_none(
                    "Parameter *",
                    list(nc_param_ids),
                    key=f"spkr_{field}_nc_param",
                    help=describe("AnalysisSeries", "parameter_id"),
                )
                nc_param_id = nc_param_ids.get(nc_param_label or "")

                nc_sampling_points = (
                    sampling_points
                    if nc_campaign_id is None
                    else _sampling_points_for_campaign(nc_campaign_id)
                )
                nc_sp_ids = {
                    sp["label"]: sp["sampling_point_id"] for sp in nc_sampling_points
                }
                nc_sp_label = select_or_none(
                    "Sampling point *",
                    list(nc_sp_ids),
                    key=f"spkr_{field}_nc_sp",
                    help=describe("AnalysisSeries", "sampling_point_id"),
                )
                nc_sp_id = nc_sp_ids.get(nc_sp_label or "")

            with cc2:
                nc_unit_id = unit_select(
                    "Unit *",
                    parameter_id=nc_param_id,
                    all_units=units,
                    key=f"spkr_{field}_nc_unit",
                    help=describe("AnalysisSeries", "unit_id"),
                )

                # Fixed by the parameter — a series whose value kind disagrees
                # with its parameter's is not storable.
                nc_vk_id = next(
                    (
                        p.get("value_kind_id")
                        for p in parameters
                        if p["parameter_id"] == nc_param_id
                    ),
                    None,
                )
                st.text_input(
                    "Value kind",
                    value=_VALUE_KINDS.get(nc_vk_id or 0, "—"),
                    disabled=True,
                    help="Determined by the parameter.",
                )

            # Auto-generate name
            auto_name = ""
            if nc_param_id and nc_sp_id:
                p_name = next(
                    (p["parameter_name"] for p in parameters if p["parameter_id"] == nc_param_id),
                    "",
                )
                sp_name = next(
                    (
                        sp["label"]
                        for sp in nc_sampling_points
                        if sp["sampling_point_id"] == nc_sp_id
                    ),
                    "",
                )
                auto_name = f"{p_name} at {sp_name}"
            # A keyed widget ignores `value=` once its state exists, so push the
            # regenerated name in ourselves — unless the user typed their own.
            nk = f"spkr_{field}_nc_name"
            nk_auto = f"spkr_{field}_nc_name_auto"
            if st.session_state.get(nk, "") in ("", st.session_state.get(nk_auto)):
                st.session_state[nk] = auto_name
            st.session_state[nk_auto] = auto_name
            nc_name = st.text_input(
                "Series name *",
                key=nk,
                help=describe("AnalysisSeries", "name"),
            )

            if st.button("Create & Add", type="primary", key=f"spkr_{field}_create_btn"):
                if not all([nc_param_id, nc_sp_id, nc_unit_id, nc_vk_id, nc_name.strip()]):
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
                        st.session_state.setdefault(sk_new, []).append({
                            "analysis_series_id": new_id,
                            "name": nc_name.strip(),
                            "parameter_id": nc_param_id,
                            "parameter_name": nc_param_label or "",
                            "sampling_point_id": nc_sp_id,
                            "sampling_point_label": nc_sp_label or "",
                            "unit_id": nc_unit_id,
                            "unit_name": next(
                                (u["unit"] for u in units if u["unit_id"] == nc_unit_id),
                                "",
                            ),
                            "value_kind_id": nc_vk_id,
                            "campaign_id": nc_campaign_id,
                        })
                        # Everything above already rendered this pass, so redraw.
                        # Fragment scope keeps the surrounding dialog open; it
                        # is only legal during a fragment rerun.
                        try:
                            st.rerun(scope="fragment")
                        except StreamlitAPIException:
                            st.rerun()
                    except APIError as e:
                        st.error(f"Failed to create series: {e.message}")

    return list(st.session_state.get(sk_sel, []))
