"""AppTest for the Explore page-level campaign filter.

Selecting a campaign must scope the whole explorer: snap the time window to the
campaign's span and restrict the picker (picker_campaign_id) to that campaign, so
both the plot and the export inherit the scope.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

HARNESS = str(Path(__file__).parent / "explore_harness.py")
MOD = "app.pages.explore"
DATA = "app.components.explore_data"

_CAMPAIGNS = [{"campaign_id": 1, "name": "Winter 2026"}]
_CAMPAIGN = {"campaign_id": 1, "name": "Winter 2026",
             "start_date": "2026-01-01", "end_date": "2026-04-01"}


def _patches(stack: ExitStack) -> None:
    stack.enter_context(patch(f"{MOD}.list_equipment_lookup", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_annotation_kinds", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_equipment_event_kinds", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_analysis_series_lookup", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_deployment_traces_lookup", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_campaigns_lookup", return_value=_CAMPAIGNS))
    stack.enter_context(patch(f"{MOD}.get_campaign", return_value=_CAMPAIGN))


def test_selecting_campaign_snaps_window_and_restricts_picker():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        at.run()

        at.selectbox(key="explore_campaign_filter_sel").set_value("Winter 2026").run()

        assert at.session_state["explore_campaign_filter_id"] == 1
        # Window snapped to the campaign span (applied via the pending-range flag).
        assert at.session_state["explore_start"] == date(2026, 1, 1)
        assert at.session_state["explore_end"] == date(2026, 4, 1)
        assert not at.exception


def test_clearing_campaign_filter_removes_scope():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_campaign_filter_id"] = 1
        at.run()

        at.selectbox(key="explore_campaign_filter_sel").set_value(
            "📂 All campaigns (no filter)"
        ).run()

        assert at.session_state["explore_campaign_filter_id"] is None
        assert not at.exception
