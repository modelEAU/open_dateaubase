"""Selection-driven behavior on the Explore scalar view.

Brushing points must (a) list them in a table and (b) drive annotation against
only the selected streams/points — never the plotted view range.
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
    stack.enter_context(patch(f"{MOD}.list_equipment_lookup", return_value=_EQUIPMENT))
    stack.enter_context(
        patch(f"{MOD}.list_annotation_kinds",
              return_value=[{"id": 3, "name": "Fault", "color": "#FF0000"}])
    )
    stack.enter_context(patch(f"{MOD}.list_equipment_event_kinds", return_value=[]))
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
        # Brush both points of the single sensor series (seriesIndex 0).
        at.session_state["scalar_chart_p1"] = [{"seriesIndex": 0, "dataIndex": [0, 1]}]
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


def test_equipment_event_button_always_available_and_lists_selected_equipment():
    """The equipment-event button is no longer gated behind a selection, and the
    selected equipment is listed so it's clear what an event would target."""
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_channels"] = [5]
        at.session_state["explore_channel_meta"] = {5: _M5}
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        at.run()
        # No selection yet — the equipment-event button is still present.
        assert "btn_eq_event_p1" in [b.key for b in at.button]

        # Select a CH-5 point; its equipment (EQ5) is now listed.
        at.session_state["scalar_chart_p1"] = [{"seriesIndex": 0, "dataIndex": [0]}]
        at.run()
        assert "btn_eq_event_p1" in [b.key for b in at.button]
        body = " ".join((m.value or "") for m in at.markdown)
        assert "EQ5" in body, "selected equipment identifier not shown"


def test_annotation_scoped_to_selected_stream_only():
    """Two sensor channels active; brushing a point on CH-5 only must annotate
    CH-5 alone — not every channel in the plot (the old view-range behavior)."""
    captured: dict = {}

    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(f"{MOD}._annotation_dialog", side_effect=lambda **kw: captured.update(kw))
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_channels"] = [5, 6]
        at.session_state["explore_channel_meta"] = {5: _M5, 6: _M6}
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        # seriesIndex 0 == CH-5 (first added). Select its first point only.
        at.session_state["scalar_chart_p1"] = [{"seriesIndex": 0, "dataIndex": [0]}]
        at.run()
        at.button(key="btn_sensor_ann_p1").click().run()

    assert not at.exception
    assert captured, "annotation dialog not opened"
    assert captured.get("channel_ids") == [5], (
        f"annotation should target only the selected stream CH-5; got {captured.get('channel_ids')}"
    )
    # Single selected point pins to its exact observation.
    assert captured.get("observation_id") == 501
