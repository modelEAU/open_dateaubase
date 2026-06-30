"""Unit tests for PRD-4 S2 — target-resolution confirm UX (deterministic core).

Acceptance: ambiguous entries are never auto-guessed into the wrong target —
the user confirms. These cover the pure logic behind the confirm UI: the level
heuristic (a *hint* only) and the override application that turns a confirmed
pick into a submittable row.
"""

from __future__ import annotations

from app.components.resolver import TARGET_LEVELS, guess_target_level
from app.pages.mapper import (
    _apply_target_override,
    _make_target,
    _override_targets,
)


def test_guess_target_level_is_a_hint_not_a_resolution():
    # Equipment-style tag → Equipment.
    assert guess_target_level("replaced P-205 seal") == "Equipment"
    assert guess_target_level("LDO-241 drift") == "Equipment"
    # Keyword → Site / ProcessUnit.
    assert guess_target_level("building power outage") == "Site"
    assert guess_target_level("PLC rebooted") == "ProcessUnit"
    # No signal → no guess (so the UI defaults to nothing auto-applied).
    assert guess_target_level("misc note") is None
    assert guess_target_level("") is None


def _row(idx: int, *, ok: bool, has_date: bool = True) -> dict:
    return {
        "row_index": idx,
        "start_datetime": object() if has_date else None,
        "notes": "n",
        "title": "t",
        "person": None,
        "person_text": "",
        "target": None,
        "errors": [] if ok else ["no target resolved from comment — pick one before submit"],
        "ok": ok,
    }


def test_apply_override_makes_row_submittable_and_clears_flag():
    rr = _row(0, ok=False)
    target = _make_target("Equipment", {"id": 5, "label": "P-205"})
    out = _apply_target_override(rr, target)
    assert out["ok"] is True
    assert out["target"]["arc_field"] == "equipment_id"
    assert out["target"]["entity_id"] == 5
    # The stale "no target resolved" flag is dropped once confirmed.
    assert not any("no target resolved" in e for e in out["errors"])
    # Original row is untouched (pure function).
    assert rr["ok"] is False


def test_override_without_date_stays_unsubmittable():
    rr = _row(1, ok=False, has_date=False)
    out = _apply_target_override(rr, _make_target("Site", {"id": 2, "label": "Pouliot"}))
    assert out["ok"] is False  # no date → still not submittable


def test_override_targets_recomputes_counts():
    rows = [_row(0, ok=False), _row(1, ok=True), _row(2, ok=False)]
    rows[1]["target"] = _make_target("Site", {"id": 2, "label": "Pouliot"})
    overrides = {0: _make_target("Equipment", {"id": 5, "label": "P-205"})}
    out, n_resolved, n_unresolved = _override_targets(rows, overrides)
    assert n_resolved == 2  # row 0 (overridden) + row 1 (already ok)
    assert n_unresolved == 1  # row 2 still unconfirmed
    assert out[0]["target"]["entity_id"] == 5


def test_make_target_uses_the_arc_field_for_the_level():
    for level, arc in TARGET_LEVELS.items():
        t = _make_target(level, {"id": 1, "label": "x"})
        assert t["arc_field"] == arc
        assert t["level"] == level
