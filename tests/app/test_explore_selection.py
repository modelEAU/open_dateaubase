"""Selection-driven Recording on the Explore scalar view (wayfinder 004/007/008).

Brushing points must (a) list them in a table and (b) open the Recording dialog
against exactly the selected streams — the rung the user then picks routes the
write (stream rung → Annotation, any other rung → Event on one arc FK).
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


def _meta(ch_id: int, eq: str, param: str) -> dict:
    return {
        "channel_id": ch_id, "equipment_id": ch_id, "equipment_identifier": eq,
        "parameter_id": ch_id, "parameter_name": param, "unit_name": "mg/L",
        "value_kind_id": 1, "sampling_point_label": "Effluent",
        "campaign_name": "Campaign A",
    }


_M5 = _meta(5, "EQ5", "TSS")
_M6 = _meta(6, "EQ6", "COD")


def _ts(ch_id: int, **_kw) -> dict:
    return {
        "channel_id": ch_id, "parameter": "P", "unit": "mg/L", "row_count": 2,
        "data": [
            {"timestamp": "2026-05-02T00:00:00", "value": 10.0, "quality_code": 1,
             "observation_id": ch_id * 100 + 1},
            {"timestamp": "2026-05-03T00:00:00", "value": 12.0, "quality_code": 1,
             "observation_id": ch_id * 100 + 2},
        ],
    }


def _patches(stack: ExitStack) -> None:
    stack.enter_context(patch(f"{MOD}.list_analysis_series_lookup", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_deployment_traces_lookup", return_value=[]))
    stack.enter_context(patch(f"{DATA}.get_channel_timeseries", side_effect=_ts))
    stack.enter_context(
        patch(f"{MOD}.get_channel_stats",
              side_effect=lambda cid: {"channel_id": cid,
                                       "min_timestamp": "2026-05-02T00:00:00",
                                       "max_timestamp": "2026-05-03T00:00:00",
                                       "row_count": 2})
    )
    stack.enter_context(patch(f"{DATA}._api_list_annotations_for_channel", return_value=[]))
    stack.enter_context(patch(f"{DATA}.get_equipment_events", return_value=[]))


def test_selected_points_listed_in_a_table():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_channels"] = [5]
        at.session_state["explore_channel_meta"] = {5: _M5}
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        # Each sensor renders as a decorative line (seriesIndex 0) + a brushable
        # marker scatter (seriesIndex 1) that carries identity. Brush the markers.
        at.session_state["scalar_chart_p1"] = [{"seriesIndex": 1, "dataIndex": [0, 1]}]
        at.run()

    assert not at.exception
    sel_tables = [
        df.value for df in at.dataframe
        if "Observation" in getattr(df.value, "columns", [])
    ]
    assert sel_tables, "selection table not rendered"
    recs = sel_tables[0].to_dict("records")
    assert {r["Observation"] for r in recs} == {501, 502}
    assert all(r["Stream"] == "CH-5" for r in recs)


def test_record_button_opens_dialog_for_selected_streams_only():
    """Two sensor channels active; brushing a point on CH-5 only opens Recording
    against CH-5 alone — the selection is the target, not the whole plot."""
    captured: dict = {}

    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(f"{MOD}._recording_dialog", side_effect=lambda **kw: captured.update(kw))
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_channels"] = [5, 6]
        at.session_state["explore_channel_meta"] = {5: _M5, 6: _M6}
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        # Per channel: decorative line + marker scatter. CH-5 markers are at
        # seriesIndex 1 (0=CH-5 line, 1=CH-5 markers, 2=CH-6 line, 3=CH-6 markers).
        at.session_state["scalar_chart_p1"] = [{"seriesIndex": 1, "dataIndex": [0]}]
        at.run()
        at.button(key="btn_record_p1").click().run()

    assert not at.exception
    assert captured, "recording dialog not opened"
    assert captured.get("streams") == [("channel", 5)], (
        f"recording should target only the selected stream CH-5; got {captured.get('streams')}"
    )
    # A single selected point pins to its exact observation.
    assert captured.get("observation_id") == 501


def test_quality_flag_button_is_sensor_only():
    """The 'Set quality code…' gesture (an edit, not a recording) appears for a
    selected sensor point and is separate from Record."""
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_channels"] = [5]
        at.session_state["explore_channel_meta"] = {5: _M5}
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        at.session_state["scalar_chart_p1"] = [{"seriesIndex": 1, "dataIndex": [0]}]
        at.run()

    assert not at.exception
    keys = [b.key for b in at.button]
    assert "btn_record_p1" in keys
    assert "btn_qc_p1" in keys, "sensor selection should offer a quality-code button"
