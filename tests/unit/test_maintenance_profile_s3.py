"""Unit tests for PRD-4 S3 — per-equipment maintenance-sheet profile.

Acceptance: a `Solitax R240` row imports as a maintenance Event on the right
target. One spanning Event per row; the target is the *whole sheet's*
equipment/channel (not per-row); before/after readings are not stored.
"""

from __future__ import annotations

import pandas as pd

from app.components.resolver import EntityResolver
from app.pages.mapper import (
    PROFILES,
    MAINTENANCE_ROLES,
    _build_maintenance_payloads,
    _default_kind_index,
    _make_target,
    _resolve_maintenance,
)

_MAINT_ROLE_MAP = {
    "Date": "event_date",
    "Start": "start_time",
    "End": "end_time",
    "Comment": "notes",
}


def test_maintenance_profile_registered():
    assert "Logbook (Maintenance)" in PROFILES
    assert PROFILES["Logbook (Maintenance)"] == MAINTENANCE_ROLES
    assert {"event_date", "start_time", "end_time", "notes"} <= set(MAINTENANCE_ROLES)


def test_sheet_name_resolves_to_equipment_target():
    """'Solitax R240' sheet → its equipment, the single target for every row."""
    resolver = EntityResolver(
        units=[], parameters=[], sampling_points=[],
        equipment=[{"equipment_id": 12, "identifier": "Solitax R240"}],
    )
    tgt = resolver.resolve_target("Solitax R240")
    assert tgt["arc_field"] == "equipment_id"
    assert tgt["entity_id"] == 12


def test_resolve_maintenance_spans_and_targets_the_sheet():
    sheet_target = _make_target("Equipment", {"id": 12, "label": "Solitax R240"})
    df = pd.DataFrame([
        {"Date": "2023-06-01", "Start": "09:00", "End": "09:30", "Comment": "zero check ok"},
        {"Date": "2023-06-15", "Start": "10:00", "End": "10:20", "Comment": ""},
    ])
    result = _resolve_maintenance(_MAINT_ROLE_MAP, df, sheet_target)
    assert result["n_resolved"] == 2

    payloads = _build_maintenance_payloads(result["row_resolutions"], event_kind_id=4)
    assert len(payloads) == 2
    p = payloads[0]
    assert p["equipment_id"] == 12  # every row targets the sheet equipment
    assert p["event_kind_id"] == 4
    assert p["is_instantaneous"] is False  # spanning maintenance Event
    assert p["start_datetime"].startswith("2023-06-01T09:00")
    assert p["end_datetime"].startswith("2023-06-01T09:30")
    assert p["notes"] == "zero check ok"  # manual zero-check kept as notes
    # No before/after value fields leak into the payload.
    assert "value" not in p and "before" not in p and "after" not in p


def test_resolve_maintenance_flags_unparseable_date():
    sheet_target = _make_target("Equipment", {"id": 12, "label": "Solitax R240"})
    df = pd.DataFrame([{"Date": "", "Start": "", "End": "", "Comment": "no date"}])
    result = _resolve_maintenance(_MAINT_ROLE_MAP, df, sheet_target)
    assert result["n_resolved"] == 0
    assert result["row_resolutions"][0]["ok"] is False
    assert _build_maintenance_payloads(result["row_resolutions"], event_kind_id=1) == []


def test_default_kind_index_prefers_maintenance():
    kinds = [{"name": "general"}, {"name": "Probe maintenance"}, {"name": "calibration"}]
    assert _default_kind_index(kinds) == 1
    assert _default_kind_index([{"name": "general"}]) == 0  # falls back to 0
