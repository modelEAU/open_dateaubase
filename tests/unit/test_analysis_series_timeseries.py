"""Unit tests for the lab AnalysisSeries timeseries service.

Repository layer mocked; asserts the assembled response shape and 404 path.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from api.v1.services import timeseries_service

T1 = datetime(2026, 5, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 5, 8, tzinfo=timezone.utc)

_SERIES = {
    "analysis_series_id": 42,
    "name": "TSS Gravimetric at Effluent",
    "parameter_name": "TSS",
    "unit_name": "mg/L",
    "sampling_point_label": "Effluent",
    "value_kind_id": 1,
}


def test_builds_response_from_series_and_data(monkeypatch):
    ing = MagicMock()
    ing.get_analysis_series_by_id.return_value = _SERIES
    val = MagicMock()
    val.get_analysis_series_values_for_metadata.return_value = [
        {"timestamp": T1, "value": 11.0, "quality_code": 1},
        {"timestamp": T2, "value": 13.0, "quality_code": 1},
    ]
    monkeypatch.setattr(timeseries_service, "ingestion_repository", ing)
    monkeypatch.setattr(timeseries_service, "value_repository", val)

    out = timeseries_service.get_analysis_series_timeseries(MagicMock(), 42, None, None)

    assert out["analysis_series_id"] == 42
    assert out["parameter"] == "TSS"
    assert out["unit"] == "mg/L"
    assert out["sampling_point"] == "Effluent"
    assert out["data_shape"] == "Scalar"
    assert out["from_timestamp"] == T1
    assert out["to_timestamp"] == T2
    assert out["row_count"] == 2
    assert len(out["data"]) == 2
    # ADR 0005: lab AnalysisSeries has no processing kind — the retired
    # processing_degree field must not be surfaced for the lab read path.
    assert "processing_degree" not in out


def test_404_when_series_missing(monkeypatch):
    ing = MagicMock()
    ing.get_analysis_series_by_id.return_value = None
    monkeypatch.setattr(timeseries_service, "ingestion_repository", ing)

    with pytest.raises(HTTPException) as exc:
        timeseries_service.get_analysis_series_timeseries(MagicMock(), 999, None, None)
    assert exc.value.status_code == 404


def test_empty_data_yields_null_range(monkeypatch):
    ing = MagicMock()
    ing.get_analysis_series_by_id.return_value = _SERIES
    val = MagicMock()
    val.get_analysis_series_values_for_metadata.return_value = []
    monkeypatch.setattr(timeseries_service, "ingestion_repository", ing)
    monkeypatch.setattr(timeseries_service, "value_repository", val)

    out = timeseries_service.get_analysis_series_timeseries(MagicMock(), 42, None, None)
    assert out["row_count"] == 0
    assert out["from_timestamp"] is None
    assert out["to_timestamp"] is None


_CHANNEL = {
    "parameter_name": "TSS",
    "unit_name": "mg/L",
    "value_kind_name": "Scalar",
    "value_kind_id": 1,
    "data_provenance_kind_name": "Measured",
}


def test_sensor_timeseries_surfaces_trait_list_not_processing_degree(monkeypatch):
    """ADR 0005: the sensor read path replaces the retired processing_degree
    scalar with the accumulated ChannelTrait set (OperationKind names)."""
    chan = MagicMock()
    chan.get_channel_by_id.return_value = _CHANNEL
    val = MagicMock()
    val.get_values_for_metadata.return_value = [
        {"timestamp": T1, "value": 11.0, "quality_code": 1, "observation_id": 1},
    ]
    val.get_channel_trait_names.return_value = ["OutlierRemoval", "Smoothing"]
    monkeypatch.setattr(timeseries_service, "channel_repository", chan)
    monkeypatch.setattr(timeseries_service, "value_repository", val)

    out = timeseries_service.get_timeseries(MagicMock(), 7, None, None)

    # New traits field is populated from ChannelTrait -> OperationKind.
    assert out["traits"] == ["OutlierRemoval", "Smoothing"]
    # Retired scalar is gone.
    assert "processing_degree" not in out
    # Trait names are fetched keyed on the channel's Stream_ID value (channel_id=7).
    val.get_channel_trait_names.assert_called_once()
    assert val.get_channel_trait_names.call_args.args[1] == 7
