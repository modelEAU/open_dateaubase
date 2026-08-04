"""Pydantic schemas for Equipment resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EquipmentOut(BaseModel):
    equipment_id: int
    identifier: str | None
    serial_number: str | None
    model_id: int | None
    model_name: str | None
    manufacturer: str | None
    owner: str | None
    purchase_date: str | None


class EquipmentEventOut(BaseModel):
    event_id: int
    event_type_id: int
    event_type_name: str | None
    is_instantaneous: bool
    start_datetime: datetime
    end_datetime: datetime | None
    performed_by_person_id: int | None
    performed_by_name: str | None
    recorded_by_person_id: int | None
    recorded_by_name: str | None
    notes: str | None


class InstallationOut(BaseModel):
    installation_id: int
    sampling_location_id: int
    location_name: str | None
    installed_date: datetime
    removed_date: datetime | None
    campaign_id: int | None
    campaign_name: str | None
    notes: str | None


class EquipmentIn(BaseModel):
    identifier: str | None = None
    serial_number: str | None = None
    model_id: int | None = None
    owner: str | None = None
    purchase_date: str | None = None  # ISO date string, e.g. "2024-01-15"


class EquipmentPatch(BaseModel):
    """Partial update schema for Equipment - all fields optional."""

    identifier: str | None = None
    serial_number: str | None = None
    model_id: int | None = None
    owner: str | None = None
    purchase_date: str | None = None


class EquipmentModelLookupOut(BaseModel):
    """Lightweight equipment model info for dropdowns."""

    model_id: int
    model_name: str
    manufacturer: str | None = None


class EquipmentModelIn(BaseModel):
    equipment_model: str | None = None
    method: str | None = None
    functions: str | None = None
    manufacturer: str | None = None
    manual_location: str | None = None
    equipment_kind_id: int | None = None


class EquipmentModelOut(BaseModel):
    model_id: int
    equipment_model: str | None = None
    method: str | None = None
    functions: str | None = None
    manufacturer: str | None = None
    manual_location: str | None = None
    equipment_kind_id: int | None = None


class EquipmentLifecycleOut(BaseModel):
    equipment: EquipmentOut
    installations: list[InstallationOut]
    events: list[EquipmentEventOut]


class EquipmentEventKindOut(BaseModel):
    event_type_id: int
    event_type_name: str
    description: str | None = None


class EquipmentEventCreate(BaseModel):
    equipment_id: int
    event_type_id: int
    is_instantaneous: bool = False
    start_datetime: datetime
    end_datetime: datetime | None = None
    performed_by_person_id: int | None = None
    recorded_by_person_id: int | None = None
    notes: str | None = None


class EquipmentLifecycleActionRequest(BaseModel):
    """Request body for commission / decommission endpoints."""

    notes: str | None = None
    performed_by_person_id: int | None = None


class EquipmentLifecycleActionResponse(BaseModel):
    """Response for commission / decommission endpoints."""

    equipment_id: int
    is_active: bool
    equipment_event_id: int


class EquipmentModelParameterIn(BaseModel):
    parameter_id: int


class EquipmentModelParameterOut(BaseModel):
    model_id: int
    parameter_id: int
    parameter_name: str | None = None


class EquipmentModelProcedureIn(BaseModel):
    procedure_id: int


class EquipmentModelProcedureOut(BaseModel):
    model_id: int
    procedure_id: int
    procedure_name: str | None = None


class EquipmentStoryOut(BaseModel):
    """Read-only Equipment Story aggregate (see equipment_repository.get_equipment_story)."""

    equipment: dict
    campaigns: list[dict]
    location_history: list[dict]
    events: list[dict]
    streams: list[dict]
    annotations: list[dict]
