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
    start_datetime: datetime
    end_datetime: datetime | None
    performed_by_person_id: int | None
    performed_by_name: str | None
    campaign_id: int | None
    campaign_name: str | None
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


class EquipmentLifecycleOut(BaseModel):
    equipment: EquipmentOut
    installations: list[InstallationOut]
    events: list[EquipmentEventOut]
