"""Mapper Engine — S5: upload CSV/XLSX → pick sheet/header/range
→ tag column roles → save/load named config → preview → resolve entities (text → DB ID)
→ preview ingest → submit via the active profile's endpoint.

PRD-3 S1: shell. PRD-3 S2: entity resolution. PRD-3 S3: lab end-to-end.
PRD-3 S4: save/reload named mapping config (PRD-5-compatible shape).
PRD-3 S5: Sensor-CSV profile — thin profile reusing the same engine,
mapping timestamp/tag/parameter/unit/value columns to /ingest/sensor.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import io
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import app.api_client as api
from app.components.resolver import (
    TARGET_LEVELS,
    EntityResolver,
    guess_target_level,
)

# ---------------------------------------------------------------------------
# Profile stub — role vocabulary (S1: hardcoded; S2+ will load from saved profile)
# ---------------------------------------------------------------------------

LAB_ROLES = [
    "(ignore)",
    "sample_datetime",
    "sampling_location",
    "replicate",
    "parameter_value",
]

# Long-format (tidy) lab profile (S6). One row = one measurement; parameter and
# unit come from cells (not the header). Resolves into the same shape as the
# wide profile so the preview/submit pipeline is reused unchanged.
LONG_LAB_ROLES = [
    "(ignore)",
    "sample_datetime",
    "sampling_location",
    "replicate",
    "parameter",
    "unit",
    "value",
]

# Sensor-CSV profile (S5). Each row is one timestamped reading; the tag,
# parameter, and unit columns identify (and auto-create) the channel.
SENSOR_ROLES = [
    "(ignore)",
    "timestamp",
    "tag",
    "parameter",
    "unit",
    "value",
]

# Logbook "Général" profile (PRD-4 S1). One flat journal row → one Event.
# Date(+Heure) → start; Commentaires → notes (+ derived title) and the target
# search source; Conductor → performed-by person. Target is resolved to the
# smallest logical unit by the shared resolver.
LOGBOOK_ROLES = [
    "(ignore)",
    "event_date",
    "event_time",
    "notes",
    "conductor",
]

# Profile registry — maps a profile key to its role vocabulary. The engine is
# profile-agnostic; profiles only supply the role set (and their resolve/submit).
PROFILES = {
    "Lab (wide)": LAB_ROLES,
    "Lab (long)": LONG_LAB_ROLES,
    "Sensor CSV": SENSOR_ROLES,
    "Logbook (Général)": LOGBOOK_ROLES,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_dataframe(
    file_bytes: bytes,
    filename: str,
    sheet_name: str | int = 0,
    header_row: int = 0,
) -> pd.DataFrame:
    """Parse uploaded file into a DataFrame using the given sheet and header."""
    if filename.endswith(".xlsx"):
        return pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=sheet_name,
            header=header_row,
        )
    # CSV — sheet_name is ignored
    return pd.read_csv(io.BytesIO(file_bytes), header=header_row)


def _parse_param_header(header: str) -> tuple[str, str]:
    """Split 'COD (mg/L)' → ('COD', 'mg/L'). Returns (header, '') on no parens."""
    if " (" in header and header.endswith(")"):
        param_part, unit_part = header.split(" (", 1)
        return param_part.strip(), unit_part.rstrip(")").strip()
    return header.strip(), ""


def _resolve_all(
    resolver: EntityResolver,
    role_map: dict[str, str],
    df_data: pd.DataFrame,
) -> dict:
    """Run full entity resolution for column headers and each row's sampling location.

    Returns a dict with:
    - ``col_resolutions``: {col_name → {param, unit, resolved, error}}
    - ``row_resolutions``: list of per-row dicts
    - ``n_resolved``, ``n_unresolved`` counts
    """
    param_value_cols = [c for c, r in role_map.items() if r == "parameter_value"]
    datetime_cols = [c for c, r in role_map.items() if r == "sample_datetime"]
    location_cols = [c for c, r in role_map.items() if r == "sampling_location"]
    replicate_cols = [c for c, r in role_map.items() if r == "replicate"]

    # Resolve column-level entities (parameter + unit per header)
    col_resolutions: dict[str, dict] = {}
    for col in param_value_cols:
        param_text, unit_text = _parse_param_header(col)
        param = resolver.resolve_parameter(param_text)
        unit = resolver.resolve_unit(unit_text) if unit_text else None
        errors = []
        if param is None:
            errors.append(f"parameter '{param_text}' not found")
        if not unit_text:
            errors.append("no unit in header — use 'Name (unit)' format")
        elif unit is None:
            errors.append(f"unit '{unit_text}' not found")
        col_resolutions[col] = {
            "param": param,
            "unit": unit,
            "resolved": param is not None and unit is not None,
            "errors": errors,
        }

    # Resolve row-level entities
    row_resolutions = []
    n_resolved = 0
    n_unresolved = 0

    for idx, row in df_data.iterrows():
        errors: list[str] = []

        # sample_datetime
        dt_val = None
        if datetime_cols:
            raw_dt = row[datetime_cols[0]]
            try:
                dt_val = pd.to_datetime(raw_dt)
                if dt_val.tzinfo is None:
                    dt_val = dt_val.replace(tzinfo=timezone.utc)
            except Exception:
                errors.append(f"cannot parse datetime '{raw_dt}'")

        # sampling_location → sampling_point_id
        sp = None
        sp_text = ""
        if location_cols:
            sp_text = str(row[location_cols[0]])
            sp = resolver.resolve_sampling_point(sp_text)
            if sp is None:
                errors.append(f"sampling point '{sp_text}' not found")

        # replicate
        replicate = 1
        if replicate_cols:
            try:
                replicate = int(row[replicate_cols[0]])
            except Exception:
                pass  # default to 1 silently

        # Per-column values
        values = []
        col_errors: list[str] = []
        for col in param_value_cols:
            cr = col_resolutions[col]
            if not cr["resolved"]:
                col_errors.append(f"column '{col}' unresolved")
                continue
            raw_val = row.get(col)
            try:
                float_val = float(raw_val)
            except (TypeError, ValueError):
                col_errors.append(f"value '{raw_val}' in column '{col}' is not numeric")
                continue
            values.append({
                "col": col,
                "parameter_id": cr["param"]["parameter_id"],
                "parameter_name": cr["param"]["name"],
                "unit_id": cr["unit"]["unit_id"],
                "unit_symbol": cr["unit"].get("symbol", cr["unit"].get("name", "")),
                "value": float_val,
            })

        errors.extend(col_errors)

        row_ok = len(errors) == 0 and dt_val is not None and sp is not None and len(values) > 0

        if row_ok:
            n_resolved += 1
        else:
            n_unresolved += 1

        row_resolutions.append({
            "row_index": int(idx),
            "datetime": dt_val,
            "sampling_point": sp,
            "sp_text": sp_text,
            "replicate": replicate,
            "values": values,
            "errors": errors,
            "ok": row_ok,
        })

    return {
        "col_resolutions": col_resolutions,
        "row_resolutions": row_resolutions,
        "n_resolved": n_resolved,
        "n_unresolved": n_unresolved,
    }


def _resolve_long(
    resolver: EntityResolver,
    role_map: dict[str, str],
    df_data: pd.DataFrame,
) -> dict:
    """Resolve a long-format (tidy) lab table into the SAME shape as
    :func:`_resolve_all`, so the wide-lab preview + submit pipeline is reused
    unchanged. Each row is one measurement: ``parameter`` and ``unit`` come from
    cells (not the header); ``sample_datetime`` / ``sampling_location`` are
    per-row. Resolved (parameter, unit) pairs are registered as synthetic
    "columns" keyed ``"<param> (<unit>)"`` so ``col_resolutions`` matches the
    wide shape consumed downstream.
    """
    datetime_cols = [c for c, r in role_map.items() if r == "sample_datetime"]
    location_cols = [c for c, r in role_map.items() if r == "sampling_location"]
    replicate_cols = [c for c, r in role_map.items() if r == "replicate"]
    parameter_cols = [c for c, r in role_map.items() if r == "parameter"]
    unit_cols = [c for c, r in role_map.items() if r == "unit"]
    value_cols = [c for c, r in role_map.items() if r == "value"]

    col_resolutions: dict[str, dict] = {}
    row_resolutions = []
    n_resolved = 0
    n_unresolved = 0

    for idx, row in df_data.iterrows():
        errors: list[str] = []

        # sample_datetime
        dt_val = None
        if datetime_cols:
            raw_dt = row[datetime_cols[0]]
            try:
                dt_val = pd.to_datetime(raw_dt)
                if dt_val.tzinfo is None:
                    dt_val = dt_val.replace(tzinfo=timezone.utc)
            except Exception:
                errors.append(f"cannot parse datetime '{raw_dt}'")
        else:
            errors.append("no sample_datetime column tagged")

        # sampling_location → sampling_point_id
        sp = None
        sp_text = ""
        if location_cols:
            sp_text = str(row[location_cols[0]])
            sp = resolver.resolve_sampling_point(sp_text)
            if sp is None:
                errors.append(f"sampling point '{sp_text}' not found")
        else:
            errors.append("no sampling_location column tagged")

        # replicate
        replicate = 1
        if replicate_cols:
            try:
                replicate = int(row[replicate_cols[0]])
            except Exception:
                pass  # default to 1 silently

        # parameter → parameter entity
        param = None
        param_text = ""
        if parameter_cols:
            param_text = str(row[parameter_cols[0]]).strip()
            param = resolver.resolve_parameter(param_text)
            if param is None:
                errors.append(f"parameter '{param_text}' not found")
        else:
            errors.append("no parameter column tagged")

        # unit → unit entity
        unit = None
        unit_text = ""
        if unit_cols:
            unit_text = str(row[unit_cols[0]]).strip()
            unit = resolver.resolve_unit(unit_text)
            if unit is None:
                errors.append(f"unit '{unit_text}' not found")
        else:
            errors.append("no unit column tagged")

        # value → numeric
        value = None
        if value_cols:
            raw_val = row[value_cols[0]]
            try:
                value = float(raw_val)
            except (TypeError, ValueError):
                errors.append(f"value '{raw_val}' is not numeric")
        else:
            errors.append("no value column tagged")

        values = []
        if param is not None and unit is not None and value is not None:
            unit_symbol = unit.get("symbol") or unit.get("name", "")
            col_key = f"{param['name']} ({unit_symbol})"
            col_resolutions.setdefault(col_key, {
                "param": param,
                "unit": unit,
                "resolved": True,
                "errors": [],
            })
            values.append({
                "col": col_key,
                "parameter_id": param["parameter_id"],
                "parameter_name": param["name"],
                "unit_id": unit["unit_id"],
                "unit_symbol": unit_symbol,
                "value": value,
            })

        row_ok = (
            len(errors) == 0
            and dt_val is not None
            and sp is not None
            and len(values) > 0
        )
        if row_ok:
            n_resolved += 1
        else:
            n_unresolved += 1

        row_resolutions.append({
            "row_index": int(idx),
            "datetime": dt_val,
            "sampling_point": sp,
            "sp_text": sp_text,
            "replicate": replicate,
            "values": values,
            "errors": errors,
            "ok": row_ok,
        })

    return {
        "col_resolutions": col_resolutions,
        "row_resolutions": row_resolutions,
        "n_resolved": n_resolved,
        "n_unresolved": n_unresolved,
    }


def _resolve_sensor(
    resolver: EntityResolver,
    role_map: dict[str, str],
    df_data: pd.DataFrame,
) -> dict:
    """Resolve a Sensor-CSV table (thin profile, reuses the shared engine).

    Each row is one timestamped reading. The ``parameter`` and ``unit`` cells
    resolve to existing DB entities; the ``tag`` cell is passed through to the
    tagged sensor-ingest endpoint (channels are auto-created server-side).

    Returns the same shape as :func:`_resolve_all`:
    ``row_resolutions`` (per-row dicts), ``n_resolved``, ``n_unresolved``.
    """
    timestamp_cols = [c for c, r in role_map.items() if r == "timestamp"]
    tag_cols = [c for c, r in role_map.items() if r == "tag"]
    parameter_cols = [c for c, r in role_map.items() if r == "parameter"]
    unit_cols = [c for c, r in role_map.items() if r == "unit"]
    value_cols = [c for c, r in role_map.items() if r == "value"]

    row_resolutions = []
    n_resolved = 0
    n_unresolved = 0

    for idx, row in df_data.iterrows():
        errors: list[str] = []

        # timestamp
        ts_val = None
        if timestamp_cols:
            raw_ts = row[timestamp_cols[0]]
            try:
                ts_val = pd.to_datetime(raw_ts)
                if ts_val.tzinfo is None:
                    ts_val = ts_val.replace(tzinfo=timezone.utc)
            except Exception:
                errors.append(f"cannot parse timestamp '{raw_ts}'")
        else:
            errors.append("no timestamp column tagged")

        # tag — free text, passed through (resolved server-side against DAS tags)
        tag = ""
        if tag_cols:
            tag = str(row[tag_cols[0]]).strip()
        if not tag:
            errors.append("missing tag")

        # parameter → parameter entity
        param = None
        param_text = ""
        if parameter_cols:
            param_text = str(row[parameter_cols[0]]).strip()
            param = resolver.resolve_parameter(param_text)
            if param is None:
                errors.append(f"parameter '{param_text}' not found")
        else:
            errors.append("no parameter column tagged")

        # unit → unit entity
        unit = None
        unit_text = ""
        if unit_cols:
            unit_text = str(row[unit_cols[0]]).strip()
            unit = resolver.resolve_unit(unit_text)
            if unit is None:
                errors.append(f"unit '{unit_text}' not found")
        else:
            errors.append("no unit column tagged")

        # value → numeric
        value = None
        if value_cols:
            raw_val = row[value_cols[0]]
            try:
                value = float(raw_val)
            except (TypeError, ValueError):
                errors.append(f"value '{raw_val}' is not numeric")
        else:
            errors.append("no value column tagged")

        row_ok = len(errors) == 0

        if row_ok:
            n_resolved += 1
        else:
            n_unresolved += 1

        row_resolutions.append({
            "row_index": int(idx),
            "timestamp": ts_val,
            "tag": tag,
            "parameter": param,
            "param_text": param_text,
            "unit": unit,
            "unit_text": unit_text,
            "value": value,
            "errors": errors,
            "ok": row_ok,
        })

    return {
        "row_resolutions": row_resolutions,
        "n_resolved": n_resolved,
        "n_unresolved": n_unresolved,
    }


def _build_sensor_payloads(
    row_resolutions: list[dict], das_name: str = ""
) -> list[dict]:
    """Group resolved sensor rows into tagged /ingest/sensor payloads.

    Rows sharing the same (tag, parameter, unit) form one channel; their
    timestamped values are batched into a single payload. Only ``ok`` rows
    are included — unresolved rows are surfaced upstream, never submitted.
    ``das_name`` names the source data-acquisition system (the tag lives under it).
    """
    grouped: dict[tuple, dict] = {}
    for rr in row_resolutions:
        if not rr["ok"]:
            continue
        key = (rr["tag"], rr["parameter"]["parameter_id"], rr["unit"]["unit_id"])
        payload = grouped.get(key)
        if payload is None:
            payload = {
                "das_name": das_name,
                "tag": rr["tag"],
                "channel_kind": "value",
                "parameter_name": rr["parameter"]["name"],
                "unit_name": rr["unit"].get("symbol") or rr["unit"].get("name", ""),
                "strict": False,
                "values": [],
            }
            grouped[key] = payload
        payload["values"].append({
            "timestamp": rr["timestamp"].isoformat(),
            "value": rr["value"],
            "quality_code": None,
        })
    return list(grouped.values())


def _derive_title(notes: str, limit: int = 60) -> str:
    """Derive a short Event title from the comment's first line."""
    first = (notes or "").strip().splitlines()[0] if notes and notes.strip() else ""
    return first[:limit].strip()


def _resolve_logbook(
    resolver: EntityResolver,
    role_map: dict[str, str],
    df_data: pd.DataFrame,
) -> dict:
    """Resolve a "Général" logbook journal (PRD-4 S1) — one Event per row.

    ``event_date`` (+ optional ``event_time``) → start datetime; ``notes`` →
    Event notes (and the text scanned for the target); ``conductor`` → the
    performed-by person. The target is resolved to the *smallest* logical unit
    found in the comment. Rows with no parseable date or no resolvable target
    are flagged (never auto-guessed into a wrong target).

    Returns ``row_resolutions`` / ``n_resolved`` / ``n_unresolved``.
    """
    date_cols = [c for c, r in role_map.items() if r == "event_date"]
    time_cols = [c for c, r in role_map.items() if r == "event_time"]
    notes_cols = [c for c, r in role_map.items() if r == "notes"]
    conductor_cols = [c for c, r in role_map.items() if r == "conductor"]

    row_resolutions = []
    n_resolved = 0
    n_unresolved = 0

    for idx, row in df_data.iterrows():
        errors: list[str] = []

        # start datetime — date (required) combined with optional time
        start_dt = None
        if date_cols:
            raw_d = row[date_cols[0]]
            try:
                start_dt = pd.to_datetime(raw_d)
                if time_cols:
                    raw_t = row[time_cols[0]]
                    if pd.notna(raw_t) and str(raw_t).strip():
                        try:
                            start_dt = pd.to_datetime(f"{start_dt.date()} {raw_t}")
                        except Exception:
                            errors.append(f"cannot parse time '{raw_t}' — using date only")
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
            except Exception:
                start_dt = None
                errors.append(f"cannot parse date '{raw_d}'")
        else:
            errors.append("no event_date column tagged")

        # notes + derived title
        notes = ""
        if notes_cols:
            raw_notes = row[notes_cols[0]]
            notes = "" if pd.isna(raw_notes) else str(raw_notes).strip()
        title = _derive_title(notes)

        # conductor → person (optional FK; unresolved warns, never blocks)
        person = None
        person_text = ""
        if conductor_cols:
            raw_c = row[conductor_cols[0]]
            person_text = "" if pd.isna(raw_c) else str(raw_c).strip()
            if person_text:
                person = resolver.resolve_person(person_text)
                if person is None:
                    errors.append(f"conductor '{person_text}' not matched — left unset")

        # target → smallest logical unit named in the comment
        target = resolver.resolve_target(notes)
        if target is None:
            errors.append("no target resolved from comment — pick one before submit")

        # A row submits when it has a start time and a target. Unmatched
        # conductor is a soft warning (person FK is optional), so it does not
        # block — but it is still surfaced in errors above.
        blocking = (start_dt is None) or (target is None)
        row_ok = not blocking

        if row_ok:
            n_resolved += 1
        else:
            n_unresolved += 1

        row_resolutions.append({
            "row_index": int(idx),
            "start_datetime": start_dt,
            "notes": notes,
            "title": title,
            "person": person,
            "person_text": person_text,
            "target": target,
            "errors": errors,
            "ok": row_ok,
        })

    return {
        "row_resolutions": row_resolutions,
        "n_resolved": n_resolved,
        "n_unresolved": n_unresolved,
    }


def _build_event_payloads(
    row_resolutions: list[dict], event_kind_id: int
) -> list[dict]:
    """Build one EventIn payload per resolved logbook row.

    Each payload sets exactly one exclusive-arc target FK (from the resolved
    target's ``arc_field``), so it satisfies EventIn's one-target invariant.
    Only ``ok`` rows are included — flagged rows are surfaced, never submitted.
    """
    payloads = []
    for rr in row_resolutions:
        if not rr["ok"]:
            continue
        target = rr["target"]
        payload = {
            "event_kind_id": event_kind_id,
            "is_instantaneous": True,
            "start_datetime": rr["start_datetime"].isoformat(),
            "notes": rr["notes"] or None,
            target["arc_field"]: target["entity_id"],
        }
        if rr["person"]:
            payload["performed_by_person_id"] = rr["person"]["person_id"]
        payloads.append(payload)
    return payloads


# ---------------------------------------------------------------------------
# Target-confirmation UX (PRD-4 S2) — heuristic hint + user-confirmed overrides
# ---------------------------------------------------------------------------


def _build_target_pools(
    equipment: list[dict],
    sampling_points: list[dict],
    process_units: list[dict],
    sites: list[dict],
    campaigns: list[dict],
) -> dict[str, list[dict]]:
    """Normalize each level's lookup into ``{id, label}`` options for pickers."""
    from app.components.resolver import _candidate_name  # local import: shared labeler

    def opts(pool: list[dict], id_key: str) -> list[dict]:
        return [
            {"id": c.get(id_key), "label": _candidate_name(c)}
            for c in pool
            if c.get(id_key) is not None and _candidate_name(c)
        ]

    return {
        "Equipment": opts(equipment, "equipment_id"),
        "SamplingPoint": opts(sampling_points, "sampling_point_id"),
        "ProcessUnit": opts(process_units, "id"),
        "Site": opts(sites, "site_id"),
        "Campaign": opts(campaigns, "campaign_id"),
    }


def _apply_target_override(rr: dict, target: dict | None) -> dict:
    """Return a copy of *rr* with a user-confirmed target, ``ok`` recomputed.

    A row is submittable when it has a start datetime and a target. Setting a
    target clears the stale "no target resolved" flag.
    """
    rr = {**rr, "target": target}
    if target is not None:
        rr["errors"] = [e for e in rr["errors"] if "no target resolved" not in e]
    rr["ok"] = rr["start_datetime"] is not None and target is not None
    return rr


def _override_targets(
    row_resolutions: list[dict], overrides: dict[int, dict]
) -> tuple[list[dict], int, int]:
    """Apply ``{row_index: target}`` overrides; return (rows, n_resolved, n_unresolved)."""
    out = []
    n_resolved = 0
    for rr in row_resolutions:
        ov = overrides.get(rr["row_index"])
        if ov is not None:
            rr = _apply_target_override(rr, ov)
        if rr["ok"]:
            n_resolved += 1
        out.append(rr)
    return out, n_resolved, len(out) - n_resolved


def _make_target(level: str, option: dict) -> dict:
    """Build a target dict from a confirmed (level, {id,label}) pick."""
    return {
        "arc_field": TARGET_LEVELS[level],
        "level": level,
        "entity_id": option["id"],
        "label": option["label"],
    }


# ---------------------------------------------------------------------------
# Config persistence (S4) — PRD-5-compatible shape
# ---------------------------------------------------------------------------

_CONFIG_VERSION = 1


def _config_dir() -> Path:
    """Return (and create) the directory where named configs are stored."""
    d = Path.home() / ".dateaubase_mapper_configs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _build_config(
    name: str,
    header_row: int,
    data_start_row: int,
    role_map: dict[str, str],
    sheet_name: str | int | None = None,
    profile: str = "Lab (wide)",
) -> dict:
    """Assemble a config dict in PRD-5-compatible shape."""
    cfg: dict = {
        "name": name,
        "version": _CONFIG_VERSION,
        "profile": profile,
        "header_row": header_row,
        "data_start_row": data_start_row,
        "role_map": role_map,
    }
    if sheet_name is not None:
        cfg["sheet_name"] = sheet_name
    return cfg


def _save_config(cfg: dict) -> Path:
    """Persist *cfg* to ~/.dateaubase_mapper_configs/<name>.json. Returns the path."""
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in cfg["name"]).strip()
    if not safe_name:
        safe_name = "unnamed"
    dest = _config_dir() / f"{safe_name}.json"
    dest.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return dest


def _list_configs() -> list[Path]:
    """Return all saved config files, sorted by name."""
    return sorted(_config_dir().glob("*.json"))


def _load_config(path: Path) -> dict:
    """Read and return a config dict from *path*."""
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


def mapper_page() -> None:
    st.header("Import Data (Mapper)")
    st.caption("PRD-3 S5 — upload → pick profile → tag roles → resolve → preview → submit")

    profile = st.selectbox(
        "Profile",
        options=list(PROFILES.keys()),
        index=0,
        key="mapper_profile",
        help="Lab (wide): rows are samples, columns are parameters. "
        "Lab (long): each row is one measurement (parameter/unit in cells). "
        "Sensor CSV: each row is one timestamped reading. "
        "Logbook (Général): each row is one operational Event.",
    )

    uploaded = st.file_uploader(
        "Upload a spreadsheet",
        type=["csv", "xlsx"],
        help="CSV or Excel files are supported.",
    )

    if uploaded is None:
        st.info("Upload a CSV or XLSX file to get started.")
        return

    active_roles = PROFILES.get(profile, LAB_ROLES)

    file_bytes = uploaded.read()
    filename = uploaded.name

    # ------------------------------------------------------------------
    # Sheet picker (XLSX only)
    # ------------------------------------------------------------------
    sheet_name: str | int = 0
    if filename.endswith(".xlsx"):
        try:
            xl = pd.ExcelFile(io.BytesIO(file_bytes))
            sheet_names = xl.sheet_names
        except Exception as exc:
            st.error(f"Could not open Excel file: {exc}")
            return

        if len(sheet_names) > 1:
            sheet_name = st.selectbox("Sheet", options=sheet_names, index=0, key="mapper_sheet")
        else:
            sheet_name = sheet_names[0]
            st.info(f"Sheet: **{sheet_name}**")

    # ------------------------------------------------------------------
    # Header row / data start row
    # ------------------------------------------------------------------
    col_h, col_d = st.columns(2)
    with col_h:
        header_row = st.number_input(
            "Header row (0-indexed)",
            min_value=0,
            value=0,
            step=1,
            key="mapper_header_row",
            help="Row number containing column names (0 = first row).",
        )
    with col_d:
        data_start_row = st.number_input(
            "Data start row (0-indexed)",
            min_value=0,
            value=1,
            step=1,
            key="mapper_data_start",
            help="First row of data (must be > header row).",
        )

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------
    try:
        df = _read_dataframe(file_bytes, filename, sheet_name=sheet_name, header_row=int(header_row))
    except Exception as exc:
        st.error(f"Could not parse file: {exc}")
        return

    if df.empty:
        st.warning("The parsed table is empty. Check header row and sheet settings.")
        return

    # Slice to data_start_row
    data_start = int(data_start_row)
    if data_start > 0:
        # header_row already consumed by pd.read_excel/csv; data_start_row is relative
        # to the full file, so offset by header_row + 1 (already stripped by pandas).
        skip = max(0, data_start - int(header_row) - 1)
        df_data = df.iloc[skip:].reset_index(drop=True)
    else:
        df_data = df.copy()

    columns = list(df.columns.astype(str))
    st.markdown(f"**{len(columns)} columns** detected")

    # ------------------------------------------------------------------
    # Role tagging — one selectbox per column
    # ------------------------------------------------------------------
    st.subheader("Tag column roles")
    st.caption("Assign a role to each column. Columns tagged '(ignore)' are excluded from the preview.")

    role_map: dict[str, str] = {}
    n_cols = min(len(columns), 4)
    grid_rows = [columns[i : i + n_cols] for i in range(0, len(columns), n_cols)]

    for row_cols in grid_rows:
        grid = st.columns(len(row_cols))
        for col_widget, col_name in zip(grid, row_cols):
            with col_widget:
                role = st.selectbox(
                    col_name,
                    options=active_roles,
                    index=0,
                    key=f"mapper_role_{col_name}",
                )
                role_map[col_name] = role

    # ------------------------------------------------------------------
    # S4: Save / Load mapping config
    # ------------------------------------------------------------------
    with st.expander("💾 Save config", expanded=False):
        cfg_name = st.text_input(
            "Config name",
            value="My Lab Sheet v1",
            key="mapper_cfg_name",
            help="A descriptive name — saved as a JSON file in ~/.dateaubase_mapper_configs/",
        )
        if st.button("Save", key="mapper_cfg_save"):
            if not cfg_name.strip():
                st.error("Please enter a config name before saving.")
            else:
                cfg = _build_config(
                    name=cfg_name.strip(),
                    header_row=int(header_row),
                    data_start_row=int(data_start_row),
                    role_map=role_map,
                    sheet_name=sheet_name if filename.endswith(".xlsx") else None,
                    profile=profile,
                )
                saved_path = _save_config(cfg)
                st.success(f"Config saved to `{saved_path}`")

    with st.expander("📂 Load config", expanded=False):
        config_files = _list_configs()
        if not config_files:
            st.info("No saved configs yet. Save one above first.")
        else:
            selected_cfg_path = st.selectbox(
                "Saved configs",
                options=config_files,
                format_func=lambda p: p.stem,
                key="mapper_cfg_select",
            )
            if st.button("Load", key="mapper_cfg_load") and selected_cfg_path is not None:
                try:
                    loaded = _load_config(selected_cfg_path)
                    # Apply layout settings via session_state
                    st.session_state["mapper_header_row"] = loaded.get("header_row", 0)
                    st.session_state["mapper_data_start"] = loaded.get("data_start_row", 1)
                    # Apply role assignments per column
                    loaded_profile = loaded.get("profile")
                    if loaded_profile in PROFILES:
                        st.session_state["mapper_profile"] = loaded_profile
                    valid_roles = PROFILES.get(loaded_profile, active_roles)
                    for col_name, role in loaded.get("role_map", {}).items():
                        key = f"mapper_role_{col_name}"
                        if role in valid_roles:
                            st.session_state[key] = role
                    st.success(
                        f"Config **{loaded.get('name', selected_cfg_path.stem)}** loaded. "
                        "Roles have been applied — scroll up to review."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to load config: {exc}")

    # ------------------------------------------------------------------
    # Dumb preview — first 5 rows, role-tagged columns only
    # ------------------------------------------------------------------
    st.subheader("Preview")
    active_cols = {col: role for col, role in role_map.items() if role != "(ignore)"}

    if not active_cols:
        st.info("Tag at least one column with a role to see the preview.")
        return

    preview_df = df_data[list(active_cols.keys())].head(5).copy()
    preview_df.columns = [f"{col} [{role}]" for col, role in active_cols.items()]
    st.dataframe(preview_df, use_container_width=True)
    st.caption("Preview shows the first 5 data rows with role labels as column headers.")

    # ------------------------------------------------------------------
    # S5: Sensor-CSV profile — thin profile branch (reuses the same engine)
    # ------------------------------------------------------------------
    if profile == "Sensor CSV":
        _sensor_resolve_and_submit(role_map, active_cols, df_data)
        return

    if profile == "Logbook (Général)":
        _logbook_resolve_and_submit(role_map, active_cols, df_data)
        return

    # ------------------------------------------------------------------
    # S2 / S3: Entity resolution (wide lab) — or S6 long-format lab.
    # Long format resolves into the same shape, so the preview + submit
    # pipeline below is shared verbatim.
    # ------------------------------------------------------------------
    is_long = profile == "Lab (long)"
    if is_long:
        needed = {"sample_datetime", "sampling_location", "parameter", "unit", "value"}
        missing = needed - set(active_cols.values())
        if missing:
            st.info(
                "Tag one column for each of: sample_datetime, sampling_location, "
                f"parameter, unit, value. Still missing: {', '.join(sorted(missing))}."
            )
            return
    else:
        param_value_cols = [col for col, role in active_cols.items() if role == "parameter_value"]
        if not param_value_cols:
            st.info("Tag at least one column as **parameter_value** to enable entity resolution and ingest.")
            return

    st.subheader("Resolve entities")
    st.caption(
        "Match row cells to database entities using fuzzy text matching. "
        + (
            "Each row is one measurement (parameter and unit from cells). "
            if is_long
            else "Parameter column headers should follow the format **Name (unit)** e.g. *COD (mg/L)*. "
        )
        + "Unresolved columns/rows are listed — they are never silently submitted."
    )

    if st.button("Resolve entities", key="mapper_resolve"):
        try:
            units_list = api.list_units_lookup()
            params_list = api.list_parameters_lookup()
            sps_list = api.list_sampling_points_lookup()
        except Exception as exc:
            st.error(f"Could not load lookup data from API: {exc}")
            return

        resolver = EntityResolver(
            units=units_list,
            parameters=params_list,
            sampling_points=sps_list,
        )
        resolution = (
            _resolve_long(resolver, role_map, df_data)
            if is_long
            else _resolve_all(resolver, role_map, df_data)
        )
        st.session_state["mapper_resolution"] = resolution

    # ------------------------------------------------------------------
    # Show resolution results (persisted in session state)
    # ------------------------------------------------------------------
    resolution = st.session_state.get("mapper_resolution")
    if resolution is None:
        return

    col_resolutions: dict = resolution["col_resolutions"]
    row_resolutions: list = resolution["row_resolutions"]
    n_resolved: int = resolution["n_resolved"]
    n_unresolved: int = resolution["n_unresolved"]

    # Column resolution table
    col_rows = []
    for col, cr in col_resolutions.items():
        param_name = cr["param"]["name"] if cr["param"] else "— unresolved —"
        unit_display = (
            cr["unit"].get("symbol") or cr["unit"].get("name", "— unresolved —")
            if cr["unit"]
            else "— unresolved —"
        )
        col_rows.append({
            "Column header": col,
            "Matched parameter": param_name,
            "Matched unit": unit_display,
            "Status": "resolved" if cr["resolved"] else "unresolved",
        })
    col_df = pd.DataFrame(col_rows)
    st.markdown("**Column resolution**")
    st.dataframe(col_df, use_container_width=True)

    unresolved_cols = [c for c, cr in col_resolutions.items() if not cr["resolved"]]
    if unresolved_cols:
        for col in unresolved_cols:
            st.warning(
                f"Column **{col}**: " + "; ".join(col_resolutions[col]["errors"])
                + ". Review column names or add missing entities."
            )
    else:
        st.success("All parameter_value columns resolved.")

    # ------------------------------------------------------------------
    # Preview ingest table
    # ------------------------------------------------------------------
    st.subheader("Preview ingest")
    n_total = len(row_resolutions)
    st.caption(
        f"{n_resolved} of {n_total} rows resolved — "
        f"{n_unresolved} row(s) have errors and will NOT be submitted."
    )

    # Build preview table
    preview_rows = []
    for rr in row_resolutions:
        dt_str = rr["datetime"].isoformat() if rr["datetime"] else "— missing —"
        sp_name = rr["sampling_point"]["name"] if rr["sampling_point"] else f"— {rr['sp_text']} not found —"
        val_summary = ", ".join(
            f"{v['parameter_name']}={v['value']} {v['unit_symbol']}"
            for v in rr["values"]
        )
        row_dict = {
            "row#": rr["row_index"],
            "datetime": dt_str,
            "sampling_point": sp_name,
            "replicate": rr["replicate"],
            "values": val_summary if val_summary else "—",
            "status": "ok" if rr["ok"] else ("error: " + "; ".join(rr["errors"])),
        }
        preview_rows.append(row_dict)

    preview_ingest_df = pd.DataFrame(preview_rows)
    st.dataframe(preview_ingest_df, use_container_width=True)

    if n_unresolved > 0:
        st.warning(
            f"{n_unresolved} row(s) have unresolved entities or missing values and will be skipped. "
            "Fix the data or add missing parameters/locations before submitting."
        )

    if n_resolved == 0:
        st.error("No rows can be submitted — all rows have errors.")
        return

    # ------------------------------------------------------------------
    # Submit to /ingest/lab
    # ------------------------------------------------------------------
    st.subheader("Submit to /ingest/lab")

    exp_name = st.text_input(
        "Experiment name",
        value=f"Mapper import {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        key="mapper_exp_name",
    )
    exp_datetime = st.text_input(
        "Experiment datetime (ISO, UTC)",
        value=datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        key="mapper_exp_datetime",
    )

    col_submit, col_info = st.columns([1, 3])
    with col_info:
        st.info(
            f"Will submit **{n_resolved}** row(s) × {len([c for c in col_resolutions if col_resolutions[c]['resolved']])} "
            f"parameter(s) = up to **{n_resolved * len([c for c in col_resolutions if col_resolutions[c]['resolved']])}** measurement(s). "
            f"{n_unresolved} row(s) will be skipped."
        )

    if col_submit.button("Submit to /ingest/lab", key="mapper_submit", type="primary"):
        _do_submit(row_resolutions, col_resolutions, exp_name, exp_datetime)


def _do_submit(
    row_resolutions: list[dict],
    col_resolutions: dict,
    exp_name: str,
    exp_datetime_str: str,
) -> None:
    """Build payloads per row and call POST /ingest/lab. Reports per-row results."""
    resolved_cols = {
        col: cr for col, cr in col_resolutions.items() if cr["resolved"]
    }
    if not resolved_cols:
        st.error("No resolved parameter columns — cannot submit.")
        return

    try:
        exp_dt = datetime.fromisoformat(exp_datetime_str)
    except Exception:
        st.error(f"Invalid experiment datetime: '{exp_datetime_str}'. Use ISO format.")
        return

    ok_rows = [rr for rr in row_resolutions if rr["ok"]]
    if not ok_rows:
        st.error("No resolved rows to submit.")
        return

    results = []
    progress = st.progress(0, text="Submitting rows…")

    for i, rr in enumerate(ok_rows):
        # Create a sample for this row
        sample_datetime = rr["datetime"]
        sp_id = rr["sampling_point"]["sampling_point_id"]
        try:
            sample_resp = api.create_sample({
                "sampling_point_id": sp_id,
                "sample_datetime_start": sample_datetime.isoformat(),
            })
            sample_id = sample_resp["sample_id"]
        except Exception as exc:
            results.append({"row": rr["row_index"], "status": "error", "detail": f"create_sample failed: {exc}"})
            progress.progress((i + 1) / len(ok_rows), text=f"Row {rr['row_index']}: sample creation error")
            continue

        # Build measurements list
        measurements = []
        for v in rr["values"]:
            col_name = v["col"]
            param = col_resolutions[col_name]["param"]
            unit = col_resolutions[col_name]["unit"]
            measurements.append({
                "parameter_id": v["parameter_id"],
                "sampling_point_id": sp_id,
                "unit_id": v["unit_id"],
                "value_kind_id": 1,
                "series_name": f"{param['name']}@{rr['sampling_point']['name']}",
                "sample_id": sample_id,
                "value": v["value"],
                "replicate": rr["replicate"],
            })

        payload = {
            "name": exp_name,
            "experiment_datetime": exp_dt.isoformat(),
            "measurements": measurements,
        }

        try:
            resp = api.ingest_lab(payload)
            results.append({
                "row": rr["row_index"],
                "status": "ok",
                "detail": f"lab_experiment_id={resp.get('lab_experiment_id')}, rows_written={resp.get('rows_written')}",
            })
        except Exception as exc:
            results.append({"row": rr["row_index"], "status": "error", "detail": str(exc)})

        progress.progress((i + 1) / len(ok_rows), text=f"Row {rr['row_index']} done")

    progress.empty()

    # Report
    n_ok = sum(1 for r in results if r["status"] == "ok")
    n_err = sum(1 for r in results if r["status"] == "error")
    if n_err == 0:
        st.success(f"All {n_ok} row(s) submitted successfully.")
    else:
        st.warning(f"{n_ok} row(s) submitted; {n_err} row(s) failed.")

    st.dataframe(pd.DataFrame(results), use_container_width=True)


# ---------------------------------------------------------------------------
# Sensor-CSV profile UI (S5) — thin profile over the shared engine
# ---------------------------------------------------------------------------


def _sensor_resolve_and_submit(
    role_map: dict[str, str],
    active_cols: dict[str, str],
    df_data: pd.DataFrame,
) -> None:
    """Resolve, preview, and submit a Sensor-CSV table to /ingest/sensor."""
    needed = {"timestamp", "tag", "parameter", "unit", "value"}
    tagged = set(active_cols.values())
    missing = needed - tagged
    if missing:
        st.info(
            "Tag one column for each of: timestamp, tag, parameter, unit, value. "
            f"Still missing: {', '.join(sorted(missing))}."
        )
        return

    st.subheader("Resolve entities")
    st.caption(
        "Parameter and unit cells are matched to database entities by fuzzy text. "
        "The tag is passed through to the tagged sensor endpoint (channels are "
        "auto-created). Unresolved rows are listed — never silently submitted."
    )

    if st.button("Resolve entities", key="mapper_sensor_resolve"):
        try:
            units_list = api.list_units_lookup()
            params_list = api.list_parameters_lookup()
            sps_list = api.list_sampling_points_lookup()
        except Exception as exc:
            st.error(f"Could not load lookup data from API: {exc}")
            return
        resolver = EntityResolver(
            units=units_list,
            parameters=params_list,
            sampling_points=sps_list,
        )
        st.session_state["mapper_sensor_resolution"] = _resolve_sensor(
            resolver, role_map, df_data
        )

    resolution = st.session_state.get("mapper_sensor_resolution")
    if resolution is None:
        return

    row_resolutions = resolution["row_resolutions"]
    n_resolved = resolution["n_resolved"]
    n_unresolved = resolution["n_unresolved"]
    n_total = len(row_resolutions)

    st.subheader("Preview ingest")
    st.caption(
        f"{n_resolved} of {n_total} rows resolved — "
        f"{n_unresolved} row(s) have errors and will NOT be submitted."
    )

    preview_rows = []
    for rr in row_resolutions:
        ts_str = rr["timestamp"].isoformat() if rr["timestamp"] else "— missing —"
        param_name = rr["parameter"]["name"] if rr["parameter"] else f"— {rr['param_text']} not found —"
        unit_disp = (
            (rr["unit"].get("symbol") or rr["unit"].get("name", ""))
            if rr["unit"]
            else f"— {rr['unit_text']} not found —"
        )
        preview_rows.append({
            "row#": rr["row_index"],
            "timestamp": ts_str,
            "tag": rr["tag"],
            "parameter": param_name,
            "unit": unit_disp,
            "value": rr["value"] if rr["value"] is not None else "—",
            "status": "ok" if rr["ok"] else ("error: " + "; ".join(rr["errors"])),
        })
    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)

    if n_unresolved > 0:
        st.warning(
            f"{n_unresolved} row(s) have unresolved entities or invalid values and will be skipped."
        )
    if n_resolved == 0:
        st.error("No rows can be submitted — all rows have errors.")
        return

    st.subheader("Submit to /ingest/sensor")
    das_name = st.text_input(
        "Data-acquisition system (DAS)",
        key="mapper_sensor_das",
        help="The source system the tags belong to; auto-created if it doesn't exist.",
    ).strip()
    payloads = _build_sensor_payloads(row_resolutions, das_name)
    st.info(
        f"Will submit **{n_resolved}** reading(s) grouped into **{len(payloads)}** "
        f"channel(s) (one tagged /ingest/sensor call each). {n_unresolved} row(s) skipped."
    )

    submit_disabled = not das_name
    if submit_disabled:
        st.caption("Enter a DAS name to enable submit.")
    if st.button(
        "Submit to /ingest/sensor",
        key="mapper_sensor_submit",
        type="primary",
        disabled=submit_disabled,
    ):
        _do_sensor_submit(payloads)


def _do_sensor_submit(payloads: list[dict]) -> None:
    """Call POST /ingest/sensor for each (tag, parameter, unit) channel payload."""
    if not payloads:
        st.error("No resolved readings to submit.")
        return

    results = []
    progress = st.progress(0, text="Submitting channels…")
    for i, payload in enumerate(payloads):
        try:
            resp = api.ingest_sensor(payload)
            results.append({
                "tag": payload["tag"],
                "parameter": payload["parameter_name"],
                "rows": len(payload["values"]),
                "status": "ok",
                "detail": f"channel_id={resp.get('channel_id')}, rows_written={resp.get('rows_written')}",
            })
        except Exception as exc:
            results.append({
                "tag": payload["tag"],
                "parameter": payload["parameter_name"],
                "rows": len(payload["values"]),
                "status": "error",
                "detail": str(exc),
            })
        progress.progress((i + 1) / len(payloads), text=f"Channel '{payload['tag']}' done")
    progress.empty()

    n_ok = sum(1 for r in results if r["status"] == "ok")
    n_err = sum(1 for r in results if r["status"] == "error")
    if n_err == 0:
        st.success(f"All {n_ok} channel(s) submitted successfully.")
    else:
        st.warning(f"{n_ok} channel(s) submitted; {n_err} failed.")
    st.dataframe(pd.DataFrame(results), use_container_width=True)


# ---------------------------------------------------------------------------
# Logbook "Général" profile UI (PRD-4 S1) — map → resolve target → create Events
# ---------------------------------------------------------------------------


def _logbook_resolve_and_submit(
    role_map: dict[str, str],
    active_cols: dict[str, str],
    df_data: pd.DataFrame,
) -> None:
    """Resolve, preview, and create Events from a "Général" logbook journal."""
    tagged = set(active_cols.values())
    if "event_date" not in tagged:
        st.info("Tag the date column as **event_date** (and optionally a time column).")
        return
    if "notes" not in tagged:
        st.info("Tag the comments column as **notes** — it carries the entry text and target.")
        return

    st.subheader("Resolve targets")
    st.caption(
        "Each row becomes one Event. The comment is scanned for the smallest "
        "logical target it names (Equipment → SamplingPoint → ProcessUnit → "
        "Site → Campaign). Rows with no parseable date or no resolved target "
        "are flagged — never auto-guessed into a wrong target."
    )

    # Event kind isn't in the sheet — the user picks a default for all rows.
    try:
        event_kinds = api.list_event_kinds_lookup()
    except Exception as exc:
        st.error(f"Could not load event kinds: {exc}")
        return
    if not event_kinds:
        st.warning("No event kinds defined yet — create one before importing the logbook.")
        return
    kind_label = st.selectbox(
        "Default event kind",
        options=[k["name"] for k in event_kinds],
        key="mapper_logbook_kind",
        help="Applied to every imported row (the Général sheet has no kind column).",
    )
    event_kind_id = next(k["event_kind_id"] for k in event_kinds if k["name"] == kind_label)

    if st.button("Resolve targets", key="mapper_logbook_resolve"):
        try:
            equipment = api.list_equipment_lookup()
            sampling_points = api.list_sampling_points_lookup()
            process_units = api.list_process_units_lookup()
            sites = api.list_sites_lookup()
            campaigns = api.list_campaigns_lookup()
            resolver = EntityResolver(
                units=[],
                parameters=[],
                sampling_points=sampling_points,
                equipment=equipment,
                sites=sites,
                process_units=process_units,
                campaigns=campaigns,
                persons=api.list_persons_lookup(),
            )
        except Exception as exc:
            st.error(f"Could not load lookup data from API: {exc}")
            return
        st.session_state["mapper_logbook_resolution"] = _resolve_logbook(
            resolver, role_map, df_data
        )
        # Stash the picker pools for the S2 confirm UX; reset prior overrides.
        st.session_state["mapper_logbook_pools"] = _build_target_pools(
            equipment, sampling_points, process_units, sites, campaigns
        )
        st.session_state["mapper_logbook_overrides"] = {}

    resolution = st.session_state.get("mapper_logbook_resolution")
    if resolution is None:
        return

    base_rows = resolution["row_resolutions"]
    pools = st.session_state.get("mapper_logbook_pools", {})
    overrides = st.session_state.get("mapper_logbook_overrides", {})

    # ------------------------------------------------------------------
    # S2: confirm / override ambiguous targets (never auto-committed).
    # Only rows that have a date but no resolved target are fixable here.
    # ------------------------------------------------------------------
    fixable = [
        rr for rr in base_rows
        if rr["start_datetime"] is not None
        and rr["row_index"] not in overrides
        and rr["target"] is None
    ]
    if fixable and pools:
        with st.expander(f"🎯 Confirm targets ({len(fixable)} need a pick)", expanded=True):
            st.caption(
                "These rows name no known entity. Pick the right target — nothing "
                "is submitted until you confirm. The level is pre-filled from a "
                "heuristic guess; it is only a hint."
            )
            level_names = list(TARGET_LEVELS.keys())
            for rr in fixable:
                ri = rr["row_index"]
                st.markdown(f"**Row {ri}** — {rr['title'] or '(no title)'}")
                guess = guess_target_level(rr["notes"])
                lvl_col, ent_col = st.columns(2)
                with lvl_col:
                    level = st.selectbox(
                        "Level",
                        options=level_names,
                        index=level_names.index(guess) if guess in level_names else 0,
                        key=f"mapper_logbook_lvl_{ri}",
                    )
                opts = pools.get(level, [])
                with ent_col:
                    choice = st.selectbox(
                        "Target",
                        options=["— pick —"] + [o["label"] for o in opts],
                        key=f"mapper_logbook_ent_{ri}",
                    )
                col_apply, col_bulk = st.columns(2)
                picked = next((o for o in opts if o["label"] == choice), None)
                if col_apply.button("Apply", key=f"mapper_logbook_apply_{ri}", disabled=picked is None):
                    overrides[ri] = _make_target(level, picked)
                    st.session_state["mapper_logbook_overrides"] = overrides
                    st.rerun()
                if col_bulk.button(
                    "Apply to all flagged",
                    key=f"mapper_logbook_bulk_{ri}",
                    disabled=picked is None,
                    help="Set this same target on every still-unresolved dated row.",
                ):
                    for other in fixable:
                        overrides[other["row_index"]] = _make_target(level, picked)
                    st.session_state["mapper_logbook_overrides"] = overrides
                    st.rerun()

    row_resolutions, n_resolved, n_unresolved = _override_targets(base_rows, overrides)
    n_total = len(row_resolutions)

    st.subheader("Preview events")
    st.caption(
        f"{n_resolved} of {n_total} rows resolved — "
        f"{n_unresolved} row(s) have errors and will NOT be submitted."
    )

    preview_rows = []
    for rr in row_resolutions:
        ts_str = rr["start_datetime"].isoformat() if rr["start_datetime"] else "— missing —"
        tgt = rr["target"]
        target_disp = f"{tgt['level']}: {tgt['label']}" if tgt else "— unresolved —"
        preview_rows.append({
            "row#": rr["row_index"],
            "start": ts_str,
            "title": rr["title"] or "—",
            "target": target_disp,
            "conductor": (rr["person"]["label"] if rr["person"] else (rr["person_text"] or "—")),
            "status": "ok" if rr["ok"] else ("error: " + "; ".join(rr["errors"])),
        })
    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)

    if n_unresolved > 0:
        st.warning(
            f"{n_unresolved} row(s) have no date or no resolved target and will be skipped."
        )
    if n_resolved == 0:
        st.error("No rows can be submitted — confirm a target above, or fix the dates.")
        return

    payloads = _build_event_payloads(row_resolutions, event_kind_id)
    st.subheader("Create events")
    st.info(f"Will create **{len(payloads)}** Event(s). {n_unresolved} row(s) skipped.")
    if st.button("Create events", key="mapper_logbook_submit", type="primary"):
        _do_event_submit(payloads, row_resolutions)


def _do_event_submit(payloads: list[dict], row_resolutions: list[dict]) -> None:
    """Call POST /events for each resolved logbook row. Reports per-row results."""
    if not payloads:
        st.error("No resolved rows to submit.")
        return

    # One ok row per payload, in the same order, for the result table.
    ok_rows = [rr for rr in row_resolutions if rr["ok"]]
    results = []
    progress = st.progress(0, text="Creating events…")
    for i, (payload, rr) in enumerate(zip(payloads, ok_rows)):
        tgt = rr["target"]
        try:
            resp = api.create_event(payload)
            results.append({
                "row": rr["row_index"],
                "target": f"{tgt['level']}: {tgt['label']}",
                "status": "ok",
                "detail": f"event_id={resp.get('event_id')}",
            })
        except Exception as exc:
            results.append({
                "row": rr["row_index"],
                "target": f"{tgt['level']}: {tgt['label']}",
                "status": "error",
                "detail": str(exc),
            })
        progress.progress((i + 1) / len(payloads), text=f"Row {rr['row_index']} done")
    progress.empty()

    n_ok = sum(1 for r in results if r["status"] == "ok")
    n_err = sum(1 for r in results if r["status"] == "error")
    if n_err == 0:
        st.success(f"All {n_ok} event(s) created successfully.")
    else:
        st.warning(f"{n_ok} event(s) created; {n_err} failed.")
    st.dataframe(pd.DataFrame(results), use_container_width=True)


mapper_page()
