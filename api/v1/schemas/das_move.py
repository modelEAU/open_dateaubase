"""Pydantic schemas for DAS deployment endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DASDeployRequest(BaseModel):
    """Deploy a DAS to a site, closing any existing active deployment."""

    site_id: int
    valid_from: datetime
    campaign_id: int | None = None
    notes: str | None = None


class DASDeployResponse(BaseModel):
    das_id: int
    new_history_id: int
    closed_history_id: int | None


class DASActiveDeploymentResponse(BaseModel):
    das_id: int
    history_id: int | None
    site_id: int | None
    site_name: str | None
    campaign_id: int | None
    campaign_name: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    notes: str | None


class DASConflictResponse(BaseModel):
    """Result of a conflict check. ``conflict`` is True when the DAS is active
    at a *different* site."""

    das_id: int
    site_id: int
    conflict: bool
    conflicting_site_id: int | None
    conflicting_site_name: str | None
    conflicting_campaign_id: int | None
    conflicting_campaign_name: str | None
