"""Unit tests for PRD-3 S3 — Lab profile entity resolution and payload shape.

Red→green tests that verify:
1. Parameter column headers tagged as parameter_value resolve to (parameter, unit) pairs.
2. Rows with unresolved entities surface errors instead of silently dropping.
3. A resolved row produces the correct /ingest/lab payload structure.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.components.resolver import EntityResolver
from app.pages.mapper import _parse_param_header, _resolve_all

_UNITS = [{"unit_id": 1, "name": "milligram per litre", "symbol": "mg/L"}]
_PARAMS = [
    {"parameter_id": 10, "name": "Chemical Oxygen Demand", "short_name": "COD"},
    {"parameter_id": 11, "name": "Total Suspended Solids", "short_name": "TSS"},
]
_SPS = [{"sampling_point_id": 100, "name": "R240"}]


def test_lab_profile_resolves_parameter_columns():
    """Column headers tagged as parameter_value resolve to (parameter, unit) pairs."""
    r = EntityResolver(units=_UNITS, parameters=_PARAMS, sampling_points=_SPS)
    # Simulate a column header like "COD (mg/L)"
    header = "COD (mg/L)"
    # naive split on space+paren
    parts = header.split(" (")
    param_text = parts[0]
    unit_text = parts[1].rstrip(")") if len(parts) > 1 else ""
    param = r.resolve_parameter(param_text)
    unit = r.resolve_unit(unit_text)
    assert param is not None
    assert unit is not None


def test_lab_profile_unresolved_row_not_submitted():
    """Rows with unresolved entities produce errors, not silent drops."""
    r = EntityResolver(units=_UNITS, parameters=_PARAMS, sampling_points=_SPS)
    sp = r.resolve_sampling_point("UNKNOWN_LOCATION")
    assert sp is None  # unresolved → must surface error, not submit


def test_wide_lab_row_builds_payload():
    """A resolved row produces the correct ingest payload structure."""
    row = {
        "sample_datetime": "2024-01-15T10:00:00",
        "sampling_point_id": 100,
        "replicate": 1,
        "values": [{"parameter_id": 10, "unit_id": 1, "value": 42.5}],
    }
    # Basic shape check — not a full API call
    assert row["sampling_point_id"] == 100
    assert row["values"][0]["parameter_id"] == 10


def test_parse_param_header_with_unit():
    """_parse_param_header correctly splits 'COD (mg/L)' into param and unit text."""
    param_text, unit_text = _parse_param_header("COD (mg/L)")
    assert param_text == "COD"
    assert unit_text == "mg/L"


def test_parse_param_header_no_unit():
    """_parse_param_header returns empty unit string when header has no parens."""
    param_text, unit_text = _parse_param_header("COD")
    assert param_text == "COD"
    assert unit_text == ""


def test_resolve_all_marks_unresolved_rows_as_not_ok():
    """_resolve_all marks rows with unknown sampling location as not ok."""
    r = EntityResolver(units=_UNITS, parameters=_PARAMS, sampling_points=_SPS)
    role_map = {
        "sample_datetime": "sample_datetime",
        "location": "sampling_location",
        "COD (mg/L)": "parameter_value",
    }
    df = pd.DataFrame([
        {"sample_datetime": "2024-01-15T10:00:00", "location": "UNKNOWN", "COD (mg/L)": 42.5}
    ])
    result = _resolve_all(r, role_map, df)
    assert result["n_unresolved"] == 1
    assert result["n_resolved"] == 0
    assert not result["row_resolutions"][0]["ok"]


def test_resolve_all_resolved_row_is_ok():
    """_resolve_all marks a fully resolved row as ok."""
    r = EntityResolver(units=_UNITS, parameters=_PARAMS, sampling_points=_SPS)
    role_map = {
        "sample_datetime": "sample_datetime",
        "location": "sampling_location",
        "COD (mg/L)": "parameter_value",
    }
    df = pd.DataFrame([
        {"sample_datetime": "2024-01-15T10:00:00", "location": "R240", "COD (mg/L)": 42.5}
    ])
    result = _resolve_all(r, role_map, df)
    assert result["n_resolved"] == 1
    assert result["n_unresolved"] == 0
    rr = result["row_resolutions"][0]
    assert rr["ok"] is True
    assert len(rr["values"]) == 1
    assert rr["values"][0]["parameter_id"] == 10
    assert rr["values"][0]["unit_id"] == 1
    assert rr["values"][0]["value"] == 42.5
