"""Data Health page coverage (consistency audit F5, F11) via AppTest.

The page surfaces two reconciling reports; assert it warns when each has
findings and reports clean when empty. API calls are mocked.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).parent.parent.parent / "app" / "pages" / "data_health.py")
MOD = "app.pages.data_health"

_UNLINKED = [
    {
        "channel_id": 7,
        "tag_name": "TSS-RAW",
        "signal_interface_id": 3,
        "signal_interface_name": "AI_01",
        "observation_count": 1680,
        "first_observation": "2026-04-01T00:00:00",
        "last_observation": "2026-06-01T00:00:00",
    }
]
_INACTIVE_REFS = [
    {
        "reference_type": "active-wiring->interface",
        "wiring_history_id": 12,
        "equipment_id": 5,
        "parent_id": 3,
        "parent_label": "AI_01",
    }
]


def _warnings(at) -> str:
    return " ".join(w.value for w in at.warning)


def _successes(at) -> str:
    return " ".join(s.value for s in at.success)


def test_warns_when_findings_present():
    with (
        patch("app.api_client.get_unlinked_channels", return_value=_UNLINKED),
        patch("app.api_client.get_inactive_parent_references", return_value=_INACTIVE_REFS),
    ):
        at = AppTest.from_file(PAGE).run()
    assert not at.exception
    warns = _warnings(at)
    assert "1 channel(s)" in warns and "no active equipment wiring" in warns
    assert "1 active wiring row(s)" in warns


def test_reports_clean_when_empty():
    with (
        patch("app.api_client.get_unlinked_channels", return_value=[]),
        patch("app.api_client.get_inactive_parent_references", return_value=[]),
    ):
        at = AppTest.from_file(PAGE).run()
    assert not at.exception
    successes = _successes(at)
    assert "All channels with data are wired" in successes
    assert "No active wiring points at a deactivated" in successes
