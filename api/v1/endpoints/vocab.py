"""Vocabulary and entity CRUD endpoints.

Covers:
  GET  /vocab/processing-kinds                 — list (read-only)

  GET  /vocab/procedures                         — list all
  POST /vocab/procedures                         — create
  PUT  /vocab/procedures/{id}                    — update
  DELETE /vocab/procedures/{id}                  — delete

  GET  /vocab/watersheds                         — list all
  POST /vocab/watersheds                         — create
  PUT  /vocab/watersheds/{id}                    — update
  DELETE /vocab/watersheds/{id}                  — delete
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import lookup_repository
from ..schemas.metadata import (
    ProcessingKindOut,
    ProcedureIn,
    ProcedureOut,
    WatershedIn,
    WatershedOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# ProcessingKind (read-only)
# ---------------------------------------------------------------------------


@router.get("/processing-kinds", response_model=list[ProcessingKindOut])
def list_processing_kinds(conn=Depends(get_db)):
    return lookup_repository.get_processing_kinds(conn)


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
        body.procedure_type,
        body.description,
        body.procedure_location,
    )


@router.put("/procedures/{procedure_id}", response_model=ProcedureOut)
def update_procedure(procedure_id: int, body: ProcedureIn, conn=Depends(get_db)):
    updated = lookup_repository.update_procedure(
        conn,
        procedure_id,
        body.procedure_name,
        body.procedure_type,
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
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Watershed {watershed_id} not found.")
    return updated


@router.delete("/watersheds/{watershed_id}", status_code=204)
def delete_watershed(watershed_id: int, conn=Depends(get_db)):
    deleted = lookup_repository.delete_watershed(conn, watershed_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Watershed {watershed_id} not found.")
