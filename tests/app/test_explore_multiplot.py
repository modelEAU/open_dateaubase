"""Multi-plot workspace coverage for the Data Explorer.

Streams stay in the canonical active_* lists; a thin assignment layer groups
them across scalar plots. Verifies: new streams land in the target plot, "Add
plot" switches the target, and the per-chip move control reassigns a stream.
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

_EQUIPMENT = [{"equipment_id": 5, "identifier": "EQ5"}]


def _trace(ch_id: int, eq: str, param: str) -> dict:
    return {
        "equipment_location_history_id": ch_id,
        "channel_id": ch_id, "equipment_id": ch_id, "equipment_identifier": eq,
        "sampling_point_id": 100, "sampling_point_label": "Effluent",
        "parameter_id": ch_id, "parameter_name": param,
        "value_kind_id": 1, "campaign_id": 1, "campaign_name": "Campaign A",
        "valid_from": "2026-01-01T00:00:00", "valid_to": None,
    }


_DT5 = _trace(5, "EQ5", "TSS")
_DT6 = _trace(6, "EQ6", "COD")
_TS = {"channel_id": 0, "parameter": "P", "unit": "mg/L", "row_count": 1,
       "data": [{"timestamp": "2026-05-02T00:00:00", "value": 1.0, "quality_code": 1}]}
_STATS = {"min_timestamp": "2026-05-01T00:00:00", "max_timestamp": "2026-05-08T00:00:00",
          "row_count": 1}


def _patches(stack: ExitStack) -> None:
    stack.enter_context(patch(f"{MOD}.list_analysis_series_lookup", return_value=[]))
    stack.enter_context(
        patch(f"{MOD}.list_deployment_traces_lookup", return_value=[_DT5, _DT6])
    )
    stack.enter_context(patch(f"{DATA}.get_channel_timeseries", return_value=_TS))
    stack.enter_context(
        patch(f"{MOD}.get_channel_stats", side_effect=lambda cid: {"channel_id": cid, **_STATS})
    )


def test_add_plot_switches_target_and_new_streams_land_there():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        at.run()

        # Add the first stream (default picker selection = CH-5) -> plot 1.
        at.button(key="upicker_add_btn").click().run()
        assert at.session_state["explore_plot_of"] == {"ch:5": 1}
        assert at.session_state["explore_plots"] == [1]

        # Add a plot -> it becomes the target.
        at.button(key="btn_add_plot").click().run()
        assert at.session_state["explore_plots"] == [1, 2]
        assert at.session_state["explore_target_plot"] == 2

        # Add the second stream -> lands in plot 2.
        at.selectbox(key="upicker_trace_select").set_value(
            "Campaign A › Effluent / COD (EQ6)"
        ).run()
        at.button(key="upicker_add_btn").click().run()
        assert at.session_state["explore_plot_of"]["ch:6"] == 2
        assert not at.exception


def test_per_chip_move_control_reassigns_stream():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        # Two channels, both in plot 1; a second (empty) plot exists.
        at.session_state["explore_active_channels"] = [5, 6]
        at.session_state["explore_channel_meta"] = {5: _DT5, 6: _DT6}
        at.session_state["explore_plots"] = [1, 2]
        at.session_state["explore_next_plot_id"] = 3
        at.session_state["explore_plot_of"] = {"ch:5": 1, "ch:6": 1}
        at.run()

        # Move CH-6 to Plot 2 via its chip selectbox.
        at.selectbox(key="move_ch_6").set_value("Plot 2").run()
        assert at.session_state["explore_plot_of"]["ch:6"] == 2
        assert at.session_state["explore_plot_of"]["ch:5"] == 1
        assert not at.exception


def test_delete_plot_badge_reassigns_its_streams_to_first_plot():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        at.session_state["explore_active_channels"] = [5, 6]
        at.session_state["explore_channel_meta"] = {5: _DT5, 6: _DT6}
        at.session_state["explore_plots"] = [1, 2]
        at.session_state["explore_next_plot_id"] = 3
        at.session_state["explore_plot_of"] = {"ch:5": 1, "ch:6": 2}
        at.run()

        # Delete Plot 2 via its badge ✕ — the plot is removed and its stream
        # (CH-6) falls back to the first remaining plot (not deleted).
        at.button(key="delplot_2").click().run()
        assert at.session_state["explore_plots"] == [1]
        assert at.session_state["explore_plot_of"]["ch:6"] == 1
        assert 6 in at.session_state["explore_active_channels"]
        assert not at.exception
