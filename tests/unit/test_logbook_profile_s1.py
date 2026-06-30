"""Unit tests for PRD-4 S1 — Général-sheet logbook profile → Event.

Acceptance (red→green): a power-outage row lands as a Site-targeted Event, a
pump row as an Equipment-targeted Event — resolved to the *smallest* logical
unit named in the comment, never auto-guessed into the wrong target.
"""

from __future__ import annotations

import pandas as pd

from app.components.resolver import EntityResolver
from app.pages.mapper import (
    PROFILES,
    LOGBOOK_ROLES,
    _build_event_payloads,
    _resolve_logbook,
)

# Lookup pools in their production key shapes.
_EQUIPMENT = [{"equipment_id": 5, "identifier": "P-100"}]
_SITES = [{"site_id": 2, "name": "Pouliot"}]
_PROCESS_UNITS = [{"id": 9, "name": "Primary Clarifier", "tag": "PC-1"}]
_PERSONS = [{"person_id": 3, "label": "Marie Tremblay"}]

_LOGBOOK_ROLE_MAP = {
    "Date": "event_date",
    "Heure": "event_time",
    "Commentaires": "notes",
    "Conductor": "conductor",
}


def _resolver() -> EntityResolver:
    return EntityResolver(
        units=[],
        parameters=[],
        sampling_points=[],
        equipment=_EQUIPMENT,
        sites=_SITES,
        process_units=_PROCESS_UNITS,
        persons=_PERSONS,
    )


def test_logbook_profile_registered():
    assert "Logbook (Général)" in PROFILES
    assert PROFILES["Logbook (Général)"] == LOGBOOK_ROLES
    assert {"event_date", "notes", "conductor"} <= set(LOGBOOK_ROLES)


def test_target_resolution_picks_smallest_unit():
    """A pump mention resolves to Equipment even when a Site is also present."""
    r = _resolver()
    # Equipment is the smallest level, so it wins over Site in the same text.
    eq = r.resolve_target("Cleaned pump P-100 at Pouliot")
    assert eq["arc_field"] == "equipment_id"
    assert eq["entity_id"] == 5
    # No equipment named → falls through to Site.
    site = r.resolve_target("Building power outage at Pouliot")
    assert site["arc_field"] == "site_id"
    assert site["entity_id"] == 2
    # Nothing recognizable → no auto-guess.
    assert r.resolve_target("misc note with no entity") is None


def test_resolve_logbook_pump_and_outage_rows():
    """The acceptance: pump row → Equipment Event, outage row → Site Event."""
    df = pd.DataFrame([
        {"Date": "2023-05-01", "Heure": "08:30", "Commentaires": "Cleaned pump P-100", "Conductor": "Marie Tremblay"},
        {"Date": "2023-05-02", "Heure": "14:00", "Commentaires": "Building power outage at Pouliot", "Conductor": "Unknown"},
    ])
    result = _resolve_logbook(_resolver(), _LOGBOOK_ROLE_MAP, df)
    assert result["n_resolved"] == 2

    rows = result["row_resolutions"]
    assert rows[0]["target"]["arc_field"] == "equipment_id"
    assert rows[0]["person"]["person_id"] == 3  # conductor matched
    assert rows[1]["target"]["arc_field"] == "site_id"
    assert rows[1]["person"] is None  # unmatched conductor left unset, row still ok

    payloads = _build_event_payloads(rows, event_kind_id=7)
    assert len(payloads) == 2
    # Pump → Equipment-targeted EventIn (exactly one arc FK + the kind + person).
    p0 = payloads[0]
    assert p0["equipment_id"] == 5
    assert p0["event_kind_id"] == 7
    assert p0["performed_by_person_id"] == 3
    assert "site_id" not in p0
    # Outage → Site-targeted, no person.
    p1 = payloads[1]
    assert p1["site_id"] == 2
    assert "equipment_id" not in p1
    assert "performed_by_person_id" not in p1
    # Date + time combined into the start datetime.
    assert p0["start_datetime"].startswith("2023-05-01T08:30")


def test_resolve_logbook_unresolved_target_is_flagged():
    """A row whose comment names no known entity is flagged, not submitted."""
    df = pd.DataFrame([
        {"Date": "2023-05-03", "Heure": "09:00", "Commentaires": "general note", "Conductor": ""},
    ])
    result = _resolve_logbook(_resolver(), _LOGBOOK_ROLE_MAP, df)
    assert result["n_resolved"] == 0
    assert result["n_unresolved"] == 1
    rr = result["row_resolutions"][0]
    assert rr["ok"] is False
    assert rr["target"] is None
    assert _build_event_payloads(result["row_resolutions"], event_kind_id=1) == []
