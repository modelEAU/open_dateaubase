"""Pydantic schemas for Campaign resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CampaignOut(BaseModel):
    campaign_id: int
    campaign_type_id: int
    campaign_type_name: str | None
    site_id: int
    site_name: str | None
    name: str
    description: str | None
    start_date: datetime | None
    end_date: datetime | None


class CampaignIn(BaseModel):
    name: str
    campaign_type_id: int
    site_id: int
    description: str | None = None
    start_date: str | None = None  # ISO datetime string e.g. "2024-06-01T00:00:00"
    end_date: str | None = None


class CampaignPatch(BaseModel):
    """Partial update schema for Campaign - all fields optional."""

    name: str | None = None
    campaign_type_id: int | None = None
    site_id: int | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class CampaignTypeOut(BaseModel):
    """Campaign type info for dropdowns."""

    campaign_type_id: int
    name: str
    description: str | None = None


class CampaignContextOut(BaseModel):
    """Full context for a campaign — locations, equipment, parameters, metadata."""

    campaign: CampaignOut
    sampling_locations: list[dict]
    equipment: list[dict]
    parameters: list[dict]
    metadata_count: int
    time_range_start: datetime | None
    time_range_end: datetime | None


class DeploymentOut(BaseModel):
    """A deployment pairs equipment with a sampling point for a campaign."""

    equipment_id: int
    equipment_identifier: str | None
    sampling_point_id: int | None
    sampling_point_name: str | None
    role: str | None
    installation_id: int | None
    installed_date: datetime | None


class DeploymentCreateIn(BaseModel):
    """Input for creating a deployment."""

    equipment_id: int
    sampling_point_id: int
    role: str | None = None
    notes: str | None = None


class DeploymentCreateOut(BaseModel):
    """Output after creating a deployment."""

    installation_id: int


