"""Pydantic schemas for Channel resources."""

from __future__ import annotations

from pydantic import BaseModel


class ChannelOut(BaseModel):
    """Full channel record with all resolved foreign keys."""

    channel_id: int
    signal_port_id: int
    signal_port_tag: str | None
    parameter_id: int | None
    parameter_name: str | None
    equipment_id: int | None
    equipment_identifier: str | None
    data_provenance_id: int | None
    data_provenance: str | None
    processing_degree_id: int | None
    processing_degree_name: str | None
    value_type_id: int | None
    value_type_name: str | None
    unit_id: int | None
    unit_name: str | None


class ChannelIn(BaseModel):
    """Channel input schema for create/update operations."""

    signal_port_id: int
    parameter_id: int | None = None
    data_provenance_id: int | None = None
    processing_degree_id: int | None = None
    value_type_id: int | None = None


class EquipmentLookupOut(BaseModel):
    """Lightweight equipment info for dropdowns."""

    equipment_id: int
    identifier: str


class ParameterLookupOut(BaseModel):
    """Lightweight parameter info for dropdowns."""

    parameter_id: int
    parameter_name: str


class ParameterIn(BaseModel):
    parameter: str
    description: str | None = None


class ParameterOut(BaseModel):
    parameter_id: int
    parameter_name: str | None
    description: str | None


class ProcessingDegreeLookupOut(BaseModel):
    """Lightweight processing degree info for dropdowns."""

    processing_degree_id: int
    name: str


class ChannelListResponse(BaseModel):
    """Paginated list of channels."""

    items: list[ChannelOut]
    total: int
    page: int
    page_size: int


class ChannelDerivedIn(BaseModel):
    source_channel_id: int
    processing_degree_id: int


class ChannelDerivedOut(BaseModel):
    channel_id: int
