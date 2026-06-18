"""Schemas for the Deployment Trace lookup endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DeploymentTraceLookupItem(BaseModel):
    """One selectable atom in the Data Explorer sensor picker.

    A deployed trace is a Channel scoped to one EquipmentLocationHistory row.
    An undeployed trace is a Channel with no wiring history; its deployment
    fields are None and is_deployed is False.
    """

    equipment_location_history_id: int | None = None
    channel_id: int
    equipment_id: int | None = None
    equipment_identifier: str | None = None
    sampling_point_id: int | None = None
    sampling_point_label: str | None = None
    parameter_id: int
    parameter_name: str
    value_kind_id: int
    campaign_id: int | None = None
    campaign_name: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_deployed: bool = True
