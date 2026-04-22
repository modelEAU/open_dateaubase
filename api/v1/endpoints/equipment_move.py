"""Equipment move endpoints.

Anchors on Equipment_ID and operates on EquipmentWiringHistory and
EquipmentLocationHistory.

Endpoints:
  POST /equipment/{equipment_id}/rewire            — close current + open new wiring row
  POST /equipment/{equipment_id}/register-interface — open first wiring row
  POST /equipment/{equipment_id}/relocate          — close + open location row + auto-annotate
  GET  /equipment/{equipment_id}/wiring-at         — point-in-time wiring query
  GET  /equipment/{equipment_id}/location-at       — point-in-time location query
"""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import (
    annotation_repository,
    channel_repository,
    temporal_history_repository,
)
from ..schemas.equipment_move import (
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

# AnnotationType_ID for "Equipment Relocation" — seeded in migration v1.0.0_to_v3.0.0
_EQUIPMENT_MOVE_ANNOTATION_TYPE_ID = 11


def _get_channel_ids(conn: pyodbc.Connection, equipment_id: int) -> list[int]:
    """Return Channel_IDs for equipment, or empty list if none."""
    return channel_repository.get_channel_ids_for_equipment(conn, equipment_id)


def _annotate_move(
    conn: pyodbc.Connection,
    equipment_id: int,
    title: str,
    comment: str,
    start_time: datetime,
) -> list[int]:
    """Create auto-annotations on every channel associated with the equipment."""
    channel_ids = _get_channel_ids(conn, equipment_id)
    if not channel_ids:
        return []
    return annotation_repository.create_equipment_move_annotations(
        conn,
        channel_ids=channel_ids,
        annotation_type_id=_EQUIPMENT_MOVE_ANNOTATION_TYPE_ID,
        title=title,
        comment=comment,
        start_time=start_time,
    )


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

    Automatically creates an "Equipment Move" Annotation on every
    Channel associated with this equipment so that the event is flagged
    for data quality review.
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
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Could not open a new wiring history row for equipment {equipment_id}: "
                "a concurrent active row already exists. "
                f"Database error: {exc}"
            ),
        ) from exc

    comment = (
        f"Equipment rewired to SignalInterface ID={body.signal_interface_id} "
        f"at {body.valid_from.isoformat()}."
    )
    if body.note:
        comment += f" Note: {body.note}"

    annotation_ids = _annotate_move(
        conn,
        equipment_id,
        title="Equipment Rewired",
        comment=comment,
        start_time=body.valid_from,
    )

    return EquipmentRewireResponse(
        equipment_id=equipment_id,
        new_wiring_history_id=new_id,
        closed_wiring_history_id=closed_id,
        annotation_ids=annotation_ids,
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

    Automatically creates an "Equipment Move" Annotation on every
    Channel associated with this equipment so that the event is flagged
    for data quality review.
    """
    try:
        new_id, closed_id = temporal_history_repository.relocate_equipment(
            conn,
            equipment_id=equipment_id,
            new_sampling_point_id=body.sampling_point_id,
            start_time=body.valid_from,
            notes=body.notes,
        )
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Could not open a new location history row for equipment {equipment_id}: "
                "a concurrent active row already exists. "
                f"Database error: {exc}"
            ),
        ) from exc

    comment = (
        f"Sensor physically moved to SamplingPoint ID={body.sampling_point_id} "
        f"at {body.valid_from.isoformat()}."
    )
    if body.notes:
        comment += f" Notes: {body.notes}"

    annotation_ids = _annotate_move(
        conn,
        equipment_id,
        title="Equipment Relocation",
        comment=comment,
        start_time=body.valid_from,
    )

    return EquipmentRelocateResponse(
        equipment_id=equipment_id,
        new_location_history_id=new_id,
        closed_location_history_id=closed_id,
        annotation_ids=annotation_ids,
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
