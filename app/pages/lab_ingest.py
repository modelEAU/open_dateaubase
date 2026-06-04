"""Lab Analysis Ingest page — accordion layout with experiment context,
sample creation, and per-series measurement entry.

Uses the LabIngestRequest / LabImageIngestResponse API.
"""

from __future__ import annotations

import sys
from datetime import datetime, time
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app.api_client import (
    APIError,
    create_analysis_series,
    create_lab_panel,
    create_sample,
    get_lab_experiment_series,
    get_lab_panel,
    ingest_lab,
    ingest_lab_image,
    list_analysis_series_lookup,
    list_campaigns_lookup,
    list_equipment_lookup,
    list_lab_experiments_lookup,
    list_lab_panels,
    list_parameters_lookup,
    list_persons,
    list_processing_kinds_lookup,
    list_quality_codes,
    list_sample_collection_kinds,
    list_samples_lookup,
    list_sampling_points_lookup,
    list_units_lookup,
)

# ---------------------------------------------------------------------------
# Lookups — loaded once per page load
# ---------------------------------------------------------------------------

try:
    with st.spinner("Loading reference data..."):
        _samples = list_samples_lookup()
        _sp = list_sampling_points_lookup()
        _campaigns = list_campaigns_lookup()
        _parameters = list_parameters_lookup()
        _units = list_units_lookup()
        _processing_kinds = list_processing_kinds_lookup()
        _persons_full = list_persons()
        _persons = [
            {
                "person_id": p["person_id"],
                "label": f"{p.get('first_name') or ''} {p.get('last_name') or ''}".strip()
                         or f"Person {p['person_id']}",
            }
            for p in _persons_full
        ]
        _collection_kinds = list_sample_collection_kinds()
        _equipment = list_equipment_lookup()
        _templates = list_lab_panels()
        _all_series = list_analysis_series_lookup()
        _experiments = list_lab_experiments_lookup()
        _quality_codes = list_quality_codes()
        _qc_label_to_id = {
            f"{qc['name']} — {qc.get('description') or ''}".strip(" —"): qc["quality_code_id"]
            for qc in _quality_codes
            if qc.get("is_usable", True)
        }
        _qc_id_to_label = {v: k for k, v in _qc_label_to_id.items()}
        _qc_labels = list(_qc_label_to_id.keys())
        # Reverse-lookup dicts
        _param_name_to_id = {
            p["parameter_name"]: p["parameter_id"] for p in _parameters
        }
        _unit_name_to_id = {u["unit"]: u["unit_id"] for u in _units}
        _sp_label_to_id = {s["label"]: s["sampling_point_id"] for s in _sp}
        # Default person from authenticated user email
        _current_email = (st.session_state.get("user") or {}).get("email") or ""
        _default_person_id = next(
            (
                p["person_id"]
                for p in _persons_full
                if (p.get("email") or "").lower() == _current_email.lower()
            ),
            None,
        )
except APIError as e:
    st.error(f"Cannot load lookup data: {e.message}")
    st.stop()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

_SESSION_DEFAULTS = {
    "mode": "new",
    "template_id": None,
    "experiment_id": None,
    "name": "",
    "campaign_id": None,
    "datetime": datetime.now(),
    "description": "",
    "created_by_person_id": _default_person_id,
    "series": [],
    "samples": [],
    "measurements": {},
}

if "lab_session" not in st.session_state:
    st.session_state.lab_session = dict(_SESSION_DEFAULTS)


def _reset_form() -> None:
    st.session_state.lab_session = dict(_SESSION_DEFAULTS)


# ---------------------------------------------------------------------------
# Value-kind descriptions
# ---------------------------------------------------------------------------

_VALUE_KIND_LABELS = {1: "Scalar", 2: "Vector", 3: "Matrix", 4: "Image"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auto_series_name(param: str | None, sp_label: str | None) -> str:
    if param and sp_label:
        return f"{param}@{sp_label}"
    return ""


def _series_short_label(s: dict) -> str:
    """Short label for a series tab."""
    pk = ""
    for p in _parameters:
        if p["parameter_id"] == s.get("parameter_id"):
            pk = p.get("parameter_name", "")
            break
    sp_label = ""
    for sp in _sp:
        if sp["sampling_point_id"] == s.get("sampling_point_id"):
            sp_label = sp.get("label", "")
            break
    unit = ""
    for u in _units:
        if u["unit_id"] == s.get("unit_id"):
            unit = u.get("unit", "")
            break
    vk = _VALUE_KIND_LABELS.get(s.get("value_kind_id", 1), "?")
    return f"{pk}@{sp_label} ({unit}, {vk})"




# ---------------------------------------------------------------------------
# Step 1: Experiment
# ---------------------------------------------------------------------------


def _render_experiment_step() -> None:
    sess = st.session_state.lab_session

    col1, col2 = st.columns([1, 3])
    with col1:
        mode = st.radio(
            "Mode",
            options=["New", "From panel", "Add to existing"],
            horizontal=False,
            index=["new", "panel", "existing"].index(sess.get("mode", "new")),
            key="lab_mode",
        )
    _mode_map = {
        "New": "new",
        "From panel": "panel",
        "Add to existing": "existing",
    }
    sess["mode"] = _mode_map.get(mode, "new")

    with col2:
        if sess["mode"] == "panel":
            opts = [{"id": None, "label": "— select —"}] + [
                {
                    "id": t["lab_panel_id"],
                    "label": f"{t['name']} ({t['series_count']} series)",
                }
                for t in _templates
            ]
            sel = st.selectbox(
                "Panel",
                options=[o["label"] for o in opts],
                index=0,
                key="lab_template_sel",
            )
            t_id = next((o["id"] for o in opts if o["label"] == sel), None)
            panel_name = next(
                (t["name"] for t in _templates if t["lab_panel_id"] == t_id), ""
            ) if t_id else ""
            if t_id and t_id != sess.get("template_id"):
                sess["template_id"] = t_id
                # Load template series and defaults
                try:
                    detail = get_lab_panel(t_id)
                    sess["series"] = list(detail.get("series", []))
                    sess["default_sample_collection_kind_id"] = detail.get("default_sample_collection_kind_id")
                    sess["default_sample_equipment_id"] = detail.get("default_sample_equipment_id")
                except APIError:
                    st.warning("Could not load template series.")
                # Auto-populate name from panel + today's date
                from datetime import date as _date
                sess["name"] = f"{panel_name} — {_date.today().strftime('%Y-%m-%d')}"
                st.session_state["lab_exp_name"] = sess["name"]
            sess["experiment_id"] = None

        elif sess["mode"] == "existing":
            opts = [{"id": None, "label": "— select —"}] + [
                {
                    "id": e["lab_experiment_id"],
                    "label": f"{e['name']} ({e.get('experiment_datetime', '')[:10]})",
                }
                for e in _experiments
            ]
            sel = st.selectbox(
                "Experiment",
                options=[o["label"] for o in opts],
                index=0,
                key="lab_existing_exp_sel",
            )
            e_id = next((o["id"] for o in opts if o["label"] == sel), None)
            if e_id and e_id != sess.get("experiment_id"):
                sess["experiment_id"] = e_id
                try:
                    series_list = get_lab_experiment_series(e_id)
                    sess["series"] = list(series_list)
                except APIError:
                    st.warning("Could not load experiment series.")
            elif not e_id:
                sess["experiment_id"] = None
            sess["template_id"] = None

            # Show a read-only summary of the selected experiment
            if sess.get("experiment_id"):
                exp_meta = next(
                    (e for e in _experiments if e["lab_experiment_id"] == sess["experiment_id"]),
                    None,
                )
                if exp_meta:
                    dt_str = str(exp_meta.get("experiment_datetime", ""))[:16]
                    st.info(
                        f"Appending to **{exp_meta['name']}** "
                        f"(ID {exp_meta['lab_experiment_id']}, {dt_str})"
                    )

        else:  # "new"
            sess["template_id"] = None
            sess["experiment_id"] = None

    if sess["mode"] in ("new", "panel"):
        sess["name"] = st.text_input(
            "Experiment name *",
            value=sess.get("name", ""),
            key="lab_exp_name",
        )

        col_c, col_d = st.columns(2)
        with col_c:
            d = st.date_input(
                "Date *", value=sess.get("datetime", datetime.now()), key="lab_exp_date"
            )
        with col_d:
            t = st.time_input("Time *", value=time(12, 0), key="lab_exp_time")
        sess["datetime"] = datetime.combine(d, t)

        sess["description"] = st.text_area(
            "Description",
            value=sess.get("description", ""),
            max_chars=500,
            key="lab_exp_desc",
        )

        person_opts = [{"id": None, "label": "— select —"}] + [
            {"id": p["person_id"], "label": p.get("label", str(p["person_id"]))}
            for p in _persons
        ]
        default_person_idx = next(
            (i for i, o in enumerate(person_opts) if o["id"] == sess.get("created_by_person_id")), 0
        )
        sel_person = st.selectbox(
            "Created by *",
            options=[o["label"] for o in person_opts],
            index=default_person_idx,
            key="lab_exp_person",
        )
        sess["created_by_person_id"] = next(
            (o["id"] for o in person_opts if o["label"] == sel_person), None
        )

    # -- Series manager --
    st.markdown("**Assigned AnalysisSeries**")
    if sess["series"]:
        _render_series_table(sess)
    else:
        st.caption("No series assigned yet. Add at least one below.")

    _render_add_series_row(sess)

    if sess.get("series"):
        with st.popover("💾 Save as panel", use_container_width=False):
            st.caption("Save the current series list as a reusable panel.")
            panel_name = st.text_input(
                "Panel name *",
                value=sess.get("name", ""),
                key="lab_save_panel_name",
            )
            panel_desc = st.text_area("Description (optional)", key="lab_save_panel_desc")
            if st.button("Save", type="primary", key="lab_save_panel_btn"):
                _panel_name = (panel_name or "").strip()
                _panel_desc = (panel_desc or "").strip() or None
                if not _panel_name:
                    st.error("Panel name is required.")
                else:
                    series_ids = [
                        s["analysis_series_id"]
                        for s in sess["series"]
                        if s.get("analysis_series_id")
                    ]
                    try:
                        result = create_lab_panel(
                            {
                                "name": _panel_name,
                                "description": _panel_desc,
                                "series_ids": series_ids,
                            }
                        )
                        st.success(f"Panel saved (ID {result['lab_panel_id']}).")
                    except APIError as e:
                        st.error(f"Failed to save panel: {e.message}")

    with st.popover("➕ Add Lab Series", use_container_width=False):
        st.caption("Create a new AnalysisSeries and add it immediately.")
        col_p, col_sp = st.columns(2)
        with col_p:
            param_names = [p["parameter_name"] for p in _parameters]
            sel_param = st.selectbox(
                "Parameter *", options=param_names, index=None, key="lab_quick_param"
            )
        with col_sp:
            sp_labels = [s["label"] for s in _sp]
            sel_sp = st.selectbox(
                "Sampling point *", options=sp_labels, index=None, key="lab_quick_sp"
            )
        col_u, col_pk = st.columns(2)
        with col_u:
            unit_names = [u["unit"] for u in _units]
            sel_unit = st.selectbox(
                "Unit *", options=unit_names, index=None, key="lab_quick_unit"
            )
        with col_pk:
            vk_opts = {"Scalar": 1, "Vector": 2, "Matrix": 3, "Image": 4}
            sel_vk = st.selectbox(
                "Value kind *",
                options=list(vk_opts.keys()),
                index=0,
                key="lab_quick_vk",
            )
        pk_opts = {
            pk["processing_kind_id"]: pk.get("name", str(pk["processing_kind_id"]))
            for pk in _processing_kinds
        }
        sel_pk_id = st.selectbox(
            "Processing kind",
            options=list(pk_opts.values()),
            index=0,
            key="lab_quick_pk",
        )
        _pk_id_map = {v: k for k, v in pk_opts.items()}
        auto_name = _auto_series_name(sel_param, sel_sp)
        if auto_name:
            st.session_state["lab_quick_series_name"] = auto_name
        series_name = st.text_input("Series name", key="lab_quick_series_name")

        if st.button("Create & Add", type="primary", key="lab_quick_create"):
            param_id = _param_name_to_id.get(sel_param or "")
            sp_id = _sp_label_to_id.get(sel_sp or "")
            unit_id = _unit_name_to_id.get(sel_unit or "")
            vk_id = vk_opts.get(sel_vk, 1)
            pk_id = _pk_id_map.get(sel_pk_id, 1)
            if not (param_id and sp_id and unit_id and series_name):
                st.error("Parameter, sampling point, unit, and name are required.")
            else:
                try:
                    result = create_analysis_series(
                        {
                            "name": series_name,
                            "parameter_id": param_id,
                            "sampling_point_id": sp_id,
                            "unit_id": unit_id,
                            "value_kind_id": vk_id,
                            "processing_kind_id": pk_id,
                        }
                    )
                    new_id = result["analysis_series_id"]
                    sess["series"].append(
                        {
                            "analysis_series_id": new_id,
                            "name": series_name,
                            "parameter_id": param_id,
                            "sampling_point_id": sp_id,
                            "unit_id": unit_id,
                            "value_kind_id": vk_id,
                            "processing_kind_id": pk_id,
                        }
                    )
                    st.success(f"Series {new_id} added.")
                    st.rerun()
                except APIError as e:
                    st.error(f"Create failed: {e.message}")


def _render_series_table(sess: dict) -> None:
    """Display the currently assigned series with remove buttons."""
    for i, s in enumerate(sess["series"]):
        pk = next(
            (
                p["parameter_name"]
                for p in _parameters
                if p["parameter_id"] == s.get("parameter_id")
            ),
            "?",
        )
        sp_label = next(
            (
                sp["label"]
                for sp in _sp
                if sp["sampling_point_id"] == s.get("sampling_point_id")
            ),
            "?",
        )
        unit = next(
            (u["unit"] for u in _units if u["unit_id"] == s.get("unit_id")), "?"
        )
        vk = _VALUE_KIND_LABELS.get(s.get("value_kind_id", 1), "?")
        col_a, col_b, col_c = st.columns([4, 1, 1])
        with col_a:
            st.caption(f"**{s.get('name', '')}** — {pk} @ {sp_label} ({unit}, {vk})")
        with col_b:
            st.caption(f"ID: {s.get('analysis_series_id', '')}")
        with col_c:
            if st.button(
                "🗑️",
                key=f"lab_remove_series_{i}",
                help="Remove series from this session",
            ):
                sess["series"].pop(i)
                # Also clean up any measurements for this series index
                if str(i) in sess["measurements"]:
                    del sess["measurements"][str(i)]
                st.rerun()


def _render_add_series_row(sess: dict) -> None:
    """Inline add-series control."""
    already_ids = {
        s["analysis_series_id"] for s in sess["series"] if s.get("analysis_series_id")
    }
    available = [o for o in _all_series if o["analysis_series_id"] not in already_ids]
    if not available:
        return
    opts = [{"id": None, "label": "— select —"}] + [
        {
            "id": a["analysis_series_id"],
            "label": f"{a.get('name', '')} — {a.get('parameter_name', '')} @ {a.get('sampling_point_label', '')}",
        }
        for a in available
    ]
    sel = st.selectbox(
        "Add existing series",
        options=[o["label"] for o in opts],
        index=0,
        key="lab_add_series_sel",
    )
    s_id = next((o["id"] for o in opts if o["label"] == sel), None)
    if s_id:
        # Find full dict
        found = next((a for a in _all_series if a["analysis_series_id"] == s_id), None)
        if found and s_id not in already_ids:
            sess["series"].append(dict(found))
            st.rerun()


# ---------------------------------------------------------------------------
# Step 2: Sample — one section per unique sampling point in the series list
# ---------------------------------------------------------------------------


def _unique_sps_from_series(sess: dict) -> list[tuple[int, str]]:
    """Return ordered list of (sampling_point_id, label) deduplicated from series."""
    seen: dict[int, str] = {}
    for s in sess.get("series", []):
        sp_id = s.get("sampling_point_id")
        if sp_id and sp_id not in seen:
            label = next(
                (sp["label"] for sp in _sp if sp["sampling_point_id"] == sp_id),
                f"SP {sp_id}",
            )
            seen[sp_id] = label
    return list(seen.items())


def _render_sample_step() -> None:
    sess = st.session_state.lab_session

    unique_sps = _unique_sps_from_series(sess)
    if not unique_sps:
        st.caption("Assign series in Step 1 to enable sample creation.")
        return

    # Sync sess["samples"] to match current unique SPs (preserve resolved entries)
    existing_by_sp: dict[int, dict] = {
        e["sampling_point_id"]: e for e in sess.get("samples", [])
    }
    sess["samples"] = [
        existing_by_sp.get(sp_id) or {"sampling_point_id": sp_id, "label": label, "sample_id": None}
        for sp_id, label in unique_sps
    ]

    for sp_idx, sample_entry in enumerate(sess["samples"]):
        sp_label = sample_entry["label"]
        resolved = sample_entry.get("sample_id") is not None
        header = f"{'✅' if resolved else '○'} Sample — **{sp_label}**"
        with st.expander(header, expanded=not resolved):
            _render_sp_sample_section(sess, sample_entry, sp_idx)


def _render_sp_sample_section(sess: dict, sample_entry: dict, sp_idx: int) -> None:
    sp_id = sample_entry["sampling_point_id"]
    sp_label = sample_entry["label"]

    if sample_entry.get("sample_id"):
        st.success(f"Sample ID: **{sample_entry['sample_id']}**")
        if st.button("Change", key=f"lab_sp_change_{sp_idx}"):
            sample_entry["sample_id"] = None
            st.rerun()
        return

    mode_key = f"lab_sp_mode_{sp_idx}"
    sample_mode = st.radio(
        "Mode",
        ["Create new sample", "Use existing sample"],
        horizontal=True,
        label_visibility="collapsed",
        key=mode_key,
    )

    if sample_mode == "Use existing sample":
        opts = [{"id": None, "label": "— none —"}] + [
            {"id": s["sample_id"], "label": s["label"]} for s in _samples
        ]
        sel = st.selectbox(
            "Select sample",
            options=[o["label"] for o in opts],
            index=0,
            key=f"lab_sp_existing_{sp_idx}",
        )
        chosen_id = next((o["id"] for o in opts if o["label"] == sel), None)
        if st.button("Use this sample", key=f"lab_sp_use_{sp_idx}", disabled=chosen_id is None):
            sample_entry["sample_id"] = chosen_id
            st.rerun()
        return

    # --- Create new sample ---
    st.caption(f"Sampling point: **{sp_label}**")

    ck_opts = [{"id": None, "label": "— none —"}] + [
        {"id": c.get("sample_collection_kind_id") or c.get("id"), "label": c.get("name", str(c))}
        for c in _collection_kinds
    ]
    default_ck_id = sess.get("default_sample_collection_kind_id")
    default_ck_idx = next((i for i, o in enumerate(ck_opts) if o["id"] == default_ck_id), 0)
    sel_ck = st.selectbox(
        "Collection kind",
        options=[o["label"] for o in ck_opts],
        index=default_ck_idx,
        key=f"lab_sp_ck_{sp_idx}",
    )
    ck_id = next((o["id"] for o in ck_opts if o["label"] == sel_ck), None)

    eq_opts = [{"id": None, "label": "— none —"}] + [
        {"id": e.get("equipment_id") or e.get("id"), "label": e.get("identifier", str(e))}
        for e in _equipment
    ]
    default_eq_id = sess.get("default_sample_equipment_id")
    default_eq_idx = next((i for i, o in enumerate(eq_opts) if o["id"] == default_eq_id), 0)
    sel_eq = st.selectbox(
        "Equipment",
        options=[o["label"] for o in eq_opts],
        index=default_eq_idx,
        key=f"lab_sp_eq_{sp_idx}",
    )
    eq_id = next((o["id"] for o in eq_opts if o["label"] == sel_eq), None)

    col_a, col_b = st.columns(2)
    with col_a:
        start_date = st.date_input("Start date *", value=datetime.now(), key=f"lab_sp_sd_{sp_idx}")
        start_time = st.time_input("Start time *", value=time(12, 0), key=f"lab_sp_st_{sp_idx}")
        sample_start = datetime.combine(start_date, start_time)
    with col_b:
        end_date = st.date_input("End date (optional)", value=None, key=f"lab_sp_ed_{sp_idx}")
        end_time = st.time_input("End time (optional)", value=None, key=f"lab_sp_et_{sp_idx}")
        sample_end = datetime.combine(end_date, end_time) if end_date and end_time else None

    person_opts = [{"id": None, "label": "— none —"}] + [
        {"id": p["person_id"], "label": p.get("label", str(p["person_id"]))} for p in _persons
    ]
    sel_person = st.selectbox(
        "Sampled by",
        options=[o["label"] for o in person_opts],
        index=0,
        key=f"lab_sp_person_{sp_idx}",
    )
    sampled_by_id = next((o["id"] for o in person_opts if o["label"] == sel_person), None)

    description = st.text_area(
        "Description (optional)", max_chars=500, key=f"lab_sp_desc_{sp_idx}"
    )

    if st.button("Create Sample", type="secondary", key=f"lab_sp_create_{sp_idx}"):
        try:
            result = create_sample(
                {
                    "sampling_point_id": sp_id,
                    "campaign_id": sess.get("campaign_id"),
                    "sample_datetime_start": sample_start.isoformat(),
                    "sample_datetime_end": sample_end.isoformat() if sample_end else None,
                    "sample_collection_kind_id": ck_id,
                    "sample_equipment_id": eq_id,
                    "description": description or None,
                    "sampled_by_person_id": sampled_by_id,
                }
            )
            sample_entry["sample_id"] = result["sample_id"]
            st.success(f"Sample {result['sample_id']} created.")
            st.rerun()
        except APIError as e:
            st.error(f"Failed to create sample: {e.message}")


# ---------------------------------------------------------------------------
# Step 3: Measurement Values
# ---------------------------------------------------------------------------


def _render_measurement_step() -> None:
    sess = st.session_state.lab_session
    series = sess.get("series", [])

    if not series:
        st.caption(
            "Assign at least one AnalysisSeries in Step 1 before entering measurements."
        )
        return

    unique_sp_ids = {s.get("sampling_point_id") for s in series if s.get("sampling_point_id")}
    resolved_sp_ids = {
        e["sampling_point_id"] for e in sess.get("samples", []) if e.get("sample_id")
    }
    missing = unique_sp_ids - resolved_sp_ids
    if missing:
        missing_labels = [
            next((sp["label"] for sp in _sp if sp["sampling_point_id"] == m), f"SP {m}")
            for m in missing
        ]
        st.caption(f"Create samples for: {', '.join(missing_labels)}")
        return

    tab_labels = [_series_short_label(s) for s in series]
    tabs = st.tabs(tab_labels)

    for i, tab in enumerate(tabs):
        with tab:
            _render_series_tab(sess, series[i], i)


def _render_series_tab(sess: dict, series_item: dict, idx: int) -> None:
    """Render one tab: data editor for measurements of a single series."""
    s_key = str(idx)

    # Ensure measurements list exists for this series
    if s_key not in sess["measurements"]:
        sess["measurements"][s_key] = []

    rows = sess["measurements"][s_key]
    vk = series_item.get("value_kind_id", 1)

    # Show series identity
    pk = next(
        (
            p["parameter_name"]
            for p in _parameters
            if p["parameter_id"] == series_item.get("parameter_id")
        ),
        "?",
    )
    unit = next(
        (u["unit"] for u in _units if u["unit_id"] == series_item.get("unit_id")),
        "?",
    )
    st.caption(
        f"**{series_item.get('name', '')}** — {pk}  |  Unit: {unit}  |  "
        f"Kind: {_VALUE_KIND_LABELS.get(vk, '?')}"
    )

    if vk == 4:  # Image — different handling
        _render_image_tab(sess, series_item, idx)
        return

    editor_key = f"lab_measure_editor_{idx}"

    # Column config for the data editor
    col_config = {
        "value": st.column_config.NumberColumn("Value *", required=True, default=None),
        "replicate": st.column_config.NumberColumn("Replicate", default=1, min_value=1),
        "quality_code_id": st.column_config.SelectboxColumn(
            "Quality Code", options=_qc_labels, default=None, required=False,
        ),
        "notes": st.column_config.TextColumn("Notes"),
    }
    if vk in (2, 3):
        col_config["value"] = st.column_config.TextColumn(
            "Value *",
            required=True,
            default=None,
        )

    is_scalar = vk == 1

    # For scalar series: explicit Add Row button with auto-incrementing replicate.
    # Clears the editor key so the new row is seeded from session on next render.
    if is_scalar:
        next_rep = max((r.get("replicate") or 0 for r in rows), default=0) + 1
        if st.button("+ Add row", key=f"lab_add_row_{idx}"):
            rows.append({"value": None, "replicate": next_rep, "quality_code_id": None, "notes": None})
            st.session_state.pop(editor_key, None)
            st.rerun()

    # Seed the editor from session on first render (or after Add Row reset).
    # Passing an empty schema df ensures the key-stored DataFrame drives the content.
    base_df = pd.DataFrame(columns=["value", "replicate", "quality_code_id", "notes"])
    if editor_key not in st.session_state and rows:
        st.session_state[editor_key] = pd.DataFrame(rows)

    edited = st.data_editor(
        base_df,
        column_config=col_config,
        use_container_width=True,
        num_rows="fixed" if is_scalar else "dynamic",
        key=editor_key,
    )

    # Sync back to session
    if not edited.empty:
        edited = edited.dropna(how="all")
        sess["measurements"][s_key] = edited.to_dict("records")
    else:
        sess["measurements"][s_key] = []


def _render_image_tab(sess: dict, _series_item: dict, idx: int) -> None:
    """Simple image upload for Image value-kind series."""
    uploaded = st.file_uploader(
        "Select image file(s)",
        type=["jpg", "jpeg", "png", "tif", "tiff", "bmp"],
        accept_multiple_files=True,
        key=f"lab_img_upload_{idx}",
    )

    if uploaded:
        st.caption(f"{len(uploaded)} file(s) selected — replicate 1…{len(uploaded)}")
        cols = st.columns(min(len(uploaded), 4))
        for i_, f_ in enumerate(uploaded):
            with cols[i_ % 4]:
                st.image(f_, caption=f_.name, width=120)

        sess["measurements"][str(idx)] = [
            {"file": f_, "replicate": i_ + 1} for i_, f_ in enumerate(uploaded)
        ]


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


def _render_submit() -> None:
    sess = st.session_state.lab_session

    if not sess.get("series"):
        st.button(
            "Submit", disabled=True, help="Assign at least one AnalysisSeries first."
        )
        return
    _unique_sp_ids = {s.get("sampling_point_id") for s in sess.get("series", []) if s.get("sampling_point_id")}
    _resolved_sp_ids = {e["sampling_point_id"] for e in sess.get("samples", []) if e.get("sample_id")}
    if not _unique_sp_ids.issubset(_resolved_sp_ids):
        st.button("Submit", disabled=True, help="Create samples for all sampling points first.")
        return

    total_measurements = sum(len(v) for v in sess["measurements"].values())
    st.caption(
        f"Ready: {len(sess['series'])} series, {total_measurements} measurement row(s)."
    )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        submitted = st.button(
            "✅  Submit Experiment", type="primary", use_container_width=True
        )
    with col_b:
        st.button("🔄  Clear form", on_click=_reset_form, use_container_width=True)

    if submitted:
        _do_submit(sess)


def _do_submit(sess: dict) -> None:
    """Build LabIngestRequest and call the API."""
    if sess["mode"] in ("new", "panel") and not sess.get("name"):
        st.error("Experiment name is required.")
        return

    if sess["mode"] == "existing" and not sess.get("experiment_id"):
        st.error("Select an experiment to append to.")
        return

    measurements = []
    for s_key, rows in sess["measurements"].items():
        try:
            idx = int(s_key)
        except (ValueError, TypeError):
            continue
        if idx >= len(sess["series"]):
            continue
        series_item = sess["series"][idx]

        sp_id = series_item.get("sampling_point_id")
        sample_entry = next(
            (e for e in sess.get("samples", []) if e["sampling_point_id"] == sp_id), None
        )
        sample_id = sample_entry["sample_id"] if sample_entry else None

        for row in rows:
            if row.get("file"):
                # Image row — handled separately
                continue
            value = row.get("value")
            vk = series_item.get("value_kind_id", 1)
            measurements.append(
                {
                    "parameter_id": series_item["parameter_id"],
                    "sampling_point_id": sp_id,
                    "unit_id": series_item["unit_id"],
                    "value_kind_id": vk,
                    "processing_kind_id": series_item.get("processing_kind_id", 1),
                    "series_name": series_item.get("name", ""),
                    "sample_id": sample_id,
                    "value": value,
                    "replicate": row.get("replicate", 1),
                    "quality_code_id": _qc_label_to_id.get(row.get("quality_code_id")) if row.get("quality_code_id") else None,
                    "notes": row.get("notes"),
                }
            )

    if not measurements:
        st.error("No scalar/vector/matrix measurements to submit.")
        return

    if sess["mode"] == "existing":
        # Append to existing experiment — only pass experiment_id and measurements
        payload: dict = {
            "experiment_id": sess["experiment_id"],
            "measurements": measurements,
        }
    else:
        exp_name = sess.get("name", "")
        payload = {
            "name": exp_name or f"Lab-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "experiment_datetime": sess.get("datetime", datetime.now()).isoformat(),
            "campaign_id": sess.get("campaign_id"),
            "description": sess.get("description") or None,
            "created_by_person_id": sess.get("created_by_person_id"),
            "lab_panel_id": sess.get("template_id") if sess["mode"] == "panel" else None,
            "measurements": measurements,
        }

    try:
        with st.spinner("Submitting..."):
            result = ingest_lab(payload)
        action_word = "updated" if sess["mode"] == "existing" else "created"
        st.success(
            f"Experiment **{result['lab_experiment_id']}** {action_word} — "
            f"{result['rows_written']} observation(s) stored."
        )
    except APIError as e:
        st.error(f"Ingest failed: {e.message}")

    # Handle image uploads separately
    for s_key, rows in sess["measurements"].items():
        try:
            idx = int(s_key)
        except (ValueError, TypeError):
            continue
        if idx >= len(sess["series"]):
            continue
        series_item = sess["series"][idx]
        if series_item.get("value_kind_id") != 4:
            continue
        image_rows = [r for r in rows if r.get("file")]
        if not image_rows:
            continue

        image_files = [(r["file"].name, r["file"].read()) for r in image_rows]
        _img_sp_id = series_item.get("sampling_point_id")
        _img_sample_entry = next(
            (e for e in sess.get("samples", []) if e["sampling_point_id"] == _img_sp_id), None
        )
        _img_sample_id = _img_sample_entry["sample_id"] if _img_sample_entry else None
        try:
            with st.spinner("Uploading images..."):
                result_img = ingest_lab_image(
                    name=payload["name"],
                    experiment_datetime=payload["experiment_datetime"],
                    sample_id=_img_sample_id,
                    parameter_id=series_item["parameter_id"],
                    sampling_point_id=series_item["sampling_point_id"],
                    unit_id=series_item["unit_id"],
                    series_name=series_item.get("name", ""),
                    image_files=image_files,
                    processing_kind_id=series_item.get("processing_kind_id", 1),
                    campaign_id=sess.get("campaign_id"),
                    description=sess.get("description") or None,
                    created_by_person_id=sess.get("created_by_person_id"),
                    quality_code=None,
                    notes=None,
                )
            st.success(
                f"✅ {result_img['rows_written']} image(s) stored. "
                f"Experiment ID: {result_img['lab_experiment_id']}"
            )
            for path in result_img.get("storage_paths", []):
                st.caption(f"Stored at: {path}")
        except APIError as e:
            st.error(f"Image upload failed: {e.message}")


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

st.title("Lab Analysis Ingest")
st.markdown("Record laboratory analysis results. Expand each section, then submit.")

_sess = st.session_state.lab_session
if _sess.get("mode", "new") != "existing":
    _camp_opts = [{"id": None, "label": "— none —"}] + [
        {"id": c["campaign_id"], "label": c["name"]} for c in _campaigns
    ]
    _sel_camp = st.selectbox(
        "Campaign",
        options=[o["label"] for o in _camp_opts],
        index=next((i for i, o in enumerate(_camp_opts) if o["id"] == _sess.get("campaign_id")), 0),
        key="lab_top_campaign",
    )
    _sess["campaign_id"] = next((o["id"] for o in _camp_opts if o["label"] == _sel_camp), None)

with st.expander("**1. Experiment**", expanded=True):
    _render_experiment_step()

with st.expander(
    "**2. Sample**",
    expanded=bool(st.session_state.lab_session.get("series")),
):
    _render_sample_step()

with st.expander(
    "**3. Measurement Values**",
    expanded=any(e.get("sample_id") for e in st.session_state.lab_session.get("samples", [])),
):
    _render_measurement_step()

st.divider()
_render_submit()
