"""F8 regression: movers must reject a move to the destination already active.

relocate_equipment / rewire_equipment / deploy_das previously closed the active
row and opened an identical one when asked to move equipment to where it already
was, producing churn rows (and spurious annotations downstream). Each now raises
ValueError before touching the DB.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from api.v1.repositories import temporal_history_repository as thr

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _conn_that_must_not_execute(monkeypatch, helper_name, active_row):
    """Patch the active-row helper and return a conn whose .cursor() blows up if
    the guard fails to short-circuit (proving no DB writes happen)."""
    monkeypatch.setattr(thr, helper_name, lambda *a, **k: active_row)

    class _Boom:
        def cursor(self):
            raise AssertionError("guard did not short-circuit; DB was touched")

        def commit(self):
            raise AssertionError("guard did not short-circuit; commit was called")

    return _Boom()


def test_relocate_to_current_sampling_point_raises(monkeypatch):
    conn = _conn_that_must_not_execute(
        monkeypatch,
        "get_active_location_for_equipment",
        {"sampling_point_id": 8},
    )
    with pytest.raises(ValueError, match="already located"):
        thr.relocate_equipment(conn, equipment_id=1, new_sampling_point_id=8,
                               start_time=NOW, campaign_id=2)


def test_rewire_to_current_interface_and_port_raises(monkeypatch):
    conn = _conn_that_must_not_execute(
        monkeypatch,
        "get_active_wiring_for_equipment",
        {"signal_interface_id": 5, "signal_interface_port_id": 3},
    )
    with pytest.raises(ValueError, match="already wired"):
        thr.rewire_equipment(conn, equipment_id=1, new_signal_interface_id=5,
                             new_signal_interface_port_id=3, swap_time=NOW)


def test_redeploy_das_to_current_site_raises(monkeypatch):
    conn = _conn_that_must_not_execute(
        monkeypatch,
        "get_active_das_deployment",
        {"site_id": 4},
    )
    with pytest.raises(ValueError, match="already deployed"):
        thr.deploy_das(conn, das_id=1, site_id=4, valid_from=NOW)


def test_rewire_to_different_port_same_interface_is_allowed(monkeypatch):
    """Port-only change must NOT be treated as a no-op (mux re-patch is real)."""
    monkeypatch.setattr(
        thr, "get_active_wiring_for_equipment",
        lambda *a, **k: {"signal_interface_id": 5, "signal_interface_port_id": 3},
    )
    # A different port → guard passes → cursor is used. Minimal mock for the path.
    from unittest.mock import MagicMock

    conn = MagicMock()
    cursor = MagicMock()
    # F7 interval guard (no conflict), then: no row closed, new id.
    cursor.fetchone.side_effect = [None, None, (99,)]
    conn.cursor.return_value = cursor

    new_id, closed_id = thr.rewire_equipment(
        conn, equipment_id=1, new_signal_interface_id=5,
        new_signal_interface_port_id=4, swap_time=NOW,
    )
    assert new_id == 99 and closed_id is None
