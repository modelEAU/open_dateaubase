"""Data Explorer lab-overlay coverage using streamlit.testing.v1.AppTest.

All API calls mocked; no live server. Verifies the page renders both pickers,
that a lab AnalysisSeries can be added as an active Trace, and that the scalar
overlay figure contains both a sensor line trace and a lab marker trace.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

HARNESS = str(Path(__file__).parent / "explore_harness.py")
MOD = "app.pages.explore"
# Data loaders moved to explore_data; patch the timeseries/stats/annotation API
# calls where those loaders look them up, not in the page namespace.
DATA = "app.components.explore_data"

_EQUIPMENT = [{"equipment_id": 5, "identifier": "EQ5"}]
_SERIES = [
    {"analysis_series_id": 1, "name": "TSS@Eff", "parameter_id": 10,
     "parameter_name": "TSS", "sampling_point_id": 100,
     "sampling_point_label": "Effluent", "unit_id": 1, "unit_name": "mg/L",
     "value_kind_id": 1, "processing_kind_id": 1,
     "campaign_id": 1, "campaign_name": "Campaign A"},
]
_DEPLOYMENT_TRACE = {
    "equipment_location_history_id": 1,
    "channel_id": 5, "equipment_id": 5, "equipment_identifier": "EQ5",
    "sampling_point_id": 100, "sampling_point_label": "Effluent",
    "parameter_id": 10, "parameter_name": "TSS",
    "value_kind_id": 1, "campaign_id": 1, "campaign_name": "Campaign A",
    "valid_from": "2026-01-01T00:00:00", "valid_to": None,
}
_CHANNEL = {
    "channel_id": 5, "equipment_id": 5, "equipment_identifier": "EQ5",
    "parameter_id": 10, "parameter_name": "TSS", "unit_name": "mg/L",
    "value_kind_id": 1,
}
_SERIES_TS = {
    "analysis_series_id": 1, "name": "TSS@Eff", "parameter": "TSS",
    "unit": "mg/L", "sampling_point": "Effluent", "data_shape": "Scalar",
    "processing_degree": "Raw",
    "from_timestamp": "2026-05-01T00:00:00", "to_timestamp": "2026-05-08T00:00:00",
    "row_count": 2,
    "data": [
        {"timestamp": "2026-05-01T00:00:00", "value": 11.0, "quality_code": 1},
        {"timestamp": "2026-05-08T00:00:00", "value": 13.0, "quality_code": 1},
    ],
}
_CHANNEL_TS = {
    "channel_id": 5, "parameter": "TSS", "unit": "mg/L", "data_shape": "Scalar",
    "from_timestamp": "2026-05-01T00:00:00", "to_timestamp": "2026-05-08T00:00:00",
    "row_count": 2,
    "data": [
        {"timestamp": "2026-05-02T00:00:00", "value": 10.0, "quality_code": 1},
        {"timestamp": "2026-05-06T00:00:00", "value": 12.0, "quality_code": 1},
    ],
}


def _patches(stack: ExitStack) -> None:
    stack.enter_context(patch(f"{MOD}.list_equipment_lookup", return_value=_EQUIPMENT))
    stack.enter_context(patch(f"{MOD}.list_annotation_kinds", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_equipment_event_kinds", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_analysis_series_lookup", return_value=_SERIES))
    stack.enter_context(
        patch(f"{MOD}.list_deployment_traces_lookup", return_value=[_DEPLOYMENT_TRACE])
    )
    stack.enter_context(
        patch(f"{DATA}.get_analysis_series_timeseries", return_value=_SERIES_TS)
    )
    stack.enter_context(
        patch(f"{DATA}.get_analysis_series_stats",
              return_value={"analysis_series_id": 1,
                            "min_timestamp": "2026-05-01T00:00:00",
                            "max_timestamp": "2026-05-08T00:00:00", "row_count": 2})
    )
    stack.enter_context(patch(f"{DATA}.get_channel_timeseries", return_value=_CHANNEL_TS))
    stack.enter_context(
        patch(f"{MOD}.get_channel_stats",
              return_value={"channel_id": 5,
                            "min_timestamp": "2026-05-01T00:00:00",
                            "max_timestamp": "2026-05-08T00:00:00", "row_count": 2})
    )


def test_page_renders_with_unified_picker():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS).run()
    assert not at.exception
    labels = [e.label for e in at.expander]
    assert any("Add streams" in (l or "") for l in labels), (
        f"Unified picker expander not found; saw: {labels}"
    )


_IMG_SERIES = {
    "analysis_series_id": 20, "name": "Sludge microscopy", "parameter_id": 16,
    "parameter_name": "floc_morphology", "sampling_point_id": 6,
    "sampling_point_label": "Bioreactor 4", "unit_id": 11, "unit_name": "-",
    "value_kind_id": 4, "processing_kind_id": 1, "campaign_id": 1,
}
_IMG_TS = {
    "analysis_series_id": 20, "name": "Sludge microscopy", "parameter": "floc_morphology",
    "unit": "-", "sampling_point": "Bioreactor 4", "data_shape": "Image",
    "processing_degree": "Raw",
    "from_timestamp": "2026-04-08T02:00:00", "to_timestamp": "2026-04-08T02:00:00",
    "row_count": 2,
    # Two replicates at the SAME sample-collection timestamp — the case that
    # collided widget keys before the fix.
    "data": [
        {"timestamp": "2026-04-08T02:00:00", "image_width": 240, "image_height": 180,
         "number_of_channels": 3, "image_format": "png", "file_size_bytes": 1,
         "storage_backend": "fs", "storage_path": "a.png", "quality_code": 1},
        {"timestamp": "2026-04-08T02:00:00", "image_width": 240, "image_height": 180,
         "number_of_channels": 3, "image_format": "png", "file_size_bytes": 1,
         "storage_backend": "fs", "storage_path": "b.png", "quality_code": 2},
    ],
}


def test_lab_image_replicates_same_timestamp_no_duplicate_key():
    """Regression: two lab images at the same sample-collection time must not
    collide Streamlit widget keys in the image gallery."""
    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(f"{MOD}.list_analysis_series_lookup", return_value=[_IMG_SERIES])
        )
        stack.enter_context(
            patch(f"{DATA}.get_analysis_series_timeseries", return_value=_IMG_TS)
        )
        # Force the caption fallback (no valid image bytes needed); the widget
        # keys under test fire regardless of the image/except branch.
        from app.api_client import APIError
        stack.enter_context(
            patch(f"{MOD}.get_analysis_series_thumbnail",
                  side_effect=APIError(404, "x"))
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [20]
        at.session_state["explore_series_meta"] = {20: _IMG_SERIES}
        at.run()

    assert not at.exception  # would be StreamlitDuplicateElementKey before the fix


_LAB_ANNOTATION = {
    "annotation_id": 1,
    "anchor": {"kind": "series", "id": 1},
    "type": {"id": 3, "name": "Fault", "color": "#FF0000"},
    "start_time": "2026-05-02T00:00:00",
    "end_time": "2026-05-04T00:00:00",
    "title": "Lab QA flag",
    "comment": "Re-run requested.",
    "created_at": "2026-06-10T00:00:00",
}


def test_lab_series_annotation_renders_overlay():
    """With the series-annotations API mocked to return a lab annotation, the
    explore scalar view draws the overlay for the lab Trace: the page renders a
    chart (the vrect/vline are added onto it) and the overlay summary table
    lists the lab annotation row anchored to the series (source LAB-1).

    NOTE: AppTest exposes the plotly element's selection state, not the Figure
    object, so the vrect shape itself can't be asserted directly. We assert the
    overlay_rows entry — the same record produced in lock-step with the vrect in
    the lab render loop — which is the faithful proxy for "the overlay rendered".
    """
    with ExitStack() as stack:
        _patches(stack)
        # The lab annotation loader hits this thin httpx wrapper; mock it.
        stack.enter_context(
            patch(f"{DATA}._api_list_annotations_for_series", return_value=[_LAB_ANNOTATION])
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.run()

    assert not at.exception
    # The overlay summary table lists the lab annotation anchored to LAB-1.
    overlay_tables = [
        df.value for df in at.dataframe
        if "Channel / Equipment" in df.value.columns
    ]
    assert overlay_tables, "no annotation overlay summary table rendered"
    records = overlay_tables[0].to_dict("records")
    assert any(
        r["Channel / Equipment"] == "LAB-1" and r["Title / Notes"] == "Lab QA flag"
        for r in records
    ), f"lab annotation overlay row not found in {records}"


def test_lab_annotation_dialog_is_homogeneous_no_quality_flag_tab():
    """Decision 7 (per-arm, no mixing): opening the annotation dialog for a lab
    AnalysisSeries shows ONLY the annotation form — no 'Quality Flag' tab (quality
    flags are sensor-only). The sensor dialog, by contrast, DOES show both tabs.

    This guards the `is_lab` branch in _annotation_dialog: reverting it (always
    rendering st.tabs(["Annotation", "Quality Flag"])) makes this test fail because
    a 'Quality Flag' tab would appear in the lab dialog.
    """
    # --- lab arm: open the dialog for a lab series, assert no Quality Flag tab ---
    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(f"{MOD}.list_annotation_kinds",
                  return_value=[{"id": 3, "name": "Fault", "color": "#FF0000"}])
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        # Brush-select the lab point so the selection-based annotate button appears
        # (annotations are now selection-driven, not view-range).
        at.session_state["scalar_chart_p1"] = [{"seriesIndex": 0, "dataIndex": [0]}]
        at.run()
        at.button(key="btn_lab_ann_pt_p1").click().run()
        assert not at.exception
        lab_tab_labels = [lbl for t in at.tabs for lbl in (t.label or "",)]
        assert "Quality Flag" not in lab_tab_labels, (
            f"lab annotation dialog must not expose a Quality Flag tab; "
            f"saw tabs {lab_tab_labels}"
        )


def _scalar_view_rendered(at) -> bool:
    """Proxy for 'the scalar ECharts view rendered'. The st_echarts component is
    not introspectable as an AppTest element, so we key off the mode caption that
    _render_scalar_view emits right above the chart."""
    return any(
        (c.value or "").startswith(("Visualization mode", "Extraction mode"))
        for c in at.caption
    )


def test_page_renders_with_active_traces_of_both_sources():
    """With one sensor channel and one lab series active, the scalar overlay
    view renders without error."""
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_channels"] = [5]
        at.session_state["explore_channel_meta"] = {5: _CHANNEL}
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.run()

    assert not at.exception
    assert _scalar_view_rendered(at), "scalar view did not render"


# ---------------------------------------------------------------------------
# Point-pin lab annotation tests (new behavior)
# ---------------------------------------------------------------------------

# Lab timeseries fixture that carries observation_id in each row (required for
# point-pin annotations; the real API now returns this field for every scalar row).
_SERIES_TS_WITH_OBS = {
    **_SERIES_TS,
    "data": [
        {"timestamp": "2026-05-01T00:00:00", "value": 11.0, "quality_code": 1, "observation_id": 42},
        {"timestamp": "2026-05-08T00:00:00", "value": 13.0, "quality_code": 1, "observation_id": 43},
    ],
}

# Simulated ECharts brushSelected return for a single lab marker brush.
# Shape: list of {seriesIndex, dataIndex[]} (what BRUSH_SELECTED_JS returns).
# With only the lab series active it is ECharts seriesIndex 0; dataIndex 0 is the
# first lab point (observation_id 42). resolve_brush_selection maps it back.
_LAB_PT_SELECTION = [{"seriesIndex": 0, "dataIndex": [0]}]


def test_lab_point_selection_shows_pin_button():
    """Pre-seeding the plotly chart selection with a lab point makes the page
    render a 'Create Lab Annotation (point)' button instead of the generic caption.

    Guards: the button only appears because lab_pts is non-empty (customdata[0]=="lab");
    reverting the customdata-discriminator logic or the selection split would make
    lab_pts empty → only the caption renders → this test fails.
    """
    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(f"{DATA}.get_analysis_series_timeseries", return_value=_SERIES_TS_WITH_OBS)
        )
        stack.enter_context(
            patch(f"{MOD}.list_annotation_kinds",
                  return_value=[{"id": 3, "name": "Fault", "color": "#FF0000"}])
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.session_state["scalar_chart_p1"] = _LAB_PT_SELECTION
        at.run()

    assert not at.exception
    btn_keys = [b.key for b in at.button]
    assert "btn_lab_ann_pt_p1" in btn_keys, (
        f"'Create Lab Annotation (point)' button (key=btn_lab_ann_pt) not found; "
        f"got buttons: {btn_keys}"
    )


def test_lab_point_pin_dialog_shows_observation_info():
    """After clicking 'Create Lab Annotation (point)', the dialog shows a pin
    info message that identifies the Observation_ID and value being pinned.

    Guards: if observation_id is not passed to _annotation_dialog or the info
    block is removed, the st.info call doesn't fire → no matching info text → fail.
    """
    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(f"{DATA}.get_analysis_series_timeseries", return_value=_SERIES_TS_WITH_OBS)
        )
        stack.enter_context(
            patch(f"{MOD}.list_annotation_kinds",
                  return_value=[{"id": 3, "name": "Fault", "color": "#FF0000"}])
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.session_state["scalar_chart_p1"] = _LAB_PT_SELECTION
        at.run()
        # Click the point-pin button to open the dialog
        at.button(key="btn_lab_ann_pt_p1").click().run()

    assert not at.exception
    info_texts = [i.value for i in at.info]
    assert any("42" in t for t in info_texts), (
        f"expected an info box mentioning Observation #42; got info texts: {info_texts}"
    )


def test_lab_point_pin_dialog_called_with_observation_id():
    """Clicking 'Create Lab Annotation (point)' calls _annotation_dialog with
    observation_id=42 (the id from the pre-seeded chart selection).

    Guards: if the selection block doesn't extract observation_id from customdata[2]
    and pass it through, the mock won't see observation_id=42 → test fails.
    This is the teeth-test: reverting the `single_lab_obs_id = cd[2]` assignment
    makes _annotation_dialog receive observation_id=None → assertion fails.
    """
    captured: dict = {}

    def _capture_dialog(**kwargs):
        captured.update(kwargs)

    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(f"{DATA}.get_analysis_series_timeseries", return_value=_SERIES_TS_WITH_OBS)
        )
        stack.enter_context(
            patch(f"{MOD}.list_annotation_kinds",
                  return_value=[{"id": 3, "name": "Fault", "color": "#FF0000"}])
        )
        stack.enter_context(
            patch(f"{MOD}._annotation_dialog", side_effect=_capture_dialog)
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.session_state["scalar_chart_p1"] = _LAB_PT_SELECTION
        at.run()
        at.button(key="btn_lab_ann_pt_p1").click().run()

    assert not at.exception
    assert captured, "expected _annotation_dialog to have been called"
    assert captured.get("observation_id") == 42, (
        f"expected observation_id=42 passed to dialog; got kwargs: {captured}"
    )
    assert captured.get("series_ids") == [1], (
        f"expected series_ids=[1]; got: {captured}"
    )


def test_lab_annotation_dialog_save_uses_stream_anchored_create_annotation():
    """The lab annotation dialog Save path calls the new stream-anchored
    create_annotation(stream_id=…, data=…, anchor_kind="series") signature —
    NOT a raw httpx POST against /analysis-series/{id}/annotations.

    Drives _annotation_dialog directly inside a minimal AppTest script so the
    dialog's Save button is reachable in a single run. Guards the Slice 15
    migration: reverting the Save path to the old raw POST makes create_annotation
    go uncalled and this fails.
    """
    captured: dict = {}

    def _capture_create(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"annotation_id": 99}

    def _script() -> None:
        import sys
        from pathlib import Path

        _root = str(Path(__file__).parent.parent.parent)
        if _root not in sys.path:
            sys.path.insert(0, _root)
        from app.pages import explore as ex

        ex._annotation_dialog(
            channel_ids=[],
            series_ids=[1],
            start_time="2026-05-01T00:00:00",
            end_time="2026-05-08T00:00:00",
            annotation_types=[{"id": 3, "name": "Fault", "color": "#FF0000"}],
        )

    with patch(f"{MOD}.create_annotation", side_effect=_capture_create):
        at = AppTest.from_function(_script).run()
        # The dialog renders inline; click its Save button.
        at.button(key="btn_save_ann").click().run()

    assert not at.exception
    assert captured, "create_annotation was not called from the dialog Save path"
    kwargs = captured["kwargs"]
    assert kwargs.get("stream_id") == 1, (
        f"expected stream_id=1 (the series Stream_ID); got {captured}"
    )
    assert kwargs.get("anchor_kind") == "series", (
        f"expected anchor_kind='series' for a lab stream; got {captured}"
    )
    assert "data" in kwargs and isinstance(kwargs["data"], dict), (
        f"expected the annotation payload passed as data=…; got {captured}"
    )


# ---------------------------------------------------------------------------
# Time-range quick-select regression
# ---------------------------------------------------------------------------


def test_last_7d_button_updates_date_inputs():
    """Regression: clicking 'Last 7d' must update the keyed From/To date inputs
    so the plot uses the selected range instead of the stale UI values."""
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_channels"] = [5]
        at.session_state["explore_channel_meta"] = {5: _CHANNEL}
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.run()
        at.button(key="tstrip_7d").click().run()

    assert not at.exception
    from_date = at.date_input(key="explore_start").value
    to_date = at.date_input(key="explore_end").value
    assert from_date == date(2026, 5, 1), (
        f"expected From=2026-05-01 after Last 7d, got {from_date}"
    )
    assert to_date == date(2026, 5, 8), (
        f"expected To=2026-05-08 after Last 7d, got {to_date}"
    )


# ---------------------------------------------------------------------------
# Provenance panel layout regression
# ---------------------------------------------------------------------------

_PROV_GRAPH = {
    "root_id": 5,
    "nodes": [
        {
            "stream_id": 5,
            "kind": "channel",
            "label": "TSS raw",
            "is_derived": False,
            "provenance_kind_name": "Sensor",
            "traits": [],
            "channel_id": 5,
            "analysis_series_id": None,
        },
    ],
    "ancestors": [],
    "descendants": [],
}


def test_provenance_panel_renders_in_global_layout():
    """When a provenance trail is active, the page should render the chart in
    the main body and the provenance panel in the right-hand sidebar column
    without throwing."""
    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(
                "app.components.explore_provenance.get_stream_provenance",
                return_value=_PROV_GRAPH,
            )
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_channels"] = [5]
        at.session_state["explore_channel_meta"] = {5: _CHANNEL}
        at.session_state["explore_inspect_trail"] = [("channel", 5)]
        at.run()

    assert not at.exception
    assert _scalar_view_rendered(at), "chart should still render in the global layout"
    headers = [h.value for h in at.subheader]
    assert any("Provenance" in h for h in headers), (
        f"provenance panel header not found; got {headers}"
    )


