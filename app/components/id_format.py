"""Consistent rendering of foreign-key id columns in tables.

`humanize_id_columns` turns each `*_id` foreign-key column into a single
``"Label (id)"`` column so every table shows ids the same way. A row's own
primary key (`pk_field`) is left as a raw number.

Label resolution, in order:
1. A sibling label column already present in the data (e.g. ``site_id`` +
   ``site_name``, ``unit_id`` + ``unit``) is merged and dropped.
2. Otherwise the column is looked up via ``_ID_RESOLVERS`` against the cached
   ``list_*_lookup()`` endpoints in :mod:`app.api_client`.
3. If neither yields a label, the raw id is left untouched.
"""

from __future__ import annotations

import pandas as pd

# Orphan FK id columns (no sibling label in the row data) -> api_client lookup
# function name. Each lookup returns ``[{*_id: ..., name/label/...: ...}]`` and
# the id/label fields are auto-detected. Add a line to extend coverage.
_ID_RESOLVERS: dict[str, str] = {
    "das_id": "list_das_lookup",
    "parent_watershed_id": "list_watershed_lookup",
    "model_id": "list_equipment_models_lookup",
    "signal_interface_id": "list_signal_interface_lookup",
    "parameter_id": "list_parameter_lookup",
    "unit_id": "list_unit_lookup",
    "site_id": "list_site_lookup",
}

# Sibling label suffixes, highest priority first. "" matches a column named
# exactly like the base (e.g. ``unit_id`` -> ``unit``).
_LABEL_SUFFIXES = ("_name", "_label", "", "_identifier", "_tag", "_code")


def _is_null(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v))


def _fmt_id(idv) -> str:
    # Nullable id columns are promoted to float by pandas; show 2.0 as "2".
    if isinstance(idv, float) and idv.is_integer():
        return str(int(idv))
    return str(idv)


def _combine(label, idv) -> str:
    if _is_null(idv):
        return "" if _is_null(label) else str(label)
    if _is_null(label):
        return _fmt_id(idv)
    return f"{label} ({_fmt_id(idv)})"


def _detect_id_label(rows: list[dict]) -> tuple[str | None, str | None]:
    """Pick the id and label fields from a lookup response (mirrors the
    heuristic in ``generic_crud._normalize_options``)."""
    sample = rows[0]
    id_keys = [k for k in sample if k.endswith("_id")]
    label_keys = [
        k for k in sample if k in ("name", "label", "unit", "identifier", "code", "tag")
    ]
    id_k = id_keys[0] if id_keys else None
    if label_keys:
        return id_k, label_keys[0]
    keys = list(sample)
    if id_k and len(keys) >= 2:
        return id_k, next((k for k in keys if k != id_k), None)
    return id_k, None


def _resolve_map(col: str) -> dict:
    """``{id: label}`` for an orphan FK column via its lookup; ``{}`` on failure."""
    fn_name = _ID_RESOLVERS.get(col)
    if not fn_name:
        return {}
    try:
        from app import api_client

        fn = getattr(api_client, fn_name, None)
        rows = fn() if fn else None
    except Exception:
        return {}
    if not rows:
        return {}
    id_k, label_k = _detect_id_label(rows)
    if not id_k or not label_k:
        return {}
    return {r[id_k]: r[label_k] for r in rows if r.get(id_k) is not None}


def humanize_id_columns(
    df: pd.DataFrame,
    pk_field: str | None = None,
    resolvers: dict[str, dict] | None = None,
) -> pd.DataFrame:
    """Return a copy of ``df`` with foreign-key ``*_id`` columns rendered as
    ``"Label (id)"``. ``pk_field`` is left raw. Pass ``resolvers`` (a
    ``{column: {id: label}}`` map) to override the lookup registry — when given,
    the network registry is not consulted (used in tests)."""
    if df is None or len(df.columns) == 0:
        return df
    out = df.copy()
    lower_to_actual = {c.lower(): c for c in df.columns}
    for col in list(df.columns):
        if col == pk_field or not col.lower().endswith("_id"):
            continue
        if col not in out.columns:  # consumed as another column's label
            continue
        base = col[:-3]

        # 1. sibling label already present in the data
        label_col = None
        for suf in _LABEL_SUFFIXES:
            cand = lower_to_actual.get((base + suf).lower())
            if cand and cand != col and cand in out.columns:
                label_col = cand
                break
        if label_col is not None:
            out[col] = [_combine(lbl, idv) for lbl, idv in zip(df[label_col], df[col])]
            out = out.drop(columns=[label_col])
        else:
            # 2. resolve orphan via injected resolvers or the lookup registry
            mapping = resolvers.get(col, {}) if resolvers is not None else _resolve_map(col)
            if not mapping:
                continue  # 3. leave raw
            out[col] = [_combine(mapping.get(idv), idv) for idv in df[col]]

        out = out.rename(columns={col: base.replace("_", " ").capitalize()})
    return out
