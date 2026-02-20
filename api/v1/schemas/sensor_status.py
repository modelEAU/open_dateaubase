"""Pydantic schemas for sensor status API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StatusCodeResponse(BaseModel):
    """Response schema for a sensor status code."""

    id: int
    name: str
    description: Optional[str] = None
    is_operational: bool
    severity: int


class StatusCodeListResponse(BaseModel):
    """Response schema for listing all status codes."""

    status_codes: list[StatusCodeResponse]


class ChannelStatus(BaseModel):
    """Status for a single measurement channel."""

    measurement_metadata_id: int
    parameter: str
    location: str
    status_code: int
    status_name: str
    is_operational: bool
    severity: int
    since: datetime


class DeviceStatus(BaseModel):
    """Device-level status."""

    status_code: int
    status_name: str
    is_operational: bool
    severity: int
    since: datetime


class EquipmentStatusResponse(BaseModel):
    """Full status response for an equipment."""

    equipment_id: int
    equipment_name: str
    queried_at: datetime
    device_status: Optional[DeviceStatus] = None
    channel_statuses: list[ChannelStatus]
    overall_operational: bool
    worst_severity: int


class StatusTransition(BaseModel):
    """A single status transition event."""

    timestamp: datetime
    status_code: int
    status_name: str
    is_operational: bool


class ChannelTransitions(BaseModel):
    """Status transitions for a single channel."""

    measurement_metadata_id: int
    transitions: list[StatusTransition]


class EquipmentStatusHistoryResponse(BaseModel):
    """Response for equipment status history endpoint."""

    equipment_id: int
    equipment_name: str
    query_range: dict
    device_transitions: list[StatusTransition]
    channel_transitions: dict[str, ChannelTransitions]


class StatusInterval(BaseModel):
    """A status interval for rendering bands in UI."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "properties": {
                "from": {"type": "string", "format": "date-time"},
                "to": {"type": "string", "format": "date-time"},
            }
        },
    )

    from_time: datetime = Field(..., alias="from")
    to_time: datetime = Field(..., alias="to")
    status_code: int
    status_name: str
    is_operational: bool
    severity: int


class TimeSeriesStatusBand(BaseModel):
    """Status band response for a time series."""

    metadata_id: int
    parameter: Optional[str] = None
    equipment_name: Optional[str] = None
    query_range: dict
    status_intervals: list[StatusInterval]
    has_status_data: bool


class TimeSeriesOut(BaseModel):
    """Extended time series response with optional status."""

    metadata_id: int
    location: Optional[str] = None
    site: Optional[str] = None
    parameter: Optional[str] = None
    unit: Optional[str] = None
    data_shape: str
    provenance: Optional[str] = None
    processing_degree: Optional[str] = None
    campaign: Optional[str] = None
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    row_count: int
    data: list[dict]
    status_band: Optional[list[StatusInterval]] = None
    has_status_data: bool = False
