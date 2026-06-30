"""Maintenance-drift derived Channel endpoint (PRD-2.5 S1).

POST /channels/derived/maintenance-drift
  - Creates a ProcessingStep (method='maintenance_drift') recording the source
    channel and maintenance event IDs in MethodParameters JSON.
  - Mints a derived Channel linked to that step.
  - Does NOT compute or insert %diff Values (S2 scope).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from api.v1.errors import EntityNotFoundError
from ..repositories import maintenance_drift_repository
from ..schemas.maintenance_drift import MaintenanceDriftIn, MaintenanceDriftOut

router = APIRouter()


@router.post(
    "/derived/maintenance-drift",
    response_model=MaintenanceDriftOut,
    status_code=201,
    tags=["channels"],
    summary="Create a maintenance-drift derived Channel",
    description=(
        "Model maintenance drift as a first-class derived Channel. "
        "Creates a ProcessingStep storing source_channel_id + event_ids in "
        "MethodParameters JSON, then mints a derived Channel linked to that step. "
        "Value computation (%diff points) is S2 scope and is not performed here."
    ),
)
def create_maintenance_drift_channel(
    body: MaintenanceDriftIn,
    conn=Depends(get_db),
) -> MaintenanceDriftOut:
    """Create a ProcessingStep + derived Channel for maintenance drift tracking."""
    try:
        result = maintenance_drift_repository.create_drift_channel(
            conn,
            source_channel_id=body.source_channel_id,
            event_ids=body.event_ids,
            name=body.name,
            performed_by_person_id=body.performed_by_person_id,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MaintenanceDriftOut(**result)
