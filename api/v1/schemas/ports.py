"""Pydantic schemas for SignalPort lifecycle endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Equipment swap / registration
# ---------------------------------------------------------------------------


class PortEquipmentSwapRequest(BaseModel):
    """Close current active PortEquipmentHistory and open a new one."""

    equipment_id: int
    swap_time: datetime
    notes: str | None = None


class PortEquipmentSwapResponse(BaseModel):
    signal_port_id: int
    new_history_id: int
    closed_history_id: int | None


class PortEquipmentRegisterRequest(BaseModel):
    """Open a new PortEquipmentHistory row (no active row must exist)."""

    equipment_id: int
    start_time: datetime | None = None
    notes: str | None = None


class PortEquipmentRegisterResponse(BaseModel):
    signal_port_id: int
    history_id: int


# ---------------------------------------------------------------------------
# Sensor relocation
# ---------------------------------------------------------------------------


class PortRelocateRequest(BaseModel):
    """Close current active LocationHistory and open a new one.

    ``start_time`` is required and must equal the physical move time.
    """

    sampling_point_id: int
    start_time: datetime
    notes: str | None = None


class PortRelocateResponse(BaseModel):
    signal_port_id: int
    new_location_history_id: int
    closed_location_history_id: int | None
    annotation_ids: list[int]
    channel_ids_affected: list[int]


# ---------------------------------------------------------------------------
# Point-in-time queries
# ---------------------------------------------------------------------------


class EquipmentAtTimeResponse(BaseModel):
    signal_port_id: int
    at_time: datetime
    history_id: int | None
    equipment_id: int | None
    equipment_identifier: str | None
    serial_number: str | None
    start_time: datetime | None
    end_time: datetime | None


class LocationAtTimeResponse(BaseModel):
    signal_port_id: int
    at_time: datetime
    history_id: int | None
    sampling_point_id: int | None
    sampling_point_name: str | None
    sampling_point_description: str | None
    start_time: datetime | None
    end_time: datetime | None


# ---------------------------------------------------------------------------
# Sub-signal navigation
# ---------------------------------------------------------------------------


class SubSignalOut(BaseModel):
    signal_port_id: int
    tag: str
    is_active: bool
    description: str | None
    parent_port_id: int
    signal_port_type_id: int
    signal_port_type_name: str


class SubSignalsResponse(BaseModel):
    parent_port_id: int
    sub_signals: list[SubSignalOut]


# ---------------------------------------------------------------------------
# SignalPort CRUD
# ---------------------------------------------------------------------------


class SignalPortOut(BaseModel):
    """Full SignalPort representation with resolved DAS and type names."""

    signal_port_id: int
    tag: str
    is_active: bool
    description: str | None
    parent_port_id: int | None
    signal_port_type_id: int
    signal_port_type_name: str
    das_id: int
    das_name: str


class SignalPortCreateRequest(BaseModel):
    """Payload for creating a new SignalPort."""

    das_id: int
    tag: str
    signal_port_type_id: int
    description: str | None = None
    parent_port_id: int | None = None


class SignalPortPatchRequest(BaseModel):
    """Partial update for a SignalPort — only supplied fields are written."""

    description: str | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------


class DasLookupOut(BaseModel):
    das_id: int
    name: str


class SignalPortTypeLookupOut(BaseModel):
    signal_port_type_id: int
    name: str
