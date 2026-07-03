"""Unit tests for PRD-2.5 S1 — maintenance-drift schema (no DB required).

Red→green: these tests verify the Pydantic models for MaintenanceDriftIn /
MaintenanceDriftOut are correct. They fail if the models don't exist or if
the validation logic is missing.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.v1.schemas.maintenance_drift import MaintenanceDriftIn, MaintenanceDriftOut


# ---------------------------------------------------------------------------
# MaintenanceDriftIn — valid construction
# ---------------------------------------------------------------------------


def test_maintenance_drift_in_valid_minimal() -> None:
    """Minimal valid payload: source + at least one event."""
    obj = MaintenanceDriftIn(
        source_channel_id=1,
        event_ids=[10, 20],
        name="NH4 drift 2024-Q1",
    )
    assert obj.source_channel_id == 1
    assert obj.event_ids == [10, 20]
    assert obj.name == "NH4 drift 2024-Q1"
    assert obj.performed_by_person_id is None


def test_maintenance_drift_in_with_person() -> None:
    """Optional person ID accepted."""
    obj = MaintenanceDriftIn(
        source_channel_id=5,
        event_ids=[1],
        name="drift-ch5",
        performed_by_person_id=99,
    )
    assert obj.performed_by_person_id == 99


# ---------------------------------------------------------------------------
# MaintenanceDriftIn — validation errors
# ---------------------------------------------------------------------------


def test_maintenance_drift_in_rejects_zero_source_channel() -> None:
    """source_channel_id = 0 must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        MaintenanceDriftIn(source_channel_id=0, event_ids=[1], name="x")
    assert "source_channel_id" in str(exc_info.value)


def test_maintenance_drift_in_rejects_negative_source_channel() -> None:
    """Negative source_channel_id must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        MaintenanceDriftIn(source_channel_id=-3, event_ids=[1], name="x")
    assert "source_channel_id" in str(exc_info.value)


def test_maintenance_drift_in_rejects_empty_event_ids() -> None:
    """Empty event_ids list must be rejected."""
    with pytest.raises(ValidationError) as exc_info:
        MaintenanceDriftIn(source_channel_id=1, event_ids=[], name="x")
    assert "event_ids" in str(exc_info.value)


def test_maintenance_drift_in_rejects_missing_name() -> None:
    """Missing name field must be rejected."""
    with pytest.raises(ValidationError):
        MaintenanceDriftIn(source_channel_id=1, event_ids=[1])  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# MaintenanceDriftOut — field presence
# ---------------------------------------------------------------------------


def test_maintenance_drift_out_has_expected_fields() -> None:
    """MaintenanceDriftOut must expose channel_id, name, produced_by_step_id."""
    obj = MaintenanceDriftOut(
        channel_id=42,
        name="NH4 drift channel",
        produced_by_step_id=7,
    )
    assert obj.channel_id == 42
    assert obj.name == "NH4 drift channel"
    assert obj.produced_by_step_id == 7


def test_maintenance_drift_out_rejects_missing_channel_id() -> None:
    """channel_id is required."""
    with pytest.raises(ValidationError):
        MaintenanceDriftOut(name="x", produced_by_step_id=1)  # type: ignore[call-arg]


def test_maintenance_drift_out_rejects_missing_produced_by_step_id() -> None:
    """produced_by_step_id is required."""
    with pytest.raises(ValidationError):
        MaintenanceDriftOut(channel_id=1, name="x")  # type: ignore[call-arg]
