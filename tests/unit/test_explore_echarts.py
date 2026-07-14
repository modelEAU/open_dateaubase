"""Unit tests for the ECharts scalar builder + brush-selection resolver.

These cover the decision-bearing logic of the Explore scalar rewrite. The
``st_echarts`` component round-trip itself needs a browser and is verified
separately; everything here is pure.
"""

from __future__ import annotations

from unittest.mock import patch

from app.components import explore_echarts as ee

_MOD = "app.components.explore_echarts"

_CH_META = {
    5: {"value_kind_id": 1, "equipment_identifier": "EQ5", "parameter_name": "TSS",
        "unit_name": "mg/L", "equipment_id": 5},
}
_S_META = {
    1: {"analysis_series_id": 1, "name": "TSS@Eff", "parameter_name": "TSS",
        "sampling_point_label": "Effluent", "unit_name": "mg/L", "value_kind_id": 1},
}
_CH_TS = {"data": [
    {"timestamp": "2026-05-02T00:00:00", "value": 10.0, "quality_code": 1, "observation_id": 901},
    {"timestamp": "2026-05-03T00:00:00", "value": 12.0, "quality_code": 2, "observation_id": 902},
]}
_S_TS = {"data": [
    {"timestamp": "2026-05-01T00:00:00", "value": 11.0, "quality_code": 1, "observation_id": 701},
    {"timestamp": "2026-05-08T00:00:00", "value": 13.0, "quality_code": 1, "observation_id": 702},
]}


def _build(**overrides):
    loaders = {
        "_load_timeseries": _CH_TS,
        "_load_series_timeseries": _S_TS,
        "_load_annotations": [],
        "_load_series_annotations": [],
        "_load_equipment_events": [],
    }
    loaders.update(overrides)
    with (
        patch(f"{_MOD}._load_timeseries", return_value=loaders["_load_timeseries"]),
        patch(f"{_MOD}._load_series_timeseries", return_value=loaders["_load_series_timeseries"]),
        patch(f"{_MOD}._load_annotations", return_value=loaders["_load_annotations"]),
        patch(f"{_MOD}._load_series_annotations", return_value=loaders["_load_series_annotations"]),
        patch(f"{_MOD}._load_equipment_events", return_value=loaders["_load_equipment_events"]),
    ):
        return ee.build_scalar_echarts_option(
            [5], _CH_META, "extract", [1], _S_META
        )


def test_option_has_line_and_scatter_with_zoom_and_brush():
    option, smap, _ = _build()
    types = [s["type"] for s in option["series"]]
    # Sensor = decorative line (no symbols) + brushable marker scatter; lab = scatter.
    # ECharts line series aren't brush-selectable, so the identity lives on scatter.
    assert types == ["line", "scatter", "scatter"], types
    assert option["series"][0]["showSymbol"] is False  # line is decorative only
    # dataZoom slider + inside, and a brush config (the UX wins)
    assert {z["type"] for z in option["dataZoom"]} == {"inside", "slider"}
    assert "brush" in option and option["xAxis"]["type"] == "time"
    # series_index_map aligns 1:1 with series order; the decor line is skipped,
    # sensor identity rides on the (brushable) marker scatter at index 1.
    assert smap[0]["kind"] == "decor"
    assert smap[1]["kind"] == "sensor" and smap[1]["id"] == 5
    assert smap[2]["kind"] == "lab" and smap[2]["id"] == 1
    assert [p["obs_id"] for p in smap[1]["points"]] == [901, 902]
    assert [p["obs_id"] for p in smap[2]["points"]] == [701, 702]


def test_yaxis_labelled_with_parameter_and_unit_from_data():
    # Sensor meta (DeploymentTraceLookupItem) has no unit_name; the unit must come
    # from the loaded time-series payload so the axis reads "parameter (unit)".
    meta_no_unit = {5: {"value_kind_id": 1, "equipment_identifier": "EQ5",
                        "parameter_name": "TSS", "equipment_id": 5}}
    ch_ts = {"parameter": "TSS", "unit": "mg/L", "data": _CH_TS["data"]}
    with (
        patch(f"{_MOD}._load_timeseries", return_value=ch_ts),
        patch(f"{_MOD}._load_series_timeseries", return_value={"data": []}),
        patch(f"{_MOD}._load_annotations", return_value=[]),
        patch(f"{_MOD}._load_series_annotations", return_value=[]),
        patch(f"{_MOD}._load_equipment_events", return_value=[]),
    ):
        option, _, _ = ee.build_scalar_echarts_option([5], meta_no_unit, "extract", [], {})
    assert option["yAxis"]["name"] == "TSS (mg/L)"
    # rendered as a proper centered axis title, not the tiny default
    assert option["yAxis"]["nameLocation"] == "middle"


def test_click_handler_returns_brush_shape():
    # Click handler must emit the same {seriesIndex, dataIndex[]} shape the
    # resolver consumes, so one resolver handles click + brush.
    assert "seriesIndex" in ee.CLICK_SELECTED_JS
    assert "dataIndex" in ee.CLICK_SELECTED_JS


def test_quality_code_drives_per_point_color():
    option, _, _ = _build()
    line = option["series"][0]
    # first point qc=1 (accepted/green), second qc=2 (suspect/orange)
    assert line["data"][0]["itemStyle"]["color"] == ee.QUALITY_COLORS[1]
    assert line["data"][1]["itemStyle"]["color"] == ee.QUALITY_COLORS[2]


def test_annotation_and_event_overlays_become_markareas_and_rows():
    ann = [{"start_time": "2026-05-02T00:00:00", "end_time": "2026-05-02T06:00:00",
            "type": {"name": "Fault", "color": "#DC2626"}, "title": "Lamp", "comment": "x"}]
    ev = [{"start_datetime": "2026-05-03T00:00:00", "end_datetime": None,
           "event_type_name": "Calibration", "notes": "annual"}]
    option, _, rows = _build(_load_annotations=ann, _load_equipment_events=ev)
    line = option["series"][0]
    # both overlays decorate the sensor series
    assert len(line["markArea"]["data"]) == 2
    assert {r["kind"] for r in rows} == {"Annotation", "Equipment Event"}
    assert any(r["category"] == "Fault" for r in rows)
    assert any(r["category"] == "Calibration" for r in rows)


def test_resolve_brush_selection_maps_indices_to_observations():
    _, smap, _ = _build()
    payload = [
        {"seriesIndex": 0, "dataIndex": [0, 1]},   # decor line — must be ignored
        {"seriesIndex": 1, "dataIndex": [1]},      # sensor 2nd point -> obs 902
        {"seriesIndex": 2, "dataIndex": [0, 1]},   # both lab points
    ]
    sel = ee.resolve_brush_selection(payload, smap)
    assert [p["obs_id"] for p in sel["sensor_pts"]] == [902]
    assert sel["sensor_pts"][0]["id"] == 5 and sel["sensor_pts"][0]["y"] == 12.0
    assert [p["obs_id"] for p in sel["lab_pts"]] == [701, 702]


def test_resolve_brush_selection_handles_none_and_bad_indices():
    _, smap, _ = _build()
    assert ee.resolve_brush_selection(None, smap) == {"sensor_pts": [], "lab_pts": []}
    # out-of-range seriesIndex / dataIndex are ignored, not raised
    bad = [{"seriesIndex": 99, "dataIndex": [0]}, {"seriesIndex": 0, "dataIndex": [50]}]
    assert ee.resolve_brush_selection(bad, smap) == {"sensor_pts": [], "lab_pts": []}


class TestImageTimeline:
    """One tick per image on a time axis, thumbnail in the hover tooltip."""

    def test_replicates_sharing_a_timestamp_stay_separate_ticks(self):
        ts = "2026-07-14T16:00:00"
        opt = ee.build_image_timeline_option(
            [{"timestamp": ts, "observation_id": 501},
             {"timestamp": ts, "observation_id": 502}],
            {501: ee.thumbnail_data_uri(b"one"), 502: ee.thumbnail_data_uri(b"two")},
        )
        pts = opt["series"][0]["data"]
        assert [p["obs"] for p in pts] == [501, 502]
        assert len({p["img"] for p in pts}) == 2
        assert opt["xAxis"]["type"] == "time"
        # The tooltip must render the thumbnail, not just the timestamp.
        assert "<img src=" in opt["tooltip"]["formatter"]

    def test_missing_thumbnail_degrades_to_a_label_only_tick(self):
        opt = ee.build_image_timeline_option(
            [{"timestamp": "2026-07-14T16:00:00", "observation_id": 7}], {}
        )
        assert opt["series"][0]["data"][0]["img"] is None
