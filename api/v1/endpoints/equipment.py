"""Equipment endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import equipment_repository
from ..schemas.equipment import EquipmentLifecycleOut, EquipmentOut

router = APIRouter()


@router.get("", response_model=list[EquipmentOut])
def list_equipment(conn=Depends(get_db)):
    """Return all equipment."""
    return equipment_repository.list_equipment(conn)


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment(equipment_id: int, conn=Depends(get_db)):
    """Return a single equipment record by ID."""
    equip = equipment_repository.get_equipment_by_id(conn, equipment_id)
    if equip is None:
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found.")
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
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found.")

    installations = equipment_repository.get_equipment_installations(
        conn, equipment_id, from_dt, to_dt
    )
    events = equipment_repository.get_equipment_events(conn, equipment_id, from_dt, to_dt)

    return EquipmentLifecycleOut(
        equipment=equip,
        installations=installations,
        events=events,
    )
