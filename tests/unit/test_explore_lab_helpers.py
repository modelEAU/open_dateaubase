"""Unit tests for the lab (AnalysisSeries) helpers in the Data Explorer.

Pure functions only — no Streamlit runtime. Importing the page does NOT run
main() because of the _in_streamlit_run() guard (no script-run context here).
"""

from __future__ import annotations

from unittest.mock import patch

from app.pages import explore


_SERIES = [
    # TSS at Effluent, campaign 1, scalar
    {"analysis_series_id": 1, "name": "TSS@Eff", "parameter_id": 10,
     "parameter_name": "TSS", "sampling_point_id": 100,
     "sampling_point_label": "Effluent", "unit_name": "mg/L",
     "value_kind_id": 1, "campaign_id": 1},
    # COD at Effluent, campaign 1, scalar
    {"analysis_series_id": 2, "name": "COD@Eff", "parameter_id": 11,
     "parameter_name": "COD", "sampling_point_id": 100,
     "sampling_point_label": "Effluent", "unit_name": "mg/L",
     "value_kind_id": 1, "campaign_id": 1},
    # TSS at Influent, campaign 1, scalar
    {"analysis_series_id": 3, "name": "TSS@Inf", "parameter_id": 10,
     "parameter_name": "TSS", "sampling_point_id": 200,
     "sampling_point_label": "Influent", "unit_name": "mg/L",
     "value_kind_id": 1, "campaign_id": 1},
    # PSD at Effluent, campaign 2, vector
    {"analysis_series_id": 4, "name": "PSD@Eff", "parameter_id": 12,
     "parameter_name": "PSD", "sampling_point_id": 100,
     "sampling_point_label": "Effluent", "unit_name": "-",
     "value_kind_id": 2, "campaign_id": 2},
]


class TestApplyPickerFilters:
    """Tests for _apply_picker_filters (replaced the old _series_cross_filter)."""

    def _filter(self, campaign_id=None, location_id=None, parameter_id=None,
                equipment_id=None, vtype_id=None, search_text="") -> list[dict]:
        """Helper: call _apply_picker_filters with only the series side and return matches."""
        _, matches = explore._apply_picker_filters(
            [], _SERIES,
            campaign_id=campaign_id, location_id=location_id,
            parameter_id=parameter_id, equipment_id=equipment_id,
            vtype_id=vtype_id, search_text=search_text,
        )
        return matches

    def test_campaign_scope(self):
        matches = self._filter(campaign_id=1)
        assert {m["analysis_series_id"] for m in matches} == {1, 2, 3}

    def test_no_campaign_shows_all(self):
        matches = self._filter()
        assert len(matches) == 4

    def test_param_filter(self):
        # TSS (param 10) within campaign 1 → Effluent + Influent entries
        matches = self._filter(campaign_id=1, parameter_id=10)
        assert {m["analysis_series_id"] for m in matches} == {1, 3}

    def test_location_filter(self):
        # Effluent (sp 100) within campaign 1 → TSS + COD entries
        matches = self._filter(campaign_id=1, location_id=100)
        assert {m["analysis_series_id"] for m in matches} == {1, 2}

    def test_param_plus_location_matches_single(self):
        matches = self._filter(campaign_id=1, parameter_id=10, location_id=200)
        assert [m["analysis_series_id"] for m in matches] == [3]


class TestKindOptions:
    def test_merges_channels_and_series_of_type(self):
        channel_meta = {5: {"value_kind_id": 1, "equipment_identifier": "EQ5",
                            "parameter_name": "TSS"}}
        series_meta = {1: _SERIES[0]}  # scalar
        opts = explore._kind_options(
            explore.VALUE_TYPE_SCALAR, [5], channel_meta, [1], series_meta
        )
        kinds = set(opts.values())
        assert ("channel", 5) in kinds
        assert ("series", 1) in kinds

    def test_excludes_other_value_types(self):
        series_meta = {4: _SERIES[3]}  # vector
        opts = explore._kind_options(
            explore.VALUE_TYPE_SCALAR, [], {}, [4], series_meta
        )
        assert opts == {}
        opts_vec = explore._kind_options(
            explore.VALUE_TYPE_VECTOR, [], {}, [4], series_meta
        )
        assert ("series", 4) in set(opts_vec.values())


class TestScalarFigureOverlay:
    def test_sensor_line_and_lab_markers_on_one_figure(self):
        channel_meta = {5: {"value_kind_id": 1, "equipment_identifier": "EQ5",
                            "parameter_name": "TSS", "unit_name": "mg/L",
                            "equipment_id": 5}}
        series_meta = {1: _SERIES[0]}
        ch_data = {"data": [
            {"timestamp": "2026-05-02T00:00:00", "value": 10.0, "quality_code": 1},
        ]}
        s_data = {"data": [
            {"timestamp": "2026-05-01T00:00:00", "value": 11.0, "quality_code": 1},
            {"timestamp": "2026-05-08T00:00:00", "value": 13.0, "quality_code": 1},
        ]}
        with patch.object(explore, "_load_timeseries", return_value=ch_data), \
             patch.object(explore, "_load_annotations", return_value=[]), \
             patch.object(explore, "_load_series_annotations", return_value=[]), \
             patch.object(explore, "_load_equipment_events", return_value=[]), \
             patch.object(explore, "_load_series_timeseries", return_value=s_data):
            fig, _ = explore._build_scalar_figure(
                [5], channel_meta, "extract", [1], series_meta
            )

        names = [tr.name or "" for tr in fig.data]
        assert any(n.startswith("CH-5") for n in names), names
        assert any(n.startswith("LAB-1") for n in names), names

        ch_trace = next(tr for tr in fig.data if (tr.name or "").startswith("CH-5"))
        lab_trace = next(tr for tr in fig.data if (tr.name or "").startswith("LAB-1"))
        assert ch_trace.mode == "lines+markers"
        assert lab_trace.mode == "markers"  # discrete lab samples
        # Both replicates plotted as individual points.
        assert len(lab_trace.x) == 2
