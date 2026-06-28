"""Reactive-state regressions for the Data Explorer (issue: state resets).

Adding a stream to the plot must not wipe the range-keyed data cache: an
already-plotted stream must NOT be re-fetched when a second stream is added.
Before the fix, both add paths called _invalidate_data_cache(), forcing a full
reload of every active stream on each add (the "data is immediately requested,
which is slow" symptom).
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


def _ts_for(channel_id: int, **_kw) -> dict:
    return {
        "channel_id": channel_id, "parameter": "P", "unit": "mg/L",
        "data_shape": "Scalar", "row_count": 1,
        "data": [{"timestamp": "2026-03-05T00:00:00", "value": 1.0, "quality_code": 1}],
    }


def _stats(channel_id: int) -> dict:
    return {"channel_id": channel_id, "min_timestamp": "2026-03-02T00:00:00",
            "max_timestamp": "2026-03-10T00:00:00", "row_count": 1}


def test_adding_a_stream_does_not_refetch_already_plotted_streams():
    calls: list[int] = []

    def _track(channel_id, **kw):
        calls.append(channel_id)
        return _ts_for(channel_id)

    with ExitStack() as stack:
        stack.enter_context(patch(f"{MOD}.list_equipment_lookup", return_value=_EQUIPMENT))
        stack.enter_context(patch(f"{MOD}.list_annotation_kinds", return_value=[]))
        stack.enter_context(patch(f"{MOD}.list_equipment_event_kinds", return_value=[]))
        stack.enter_context(patch(f"{MOD}.list_analysis_series_lookup", return_value=[]))
        stack.enter_context(
            patch(f"{MOD}.list_deployment_traces_lookup", return_value=[_DT5, _DT6])
        )
        stack.enter_context(patch(f"{DATA}.get_channel_timeseries", side_effect=_track))
        stack.enter_context(
            patch(f"{MOD}.get_channel_stats", side_effect=lambda cid: _stats(cid))
        )

        at = AppTest.from_file(HARNESS)
        # Channel 5 already plotted; first run loads its data once.
        at.session_state["explore_active_channels"] = [5]
        at.session_state["explore_channel_meta"] = {5: _DT5}
        at.session_state["explore_channel_stats"] = {5: _stats(5)}
        at.session_state["explore_start"] = date(2026, 3, 1)
        at.session_state["explore_end"] = date(2026, 3, 15)
        at.run()
        assert not at.exception
        assert calls.count(5) == 1, f"ch5 not loaded exactly once on first run: {calls}"

        # Add channel 6 through the picker, then click "+ Add to plot".
        at.selectbox(key="upicker_trace_select").set_value(
            "Campaign A › Effluent / COD (EQ6)"
        ).run()
        at.button(key="upicker_add_btn").click().run()
        assert not at.exception

        # ch6 was added and loaded; ch5 must NOT have been re-fetched.
        assert 6 in at.session_state["explore_active_channels"]
        assert calls.count(6) == 1, f"ch6 should load once: {calls}"
        assert calls.count(5) == 1, (
            f"ch5 was re-fetched when ch6 was added (cache wiped): {calls}"
        )
