"""Unit tests for CSV export helpers covering unit/parameter columns and timestamp conversion.

Pure functions — no Streamlit runtime. Tests:
  _flat_scalar_rows     — includes parameter + unit columns from API response
  _flat_series_scalar_rows — includes parameter + unit columns from API response
"""

from __future__ import annotations

from unittest.mock import patch

from app.pages import explore


_CHANNEL_TS = {
    "channel_id": 5,
    "parameter": "TSS",
    "unit": "mg/L",
    "data_shape": "Scalar",
    "from_timestamp": "2026-06-19T04:00:00",
    "to_timestamp": "2026-06-19T08:00:00",
    "row_count": 2,
    "data": [
        {"timestamp": "2026-06-19T04:00:00", "value": 10.0, "quality_code": 1},
        {"timestamp": "2026-06-19T08:00:00", "value": 12.0, "quality_code": 1},
    ],
}

_SERIES_TS = {
    "analysis_series_id": 1,
    "name": "TSS@Eff",
    "parameter": "TSS",
    "unit": "mg/L",
    "sampling_point": "Effluent",
    "data_shape": "Scalar",
    "from_timestamp": "2026-05-01T00:00:00",
    "to_timestamp": "2026-05-08T00:00:00",
    "row_count": 2,
    "data": [
        {"timestamp": "2026-05-01T00:00:00", "value": 11.0, "quality_code": 1},
        {"timestamp": "2026-05-08T00:00:00", "value": 13.0, "quality_code": 1},
    ],
}

_CHANNEL_META = {5: {"equipment_identifier": "EQ5", "parameter_name": "TSS"}}

_SERIES_META = {1: {"parameter_name": "TSS", "sampling_point_label": "Effluent"}}


class TestFlatScalarRows:
    def test_includes_unit_and_parameter_columns(self):
        with patch.object(explore, "_load_timeseries", return_value=_CHANNEL_TS):
            rows = explore._flat_scalar_rows([5], _CHANNEL_META)

        assert len(rows) == 2
        for row in rows:
            assert "parameter" in row, f"missing 'parameter' column, got: {list(row.keys())}"
            assert "unit" in row, f"missing 'unit' column, got: {list(row.keys())}"
            assert row["parameter"] == "TSS"
            assert row["unit"] == "mg/L"

    def test_includes_channel_id_and_label(self):
        with patch.object(explore, "_load_timeseries", return_value=_CHANNEL_TS):
            rows = explore._flat_scalar_rows([5], _CHANNEL_META)

        row = rows[0]
        assert row["channel_id"] == 5
        assert "EQ5" in row["channel_label"]
        assert "TSS" in row["channel_label"]

    def test_timestamps_present(self):
        with patch.object(explore, "_load_timeseries", return_value=_CHANNEL_TS):
            rows = explore._flat_scalar_rows([5], _CHANNEL_META)

        assert rows[0]["timestamp"] == "2026-06-19T04:00:00"
        assert rows[1]["timestamp"] == "2026-06-19T08:00:00"

    def test_no_data_returns_empty(self):
        empty_ts = {**_CHANNEL_TS, "data": []}
        with patch.object(explore, "_load_timeseries", return_value=empty_ts):
            rows = explore._flat_scalar_rows([5], _CHANNEL_META)
        assert rows == []

    def test_missing_unit_param_columns_fall_back_to_empty(self):
        no_meta_ts = {**_CHANNEL_TS}
        no_meta_ts.pop("parameter", None)
        no_meta_ts.pop("unit", None)
        with patch.object(explore, "_load_timeseries", return_value=no_meta_ts):
            rows = explore._flat_scalar_rows([5], _CHANNEL_META)
        assert rows[0]["parameter"] == ""
        assert rows[0]["unit"] == ""


class TestFlatSeriesScalarRows:
    def test_includes_unit_and_parameter_columns(self):
        with patch.object(explore, "_load_series_timeseries", return_value=_SERIES_TS):
            rows = explore._flat_series_scalar_rows([1], _SERIES_META)

        assert len(rows) == 2
        for row in rows:
            assert "parameter" in row, f"missing 'parameter' column, got: {list(row.keys())}"
            assert "unit" in row, f"missing 'unit' column, got: {list(row.keys())}"
            assert row["parameter"] == "TSS"
            assert row["unit"] == "mg/L"

    def test_lab_prefixed_channel_id(self):
        with patch.object(explore, "_load_series_timeseries", return_value=_SERIES_TS):
            rows = explore._flat_series_scalar_rows([1], _SERIES_META)

        assert rows[0]["channel_id"] == "LAB-1"

    def test_no_data_returns_empty(self):
        empty_ts = {**_SERIES_TS, "data": []}
        with patch.object(explore, "_load_series_timeseries", return_value=empty_ts):
            rows = explore._flat_series_scalar_rows([1], _SERIES_META)
        assert rows == []
