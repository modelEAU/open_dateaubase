"""Equipment move endpoints.

Anchors on Equipment_ID and operates on EquipmentWiringHistory and
EquipmentLocationHistory.

Endpoints:
  POST /equipment/{equipment_id}/rewire            — close current + open new wiring row
  POST /equipment/{equipment_id}/register-interface — open first wiring row
  POST /equipment/{equipment_id}/relocate          — close + open location row
  GET  /equipment/{equipment_id}/wiring-at         — point-in-time wiring query
  GET  /equipment/{equipment_id}/location-at       — point-in-time location query

A move writes no recording. The history rows *are* the record of the move, and
per ADR-0007 an Annotation is a verdict on data, never a cause. If a mover wants
the surrounding window flagged, they record it themselves.
"""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import temporal_history_repository
from ..schemas.equipment_move import (
    ActiveCampaignDeploymentResponse,
    EquipmentRegisterInterfaceRequest,
    EquipmentRegisterInterfaceResponse,
    EquipmentRelocateRequest,
    EquipmentRelocateResponse,
    EquipmentRewireRequest,
    EquipmentRewireResponse,
    LocationAtTimeResponse,
    WiringAtTimeResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Rewire
# ---------------------------------------------------------------------------


@router.post(
    "/{equipment_id}/rewire",
    response_model=EquipmentRewireResponse,
    status_code=201,
)
def rewire_equipment_endpoint(
    equipment_id: int,
    body: EquipmentRewireRequest,
    conn=Depends(get_db),
):
    """Replace the signal interface behind a piece of equipment.

    Closes the current active EquipmentWiringHistory row (if any) with
    ``ValidTo = valid_from`` and opens a new row.
    """
    try:
        new_id, closed_id = temporal_history_repository.rewire_equipment(
            conn,
            equipment_id=equipment_id,
            new_signal_interface_id=body.signal_interface_id,
            new_signal_interface_port_id=body.signal_interface_port_id,
            swap_time=body.valid_from,
            note=body.note,
        )
    except pyodbc.Error as exc:
        sqlstate = exc.args[0] if exc.args else None
        if sqlstate == "23000":
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Could not open a new wiring history row for equipment {equipment_id}: "
                    "a concurrent active row already exists. "
                    f"Database error: {exc}"
                ),
            ) from exc
        raise HTTPException(
            status_code=422,
            detail=(
                f"Could not rewire equipment {equipment_id}. "
                f"Database error: {exc}"
            ),
        ) from exc

    return EquipmentRewireResponse(
        equipment_id=equipment_id,
        new_wiring_history_id=new_id,
        closed_wiring_history_id=closed_id,
    )


# ---------------------------------------------------------------------------
# Register interface
# ---------------------------------------------------------------------------


@router.post(
    "/{equipment_id}/register-interface",
    response_model=EquipmentRegisterInterfaceResponse,
    status_code=201,
)
def register_equipment_interface_endpoint(
    equipment_id: int,
    body: EquipmentRegisterInterfaceRequest,
    conn=Depends(get_db),
):
    """Register equipment against a signal interface that has no active wiring row.

    Used for late registration: the equipment already exists but has not yet
    been linked to a signal interface.

    Returns 409 if an active wiring row already exists — use ``rewire`` to
    replace the current wiring.
    """
    try:
        history_id = temporal_history_repository.register_equipment_at_interface(
            conn,
            equipment_id=equipment_id,
            signal_interface_id=body.signal_interface_id,
            signal_interface_port_id=body.signal_interface_port_id,
            start_time=body.valid_from,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return EquipmentRegisterInterfaceResponse(
        equipment_id=equipment_id,
        wiring_history_id=history_id,
    )


# ---------------------------------------------------------------------------
# Relocate
# ---------------------------------------------------------------------------


@router.post(
    "/{equipment_id}/relocate",
    response_model=EquipmentRelocateResponse,
    status_code=201,
)
def relocate_equipment_endpoint(
    equipment_id: int,
    body: EquipmentRelocateRequest,
    conn=Depends(get_db),
):
    """Move equipment to a new SamplingPoint.

    Closes the current active EquipmentLocationHistory row with
    ``ValidTo = valid_from`` and opens a new row for the new
    ``sampling_point_id``.
    """
    try:
        new_id, closed_id = temporal_history_repository.relocate_equipment(
            conn,
            equipment_id=equipment_id,
            new_sampling_point_id=body.sampling_point_id,
            start_time=body.valid_from,
            campaign_id=body.campaign_id,
            notes=body.notes,
        )
    except pyodbc.Error as exc:
        sqlstate = exc.args[0] if exc.args else None
        if sqlstate == "23000":
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Could not open a new location history row for equipment {equipment_id}: "
                    "a concurrent active row already exists. "
                    f"Database error: {exc}"
                ),
            ) from exc
        raise HTTPException(
            status_code=422,
            detail=(
                f"Could not relocate equipment {equipment_id}. "
                f"Database error: {exc}"
            ),
        ) from exc

    return EquipmentRelocateResponse(
        equipment_id=equipment_id,
        new_location_history_id=new_id,
        closed_location_history_id=closed_id,
    )


# ---------------------------------------------------------------------------
# Point-in-time queries
# ---------------------------------------------------------------------------


@router.get(
    "/{equipment_id}/wiring-at",
    response_model=WiringAtTimeResponse,
)
def get_wiring_at_time_endpoint(
    equipment_id: int,
    at_time: datetime = Query(..., alias="at", description="ISO 8601 timestamp"),
    conn=Depends(get_db),
):
    """Return the wiring that was active at *at_time*, or None."""
    row = temporal_history_repository.get_wiring_at_time(conn, equipment_id, at_time)
    if row is None:
        return WiringAtTimeResponse(
            equipment_id=equipment_id,
            at_time=at_time,
            history_id=None,
            signal_interface_id=None,
            signal_interface_port_id=None,
            signal_interface_name=None,
            equipment_identifier=None,
            valid_from=None,
            valid_to=None,
        )
    return WiringAtTimeResponse(
        equipment_id=equipment_id,
        at_time=at_time,
        history_id=row["history_id"],
        signal_interface_id=row["signal_interface_id"],
        signal_interface_port_id=row.get("signal_interface_port_id"),
        signal_interface_name=row.get("signal_interface_name"),
        equipment_identifier=row.get("equipment_identifier"),
        valid_from=row["valid_from"],
        valid_to=row["valid_to"],
    )


@router.get(
    "/{equipment_id}/location-at",
    response_model=LocationAtTimeResponse,
)
def get_location_at_time_endpoint(
    equipment_id: int,
    at_time: datetime = Query(..., alias="at", description="ISO 8601 timestamp"),
    conn=Depends(get_db),
):
    """Return the location that was active at *at_time*, or None."""
    row = temporal_history_repository.get_location_at_time(conn, equipment_id, at_time)
    if row is None:
        return LocationAtTimeResponse(
            equipment_id=equipment_id,
            at_time=at_time,
            history_id=None,
            sampling_point_id=None,
            sampling_point_name=None,
            valid_from=None,
            valid_to=None,
        )
    return LocationAtTimeResponse(
        equipment_id=equipment_id,
        at_time=at_time,
        history_id=row["history_id"],
        sampling_point_id=row["sampling_point_id"],
        sampling_point_name=row.get("sampling_point_name"),
        valid_from=row["valid_from"],
        valid_to=row["valid_to"],
    )


@router.get(
    "/{equipment_id}/active-campaign",
    response_model=ActiveCampaignDeploymentResponse,
)
def get_active_campaign_endpoint(
    equipment_id: int,
    conn=Depends(get_db),
):
    """Return the still-running campaign whose deployment placed this equipment.

    Reconfiguring (relocate/rewire) equipment placed by a campaign that has not
    ended will close that campaign's deployment, since physical configuration is
    shared across campaigns. The move UIs call this to warn before acting. All
    fields are None when no open campaign row exists."""
    row = temporal_history_repository.get_active_campaign_deployment(conn, equipment_id)
    if row is None:
        return ActiveCampaignDeploymentResponse(
            equipment_id=equipment_id,
            campaign_id=None,
            campaign_name=None,
            equipment_location_history_id=None,
            sampling_point_id=None,
            sampling_point_name=None,
        )
    return ActiveCampaignDeploymentResponse(
        equipment_id=equipment_id,
        campaign_id=row["campaign_id"],
        campaign_name=row.get("campaign_name"),
        equipment_location_history_id=row.get("equipment_location_history_id"),
        sampling_point_id=row.get("sampling_point_id"),
        sampling_point_name=row.get("sampling_point_name"),
    )
