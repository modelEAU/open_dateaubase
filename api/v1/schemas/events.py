"""Pydantic models for Event and EventKind request/response shapes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator


# ---------------------------------------------------------------------------
# EventKind schemas
# ---------------------------------------------------------------------------


class EventKindOut(BaseModel):
    event_kind_id: int
    name: str
    description: Optional[str] = None


class EventKindIn(BaseModel):
    name: str
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Event schemas
# ---------------------------------------------------------------------------

# The 8 exclusive-arc FK field names (Python snake_case).
_ARC_FIELDS = (
    "channel_id",
    "equipment_id",
    "signal_interface_id",
    "data_acquisition_system_id",
    "sampling_point_id",
    "process_unit_id",
    "site_id",
    "campaign_id",
)


class EventOut(BaseModel):
    event_id: int
    event_kind_id: int
    event_kind_name: Optional[str] = None
    is_instantaneous: bool
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    performed_by_person_id: Optional[int] = None
    recorded_by_person_id: Optional[int] = None
    notes: Optional[str] = None
    # Exclusive-arc target FKs (exactly one non-NULL in a valid row)
    channel_id: Optional[int] = None
    equipment_id: Optional[int] = None
    signal_interface_id: Optional[int] = None
    data_acquisition_system_id: Optional[int] = None
    sampling_point_id: Optional[int] = None
    process_unit_id: Optional[int] = None
    site_id: Optional[int] = None
    campaign_id: Optional[int] = None


class EventIn(BaseModel):
    event_kind_id: int
    is_instantaneous: bool = False
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    performed_by_person_id: Optional[int] = None
    recorded_by_person_id: Optional[int] = None
    notes: Optional[str] = None
    # Exclusive-arc target FKs — exactly one must be provided
    channel_id: Optional[int] = None
    equipment_id: Optional[int] = None
    signal_interface_id: Optional[int] = None
    data_acquisition_system_id: Optional[int] = None
    sampling_point_id: Optional[int] = None
    process_unit_id: Optional[int] = None
    site_id: Optional[int] = None
    campaign_id: Optional[int] = None

    @model_validator(mode="after")
    def exactly_one_target(self) -> "EventIn":
        count = sum(
            1 for field in _ARC_FIELDS if getattr(self, field) is not None
        )
        if count != 1:
            raise ValueError(
                f"exactly one target required — {count} arc FK(s) provided "
                f"(must be exactly 1 of: {', '.join(_ARC_FIELDS)})"
            )
        return self


class EventPatch(BaseModel):
    """Partial update — all fields optional, arc-FK invariant re-checked if any FK provided."""

    event_kind_id: Optional[int] = None
    is_instantaneous: Optional[bool] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    performed_by_person_id: Optional[int] = None
    recorded_by_person_id: Optional[int] = None
    notes: Optional[str] = None
    channel_id: Optional[int] = None
    equipment_id: Optional[int] = None
    signal_interface_id: Optional[int] = None
    data_acquisition_system_id: Optional[int] = None
    sampling_point_id: Optional[int] = None
    process_unit_id: Optional[int] = None
    site_id: Optional[int] = None
    campaign_id: Optional[int] = None
