"""Pydantic schemas for Channel resources."""

from __future__ import annotations

from pydantic import BaseModel


class ChannelOut(BaseModel):
    """Full channel record with all resolved foreign keys."""

    channel_id: int
    parameter_id: int | None
    parameter_name: str | None
    unit_id: int | None
    unit_name: str | None
    equipment_id: int | None
    equipment_identifier: str | None
    data_provenance_id: int | None
    data_provenance: str | None
    processing_degree_id: int | None
    processing_degree_name: str | None
    value_type_id: int | None
    value_type_name: str | None


class ChannelListResponse(BaseModel):
    """Paginated list of channels."""

    items: list[ChannelOut]
    total: int
    page: int
    page_size: int
