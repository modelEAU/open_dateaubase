"""Unit tests for PRD-4 S4 — drift read-back derivation (before/after + %diff).

Acceptance: the drift Channel shows before/after derived from the *source*
stream around the event window. These cover the pure derivation: last reading
before the window is "before" (fouled), first after is "after" (clean), with a
guarded percent-drift.
"""

from __future__ import annotations

from datetime import datetime, timezone

from api.v1.repositories.maintenance_drift_repository import derive_before_after


def _dt(day: int, hour: int = 0) -> datetime:
    return datetime(2023, 6, day, hour, tzinfo=timezone.utc)


def _row(day: int, value, hour: int = 0) -> dict:
    return {"timestamp": _dt(day, hour), "value": value}


def test_before_is_last_pre_window_after_is_first_post_window():
    rows = [
        _row(1, 10.0),   # before (older)
        _row(4, 12.0),   # before (nearest before start) → picked
        _row(5, 99.0),   # inside window (start=5, end=6) → ignored
        _row(7, 6.0),    # after (nearest after end) → picked
        _row(9, 5.0),    # after (later)
    ]
    result = derive_before_after(rows, window_start=_dt(5), window_end=_dt(6))
    assert result["before"]["value"] == 12.0
    assert result["after"]["value"] == 6.0
    # Drift: (6 - 12) / 12 * 100 = -50%
    assert result["percent_diff"] == -50.0


def test_instantaneous_event_uses_start_for_both_sides():
    rows = [_row(4, 8.0), _row(5, 4.0)]  # window is instantaneous at day 5
    result = derive_before_after(rows, window_start=_dt(5), window_end=None)
    assert result["before"]["value"] == 8.0
    assert result["after"]["value"] == 4.0
    assert result["percent_diff"] == -50.0


def test_missing_side_yields_none_and_no_percent():
    rows = [_row(4, 8.0)]  # nothing after the window
    result = derive_before_after(rows, window_start=_dt(5), window_end=_dt(6))
    assert result["before"]["value"] == 8.0
    assert result["after"] is None
    assert result["percent_diff"] is None


def test_zero_baseline_guards_percent():
    rows = [_row(4, 0.0), _row(7, 3.0)]
    result = derive_before_after(rows, window_start=_dt(5), window_end=_dt(6))
    assert result["before"]["value"] == 0.0
    assert result["after"]["value"] == 3.0
    assert result["percent_diff"] is None  # no divide-by-zero


def test_empty_rows_are_all_none():
    result = derive_before_after([], window_start=_dt(5), window_end=_dt(6))
    assert result == {"before": None, "after": None, "percent_diff": None}
