"""Unit tests for PRD-3 S6 — Long-format (tidy) lab profile.

A long-format lab sheet has one measurement per row, with parameter and unit
in *cells* (not the column header). It must resolve into the SAME shape as the
wide-lab engine (``_resolve_all``) so the existing preview + ``/ingest/lab``
submit pipeline is reused unchanged.
"""

from __future__ import annotations

import pandas as pd

from app.components.resolver import EntityResolver
from app.pages.mapper import (
    PROFILES,
    LONG_LAB_ROLES,
    _resolve_all,
    _resolve_long,
)

_UNITS = [{"unit_id": 1, "name": "milligram per litre", "symbol": "mg/L"}]
_PARAMS = [
    {"parameter_id": 10, "name": "Chemical Oxygen Demand", "short_name": "COD"},
]
_SPS = [{"sampling_point_id": 100, "name": "R240"}]

_LONG_ROLE_MAP = {
    "when": "sample_datetime",
    "where": "sampling_location",
    "param_col": "parameter",
    "unit_col": "unit",
    "val_col": "value",
}


def _resolver() -> EntityResolver:
    return EntityResolver(units=_UNITS, parameters=_PARAMS, sampling_points=_SPS)


def test_long_profile_registered():
    """The Lab (long) profile is selectable and exposes its role vocabulary."""
    assert "Lab (long)" in PROFILES
    assert PROFILES["Lab (long)"] == LONG_LAB_ROLES
    assert {"sample_datetime", "sampling_location", "parameter", "unit", "value"} <= set(
        LONG_LAB_ROLES
    )


def test_resolve_long_returns_wide_compatible_shape():
    """A resolved long row matches the wide engine's row/col shape exactly."""
    df = pd.DataFrame([
        {
            "when": "2024-01-15T10:00:00",
            "where": "R240",
            "param_col": "COD",
            "unit_col": "mg/L",
            "val_col": 42.5,
        }
    ])
    result = _resolve_long(_resolver(), _LONG_ROLE_MAP, df)

    # Same top-level keys as _resolve_all (so the downstream pipeline is shared).
    assert set(result.keys()) == set(
        _resolve_all(_resolver(), {}, df.iloc[0:0]).keys()
    )
    assert result["n_resolved"] == 1
    assert result["n_unresolved"] == 0

    rr = result["row_resolutions"][0]
    assert rr["ok"] is True
    assert rr["datetime"] is not None
    assert rr["sampling_point"]["sampling_point_id"] == 100
    assert rr["replicate"] == 1
    # One synthesized value entry, in the wide value shape (incl. its "col" key).
    assert len(rr["values"]) == 1
    v = rr["values"][0]
    assert v["parameter_id"] == 10
    assert v["unit_id"] == 1
    assert v["value"] == 42.5
    # The value's col key is registered in col_resolutions (used by _do_submit).
    assert v["col"] in result["col_resolutions"]
    assert result["col_resolutions"][v["col"]]["resolved"] is True


def test_resolve_long_unknown_unit_not_ok():
    """A row with an unresolvable unit surfaces an error, not a silent drop."""
    df = pd.DataFrame([
        {
            "when": "2024-01-15T10:00:00",
            "where": "R240",
            "param_col": "COD",
            "unit_col": "furlongs",
            "val_col": 42.5,
        }
    ])
    result = _resolve_long(_resolver(), _LONG_ROLE_MAP, df)
    assert result["n_resolved"] == 0
    assert result["n_unresolved"] == 1
    rr = result["row_resolutions"][0]
    assert rr["ok"] is False
    assert rr["values"] == []
    assert any("furlongs" in e for e in rr["errors"])
