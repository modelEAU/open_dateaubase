"""
Pydantic models (DTOs) for the datEAUbase Metadata API.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------

class LookupItem(BaseModel):
    id: int
    label: str


class LookupCreateRequest(BaseModel):
    label: str


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    equipment_id: int
    parameter_id: int
    unit_id: int
    purpose_id: int
    sampling_point_id: int
    project_id: int
    value: float
    timestamp: datetime


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------

class ValueItem(BaseModel):
    value_id: int
    value: float
    metadata_id: int
    timestamp: int


# ---------------------------------------------------------------------------
# Metadata listing
# ---------------------------------------------------------------------------

class RefLabel(BaseModel):
    id: Optional[int] = None
    label: Optional[str] = None


class MetadataListItem(BaseModel):
    metadata_id: int
    equipment: Optional[RefLabel] = None
    parameter: Optional[RefLabel] = None
    unit: Optional[RefLabel] = None
    purpose: Optional[RefLabel] = None
    project: Optional[RefLabel] = None
    sampling_point: Optional[RefLabel] = None
    start_ts: Optional[int] = None
    end_ts: Optional[int] = None


class MetadataListResponse(BaseModel):
    total: int
    items: List[MetadataListItem]


# ---------------------------------------------------------------------------
# Metadata creation
# ---------------------------------------------------------------------------

class MetadataCreateRequest(BaseModel):
    equipment_id: int
    parameter_id: int
    unit_id: int
    purpose_id: int
    sampling_point_id: int
    project_id: int
    procedure_id: Optional[int] = None
    contact_id: Optional[int] = None
    condition_id: Optional[int] = None
    start_ts: int
    end_ts: Optional[int] = None