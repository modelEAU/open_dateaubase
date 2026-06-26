"""Pydantic schemas for Channel resources."""

from __future__ import annotations

from pydantic import BaseModel


class ChannelOut(BaseModel):
    """Full channel record with all resolved foreign keys."""

    channel_id: int
    signal_interface_id: int | None
    signal_interface_name: str | None
    signal_interface_port_id: int | None
    signal_interface_port_identifier: str | None
    tag_name: str
    parent_channel_id: int | None
    parent_channel_tag_name: str | None
    channel_kind_id: int | None
    channel_kind_name: str | None
    parameter_id: int | None
    parameter_name: str | None
    data_provenance_kind_id: int | None
    data_provenance_kind_name: str | None
    produced_by_step_id: int | None
    value_kind_id: int | None
    value_kind_name: str | None
    unit_id: int | None
    unit_name: str | None
    equipment_id: int | None
    equipment_identifier: str | None


class ChannelIn(BaseModel):
    """Channel input schema for create/update operations."""

    signal_interface_id: int | None = None
    tag_name: str
    signal_interface_port_id: int | None = None
    parent_channel_id: int | None = None
    channel_kind_id: int = 1
    parameter_id: int | None = None
    data_provenance_kind_id: int | None = None
    produced_by_step_id: int | None = None
    value_kind_id: int | None = None


class ChannelLookupOut(BaseModel):
    """Lightweight channel info for dropdowns."""

    channel_id: int
    tag_name: str
    signal_interface_name: str | None


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
    envo_iri: str | None = None


class ParameterOut(BaseModel):
    parameter_id: int
    parameter_name: str | None
    description: str | None
    envo_iri: str | None = None
    value_kind_id: int | None = None


class UnitOut(BaseModel):
    unit_id: int
    unit: str
    qudt_iri: str | None = None
    unit_vector: str | None = None


class UnitIn(BaseModel):
    unit: str
    qudt_iri: str | None = None
    unit_vector: str | None = None
    si_multiplier: float | None = None
    si_offset: float | None = None


class ChannelKindLookupOut(BaseModel):
    """Lightweight channel role info for dropdowns."""

    channel_kind_id: int
    name: str
    description: str | None


class ChannelListResponse(BaseModel):
    """Paginated list of channels."""

    items: list[ChannelOut]
    total: int
    page: int
    page_size: int


class ChannelDerivedIn(BaseModel):
    source_channel_id: int
    produced_by_step_id: int | None = None


class ChannelDerivedOut(BaseModel):
    channel_id: int


class ChannelResolveIn(BaseModel):
    """Request to resolve a channel by its natural keys."""

    signal_interface_name: str
    tag_name: str
    parameter_name: str | None = None
    create_missing: bool = False


class ChannelResolveOut(BaseModel):
    """Response from channel resolution."""

    channel_id: int


class ChannelProvisionIn(BaseModel):
    """Payload for find-or-create a Channel by name-based fields (used by L5X loader)."""

    signal_interface_id: int
    tag_name: str
    signal_interface_port_id: int | None = None
    parent_channel_id: int | None = None
    channel_kind: str = "value"
    parameter_name: str | None = None
    unit_name: str | None = None
    data_provenance_kind_id: int | None = None
    produced_by_step_id: int | None = None
    value_kind_id: int | None = None


class ChannelPortHistoryIn(BaseModel):
    """Payload for opening a ChannelPortHistory row."""

    signal_interface_port_id: int | None = None
    valid_from: str
    gating_note: str | None = None


class ChannelPortHistoryOut(BaseModel):
    """Response after opening a ChannelPortHistory row."""

    channel_port_history_id: int
    channel_id: int
    signal_interface_port_id: int | None
    valid_from: str
    gating_note: str | None


class ParameterUnitIn(BaseModel):
    unit_id: int


class ParameterUnitOut(BaseModel):
    parameter_id: int
    unit_id: int
    unit: str
