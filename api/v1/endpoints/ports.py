"""SignalPort lifecycle endpoints.

Covers:
  POST /ports/{signal_port_id}/swap-equipment     — close current + open new PortEquipmentHistory
  POST /ports/{signal_port_id}/register-equipment — open first PortEquipmentHistory (no active row)
  POST /ports/{signal_port_id}/relocate           — close + open LocationHistory + auto-annotation
  GET  /ports/{signal_port_id}/equipment-at       — point-in-time equipment query
  GET  /ports/{signal_port_id}/location-at        — point-in-time location query
"""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import annotation_repository, signal_port_repository, temporal_history_repository
from ..schemas.ports import (
    EquipmentAtTimeResponse,
    LocationAtTimeResponse,
    PortEquipmentRegisterRequest,
    PortEquipmentRegisterResponse,
    PortEquipmentSwapRequest,
    PortEquipmentSwapResponse,
    PortRelocateRequest,
    PortRelocateResponse,
    SubSignalOut,
    SubSignalsResponse,
)

router = APIRouter()

# AnnotationType_ID for "Equipment Relocation" — seeded in migration
_EQUIPMENT_RELOCATION_ANNOTATION_TYPE_ID = 11


# ---------------------------------------------------------------------------
# Equipment history
# ---------------------------------------------------------------------------


@router.post(
    "/{signal_port_id}/swap-equipment",
    response_model=PortEquipmentSwapResponse,
    status_code=201,
)
def swap_equipment(
    signal_port_id: int,
    body: PortEquipmentSwapRequest,
    conn=Depends(get_db),
):
    """Replace the equipment behind a port.

    Closes the current active ``SignalPortEquipmentHistory`` row (if any) with
    ``EndTime = swap_time`` and opens a new row for ``new_equipment_id``.

    Channel_ID and all observations are unaffected.
    """
    try:
        new_id, closed_id = temporal_history_repository.swap_equipment(
            conn,
            signal_port_id=signal_port_id,
            new_equipment_id=body.equipment_id,
            swap_time=body.swap_time,
            notes=body.notes,
        )
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Could not open a new equipment history row for port {signal_port_id}: "
                "a concurrent active row already exists. "
                f"Database error: {exc}"
            ),
        ) from exc

    return PortEquipmentSwapResponse(
        signal_port_id=signal_port_id,
        new_history_id=new_id,
        closed_history_id=closed_id,
    )


@router.post(
    "/{signal_port_id}/register-equipment",
    response_model=PortEquipmentRegisterResponse,
    status_code=201,
)
def register_equipment(
    signal_port_id: int,
    body: PortEquipmentRegisterRequest,
    conn=Depends(get_db),
):
    """Register equipment against a port that has no active history row.

    Used for late registration: the port already exists (created at ingest
    time) but no physical instrument was linked at that time.

    Returns 409 if an active row already exists — use ``swap-equipment`` to
    replace the current equipment.
    """
    try:
        history_id = temporal_history_repository.register_equipment_at_port(
            conn,
            signal_port_id=signal_port_id,
            equipment_id=body.equipment_id,
            start_time=body.start_time,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return PortEquipmentRegisterResponse(
        signal_port_id=signal_port_id,
        history_id=history_id,
    )


# ---------------------------------------------------------------------------
# Sensor relocation
# ---------------------------------------------------------------------------


@router.post(
    "/{signal_port_id}/relocate",
    response_model=PortRelocateResponse,
    status_code=201,
)
def relocate_sensor(
    signal_port_id: int,
    body: PortRelocateRequest,
    conn=Depends(get_db),
):
    """Move a sensor to a new SamplingPoint.

    Closes the current active ``SignalPortLocationHistory`` row with
    ``EndTime = start_time`` and opens a new row for the new
    ``sampling_point_id``.

    ``start_time`` must equal the physical move time — it must be supplied
    explicitly and cannot default to now.

    Automatically creates an "Equipment Relocation" Annotation on every
    Channel associated with this port so that the event is flagged for data
    quality review.

    Channel_ID and all observations are unaffected.
    """
    # Sub-signal ports cannot be relocated independently.
    parent_port_id = signal_port_repository.get_parent_port_id(conn, signal_port_id)
    if parent_port_id is not None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"SignalPort {signal_port_id} is a sub-signal port "
                f"(ParentPort_ID={parent_port_id}) and cannot be relocated independently. "
                "Relocate the parent port instead."
            ),
        )

    try:
        new_loc_id, closed_loc_id, channel_ids = temporal_history_repository.relocate_sensor(
            conn,
            signal_port_id=signal_port_id,
            new_sampling_point_id=body.sampling_point_id,
            start_time=body.start_time,
            notes=body.notes,
        )
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Could not open a new location history row for port {signal_port_id}: "
                "a concurrent active row already exists. "
                f"Database error: {exc}"
            ),
        ) from exc

    # Auto-annotate all affected channels.
    annotation_ids: list[int] = []
    relocation_title = "Equipment Relocation"
    relocation_comment = (
        f"Sensor physically moved to SamplingPoint ID={body.sampling_point_id} "
        f"at {body.start_time.isoformat()}."
    )
    if body.notes:
        relocation_comment += f" Notes: {body.notes}"

    for channel_id in channel_ids:
        result = annotation_repository.create_annotation(
            conn,
            channel_id=channel_id,
            annotation_type_id=_EQUIPMENT_RELOCATION_ANNOTATION_TYPE_ID,
            start_time=body.start_time,
            end_time=None,
            author_person_id=None,
            campaign_id=None,
            equipment_event_id=None,
            title=relocation_title,
            comment=relocation_comment,
        )
        annotation_ids.append(result["annotation_id"])

    return PortRelocateResponse(
        signal_port_id=signal_port_id,
        new_location_history_id=new_loc_id,
        closed_location_history_id=closed_loc_id,
        annotation_ids=annotation_ids,
        channel_ids_affected=channel_ids,
    )


# ---------------------------------------------------------------------------
# Point-in-time queries
# ---------------------------------------------------------------------------


@router.get(
    "/{signal_port_id}/equipment-at",
    response_model=EquipmentAtTimeResponse,
)
def get_equipment_at(
    signal_port_id: int,
    at: datetime = Query(..., description="UTC datetime for the point-in-time query"),
    conn=Depends(get_db),
):
    """Return the equipment that was behind this port at time ``at``.

    Returns null equipment fields when no history row covers ``at``.
    """
    row = temporal_history_repository.get_equipment_at_time(conn, signal_port_id, at)
    if row is None:
        return EquipmentAtTimeResponse(
            signal_port_id=signal_port_id,
            at_time=at,
            history_id=None,
            equipment_id=None,
            equipment_identifier=None,
            serial_number=None,
            start_time=None,
            end_time=None,
        )
    return EquipmentAtTimeResponse(
        signal_port_id=signal_port_id,
        at_time=at,
        history_id=row["history_id"],
        equipment_id=row["equipment_id"],
        equipment_identifier=row["equipment_identifier"],
        serial_number=row["serial_number"],
        start_time=row["start_time"],
        end_time=row["end_time"],
    )


@router.get(
    "/{signal_port_id}/location-at",
    response_model=LocationAtTimeResponse,
)
def get_location_at(
    signal_port_id: int,
    at: datetime = Query(..., description="UTC datetime for the point-in-time query"),
    conn=Depends(get_db),
):
    """Return the SamplingPoint this port was measuring at time ``at``.

    Returns null location fields when no history row covers ``at``.
    """
    row = temporal_history_repository.get_location_at_time(conn, signal_port_id, at)
    if row is None:
        return LocationAtTimeResponse(
            signal_port_id=signal_port_id,
            at_time=at,
            history_id=None,
            sampling_point_id=None,
            sampling_point_name=None,
            sampling_point_description=None,
            start_time=None,
            end_time=None,
        )
    return LocationAtTimeResponse(
        signal_port_id=signal_port_id,
        at_time=at,
        history_id=row["history_id"],
        sampling_point_id=row["sampling_point_id"],
        sampling_point_name=row["sampling_point_name"],
        sampling_point_description=row["sampling_point_description"],
        start_time=row["start_time"],
        end_time=row["end_time"],
    )


# ---------------------------------------------------------------------------
# Sub-signal navigation
# ---------------------------------------------------------------------------


@router.get(
    "/{signal_port_id}/sub-signals",
    response_model=SubSignalsResponse,
)
def get_sub_signals(
    signal_port_id: int,
    conn=Depends(get_db),
):
    """Return all sub-signal ports linked to a parent value port.

    A sub-signal port has ``ParentPort_ID = signal_port_id``.  This covers
    Status, Alarm, and Uncertainty ports associated with a measurement point.

    Returns an empty list when no sub-signals exist.
    """
    rows = signal_port_repository.get_sub_signals(conn, signal_port_id)
    return SubSignalsResponse(
        parent_port_id=signal_port_id,
        sub_signals=[
            SubSignalOut(
                signal_port_id=r["SignalPort_ID"],
                tag=r["Tag"],
                is_active=bool(r["IsActive"]),
                description=r["Description"],
                parent_port_id=r["ParentPort_ID"],
                signal_port_type_id=r["SignalPortType_ID"],
                signal_port_type_name=r["signal_port_type_name"],
            )
            for r in rows
        ],
    )
