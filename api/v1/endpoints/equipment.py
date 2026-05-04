"""Equipment endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import equipment_repository
from ..schemas.equipment import (
    EquipmentIn,
    EquipmentLifecycleActionRequest,
    EquipmentLifecycleActionResponse,
    EquipmentLifecycleOut,
    EquipmentModelIn,
    EquipmentModelOut,
    EquipmentModelParameterIn,
    EquipmentModelParameterOut,
    EquipmentModelProcedureIn,
    EquipmentModelProcedureOut,
    EquipmentOut,
    EquipmentPatch,
    EquipmentModelLookupOut,
    EquipmentEventKindOut,
    EquipmentEventCreate,
    EquipmentEventOut,
)
from ..schemas.metadata import EquipmentEventKindIn

router = APIRouter()


@router.get("", response_model=list[EquipmentOut])
def list_equipment(conn=Depends(get_db)):
    """Return all equipment."""
    return equipment_repository.list_equipment(conn)


@router.post("", response_model=EquipmentOut, status_code=201)
def create_equipment(body: EquipmentIn, conn=Depends(get_db)):
    return equipment_repository.insert_equipment(conn, body.model_dump())


@router.put("/{equipment_id}", response_model=EquipmentOut)
def update_equipment(equipment_id: int, body: EquipmentIn, conn=Depends(get_db)):
    updated = equipment_repository.update_equipment(
        conn, equipment_id, body.model_dump()
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"Equipment {equipment_id} not found."
        )
    return updated


@router.delete("/{equipment_id}", status_code=204)
def delete_equipment(equipment_id: int, conn=Depends(get_db)):
    if not equipment_repository.delete_equipment(conn, equipment_id):
        raise HTTPException(
            status_code=404, detail=f"Equipment {equipment_id} not found."
        )


@router.patch("/{equipment_id}", response_model=EquipmentOut)
def patch_equipment(equipment_id: int, body: EquipmentPatch, conn=Depends(get_db)):
    """Partial update of equipment."""
    updated = equipment_repository.patch_equipment(
        conn, equipment_id, body.model_dump(exclude_unset=True)
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"Equipment {equipment_id} not found."
        )
    return updated


@router.get("/models", response_model=list[EquipmentModelOut])
def list_equipment_models(conn=Depends(get_db)):
    """Return all equipment models."""
    return equipment_repository.list_equipment_models(conn)


@router.post("/models", response_model=EquipmentModelOut, status_code=201)
def create_equipment_model(body: EquipmentModelIn, conn=Depends(get_db)):
    return equipment_repository.insert_equipment_model(conn, body.model_dump())


@router.get("/models/lookup", response_model=list[EquipmentModelLookupOut])
def list_equipment_models_lookup(conn=Depends(get_db)):
    """Return equipment models for dropdowns."""
    return equipment_repository.get_models_lookup(conn)


@router.get("/models/{model_id}", response_model=EquipmentModelOut)
def get_equipment_model(model_id: int, conn=Depends(get_db)):
    model = equipment_repository.get_equipment_model_by_id(conn, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"EquipmentModel {model_id} not found.")
    return model


@router.put("/models/{model_id}", response_model=EquipmentModelOut)
def update_equipment_model(model_id: int, body: EquipmentModelIn, conn=Depends(get_db)):
    updated = equipment_repository.update_equipment_model(conn, model_id, body.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail=f"EquipmentModel {model_id} not found.")
    return updated


@router.delete("/models/{model_id}", status_code=204)
def delete_equipment_model(model_id: int, conn=Depends(get_db)):
    if not equipment_repository.delete_equipment_model(conn, model_id):
        raise HTTPException(status_code=404, detail=f"EquipmentModel {model_id} not found.")


@router.get("/models/{model_id}/parameters", response_model=list[EquipmentModelParameterOut])
def list_model_parameters(model_id: int, conn=Depends(get_db)):
    return equipment_repository.list_model_parameters(conn, model_id)


@router.post("/models/{model_id}/parameters", response_model=EquipmentModelParameterOut, status_code=201)
def add_model_parameter(model_id: int, body: EquipmentModelParameterIn, conn=Depends(get_db)):
    try:
        return equipment_repository.add_model_parameter(conn, model_id, body.parameter_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/models/{model_id}/parameters/{parameter_id}", status_code=204)
def remove_model_parameter(model_id: int, parameter_id: int, conn=Depends(get_db)):
    if not equipment_repository.remove_model_parameter(conn, model_id, parameter_id):
        raise HTTPException(status_code=404, detail="Association not found.")


@router.get("/models/{model_id}/procedures", response_model=list[EquipmentModelProcedureOut])
def list_model_procedures(model_id: int, conn=Depends(get_db)):
    return equipment_repository.list_model_procedures(conn, model_id)


@router.post("/models/{model_id}/procedures", response_model=EquipmentModelProcedureOut, status_code=201)
def add_model_procedure(model_id: int, body: EquipmentModelProcedureIn, conn=Depends(get_db)):
    try:
        return equipment_repository.add_model_procedure(conn, model_id, body.procedure_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/models/{model_id}/procedures/{procedure_id}", status_code=204)
def remove_model_procedure(model_id: int, procedure_id: int, conn=Depends(get_db)):
    if not equipment_repository.remove_model_procedure(conn, model_id, procedure_id):
        raise HTTPException(status_code=404, detail="Association not found.")


@router.get("/lookup", response_model=list[dict])
def list_equipment_lookup(conn=Depends(get_db)):
    """Return all equipment for dropdowns (id + identifier)."""
    return equipment_repository.get_equipment_lookup(conn)


@router.get("/event-types", response_model=list[EquipmentEventKindOut])
def list_equipment_event_kinds(conn=Depends(get_db)):
    """Return all EquipmentEventKind values for dropdowns."""
    return equipment_repository.get_equipment_event_kinds(conn)


@router.post("/event-types", response_model=EquipmentEventKindOut, status_code=201)
def create_equipment_event_kind(body: EquipmentEventKindIn, conn=Depends(get_db)):
    return equipment_repository.insert_equipment_event_kind(conn, body.name)


@router.put("/event-types/{event_type_id}", response_model=EquipmentEventKindOut)
def update_equipment_event_kind(event_type_id: int, body: EquipmentEventKindIn, conn=Depends(get_db)):
    updated = equipment_repository.update_equipment_event_kind(conn, event_type_id, body.name)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"EquipmentEventKind {event_type_id} not found.")
    return updated


@router.delete("/event-types/{event_type_id}", status_code=204)
def delete_equipment_event_kind(event_type_id: int, conn=Depends(get_db)):
    deleted = equipment_repository.delete_equipment_event_kind(conn, event_type_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"EquipmentEventKind {event_type_id} not found.")


@router.post("/events", response_model=EquipmentEventOut, status_code=201)
def create_equipment_event(body: EquipmentEventCreate, conn=Depends(get_db)):
    """Create a new EquipmentEvent."""
    return equipment_repository.insert_equipment_event(conn, body.model_dump())


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment(equipment_id: int, conn=Depends(get_db)):
    """Return a single equipment record by ID."""
    equip = equipment_repository.get_equipment_by_id(conn, equipment_id)
    if equip is None:
        raise HTTPException(
            status_code=404, detail=f"Equipment {equipment_id} not found."
        )
    return equip


@router.get("/{equipment_id}/lifecycle", response_model=EquipmentLifecycleOut)
def get_lifecycle(
    equipment_id: int,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Return the full lifecycle: installation history and all events."""
    equip = equipment_repository.get_equipment_by_id(conn, equipment_id)
    if equip is None:
        raise HTTPException(
            status_code=404, detail=f"Equipment {equipment_id} not found."
        )

    installations = equipment_repository.get_equipment_installations(
        conn, equipment_id, from_dt, to_dt
    )
    events = equipment_repository.get_equipment_events(
        conn, equipment_id, from_dt, to_dt
    )

    return EquipmentLifecycleOut(
        equipment=equip,
        installations=installations,
        events=events,
    )


@router.post(
    "/{equipment_id}/commission",
    response_model=EquipmentLifecycleActionResponse,
    status_code=201,
)
def commission_equipment(
    equipment_id: int,
    body: EquipmentLifecycleActionRequest,
    conn=Depends(get_db),
):
    """Mark equipment as active (IsActive=1) and record a Commissioning event.

    SignalPort and Channel rows are unaffected.
    """
    try:
        return equipment_repository.commission_equipment(
            conn,
            equipment_id,
            notes=body.notes,
            performed_by_person_id=body.performed_by_person_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{equipment_id}/decommission",
    response_model=EquipmentLifecycleActionResponse,
    status_code=201,
)
def decommission_equipment(
    equipment_id: int,
    body: EquipmentLifecycleActionRequest,
    conn=Depends(get_db),
):
    """Mark equipment as inactive (IsActive=0) and record a Decommissioning event.

    SignalPort and Channel rows are unaffected.
    """
    try:
        return equipment_repository.decommission_equipment(
            conn,
            equipment_id,
            notes=body.notes,
            performed_by_person_id=body.performed_by_person_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
