"""Lab Analysis Ingest page — compact header + wide measurement grid.

One Results grid per sampling point: sample-description columns on the left,
one value column per assigned (non-image) AnalysisSeries on the right. Samples
are created automatically at submit time from populated rows — rows sharing a
sample name become replicates of one Sample, so nothing links a value to its
sample by hand. Image-kind series still use a separate per-sampling-point
sample step + upload tab (D3 in .tasks/lab_wide_table_plan.md).

Uses the LabIngestRequest / LabImageIngestResponse API.
"""

from __future__ import annotations

import sys
from datetime import datetime, time, timezone
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore[no-retype]


def _lab_timezone_selector(key: str) -> zoneinfo.ZoneInfo:
    """Show the browser's timezone (read-only) and record it under ``key``.

    The experiment happens where the user is, so the zone is inferred from the
    browser (``st.context.timezone``) rather than picked — one less thing to get
    wrong. The name is stored in session_state so the UTC conversion downstream
    keeps working.
    """
    tz_name = st.context.timezone or "UTC"
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:  # unknown/legacy zone name → safe default
        tz_name, tz = "UTC", zoneinfo.ZoneInfo("UTC")
    st.session_state[key] = tz_name
    st.text_input(
        "Timezone",
        value=tz_name,
        disabled=True,
        help="Timezone inferred from your browser. Timestamps are converted to UTC on submit.",
    )
    return tz

from app.components.labels import NONE_LABEL
from app.components.kind_select import kind_options, kind_select, select_or_none
from app.components.param_unit import unit_select
from app.components.schema_registry import describe, describe_table
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
    list_quality_codes,
    list_sample_collection_kinds,
    list_sample_kind_lookup,
    list_sample_material_kind_lookup,
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
        _sample_kinds = list_sample_kind_lookup()
        _material_kinds = list_sample_material_kind_lookup()
        _equipment = list_equipment_lookup()
        # Panels are scoped to the selected campaign's sampling locations
        # (derived — panels have no Campaign_ID). Read the persisted campaign
        # here at fetch time; the campaign selectbox triggers a rerun, so the
        # next run reflects a fresh selection. A "show all" toggle bypasses it.
        _panel_campaign_id = None if st.session_state.get("lab_panels_show_all") else (
            (st.session_state.get("lab_session") or {}).get("campaign_id")
        )
        _templates = list_lab_panels(campaign_id=_panel_campaign_id)
        _all_series = list_analysis_series_lookup()
        _experiments = list_lab_experiments_lookup()
        _quality_codes = list_quality_codes()
        _qc_label_to_id = {
            f"{qc['name']} — {qc.get('description') or ''}".strip(" —"): qc["quality_code_id"]
            for qc in _quality_codes
            if qc.get("is_usable", True)
        }
        _qc_labels = list(_qc_label_to_id.keys())
        # Reverse-lookup dicts
        _param_name_to_id = {
            p["parameter_name"]: p["parameter_id"] for p in _parameters
        }
        _sp_label_to_id = {s["label"]: s["sampling_point_id"] for s in _sp}
        _ck_label_to_id = {
            c.get("name", ""): (c.get("sample_collection_kind_id") or c.get("id"))
            for c in _collection_kinds
        }
        _sk_name_to_id = {
            k.get("name", ""): k.get("sample_kind_id") for k in _sample_kinds
        }
        _mk_name_to_id = {
            m.get("name", ""): m.get("sample_material_kind_id") for m in _material_kinds
        }
        _eq_label_to_id = {
            e.get("identifier", ""): (e.get("equipment_id") or e.get("id"))
            for e in _equipment
        }
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
    "datetime": datetime.now(timezone.utc),
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
    # Results grid seeds live outside lab_session — purge them too
    # (mirrors binning_axes.py's "Cancel" cleanup).
    for k in list(st.session_state.keys()):
        if str(k).startswith("lab_grid_"):
            del st.session_state[k]


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


def _has_value(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    try:
        if pd.isna(v):  # covers float NaN and pd.NaT (datetime columns coerce to NaT)
            return False
    except (TypeError, ValueError):
        pass
    return True


def _localize_to_utc(dt) -> str | None:
    """Convert a data_editor DatetimeColumn cell to a UTC ISO string.

    Cells come back tz-naive; treat them as being in the browser timezone
    captured by the header's TZ field (same assumption the old per-sample
    date/time inputs made).
    """
    if not _has_value(dt):
        return None
    if hasattr(dt, "to_pydatetime"):
        dt = dt.to_pydatetime()
    if dt.tzinfo is None:
        tz_name = st.session_state.get("lab_exp_tz") or "UTC"
        dt = dt.replace(tzinfo=zoneinfo.ZoneInfo(tz_name))
    return dt.astimezone(timezone.utc).isoformat()




# ---------------------------------------------------------------------------
# Step 1: Experiment
# ---------------------------------------------------------------------------


def _render_header() -> None:
    """Compact header: mode, campaign, panel/experiment picker, experiment
    identity fields, and series assignment.

    Replaces the old "1. Experiment" expander (Phase 1 of the wide-table
    redesign, .tasks/lab_wide_table_plan.md) — same widget keys and logic,
    laid out in columns instead of a full-width accordion section.
    """
    sess = st.session_state.lab_session

    col1, col_camp, col2 = st.columns([1, 1, 2])
    with col1:
        mode = st.radio(
            "Mode",
            options=["New", "From panel", "Add to existing"],
            horizontal=False,
            index=["new", "panel", "existing"].index(sess.get("mode", "new")),
            key="lab_mode",
            help="Where this session's series and identity come from: 'New' starts "
            "with an empty series list, 'From panel' pre-fills it from a saved "
            "panel, and 'Add to existing' hides the identity fields and appends "
            "the measurements to an experiment that already exists.",
        )
    _mode_map = {
        "New": "new",
        "From panel": "panel",
        "Add to existing": "existing",
    }
    sess["mode"] = _mode_map.get(mode, "new")

    with col_camp:
        if sess["mode"] != "existing":
            _camp_opts = [{"id": None, "label": NONE_LABEL}] + [
                {"id": c["campaign_id"], "label": c["name"]} for c in _campaigns
            ]
            _sel_camp = st.selectbox(
                "Campaign",
                options=[o["label"] for o in _camp_opts],
                index=next(
                    (i for i, o in enumerate(_camp_opts) if o["id"] == sess.get("campaign_id")), 0
                ),
                key="lab_top_campaign",
                help=describe("LabExperiment", "campaign_id"),
            )
            sess["campaign_id"] = next(
                (o["id"] for o in _camp_opts if o["label"] == _sel_camp), None
            )

    with col2:
        if sess["mode"] == "panel":
            opts = [{"id": None, "label": NONE_LABEL}] + [
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
                help=describe("LabExperiment", "lab_panel_id"),
            )
            if sess.get("campaign_id"):
                st.checkbox(
                    "Show panels from all campaigns",
                    key="lab_panels_show_all",
                    help="Panels are reusable across campaigns. By default only "
                    "panels with a series at this campaign's sampling locations "
                    "are listed; tick to browse every panel.",
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
                    sess["default_sample_kind_id"] = detail.get("default_sample_kind_id")
                    sess["default_sample_material_kind_id"] = detail.get("default_sample_material_kind_id")
                except APIError:
                    st.warning("Could not load template series.")
                # Auto-populate name from panel + today's date
                from datetime import date as _date
                sess["name"] = f"{panel_name} — {_date.today().strftime('%Y-%m-%d')}"
                st.session_state["lab_exp_name"] = sess["name"]
            sess["experiment_id"] = None

        elif sess["mode"] == "existing":
            opts = [{"id": None, "label": NONE_LABEL}] + [
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
                help="The already-recorded lab experiment these measurements are "
                "appended to. Its series list is loaded below and no new experiment "
                "is created on submit.",
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
        if "lab_exp_name" not in st.session_state:
            st.session_state["lab_exp_name"] = sess.get("name", "")
        sess["name"] = st.text_input(
            "Experiment name *",
            key="lab_exp_name",
            help=describe("LabExperiment", "name"),
        )

        _exp_dt_help = describe("LabExperiment", "experiment_date_time")
        col_c, col_d, col_tz = st.columns([2, 2, 1])
        with col_c:
            d = st.date_input(
                "Date *",
                value=sess.get("datetime", datetime.now(timezone.utc)),
                key="lab_exp_date",
                help=_exp_dt_help,
            )
        with col_d:
            t = st.time_input(
                "Time *", value=time(12, 0), key="lab_exp_time", help=_exp_dt_help
            )
        with col_tz:
            lab_source_tz = _lab_timezone_selector(key="lab_exp_tz")
        sess["datetime"] = datetime.combine(d, t).replace(tzinfo=lab_source_tz).astimezone(timezone.utc)

        sess["description"] = st.text_area(
            "Description",
            value=sess.get("description", ""),
            max_chars=500,
            key="lab_exp_desc",
            help=describe("LabExperiment", "description"),
        )

        person_opts = [{"id": None, "label": NONE_LABEL}] + [
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
            help=describe("LabExperiment", "created_by_person_id"),
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
                help=describe("LabPanel", "name"),
            )
            panel_desc = st.text_area(
                "Description (optional)",
                key="lab_save_panel_desc",
                help=describe("LabPanel", "description"),
            )
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
            sel_param = select_or_none(
                "Parameter *",
                param_names,
                key="lab_quick_param",
                help=describe("AnalysisSeries", "parameter_id"),
            )
        with col_sp:
            sp_labels = [s["label"] for s in _sp]
            sel_sp = select_or_none(
                "Sampling point *",
                sp_labels,
                key="lab_quick_sp",
                help=describe("AnalysisSeries", "sampling_point_id"),
            )
        col_u, col_vk = st.columns(2)
        with col_u:
            unit_id = unit_select(
                "Unit *",
                parameter_id=_param_name_to_id.get(sel_param or ""),
                all_units=_units,
                key="lab_quick_unit",
                help=describe("AnalysisSeries", "unit_id"),
            )
        with col_vk:
            vk_opts = {"Scalar": 1, "Vector": 2, "Matrix": 3, "Image": 4}
            sel_vk = st.selectbox(
                "Value kind *",
                options=list(vk_opts.keys()),
                index=0,
                key="lab_quick_vk",
                help=describe("AnalysisSeries", "value_kind_id"),
            )
        auto_name = _auto_series_name(sel_param, sel_sp)
        if auto_name:
            st.session_state["lab_quick_series_name"] = auto_name
        series_name = st.text_input(
            "Series name",
            key="lab_quick_series_name",
            help=describe("AnalysisSeries", "name"),
        )

        if st.button("Create & Add", type="primary", key="lab_quick_create"):
            param_id = _param_name_to_id.get(sel_param or "")
            sp_id = _sp_label_to_id.get(sel_sp or "")
            vk_id = vk_opts.get(sel_vk, 1)
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
    series_ids = {
        f"{a.get('name', '')} — {a.get('parameter_name', '')} @ {a.get('sampling_point_label', '')}": a[
            "analysis_series_id"
        ]
        for a in available
    }
    sel = select_or_none(
        "Add existing series",
        list(series_ids),
        key="lab_add_series_sel",
        help=describe_table("AnalysisSeries"),
    )
    s_id = series_ids.get(sel or "")
    if s_id:
        # Find full dict
        found = next((a for a in _all_series if a["analysis_series_id"] == s_id), None)
        if found and s_id not in already_ids:
            sess["series"].append(dict(found))
            st.rerun()


# ---------------------------------------------------------------------------
# Wide grid — one row per sample, one column per (non-image) assigned series,
# grouped by sampling point (D1). Samples are created automatically at
# submit time from populated rows — see _build_grid_measurements.
# ---------------------------------------------------------------------------


def _grid_groups(sess: dict) -> dict[int, list[dict]]:
    """Non-image series grouped by sampling point, in first-seen order."""
    groups: dict[int, list[dict]] = {}
    for s in _grid_series(sess):
        sp_id = s.get("sampling_point_id")
        if sp_id is not None:
            groups.setdefault(sp_id, []).append(s)
    return groups


def _grid_value_columns(series_list: list[dict]) -> dict[str, dict]:
    """Map data_editor column key -> series dict, for a group's value columns."""
    return {f"val_{s['analysis_series_id']}": s for s in series_list}


_SAMPLE_META_DTYPES = {
    "sample_label": "object",
    "sample_kind": "object",
    "sample_material": "object",
    "start": "datetime64[ns]",
    "end": "datetime64[ns]",
    "collection_kind": "object",
    "equipment": "object",
}


def _coerce(df: pd.DataFrame, dtypes: dict[str, str]) -> pd.DataFrame:
    """Coerce ``df`` to the given per-column dtypes.

    An all-`object` DataFrame (what ``pd.DataFrame(columns=...)`` yields, even
    with zero rows) makes Arrow infer STRING, which DatetimeColumn/NumberColumn
    reject. Coercing up front — with or without rows — is what lets the empty
    grid render instead of raising StreamlitAPIException.
    """
    out = df.reindex(columns=list(dtypes.keys()))
    for col, dt in dtypes.items():
        if dt == "datetime64[ns]":
            out[col] = pd.to_datetime(out[col], errors="coerce")
        elif dt == "float64":
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = out[col].astype(object).where(out[col].notna(), None)
    return out


def _grid_dtypes(value_cols: dict[str, dict]) -> dict[str, str]:
    d: dict[str, str] = dict(_SAMPLE_META_DTYPES)
    for col_key, s in value_cols.items():
        d[col_key] = "float64" if s.get("value_kind_id", 1) == 1 else "object"
    d["quality_code"] = "object"
    d["notes"] = "object"
    return d


def _sample_key(row, idx: int):
    """Group rows into physical samples.

    Rows sharing a non-blank sample name are the same sample (replicates); a
    blank name means "this row is its own sample", so it gets a per-row key.
    """
    label = row.get("sample_label")
    if _has_value(label) and str(label).strip():
        return str(label).strip()
    return ("__row__", idx)


def _render_wide_grid() -> dict[int, pd.DataFrame]:
    """Render one results grid per sampling point.

    Returns ``{sp_id: edited_df}`` collected from each ``st.data_editor`` return
    value in this same render — the state flows forward to submit rather than
    being written back into ``lab_session``.
    """
    sess = st.session_state.lab_session
    groups = _grid_groups(sess)
    grid_state: dict[int, pd.DataFrame] = {}
    if not groups:
        st.caption("Assign at least one AnalysisSeries above to enter measurements.")
        return grid_state

    st.subheader("Results")
    st.caption(
        "One row per set of results: describe the sample on the left, type its "
        "measured values on the right. Give the sample a **label** you'd recognise "
        "from your bench notes — two rows sharing a label are treated as replicates "
        "of the same physical sample, and only one sample is recorded. Leave the "
        "label blank and the row stands alone as its own sample."
    )

    for sp_id, series_list in groups.items():
        sp_label = next(
            (sp["label"] for sp in _sp if sp["sampling_point_id"] == sp_id), f"SP {sp_id}"
        )
        st.markdown(f"##### 📍 {sp_label}")
        grid_state[sp_id] = _render_sp_grid(sess, sp_id, series_list)
    return grid_state


def _render_sp_grid(sess: dict, sp_id: int, series_list: list[dict]) -> pd.DataFrame:
    value_cols = _grid_value_columns(series_list)

    seed_key = f"lab_grid_seed_{sp_id}"
    editor_key = f"lab_grid_editor_{sp_id}"
    sig_key = f"lab_grid_sig_{sp_id}"
    dtypes = _grid_dtypes(value_cols)
    col_sig = tuple(dtypes)
    if seed_key not in st.session_state or st.session_state.get(sig_key) != col_sig:
        old = st.session_state.get(seed_key)
        st.session_state[seed_key] = _coerce(
            old if old is not None else pd.DataFrame(), dtypes
        )
        st.session_state[sig_key] = col_sig

    default_ck_label = next(
        (
            c.get("name")
            for c in _collection_kinds
            if (c.get("sample_collection_kind_id") or c.get("id"))
            == sess.get("default_sample_collection_kind_id")
        ),
        None,
    )
    default_eq_label = next(
        (
            e.get("identifier")
            for e in _equipment
            if (e.get("equipment_id") or e.get("id")) == sess.get("default_sample_equipment_id")
        ),
        None,
    )
    default_sk_label = next(
        (
            k.get("name")
            for k in _sample_kinds
            if k.get("sample_kind_id") == sess.get("default_sample_kind_id")
        ),
        None,
    )
    default_material_label = next(
        (
            m.get("name")
            for m in _material_kinds
            if m.get("sample_material_kind_id") == sess.get("default_sample_material_kind_id")
        ),
        None,
    )

    if st.button(
        "➕ Add replicate of last row",
        key=f"lab_grid_dup_{sp_id}",
        help="Copy the last row's sample description forward with empty values — "
        "the quick way to record a second run of the same sample.",
        disabled=st.session_state[seed_key].empty,
    ):
        df = st.session_state[seed_key]
        last = df.iloc[[-1]].copy()
        for col in (*value_cols, "quality_code", "notes"):
            last[col] = None
        st.session_state[seed_key] = pd.concat([df, last], ignore_index=True)
        st.session_state.pop(editor_key, None)
        st.rerun()

    grid_config = {
        "sample_label": st.column_config.TextColumn(
            "Sample label",
            help="Your name for this sample (the bottle or tube ID from your notes). "
            "Reuse the same name on another row to record a replicate of it.",
        ),
        "sample_kind": st.column_config.SelectboxColumn(
            "Sample kind",
            options=[k.get("name", "") for k in _sample_kinds],
            default=default_sk_label,
            help=describe("Sample", "sample_kind_id"),
        ),
        "sample_material": st.column_config.SelectboxColumn(
            "Sample material",
            options=[m.get("name", "") for m in _material_kinds],
            default=default_material_label,
            help=describe("Sample", "sample_material_kind_id"),
        ),
        "start": st.column_config.DatetimeColumn(
            "Start *", required=True, help=describe("Sample", "sample_date_time_start")
        ),
        "end": st.column_config.DatetimeColumn(
            "End", help=describe("Sample", "sample_date_time_end")
        ),
        "collection_kind": st.column_config.SelectboxColumn(
            "Collection kind",
            options=[c.get("name", "") for c in _collection_kinds],
            default=default_ck_label,
            help=describe("Sample", "sample_collection_kind_id"),
        ),
        "equipment": st.column_config.SelectboxColumn(
            "Equipment",
            options=[e.get("identifier", "") for e in _equipment],
            default=default_eq_label,
            help=describe("Sample", "sample_equipment_id"),
        ),
    }
    for col_key, s in value_cols.items():
        pk = next(
            (p["parameter_name"] for p in _parameters if p["parameter_id"] == s.get("parameter_id")),
            "?",
        )
        unit = next((u["unit"] for u in _units if u["unit_id"] == s.get("unit_id")), "?")
        label = f"{pk} ({unit})"
        col_help = f"{describe('Value', 'value')} for {pk}, in {unit}."
        grid_config[col_key] = (
            st.column_config.NumberColumn(label, help=col_help)
            if s.get("value_kind_id", 1) == 1
            else st.column_config.TextColumn(label, help=col_help)
        )
    grid_config["quality_code"] = st.column_config.SelectboxColumn(
        "Quality Code",
        options=_qc_labels,
        default=None,
        help=describe("Value", "quality_code"),
    )
    grid_config["notes"] = st.column_config.TextColumn(
        "Notes", help="Free-text remarks about this result (e.g. dilution, re-run)."
    )

    return st.data_editor(
        st.session_state[seed_key],
        column_config=grid_config,
        use_container_width=True,
        num_rows="dynamic",
        key=editor_key,
    )


# ---------------------------------------------------------------------------
# Image samples — one section per unique sampling point among *image* series
# only (D3: image series stay on the old per-sample-then-upload path; every
# other value kind gets its sample created automatically by the wide grid).
# ---------------------------------------------------------------------------


def _image_series(sess: dict) -> list[dict]:
    return [s for s in sess.get("series", []) if s.get("value_kind_id") == 4]


def _grid_series(sess: dict) -> list[dict]:
    return [s for s in sess.get("series", []) if s.get("value_kind_id") != 4]


def _unique_sps_from_series(series_list: list[dict]) -> list[tuple[int, str]]:
    """Return ordered list of (sampling_point_id, label) deduplicated from series."""
    seen: dict[int, str] = {}
    for s in series_list:
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

    unique_sps = _unique_sps_from_series(_image_series(sess))
    if not unique_sps:
        st.caption(
            "No image series assigned. Samples for other series are created "
            "automatically from the Results grid above."
        )
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
        help="Attach these results to a sample that already exists, or record a new one.",
    )

    if sample_mode == "Use existing sample":
        sample_ids = {s["label"]: s["sample_id"] for s in _samples}
        sel = select_or_none(
            "Select sample",
            list(sample_ids),
            key=f"lab_sp_existing_{sp_idx}",
            help=describe_table("Sample"),
        )
        chosen_id = sample_ids.get(sel or "")
        if st.button("Use this sample", key=f"lab_sp_use_{sp_idx}", disabled=chosen_id is None):
            sample_entry["sample_id"] = chosen_id
            st.rerun()
        return

    # --- Create new sample ---
    st.caption(f"Sampling point: **{sp_label}**")

    ck_id = kind_select(
        "Collection kind",
        kind_options(_collection_kinds, "sample_collection_kind_id"),
        id_field="id",
        name_field="label",
        default_id=sess.get("default_sample_collection_kind_id"),
        allow_empty=True,
        key=f"lab_sp_ck_{sp_idx}",
        help=describe("Sample", "sample_collection_kind_id"),
    )

    eq_names = {
        e.get("identifier", str(e)): e.get("equipment_id") or e.get("id") for e in _equipment
    }
    sel_eq = select_or_none(
        "Equipment",
        list(eq_names),
        key=f"lab_sp_eq_{sp_idx}",
        help=describe("Sample", "sample_equipment_id"),
    )
    eq_id = eq_names.get(sel_eq or "")

    col_a, col_b = st.columns(2)
    with col_a:
        start_date = st.date_input(
            "Start date *",
            value=datetime.now(timezone.utc),
            key=f"lab_sp_sd_{sp_idx}",
            help=describe("Sample", "sample_date_time_start"),
        )
        start_time = st.time_input(
            "Start time *",
            value=time(12, 0),
            key=f"lab_sp_st_{sp_idx}",
            help=describe("Sample", "sample_date_time_start"),
        )
        sample_start = datetime.combine(start_date, start_time)
        if selected_tz_name := st.session_state.get("lab_exp_tz"):
            sample_start = sample_start.replace(tzinfo=zoneinfo.ZoneInfo(selected_tz_name)).astimezone(timezone.utc)
    with col_b:
        end_date = st.date_input(
            "End date (optional)",
            value=None,
            key=f"lab_sp_ed_{sp_idx}",
            help=describe("Sample", "sample_date_time_end"),
        )
        end_time = st.time_input(
            "End time (optional)",
            value=None,
            key=f"lab_sp_et_{sp_idx}",
            help=describe("Sample", "sample_date_time_end"),
        )
        if end_date and end_time:
            sample_end = datetime.combine(end_date, end_time)
            if selected_tz_name := st.session_state.get("lab_exp_tz"):
                sample_end = sample_end.replace(tzinfo=zoneinfo.ZoneInfo(selected_tz_name)).astimezone(timezone.utc)
        else:
            sample_end = None

    person_ids = {p.get("label", str(p["person_id"])): p["person_id"] for p in _persons}
    sel_person = select_or_none(
        "Sampled by",
        list(person_ids),
        key=f"lab_sp_person_{sp_idx}",
        help=describe("Sample", "sampled_by_person_id"),
    )
    sampled_by_id = person_ids.get(sel_person or "")

    description = st.text_area(
        "Description (optional)",
        max_chars=500,
        key=f"lab_sp_desc_{sp_idx}",
        help=describe("Sample", "description"),
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
# Image uploads — one tab per image-kind series (D3: images stay a separate
# upload tab, not a grid cell; all other value kinds go through the wide grid).
# ---------------------------------------------------------------------------


def _render_measurement_step() -> None:
    sess = st.session_state.lab_session
    series = sess.get("series", [])
    image_indices = [i for i, s in enumerate(series) if s.get("value_kind_id") == 4]

    if not image_indices:
        st.caption(
            "No image series assigned. Other measurements are entered in the Results grid above."
        )
        return

    unique_sp_ids = {series[i]["sampling_point_id"] for i in image_indices}
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

    tab_labels = [_series_short_label(series[i]) for i in image_indices]
    tabs = st.tabs(tab_labels)

    for tab, i in zip(tabs, image_indices):
        with tab:
            _render_image_tab(sess, series[i], i)


def _render_image_tab(sess: dict, series_item: dict, idx: int) -> None:
    """Series identity caption + image upload for an Image value-kind series."""
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
        f"Kind: {_VALUE_KIND_LABELS.get(series_item.get('value_kind_id', 1), '?')}"
    )

    uploaded = st.file_uploader(
        "Select image file(s)",
        type=["jpg", "jpeg", "png", "tif", "tiff", "bmp"],
        accept_multiple_files=True,
        key=f"lab_img_upload_{idx}",
        help="One image per sample, in the same order as the samples registered above.",
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


def _build_grid_measurements(
    sess: dict, grid_state: dict[int, pd.DataFrame]
) -> list[dict]:
    """Create a Sample per group of populated grid rows, then build one
    LabMeasurementItem per populated value cell.

    Rows are grouped into samples by ``_sample_key``, so the sample is created
    once for the first populated row that names it and reused by its replicates
    — the replicate number is the row's ordinal within its group, never typed.
    A start-less or rejected sample surfaces its error once, not once per row.
    """
    measurements: list[dict] = []
    for sp_id, series_list in _grid_groups(sess).items():
        value_cols = _grid_value_columns(series_list)
        df = grid_state.get(sp_id)
        if df is None:
            continue

        created: dict[object, int] = {}  # sample key -> created sample_id
        replicates: dict[object, int] = {}
        blocked: set[object] = set()

        for idx, row in enumerate(df.to_dict("records")):
            populated = {k: row.get(k) for k in value_cols if _has_value(row.get(k))}
            if not populated:
                continue
            key = _sample_key(row, idx)
            if key in blocked:
                continue
            label = row.get("sample_label")
            name = str(label).strip() if _has_value(label) else f"row {idx + 1}"
            if key not in created:
                start_iso = _localize_to_utc(row.get("start"))
                if not start_iso:
                    st.error(f"Sample '{name}' has no start time (sampling point {sp_id}).")
                    blocked.add(key)
                    continue
                kind_label = row.get("sample_kind")
                material_label = row.get("sample_material")
                try:
                    result = create_sample(
                        {
                            "sampling_point_id": sp_id,
                            "campaign_id": sess.get("campaign_id"),
                            "sample_datetime_start": start_iso,
                            "sample_datetime_end": _localize_to_utc(row.get("end")),
                            "sample_collection_kind_id": _ck_label_to_id.get(
                                row.get("collection_kind")
                            ),
                            "sample_kind_id": _sk_name_to_id.get(kind_label)
                            if _has_value(kind_label)
                            else None,
                            "sample_material_kind_id": _mk_name_to_id.get(material_label)
                            if _has_value(material_label)
                            else None,
                            "sample_equipment_id": _eq_label_to_id.get(row.get("equipment")),
                            "description": label if _has_value(label) else None,
                            "sampled_by_person_id": sess.get("created_by_person_id"),
                        }
                    )
                except APIError as e:
                    st.error(f"Failed to create sample '{name}': {e.message}")
                    blocked.add(key)
                    continue
                created[key] = result["sample_id"]
            sample_id = created[key]

            replicate = replicates[key] = replicates.get(key, 0) + 1
            qc_label = row.get("quality_code")
            quality_code_id = _qc_label_to_id.get(qc_label) if _has_value(qc_label) else None
            notes = row.get("notes") if _has_value(row.get("notes")) else None
            for col_key, value in populated.items():
                s = value_cols[col_key]
                measurements.append(
                    {
                        "parameter_id": s["parameter_id"],
                        "sampling_point_id": sp_id,
                        "unit_id": s["unit_id"],
                        "value_kind_id": s.get("value_kind_id", 1),
                        "series_name": s.get("name", ""),
                        "sample_id": sample_id,
                        "value": value,
                        "replicate": replicate,
                        "quality_code_id": quality_code_id,
                        "notes": notes,
                    }
                )
    return measurements


def _render_submit(grid_state: dict[int, pd.DataFrame]) -> None:
    sess = st.session_state.lab_session

    if not sess.get("series"):
        st.button(
            "Submit", disabled=True, help="Assign at least one AnalysisSeries first."
        )
        return
    _image_sp_ids = {
        s.get("sampling_point_id") for s in _image_series(sess) if s.get("sampling_point_id")
    }
    _resolved_sp_ids = {e["sampling_point_id"] for e in sess.get("samples", []) if e.get("sample_id")}
    if not _image_sp_ids.issubset(_resolved_sp_ids):
        st.button("Submit", disabled=True, help="Create samples for all image sampling points first.")
        return

    total_grid_rows = sum(len(df.index) for df in grid_state.values())
    total_image_rows = sum(len(v) for v in sess["measurements"].values())
    st.caption(
        f"Ready: {len(sess['series'])} series, {total_grid_rows} measurement row(s), "
        f"{total_image_rows} image row(s)."
    )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        submitted = st.button(
            "✅  Submit Experiment", type="primary", use_container_width=True
        )
    with col_b:
        st.button("🔄  Clear form", on_click=_reset_form, use_container_width=True)

    if submitted:
        _do_submit(sess, grid_state)


def _do_submit(sess: dict, grid_state: dict[int, pd.DataFrame]) -> None:
    """Build LabIngestRequest and call the API."""
    if sess["mode"] in ("new", "panel") and not sess.get("name"):
        st.error("Experiment name is required.")
        return

    if sess["mode"] == "existing" and not sess.get("experiment_id"):
        st.error("Select an experiment to append to.")
        return

    measurements = _build_grid_measurements(sess, grid_state)

    has_images = any(
        r.get("file")
        for rows in sess["measurements"].values()
        for r in rows
    )
    if not measurements and not has_images:
        st.error("No measurements to submit.")
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
            "name": exp_name or f"Lab-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            "experiment_datetime": sess.get("datetime", datetime.now(timezone.utc)).isoformat(),
            "campaign_id": sess.get("campaign_id"),
            "description": sess.get("description") or None,
            "created_by_person_id": sess.get("created_by_person_id"),
            "lab_panel_id": sess.get("template_id") if sess["mode"] == "panel" else None,
            "measurements": measurements,
        }

    if measurements:
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
        if _img_sample_id is None:
            sp_label = series_item.get("sampling_point_label", f"SP {_img_sp_id}")
            st.error(
                f"Cannot upload images for **{series_item.get('name', '')}**: "
                f"no sample was registered for '{sp_label}'. "
                "Add a sample for that sampling point in Step 2 first."
            )
            continue
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
st.markdown("Record laboratory analysis results, then submit.")

_render_header()
st.divider()

_grid_state = _render_wide_grid()

if _image_series(st.session_state.lab_session):
    with st.expander("**Image samples**", expanded=True):
        _render_sample_step()

    with st.expander(
        "**Image uploads**",
        expanded=any(e.get("sample_id") for e in st.session_state.lab_session.get("samples", [])),
    ):
        _render_measurement_step()

st.divider()
_render_submit(_grid_state)
