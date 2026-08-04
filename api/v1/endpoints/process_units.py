"""ProcessUnit and ProcessUnitKind endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import process_unit_repository
from ..schemas.process_unit import (
    ProcessUnitIn,
    ProcessUnitLookupOut,
    ProcessUnitOut,
    ProcessUnitPatch,
    ProcessUnitTreeOut,
    ProcessUnitKindIn,
    ProcessUnitKindOut,
    TreatmentStageOut,
)

process_unit_kinds_router = APIRouter()
process_units_router = APIRouter()
treatment_stages_router = APIRouter()


@treatment_stages_router.get("", response_model=list[TreatmentStageOut])
def list_treatment_stages(conn=Depends(get_db)):
    return process_unit_repository.get_all_treatment_stages(conn)


# ---------------------------------------------------------------------------
# ProcessUnitKind
# ---------------------------------------------------------------------------


@process_unit_kinds_router.get("", response_model=list[ProcessUnitKindOut])
def list_process_unit_types(conn=Depends(get_db)):
    return process_unit_repository.get_all_process_unit_types(conn)


@process_unit_kinds_router.post("", response_model=ProcessUnitKindOut, status_code=201)
def create_process_unit_type(body: ProcessUnitKindIn, conn=Depends(get_db)):
    return process_unit_repository.insert_process_unit_type(
        conn, body.name, body.description, body.category
    )


@process_unit_kinds_router.put("/{process_unit_kind_id}", response_model=ProcessUnitKindOut)
def update_process_unit_type(
    process_unit_kind_id: int, body: ProcessUnitKindIn, conn=Depends(get_db)
):
    updated = process_unit_repository.update_process_unit_type(
        conn, process_unit_kind_id, body.name, body.description, body.category
    )
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail=f"ProcessUnitKind {process_unit_kind_id} not found.",
        )
    return updated


@process_unit_kinds_router.delete("/{process_unit_kind_id}", status_code=204)
def delete_process_unit_type(process_unit_kind_id: int, conn=Depends(get_db)):
    deleted = process_unit_repository.delete_process_unit_type(conn, process_unit_kind_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"ProcessUnitKind {process_unit_kind_id} not found.",
        )


# ---------------------------------------------------------------------------
# ProcessUnit
# ---------------------------------------------------------------------------


@process_units_router.get("/lookup", response_model=list[ProcessUnitLookupOut])
def list_process_units_lookup(
    site_id: int | None = Query(None),
    conn=Depends(get_db),
):
    return process_unit_repository.get_process_units_lookup(conn, site_id=site_id)


@process_units_router.get("", response_model=list[ProcessUnitOut] | list[ProcessUnitTreeOut])
def list_process_units(
    site_id: int | None = Query(None),
    tree: bool = Query(False),
    conn=Depends(get_db),
):
    if tree and site_id is not None:
        return process_unit_repository.get_process_unit_tree(conn, site_id)
    return process_unit_repository.get_all_process_units(conn, site_id=site_id)


@process_units_router.get("/{process_unit_id}", response_model=ProcessUnitOut)
def get_process_unit(process_unit_id: int, conn=Depends(get_db)):
    unit = process_unit_repository.get_process_unit_by_id(conn, process_unit_id)
    if unit is None:
        raise HTTPException(
            status_code=404, detail=f"ProcessUnit {process_unit_id} not found."
        )
    return unit


@process_units_router.post("", response_model=ProcessUnitOut, status_code=201)
def create_process_unit(body: ProcessUnitIn, conn=Depends(get_db)):
    return process_unit_repository.insert_process_unit(conn, body.model_dump())


@process_units_router.put("/{process_unit_id}", response_model=ProcessUnitOut)
def update_process_unit(process_unit_id: int, body: ProcessUnitIn, conn=Depends(get_db)):
    updated = process_unit_repository.update_process_unit(
        conn, process_unit_id, body.model_dump()
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"ProcessUnit {process_unit_id} not found."
        )
    return updated


@process_units_router.patch("/{process_unit_id}", response_model=ProcessUnitOut)
def patch_process_unit(process_unit_id: int, body: ProcessUnitPatch, conn=Depends(get_db)):
    updated = process_unit_repository.patch_process_unit(
        conn, process_unit_id, body.model_dump(exclude_unset=True)
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"ProcessUnit {process_unit_id} not found."
        )
    return updated


@process_units_router.delete("/{process_unit_id}", status_code=204)
def delete_process_unit(process_unit_id: int, conn=Depends(get_db)):
    try:
        deleted = process_unit_repository.delete_process_unit(conn, process_unit_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"ProcessUnit {process_unit_id} not found."
        )
