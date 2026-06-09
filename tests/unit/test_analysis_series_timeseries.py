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
    "processing_kind_name": "Raw",
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
