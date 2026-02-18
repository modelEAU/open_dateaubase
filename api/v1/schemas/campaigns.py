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
    project_id: int | None
    project_name: str | None


class CampaignContextOut(BaseModel):
    """Full context for a campaign — locations, equipment, parameters, metadata."""

    campaign: CampaignOut
    sampling_locations: list[dict]
    equipment: list[dict]
    parameters: list[dict]
    metadata_count: int
    time_range_start: datetime | None
    time_range_end: datetime | None
