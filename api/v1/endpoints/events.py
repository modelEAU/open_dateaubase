"""Event and EventKind endpoints.

Routers registered in api/v1/router.py:
  - events_router        → prefix /events        (CRUD on Event)
  - event_kinds_router   → prefix /event-kinds   (CRUD on EventKind)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.database import get_db
from api.v1.errors import EntityNotFoundError
from ..repositories import event_repository, maintenance_drift_repository
from ..schemas.events import EventIn, EventKindIn, EventKindOut, EventOut, EventPatch
from ..schemas.maintenance_drift import MaintenanceDriftReadback


# ---------------------------------------------------------------------------
# EventKind resource: /event-kinds
# ---------------------------------------------------------------------------

event_kinds_router = APIRouter()


@event_kinds_router.get("", response_model=list[EventKindOut])
def list_event_kinds(conn=Depends(get_db)):
    """List all EventKind vocabulary entries."""
    return event_repository.get_event_kinds(conn)


@event_kinds_router.post("", response_model=EventKindOut, status_code=201)
def create_event_kind(body: EventKindIn, conn=Depends(get_db)):
    """Create a new EventKind."""
    row = event_repository.insert_event_kind(conn, body.name, body.description)
    return EventKindOut(**row)


@event_kinds_router.put("/{event_kind_id}", response_model=EventKindOut)
def update_event_kind(event_kind_id: int, body: EventKindIn, conn=Depends(get_db)):
    """Replace an EventKind name/description."""
    row = event_repository.update_event_kind(
        conn, event_kind_id, body.name, body.description
    )
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"EventKind {event_kind_id} not found."
        )
    return EventKindOut(**row)


@event_kinds_router.delete("/{event_kind_id}", status_code=204)
def delete_event_kind(event_kind_id: int, conn=Depends(get_db)):
    """Delete an EventKind by ID."""
    deleted = event_repository.delete_event_kind(conn, event_kind_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"EventKind {event_kind_id} not found."
        )
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Event resource: /events
# ---------------------------------------------------------------------------

events_router = APIRouter()


@events_router.get("", response_model=list[EventOut])
def list_events(
    channel_id: int | None = Query(None),
    equipment_id: int | None = Query(None),
    signal_interface_id: int | None = Query(None),
    data_acquisition_system_id: int | None = Query(None),
    sampling_point_id: int | None = Query(None),
    process_unit_id: int | None = Query(None),
    site_id: int | None = Query(None),
    campaign_id: int | None = Query(None),
    conn=Depends(get_db),
):
    """List events, optionally filtered by any of the 8 arc-target FK columns."""
    return event_repository.get_events(
        conn,
        channel_id=channel_id,
        equipment_id=equipment_id,
        signal_interface_id=signal_interface_id,
        data_acquisition_system_id=data_acquisition_system_id,
        sampling_point_id=sampling_point_id,
        process_unit_id=process_unit_id,
        site_id=site_id,
        campaign_id=campaign_id,
    )


@events_router.post("", response_model=EventOut, status_code=201)
def create_event(body: EventIn, conn=Depends(get_db)):
    """Create a new Event (exactly one arc-target FK must be provided)."""
    row = event_repository.insert_event(conn, body.model_dump())
    return EventOut(**row)


@events_router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, conn=Depends(get_db)):
    """Retrieve a single Event by ID."""
    row = event_repository.get_event_by_id(conn, event_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")
    return EventOut(**row)


@events_router.get(
    "/{event_id}/maintenance-drift",
    response_model=MaintenanceDriftReadback,
    summary="Drift since last cleaning for a maintenance Event",
    description=(
        "Read-back (PRD-4 S4): the before/after readings derived from the "
        "source stream around this Event's window, via its linked "
        "maintenance-drift Channel. 404 if the Event has no drift Channel."
    ),
)
def get_event_maintenance_drift(event_id: int, conn=Depends(get_db)):
    """Return the drift read-back for a maintenance Event (before/after + %diff)."""
    try:
        result = maintenance_drift_repository.get_drift_readback(conn, event_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MaintenanceDriftReadback(**result)


@events_router.put("/{event_id}", response_model=EventOut)
def update_event(event_id: int, body: EventPatch, conn=Depends(get_db)):
    """Partial-update an Event (fields omitted or None are left unchanged)."""
    row = event_repository.update_event(conn, event_id, body.model_dump(exclude_none=True))
    if row is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")
    return EventOut(**row)


@events_router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, conn=Depends(get_db)):
    """Hard-delete an Event by ID."""
    deleted = event_repository.delete_event(conn, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")
    return Response(status_code=204)
