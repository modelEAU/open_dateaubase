"""Schemas for the Deployment Trace lookup endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DeploymentTraceLookupItem(BaseModel):
    """One selectable atom in the Data Explorer sensor picker.

    A Deployment Trace is a Channel scoped to one EquipmentLocationHistory row:
    a specific piece of equipment at a specific SamplingPoint for a specific period
    under a Campaign.
    """

    equipment_location_history_id: int
    channel_id: int
    equipment_id: int
    equipment_identifier: str
    sampling_point_id: int
    sampling_point_label: str
    parameter_id: int
    parameter_name: str
    value_kind_id: int
    campaign_id: int
    campaign_name: str
    valid_from: datetime
    valid_to: datetime | None = None
