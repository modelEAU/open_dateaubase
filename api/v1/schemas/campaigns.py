"""Pydantic schemas for Campaign resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CampaignOut(BaseModel):
    campaign_id: int
    campaign_kind_id: int
    campaign_kind_name: str | None
    # Campaigns are multi-site; sites are derived from sampling-location membership.
    site_ids: list[int] = []
    site_names: list[str] = []
    name: str
    description: str | None
    start_date: datetime | None
    end_date: datetime | None
    responsible_person_id: int | None = None
    responsible_person_name: str | None = None


class CampaignIn(BaseModel):
    name: str
    campaign_kind_id: int
    description: str | None = None
    start_date: str | None = None  # ISO datetime string e.g. "2024-06-01T00:00:00"
    end_date: str | None = None
    responsible_person_id: int | None = None


class CampaignPatch(BaseModel):
    """Partial update schema for Campaign - all fields optional."""

    name: str | None = None
    campaign_kind_id: int | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    responsible_person_id: int | None = None


class CampaignKindOut(BaseModel):
    """Campaign type info for dropdowns."""

    campaign_kind_id: int
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


class CampaignOverviewOut(BaseModel):
    """Read-only Campaign Story aggregate (see campaign_repository.get_campaign_overview)."""

    campaign: CampaignOut
    watershed: dict | None
    sampling_points: list[dict]
    data_acquisition_systems: list[dict]
    equipment: list[dict]
    lab_series: list[dict]
    lab_panels: list[dict]
    annotations: list[dict]
    freshness: list[dict]


class DeploymentOut(BaseModel):
    """A deployment pairs equipment with a sampling point for a campaign."""

    equipment_id: int
    equipment_identifier: str | None
    sampling_point_id: int | None
    sampling_point_name: str | None
    installation_id: int | None
    installed_date: datetime | None


class DeploymentCreateIn(BaseModel):
    """Input for creating a deployment."""

    equipment_id: int
    sampling_point_id: int
    valid_from: datetime | None = None
    notes: str | None = None


class DeploymentCreateOut(BaseModel):
    """Output after creating a deployment."""

    installation_id: int


