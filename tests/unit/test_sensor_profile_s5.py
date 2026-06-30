"""Unit tests for PRD-3 S5 — Sensor-CSV profile (thin profile over the engine).

Red→green tests that verify a sensor CSV imports through the *same* mapper
engine: timestamp/tag/parameter/unit/value columns resolve to existing
entities and group into tagged /ingest/sensor payloads.
"""

from __future__ import annotations

import pandas as pd

from app.components.resolver import EntityResolver
from app.pages.mapper import (
    PROFILES,
    SENSOR_ROLES,
    _build_sensor_payloads,
    _resolve_sensor,
)

_UNITS = [{"unit_id": 1, "name": "milligram per litre", "symbol": "mg/L"}]
_PARAMS = [
    {"parameter_id": 10, "name": "Chemical Oxygen Demand", "short_name": "COD"},
]
_SPS = [{"sampling_point_id": 100, "name": "R240"}]

_SENSOR_ROLE_MAP = {
    "ts": "timestamp",
    "tag_col": "tag",
    "param_col": "parameter",
    "unit_col": "unit",
    "val_col": "value",
}


def _resolver() -> EntityResolver:
    return EntityResolver(units=_UNITS, parameters=_PARAMS, sampling_points=_SPS)


def test_sensor_profile_registered():
    """The Sensor-CSV profile is selectable and exposes its role vocabulary."""
    assert "Sensor CSV" in PROFILES
    assert PROFILES["Sensor CSV"] == SENSOR_ROLES
    assert {"timestamp", "tag", "parameter", "unit", "value"} <= set(SENSOR_ROLES)


def test_resolve_sensor_resolved_row_is_ok():
    """A fully resolved sensor row is marked ok with resolved entities + value."""
    df = pd.DataFrame([
        {
            "ts": "2024-01-15T10:00:00",
            "tag_col": "PLC1.COD",
            "param_col": "COD",
            "unit_col": "mg/L",
            "val_col": 42.5,
        }
    ])
    result = _resolve_sensor(_resolver(), _SENSOR_ROLE_MAP, df)
    assert result["n_resolved"] == 1
    assert result["n_unresolved"] == 0
    rr = result["row_resolutions"][0]
    assert rr["ok"] is True
    assert rr["parameter"]["parameter_id"] == 10
    assert rr["unit"]["unit_id"] == 1
    assert rr["value"] == 42.5
    assert rr["tag"] == "PLC1.COD"


def test_resolve_sensor_unknown_unit_not_ok():
    """A row with an unresolvable unit surfaces an error, not a silent drop."""
    df = pd.DataFrame([
        {
            "ts": "2024-01-15T10:00:00",
            "tag_col": "PLC1.COD",
            "param_col": "COD",
            "unit_col": "furlongs",
            "val_col": 42.5,
        }
    ])
    result = _resolve_sensor(_resolver(), _SENSOR_ROLE_MAP, df)
    assert result["n_resolved"] == 0
    assert result["n_unresolved"] == 1
    rr = result["row_resolutions"][0]
    assert rr["ok"] is False
    assert any("furlongs" in e for e in rr["errors"])


def test_build_sensor_payloads_groups_by_channel():
    """Resolved rows group into tagged /ingest/sensor payloads keyed by channel."""
    df = pd.DataFrame([
        {"ts": "2024-01-15T10:00:00", "tag_col": "PLC1.COD", "param_col": "COD", "unit_col": "mg/L", "val_col": 1.0},
        {"ts": "2024-01-15T10:05:00", "tag_col": "PLC1.COD", "param_col": "COD", "unit_col": "mg/L", "val_col": 2.0},
    ])
    result = _resolve_sensor(_resolver(), _SENSOR_ROLE_MAP, df)
    payloads = _build_sensor_payloads(result["row_resolutions"])
    assert len(payloads) == 1  # both rows share one channel
    p = payloads[0]
    assert p["tag"] == "PLC1.COD"
    assert p["parameter_name"] == "Chemical Oxygen Demand"
    assert p["unit_name"] == "mg/L"
    assert p["strict"] is False
    assert len(p["values"]) == 2
    assert p["values"][0]["value"] == 1.0
    assert "timestamp" in p["values"][0]


def test_build_sensor_payloads_threads_das_name():
    """The user-supplied DAS name reaches the payload (not a silent empty)."""
    df = pd.DataFrame([
        {"ts": "2024-01-15T10:00:00", "tag_col": "PLC1.COD", "param_col": "COD", "unit_col": "mg/L", "val_col": 1.0},
    ])
    result = _resolve_sensor(_resolver(), _SENSOR_ROLE_MAP, df)
    payloads = _build_sensor_payloads(result["row_resolutions"], das_name="PLC1")
    assert payloads[0]["das_name"] == "PLC1"


def test_build_sensor_payloads_excludes_unresolved_rows():
    """Unresolved rows never make it into a submit payload."""
    df = pd.DataFrame([
        {"ts": "2024-01-15T10:00:00", "tag_col": "PLC1.COD", "param_col": "COD", "unit_col": "mg/L", "val_col": 1.0},
        {"ts": "2024-01-15T10:05:00", "tag_col": "PLC1.COD", "param_col": "UNKNOWN", "unit_col": "mg/L", "val_col": 2.0},
    ])
    result = _resolve_sensor(_resolver(), _SENSOR_ROLE_MAP, df)
    payloads = _build_sensor_payloads(result["row_resolutions"])
    assert sum(len(p["values"]) for p in payloads) == 1  # only the resolved row
