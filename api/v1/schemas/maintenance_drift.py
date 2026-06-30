"""Pydantic schemas for maintenance-drift derived Channel resources (PRD-2.5 S1)."""

from __future__ import annotations

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
