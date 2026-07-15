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
        {"timestamp": "2026-04-08T02:00:00", "observation_id": 501,
         "image_width": 240, "image_height": 180,
         "number_of_channels": 3, "image_format": "png", "file_size_bytes": 1,
         "storage_backend": "fs", "storage_path": "a.png", "quality_code": 1},
        {"timestamp": "2026-04-08T02:00:00", "observation_id": 502,
         "image_width": 240, "image_height": 180,
         "number_of_channels": 3, "image_format": "png", "file_size_bytes": 1,
         "storage_backend": "fs", "storage_path": "b.png", "quality_code": 2},
    ],
}


def _image_view_patches(stack: ExitStack, annotations: list[dict] | None = None):
    """Drive the image view off the lab microscopy series above. Thumbnails 404 so
    the gallery takes its caption fallback — no real JPEG bytes needed."""
    from app.api_client import APIError

    _patches(stack)
    stack.enter_context(
        patch(f"{MOD}.list_analysis_series_lookup", return_value=[_IMG_SERIES])
    )
    stack.enter_context(
        patch(f"{DATA}.get_analysis_series_timeseries", return_value=_IMG_TS)
    )
    stack.enter_context(
        patch(f"{MOD}.get_image_thumbnail", side_effect=APIError(404, "x"))
    )
    stack.enter_context(
        patch(f"{DATA}._api_list_annotations_for_series", return_value=annotations or [])
    )


def test_lab_image_replicates_same_timestamp_no_duplicate_key():
    """Regression: two lab images at the same sample-collection time must not
    collide Streamlit widget keys in the image gallery."""
    with ExitStack() as stack:
        _image_view_patches(stack)
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


def test_image_view_offers_recording_for_a_lab_series():
    """The image view used to gate annotation on `is_channel`, so a lab image
    series (the only kind we actually store images for) could not be recorded on.
    Recording replaces the old annotate/equipment-event pair with one button."""
    with ExitStack() as stack:
        _image_view_patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [20]
        at.session_state["explore_series_meta"] = {20: _IMG_SERIES}
        at.session_state["explore_selected_images"] = [501]
        at.run()

    assert not at.exception
    labels = [b.label for b in at.button]
    assert "Record what happened" in labels
    # The standalone equipment-event dialog is gone (ticket 007).
    assert "Tag equipment event" not in labels


def test_image_view_renders_the_annotation_overlay_table():
    """Annotations on an image series were invisible: no bands on the timeline and
    no summary table, unlike every other value-type view."""
    with ExitStack() as stack:
        _image_view_patches(stack, annotations=[_LAB_ANNOTATION])
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [20]
        at.session_state["explore_series_meta"] = {20: _IMG_SERIES}
        at.run()

    assert not at.exception
    overlay = [
        df.value for df in at.dataframe if "Channel / Equipment" in df.value.columns
    ]
    assert overlay, "image view rendered no annotation overlay table"
    records = overlay[0].to_dict("records")
    assert any(
        r["Channel / Equipment"] == "LAB-20" and r["Title / Notes"] == "Lab QA flag"
        for r in records
    ), records


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


def test_lab_selection_offers_record_but_no_quality_code_button():
    """Quality flags are sensor-only: a lab selection gets the Record button but
    no 'Set quality code…' button (the old is_lab special case, now gone with the
    Quality Flag tab — ticket 007)."""
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        # Brush-select the lab point so the selection-based buttons appear.
        at.session_state["scalar_chart_p1"] = [{"seriesIndex": 0, "dataIndex": [0]}]
        at.run()

    assert not at.exception
    keys = [b.key for b in at.button]
    assert "btn_record_p1" in keys, "lab selection should offer Record"
    assert "btn_qc_p1" not in keys, "quality-code button is sensor-only"


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


def test_lab_point_selection_shows_record_button():
    """Pre-seeding the chart selection with a lab point renders the Record button
    instead of the generic caption — the selection is the recording target."""
    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(f"{DATA}.get_analysis_series_timeseries", return_value=_SERIES_TS_WITH_OBS)
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.session_state["scalar_chart_p1"] = _LAB_PT_SELECTION
        at.run()

    assert not at.exception
    assert "btn_record_p1" in [b.key for b in at.button]


def test_lab_point_record_passes_observation_id_to_dialog():
    """Clicking Record on a single lab point opens _recording_dialog pinned to
    that exact observation (id 42 from the pre-seeded selection) for the series."""
    captured: dict = {}

    with ExitStack() as stack:
        _patches(stack)
        stack.enter_context(
            patch(f"{DATA}.get_analysis_series_timeseries", return_value=_SERIES_TS_WITH_OBS)
        )
        stack.enter_context(
            patch(f"{MOD}._recording_dialog", side_effect=lambda **kw: captured.update(kw))
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.session_state["scalar_chart_p1"] = _LAB_PT_SELECTION
        at.run()
        at.button(key="btn_record_p1").click().run()

    assert not at.exception
    assert captured, "expected _recording_dialog to have been called"
    assert captured.get("observation_id") == 42, captured
    assert captured.get("streams") == [("series", 1)], captured


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


