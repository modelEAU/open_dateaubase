"""Pydantic schemas for maintenance-drift derived Channel resources (PRD-2.5 S1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class MaintenanceDriftIn(BaseModel):
    """Request body for POST /channels/derived/maintenance-drift."""

    source_channel_id: int
    event_ids: list[int]
    name: str
    performed_by_person_id: int | None = None

    @field_validator("source_channel_id")
    @classmethod
    def source_channel_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("source_channel_id must be a positive integer")
        return v

    @field_validator("event_ids")
    @classmethod
    def event_ids_non_empty(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("event_ids must contain at least one event ID")
        return v


class MaintenanceDriftOut(BaseModel):
    """Response after creating a maintenance-drift derived Channel."""

    channel_id: int
    name: str
    produced_by_step_id: int


class DriftReadbackPoint(BaseModel):
    """A single source-stream reading (used for the before/after values)."""

    timestamp: datetime
    value: float | None


class MaintenanceDriftReadback(BaseModel):
    """Read-back (PRD-4 S4): drift since last cleaning for a maintenance Event.

    The before/after readings are derived from the *source* stream around the
    event window (last sample before the start, first sample after the end).
    """

    event_id: int
    drift_channel_id: int
    source_channel_id: int
    window_start: datetime
    window_end: datetime | None = None
    before: DriftReadbackPoint | None = None
    after: DriftReadbackPoint | None = None
    percent_diff: float | None = None
