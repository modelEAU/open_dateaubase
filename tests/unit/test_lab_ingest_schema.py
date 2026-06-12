"""Unit tests for LabIngestRequest Pydantic schema validation.

Covers the two-mode contract introduced in issue #30:
- New experiment: name + experiment_datetime required.
- Existing experiment: experiment_id sufficient; other fields ignored.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from api.v1.schemas.ingestion import LabIngestRequest, LabMeasurementItem

_TS = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)

_MEASUREMENT = {
    "parameter_id": 1,
    "sampling_point_id": 1,
    "unit_id": 1,
    "value_kind_id": 1,
    "series_name": "TSS@Effluent",
    "sample_id": 1,
    "value": 12.4,
}


class TestLabIngestRequestNewMode:
    def test_valid_new_experiment(self):
        req = LabIngestRequest(
            name="Test run",
            experiment_datetime=_TS,
            measurements=[LabMeasurementItem(**_MEASUREMENT)],
        )
        assert req.experiment_id is None
        assert req.name == "Test run"

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name is required"):
            LabIngestRequest(
                experiment_datetime=_TS,
                measurements=[LabMeasurementItem(**_MEASUREMENT)],
            )

    def test_missing_datetime_raises(self):
        with pytest.raises(ValueError, match="experiment_datetime is required"):
            LabIngestRequest(
                name="Test run",
                measurements=[LabMeasurementItem(**_MEASUREMENT)],
            )

    def test_empty_measurements_raises(self):
        with pytest.raises(ValueError, match="measurements list must not be empty"):
            LabIngestRequest(
                name="Test run",
                experiment_datetime=_TS,
                measurements=[],
            )


class TestLabIngestRequestExistingMode:
    def test_valid_existing_experiment(self):
        req = LabIngestRequest(
            experiment_id=42,
            measurements=[LabMeasurementItem(**_MEASUREMENT)],
        )
        assert req.experiment_id == 42
        assert req.name is None
        assert req.experiment_datetime is None

    def test_name_and_datetime_not_required_when_experiment_id_set(self):
        # Should not raise even without name/experiment_datetime
        req = LabIngestRequest(
            experiment_id=7,
            measurements=[LabMeasurementItem(**_MEASUREMENT)],
        )
        assert req.experiment_id == 7

    def test_empty_measurements_still_raises_for_existing_mode(self):
        with pytest.raises(ValueError, match="measurements list must not be empty"):
            LabIngestRequest(
                experiment_id=42,
                measurements=[],
            )
