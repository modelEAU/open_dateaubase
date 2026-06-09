"""Unit tests for the /ingest/lab endpoint's time-anchor behavior.

ADR 0002: a lab Observation.Timestamp is the sample collection time
(Sample.SampleDateTimeStart), NOT the analysis time. These tests call the
endpoint function directly with the repository layer mocked, and assert which
timestamp is handed to insert_lab_observation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from api.v1.endpoints import ingest as ingest_module
from api.v1.schemas.ingestion import LabIngestRequest, LabMeasurementItem

_SAMPLE_TIME = datetime(2026, 5, 18, 8, 15, tzinfo=timezone.utc)
_ANALYSIS_TIME = datetime(2026, 5, 21, 14, 0, tzinfo=timezone.utc)


def _measurement(sample_id: int = 7) -> LabMeasurementItem:
    return LabMeasurementItem(
        parameter_id=1,
        sampling_point_id=1,
        unit_id=1,
        value_kind_id=1,
        processing_kind_id=1,
        series_name="TSS@Effluent",
        sample_id=sample_id,
        value=12.4,
        analysis_datetime=_ANALYSIS_TIME,
    )


def test_lab_observation_anchored_on_sample_collection_time(monkeypatch):
    repo = MagicMock()
    repo.insert_lab_experiment.return_value = 11
    repo.find_or_create_analysis_series.return_value = 42
    repo.insert_lab_analysis.return_value = 55
    repo.get_sample_collection_time.return_value = _SAMPLE_TIME
    repo.insert_lab_observation.return_value = 300
    monkeypatch.setattr(ingest_module, "ingestion_repository", repo)

    data = LabIngestRequest(
        name="Weekly panel",
        experiment_datetime=_ANALYSIS_TIME,
        measurements=[_measurement()],
    )

    ingest_module.ingest_lab(data, conn=MagicMock())

    # The collection time was looked up for the measurement's sample.
    _, gsct_kwargs = repo.get_sample_collection_time.call_args
    assert gsct_kwargs == {"sample_id": 7}
    # The observation timestamp must be the sample collection time, not analysis.
    _, kwargs = repo.insert_lab_observation.call_args
    assert kwargs["timestamp"] == _SAMPLE_TIME
    assert kwargs["timestamp"] != _ANALYSIS_TIME
    # AnalysisDateTime is still recorded on the LabAnalysis row (metadata).
    _, la_kwargs = repo.insert_lab_analysis.call_args
    assert la_kwargs["analysis_datetime"] == _ANALYSIS_TIME


def test_sample_collection_time_looked_up_once_per_sample(monkeypatch):
    repo = MagicMock()
    repo.insert_lab_experiment.return_value = 11
    repo.find_or_create_analysis_series.return_value = 42
    repo.insert_lab_analysis.return_value = 55
    repo.get_sample_collection_time.return_value = _SAMPLE_TIME
    repo.insert_lab_observation.return_value = 300
    monkeypatch.setattr(ingest_module, "ingestion_repository", repo)

    data = LabIngestRequest(
        name="Weekly panel",
        experiment_datetime=_ANALYSIS_TIME,
        measurements=[_measurement(sample_id=7), _measurement(sample_id=7)],
    )

    ingest_module.ingest_lab(data, conn=MagicMock())

    # Two measurements share one sample_id -> a single collection-time lookup.
    assert repo.get_sample_collection_time.call_count == 1
    assert repo.insert_lab_observation.call_count == 2
