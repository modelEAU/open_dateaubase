"""Deployment Trace lookup endpoint for the Data Explorer picker.

GET /deployment-traces/lookup — returns the selectable atoms for the sensor
side of the unified picker: each row is a Channel scoped to one
EquipmentLocationHistory period at one SamplingPoint under one Campaign.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from api.database import get_db
from ..repositories import temporal_history_repository
from ..schemas.deployment_traces import DeploymentTraceLookupItem

router = APIRouter()


@router.get("/lookup", response_model=list[DeploymentTraceLookupItem])
def list_deployment_traces_lookup(
    sampling_point_id: int | None = Query(default=None),
    campaign_id: int | None = Query(default=None),
    parameter_id: int | None = Query(default=None),
    value_kind_id: int | None = Query(default=None),
    from_dt: datetime | None = Query(default=None),
    to_dt: datetime | None = Query(default=None),
    conn=Depends(get_db),
):
    """Return Deployment Traces for the Data Explorer picker.

    Each result is a Channel scoped to one EquipmentLocationHistory period.
    Optionally filtered by location, campaign, parameter, value type, and/or
    time-range overlap (deployments that overlapped [from_dt, to_dt]).
    """
    return temporal_history_repository.list_deployment_traces(
        conn,
        sampling_point_id=sampling_point_id,
        campaign_id=campaign_id,
        parameter_id=parameter_id,
        value_kind_id=value_kind_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )
