"""Vocabulary and entity CRUD endpoints.

Covers:
  GET  /vocab/operation-kinds                   — list (read-only)

  GET  /vocab/procedure-kinds                  — list all
  POST /vocab/procedure-kinds                  — create
  PUT  /vocab/procedure-kinds/{id}             — update
  DELETE /vocab/procedure-kinds/{id}           — delete

  GET  /vocab/procedures                         — list all
  POST /vocab/procedures                         — create
  PUT  /vocab/procedures/{id}                    — update
  DELETE /vocab/procedures/{id}                  — delete

  GET  /vocab/watersheds                         — list all
  POST /vocab/watersheds                         — create
  PUT  /vocab/watersheds/{id}                    — update
  DELETE /vocab/watersheds/{id}                  — delete

  GET  /vocab/watersheds/{id}/land-use           — get land use
  PUT  /vocab/watersheds/{id}/land-use           — upsert land use
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import lookup_repository
from ..schemas.metadata import (
    ControllerKindOut,
    DasKindOut,
    LandUseIn,
    LandUseOut,
    OperationKindOut,
    ProcedureKindIn,
    ProcedureKindOut,
    ProcedureIn,
    ProcedureOut,
    WatershedIn,
    WatershedOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# OperationKind (read-only, ADR 0005 — replaces ProcessingKind)
# ---------------------------------------------------------------------------


@router.get("/operation-kinds", response_model=list[OperationKindOut])
def list_operation_kinds(conn=Depends(get_db)):
    return lookup_repository.get_operation_kinds(conn)


@router.get("/das-kinds", response_model=list[DasKindOut])
def list_das_kinds(conn=Depends(get_db)):
    return lookup_repository.get_das_kinds(conn)


@router.get("/controller-kinds", response_model=list[ControllerKindOut])
def list_controller_kinds(conn=Depends(get_db)):
    return lookup_repository.get_controller_kinds(conn)


# ---------------------------------------------------------------------------
# ProcedureKind
# ---------------------------------------------------------------------------


@router.get("/procedure-kinds", response_model=list[ProcedureKindOut])
def list_procedure_kinds(conn=Depends(get_db)):
    return lookup_repository.get_procedure_kinds(conn)


@router.post("/procedure-kinds", response_model=ProcedureKindOut, status_code=201)
def create_procedure_kind(body: ProcedureKindIn, conn=Depends(get_db)):
    return lookup_repository.insert_procedure_kind(conn, body.name, body.description)


@router.put("/procedure-kinds/{procedure_kind_id}", response_model=ProcedureKindOut)
def update_procedure_kind(procedure_kind_id: int, body: ProcedureKindIn, conn=Depends(get_db)):
    updated = lookup_repository.update_procedure_kind(conn, procedure_kind_id, body.name, body.description)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"ProcedureKind {procedure_kind_id} not found.")
    return updated


@router.delete("/procedure-kinds/{procedure_kind_id}", status_code=204)
def delete_procedure_kind(procedure_kind_id: int, conn=Depends(get_db)):
    deleted = lookup_repository.delete_procedure_kind(conn, procedure_kind_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"ProcedureKind {procedure_kind_id} not found.")


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------


@router.get("/procedures", response_model=list[ProcedureOut])
def list_procedures(conn=Depends(get_db)):
    return lookup_repository.get_procedures(conn)


@router.post("/procedures", response_model=ProcedureOut, status_code=201)
def create_procedure(body: ProcedureIn, conn=Depends(get_db)):
    return lookup_repository.insert_procedure(
        conn,
        body.procedure_name,
        body.procedure_kind_id,
        body.description,
        body.procedure_location,
    )


@router.put("/procedures/{procedure_id}", response_model=ProcedureOut)
def update_procedure(procedure_id: int, body: ProcedureIn, conn=Depends(get_db)):
    updated = lookup_repository.update_procedure(
        conn,
        procedure_id,
        body.procedure_name,
        body.procedure_kind_id,
        body.description,
        body.procedure_location,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Procedure {procedure_id} not found.")
    return updated


@router.delete("/procedures/{procedure_id}", status_code=204)
def delete_procedure(procedure_id: int, conn=Depends(get_db)):
    deleted = lookup_repository.delete_procedure(conn, procedure_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Procedure {procedure_id} not found.")


# ---------------------------------------------------------------------------
# Watershed
# ---------------------------------------------------------------------------


@router.get("/watersheds", response_model=list[WatershedOut])
def list_watersheds(conn=Depends(get_db)):
    return lookup_repository.get_watersheds(conn)


@router.post("/watersheds", response_model=WatershedOut, status_code=201)
def create_watershed(body: WatershedIn, conn=Depends(get_db)):
    return lookup_repository.insert_watershed(
        conn,
        body.name,
        body.description,
        body.surface_area,
        body.concentration_time,
        body.impervious_surface,
        body.parent_watershed_id,
        body.geometry_geojson,
    )


@router.put("/watersheds/{watershed_id}", response_model=WatershedOut)
def update_watershed(watershed_id: int, body: WatershedIn, conn=Depends(get_db)):
    updated = lookup_repository.update_watershed(
        conn,
        watershed_id,
        body.name,
        body.description,
        body.surface_area,
        body.concentration_time,
        body.impervious_surface,
        body.parent_watershed_id,
        body.geometry_geojson,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Watershed {watershed_id} not found.")
    return updated


@router.delete("/watersheds/{watershed_id}", status_code=204)
def delete_watershed(watershed_id: int, conn=Depends(get_db)):
    deleted = lookup_repository.delete_watershed(conn, watershed_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Watershed {watershed_id} not found.")


@router.get("/watersheds/{watershed_id}/land-use", response_model=LandUseOut)
def get_land_use(watershed_id: int, conn=Depends(get_db)):
    result = lookup_repository.get_land_use(conn, watershed_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No land use data for watershed {watershed_id}.")
    return result


@router.put("/watersheds/{watershed_id}/land-use", response_model=LandUseOut)
def upsert_land_use(watershed_id: int, body: LandUseIn, conn=Depends(get_db)):
    return lookup_repository.upsert_land_use(
        conn,
        watershed_id,
        body.commercial,
        body.green_spaces,
        body.industrial,
        body.institutional,
        body.residential,
        body.agricultural,
        body.recreational,
    )
