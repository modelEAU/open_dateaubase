"""Schemas for the data-health / broken-link views (consistency audit F5, F11)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UnlinkedChannel(BaseModel):
    """A raw channel with observations but no active wiring (F5)."""

    channel_id: int
    tag_name: str | None
    signal_interface_id: int | None
    signal_interface_name: str | None
    observation_count: int
    first_observation: datetime | None
    last_observation: datetime | None


class UnlinkedChannelsResponse(BaseModel):
    count: int
    channels: list[UnlinkedChannel]


class InactiveParentReference(BaseModel):
    """An active wiring row pointing at a soft-deleted interface/port (F11)."""

    reference_type: str
    wiring_history_id: int
    equipment_id: int
    parent_id: int
    parent_label: str | None


class InactiveParentReferencesResponse(BaseModel):
    count: int
    references: list[InactiveParentReference]


class UnclassifiedEquipment(BaseModel):
    """Equipment with no model, or a model with no kind — invisible to any
    picker that scopes itself to a kind."""

    equipment_id: int
    identifier: str | None
    is_active: bool | None
    equipment_model_id: int | None
    equipment_model_name: str | None
    reason: str


class UnclassifiedEquipmentResponse(BaseModel):
    count: int
    equipment: list[UnclassifiedEquipment]
