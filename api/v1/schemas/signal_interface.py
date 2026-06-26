"""Pydantic schemas for SignalInterface resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# SignalInterface CRUD
# ---------------------------------------------------------------------------


class SignalInterfaceOut(BaseModel):
    """Full SignalInterface representation with resolved DAS name."""

    signal_interface_id: int
    name: str
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    description: str | None
    is_active: bool
    data_acquisition_system_id: int
    das_name: str


class SignalInterfaceIn(BaseModel):
    """Payload for creating a new SignalInterface."""

    data_acquisition_system_id: int
    name: str
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    description: str | None = None
    is_active: bool = True


class SignalInterfacePatchRequest(BaseModel):
    """Partial update for a SignalInterface — only supplied fields are written."""

    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    description: str | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# SignalInterfacePort CRUD
# ---------------------------------------------------------------------------


class SignalInterfacePortOut(BaseModel):
    """Full SignalInterfacePort representation."""

    signal_interface_port_id: int
    port_identifier: str
    description: str | None
    is_active: bool
    signal_interface_id: int
    signal_interface_name: str | None


class SignalInterfacePortIn(BaseModel):
    """Payload for creating a new SignalInterfacePort."""

    signal_interface_id: int
    port_identifier: str
    description: str | None = None
    is_active: bool = True


class SignalInterfacePortPatchRequest(BaseModel):
    """Partial update for a SignalInterfacePort."""

    port_identifier: str | None = None
    description: str | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Equipment wiring / location
# ---------------------------------------------------------------------------


class EquipmentWiringRequest(BaseModel):
    """Request to wire equipment to a signal interface/port."""

    equipment_id: int
    signal_interface_id: int
    signal_interface_port_id: int | None = None
    valid_from: datetime
    note: str | None = None


class EquipmentWiringResponse(BaseModel):
    """Response after wiring equipment."""

    equipment_id: int
    signal_interface_id: int
    signal_interface_port_id: int | None
    wiring_history_id: int


class EquipmentRelocateRequest(BaseModel):
    """Request to relocate equipment to a sampling point."""

    equipment_id: int
    sampling_point_id: int
    valid_from: datetime
    campaign_id: int | None = None
    notes: str | None = None


class EquipmentRelocateResponse(BaseModel):
    """Response after relocating equipment."""

    equipment_id: int
    sampling_point_id: int
    location_history_id: int


# ---------------------------------------------------------------------------
# Point-in-time queries
# ---------------------------------------------------------------------------


class EquipmentAtTimeResponse(BaseModel):
    signal_interface_id: int
    at_time: datetime
    history_id: int | None
    equipment_id: int | None
    equipment_identifier: str | None
    serial_number: str | None
    valid_from: datetime | None
    valid_to: datetime | None


class LocationAtTimeResponse(BaseModel):
    equipment_id: int
    at_time: datetime
    history_id: int | None
    sampling_point_id: int | None
    sampling_point_name: str | None
    valid_from: datetime | None
    valid_to: datetime | None


# ---------------------------------------------------------------------------
# Sub-signal navigation
# ---------------------------------------------------------------------------


class SubSignalOut(BaseModel):
    channel_id: int
    tag_name: str
    is_active: bool
    description: str | None
    parent_channel_id: int
    channel_kind_id: int
    channel_role_name: str


class SubSignalsResponse(BaseModel):
    parent_channel_id: int
    sub_signals: list[SubSignalOut]


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------


class SignalInterfaceProvisionIn(BaseModel):
    """Payload for find-or-create a SignalInterface by name (used by L5X loader)."""

    das_name: str
    name: str
    manufacturer: str | None = None
    model: str | None = None
    description: str | None = None


class SignalInterfacePortProvisionIn(BaseModel):
    """Payload for find-or-create a SignalInterfacePort by name (used by L5X loader)."""

    signal_interface_id: int
    port_identifier: str
    description: str | None = None


class SignalInterfaceLookupOut(BaseModel):
    """Lightweight SignalInterface representation for dropdowns and foreign-key lookups."""

    signal_interface_id: int
    name: str
    das_name: str


class DasOut(BaseModel):
    """Full DataAcquisitionSystem representation."""

    das_id: int
    name: str
    description: str | None = None
    das_kind_id: int | None = None
    das_kind_name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    parent_system_id: int | None = None


class DasLookupOut(BaseModel):
    das_id: int
    name: str


class DasCreateIn(BaseModel):
    name: str
    description: str | None = None
    das_kind_id: int | None = None
    manufacturer: str | None = None
    model: str | None = None
    parent_system_id: int | None = None


class DasUpdateIn(BaseModel):
    name: str
    description: str | None = None
    das_kind_id: int | None = None
    manufacturer: str | None = None
    model: str | None = None
    parent_system_id: int | None = None


class SignalInterfacePortCreateIn(BaseModel):
    """Payload for creating a port under a specific interface (signal_interface_id comes from path)."""

    port_identifier: str
    description: str | None = None


class ChannelKindLookupOut(BaseModel):
    channel_kind_id: int
    name: str
    description: str | None = None
