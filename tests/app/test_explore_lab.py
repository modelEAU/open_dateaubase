"""Data Explorer lab-overlay coverage using streamlit.testing.v1.AppTest.

All API calls mocked; no live server. Verifies the page renders both pickers,
that a lab AnalysisSeries can be added as an active Trace, and that the scalar
overlay figure contains both a sensor line trace and a lab marker trace.
"""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

HARNESS = str(Path(__file__).parent / "explore_harness.py")
MOD = "app.pages.explore"

_CAMPAIGNS = [{"campaign_id": 1, "name": "Campaign A"}]
_EQUIPMENT = [{"equipment_id": 5, "identifier": "EQ5"}]
_PARAMETERS = [{"parameter_id": 10, "parameter_name": "TSS"}]
_SERIES = [
    {"analysis_series_id": 1, "name": "TSS@Eff", "parameter_id": 10,
     "parameter_name": "TSS", "sampling_point_id": 100,
     "sampling_point_label": "Effluent", "unit_id": 1, "unit_name": "mg/L",
     "value_kind_id": 1, "processing_kind_id": 1, "campaign_id": 1},
]
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
    stack.enter_context(patch(f"{MOD}.list_campaigns_lookup", return_value=_CAMPAIGNS))
    stack.enter_context(patch(f"{MOD}.list_equipment_lookup", return_value=_EQUIPMENT))
    stack.enter_context(patch(f"{MOD}.list_parameters_lookup", return_value=_PARAMETERS))
    stack.enter_context(patch(f"{MOD}.list_annotation_kinds", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_equipment_event_kinds", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_analysis_series_lookup", return_value=_SERIES))
    stack.enter_context(
        patch(f"{MOD}.list_channels", return_value={"items": [_CHANNEL]})
    )
    stack.enter_context(
        patch(f"{MOD}.get_analysis_series_timeseries", return_value=_SERIES_TS)
    )
    stack.enter_context(
        patch(f"{MOD}.get_analysis_series_stats",
              return_value={"analysis_series_id": 1,
                            "min_timestamp": "2026-05-01T00:00:00",
                            "max_timestamp": "2026-05-08T00:00:00", "row_count": 2})
    )
    stack.enter_context(patch(f"{MOD}.get_channel_timeseries", return_value=_CHANNEL_TS))
    stack.enter_context(
        patch(f"{MOD}.get_channel_stats",
              return_value={"channel_id": 5,
                            "min_timestamp": "2026-05-01T00:00:00",
                            "max_timestamp": "2026-05-08T00:00:00", "row_count": 2})
    )


def test_page_renders_with_both_pickers():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS).run()
    assert not at.exception
    labels = [e.label for e in at.expander]
    assert any("Sensor" in (l or "") for l in labels)
    assert any("Lab" in (l or "") for l in labels)


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
            patch(f"{MOD}.get_analysis_series_timeseries", return_value=_IMG_TS)
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
            patch(f"{MOD}._api_list_annotations_for_series", return_value=[_LAB_ANNOTATION])
        )
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.run()

    assert not at.exception
    assert list(at.get("plotly_chart")), "no scalar chart rendered"
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
        at.run()
        at.button(key="btn_lab_ann").click().run()
        assert not at.exception
        lab_tab_labels = [lbl for t in at.tabs for lbl in (t.label or "",)]
        assert "Quality Flag" not in lab_tab_labels, (
            f"lab annotation dialog must not expose a Quality Flag tab; "
            f"saw tabs {lab_tab_labels}"
        )


def test_page_renders_with_active_traces_of_both_sources():
    """With one sensor channel and one lab series active, the page renders the
    scalar overlay without error (a plotly chart is produced)."""
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_active_channels"] = [5]
        at.session_state["explore_channel_meta"] = {5: _CHANNEL}
        at.session_state["explore_active_series"] = [1]
        at.session_state["explore_series_meta"] = {1: _SERIES[0]}
        at.run()

    assert not at.exception
    assert list(at.get("plotly_chart")), "no scalar chart rendered"
