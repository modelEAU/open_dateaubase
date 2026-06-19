"""Unit tests for timezone-conversion helpers in explore_data.py.

Pure functions — no Streamlit runtime. Tests exercise:
  _local_to_utc_iso  — local calendar date → UTC ISO for API queries
  _utc_to_local      — UTC ISO string → local ISO string for display
"""

from __future__ import annotations

import datetime
from datetime import date, datetime as dt, timezone
from unittest.mock import patch

import pytest
from app.components import explore_data


_FAKE_UTC = timezone.utc
_FAKE_EASTERN = timezone(datetime.timedelta(hours=-4))
_FAKE_TOKYO = timezone(datetime.timedelta(hours=9))


class TestLocalToUtcIso:
    """_local_to_utc_iso: converts a local calendar date to UTC ISO for API queries."""

    def test_midnight_local_to_utc_eastern(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_EASTERN):
            result = explore_data._local_to_utc_iso(date(2026, 6, 19), end_of_day=False)
        assert result == "2026-06-19T04:00:00+00:00"

    def test_end_of_day_local_to_utc_eastern(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_EASTERN):
            result = explore_data._local_to_utc_iso(date(2026, 6, 19), end_of_day=True)
        assert result == "2026-06-20T03:59:59.999999+00:00"

    def test_midnight_local_to_utc_utc(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_UTC):
            result = explore_data._local_to_utc_iso(date(2026, 6, 19), end_of_day=False)
        assert result == "2026-06-19T00:00:00+00:00"

    def test_end_of_day_local_to_utc_utc(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_UTC):
            result = explore_data._local_to_utc_iso(date(2026, 6, 19), end_of_day=True)
        assert result == "2026-06-19T23:59:59.999999+00:00"

    def test_midnight_local_to_utc_tokyo(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_TOKYO):
            result = explore_data._local_to_utc_iso(date(2026, 6, 19), end_of_day=False)
        assert result == "2026-06-18T15:00:00+00:00"

    def test_end_of_day_local_to_utc_tokyo(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_TOKYO):
            result = explore_data._local_to_utc_iso(date(2026, 6, 19), end_of_day=True)
        assert result == "2026-06-19T14:59:59.999999+00:00"


class TestUtcToLocal:
    """_utc_to_local: converts a naive UTC ISO string to local ISO string."""

    def test_naive_utc_to_eastern(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_EASTERN):
            result = explore_data._utc_to_local("2026-06-19T04:00:00")
        assert result == "2026-06-19T00:00:00-04:00"

    def test_naive_utc_to_utc(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_UTC):
            result = explore_data._utc_to_local("2026-06-19T04:00:00")
        assert result == "2026-06-19T04:00:00+00:00"

    def test_naive_utc_to_tokyo(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_TOKYO):
            result = explore_data._utc_to_local("2026-06-19T04:00:00")
        assert result == "2026-06-19T13:00:00+09:00"

    def test_z_suffix_handled(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_EASTERN):
            result = explore_data._utc_to_local("2026-06-19T04:00:00Z")
        assert result == "2026-06-19T00:00:00-04:00"

    def test_already_aware_utc_preserved(self):
        aware_ts = dt(2026, 6, 19, 4, 0, 0, tzinfo=timezone.utc)
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_EASTERN):
            result = explore_data._utc_to_local(aware_ts.isoformat())
        assert result == "2026-06-19T00:00:00-04:00"

    def test_empty_string_returns_empty(self):
        result = explore_data._utc_to_local("")
        assert result == ""

    def test_none_returns_empty(self):
        result = explore_data._utc_to_local(None)
        assert result == ""

    def test_invalid_string_falls_back(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_UTC):
            result = explore_data._utc_to_local("not-a-date")
        assert result == "not-a-date"


class TestTimeConversionsRoundtrip:
    """A local midnight sent through local→UTC→local should return to local midnight."""

    def test_eastern_roundtrip(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_EASTERN):
            utc_iso = explore_data._local_to_utc_iso(date(2026, 6, 19))
            local_iso = explore_data._utc_to_local(utc_iso)
        expected = "2026-06-19T00:00:00-04:00"
        assert local_iso == expected, f"expected {expected}, got {local_iso}"

    def test_tokyo_roundtrip(self):
        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_TOKYO):
            utc_iso = explore_data._local_to_utc_iso(date(2026, 6, 19))
            local_iso = explore_data._utc_to_local(utc_iso)
        expected = "2026-06-19T00:00:00+09:00"
        assert local_iso == expected, f"expected {expected}, got {local_iso}"


class TestLoadTimeseriesConvertsTimestamps:
    """_load_timeseries should convert returned timestamps to local time."""

    _MOCK_TS = {
        "channel_id": 5,
        "parameter": "TSS",
        "unit": "mg/L",
        "data_shape": "Scalar",
        "row_count": 2,
        "data": [
            {"timestamp": "2026-06-19T04:00:00", "value": 10.0, "quality_code": 1},
            {"timestamp": "2026-06-19T08:00:00", "value": 12.0, "quality_code": 1},
        ],
    }

    def test_timestamps_converted_to_local(self):
        import streamlit as st
        from unittest.mock import MagicMock

        st_mock = MagicMock()
        st_mock.session_state = MagicMock()
        st_mock.session_state.explore_start = date(2026, 6, 1)
        st_mock.session_state.explore_end = date(2026, 6, 30)
        st_mock.session_state.explore_data = {}

        with patch.object(explore_data, "st", st_mock), \
             patch.object(explore_data, "_LOCAL_TZ", _FAKE_EASTERN), \
             patch.object(explore_data, "get_channel_timeseries", return_value=self._MOCK_TS):
            result = explore_data._load_timeseries(5)

        assert result is not None
        rows = result["data"]
        assert rows[0]["timestamp"] == "2026-06-19T00:00:00-04:00"
        assert rows[1]["timestamp"] == "2026-06-19T04:00:00-04:00"


class TestLoadAnnotationsConvertsTimestamps:
    """Annotation loaders should convert UTC timestamps to local."""

    _MOCK_ANNOTATIONS = [
        {
            "annotation_id": 1,
            "start_time": "2026-06-19T04:00:00",
            "end_time": "2026-06-19T08:00:00",
            "type": {"id": 3, "name": "Fault"},
            "title": "Test",
            "comment": "",
        },
        {
            "annotation_id": 2,
            "start_time": "2026-06-19T00:00:00",
            "end_time": "",
            "type": {"id": 2, "name": "Spike"},
            "title": "",
            "comment": "",
        },
    ]

    def test_annotations_converted_to_local(self):
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.json.return_value = {"annotations": self._MOCK_ANNOTATIONS}
        mock_response.is_success = True

        mock_client = MagicMock()
        mock_client.__enter__.return_value.get.return_value = mock_response

        with patch.object(explore_data, "_LOCAL_TZ", _FAKE_EASTERN), \
             patch("app.api_client._get_client", return_value=mock_client):
            result = explore_data._api_list_annotations_for_channel(5, date(2026, 6, 1), date(2026, 6, 30))

        assert result[0]["start_time"] == "2026-06-19T00:00:00-04:00"
        assert result[0]["end_time"] == "2026-06-19T04:00:00-04:00"
        assert result[1]["start_time"] == "2026-06-18T20:00:00-04:00"
        assert result[1]["end_time"] == ""  # empty not converted
