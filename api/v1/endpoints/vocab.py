"""Vocabulary and entity CRUD endpoints.

Covers:
  GET  /vocab/equipment-event-types              — list all
  POST /vocab/equipment-event-types              — create
  PUT  /vocab/equipment-event-types/{id}         — update
  DELETE /vocab/equipment-event-types/{id}       — delete

  GET  /vocab/processing-degrees                 — list (read-only)

  GET  /vocab/purposes                           — list all
  POST /vocab/purposes                           — create
  PUT  /vocab/purposes/{id}                      — update
  DELETE /vocab/purposes/{id}                    — delete

  GET  /vocab/procedures                         — list all
  POST /vocab/procedures                         — create
  PUT  /vocab/procedures/{id}                    — update
  DELETE /vocab/procedures/{id}                  — delete

  GET  /vocab/projects                           — list all
  POST /vocab/projects                           — create
  PUT  /vocab/projects/{id}                      — update
  DELETE /vocab/projects/{id}                    — delete

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
    ProcessingDegreeOut,
    ProcedureIn,
    ProcedureOut,
    ProjectIn,
    ProjectOut,
    PurposeIn,
    PurposeOut,
    WatershedIn,
    WatershedOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# ProcessingDegree (read-only)
# ---------------------------------------------------------------------------


@router.get("/processing-degrees", response_model=list[ProcessingDegreeOut])
def list_processing_degrees(conn=Depends(get_db)):
    return lookup_repository.get_processing_degrees(conn)


# ---------------------------------------------------------------------------
# Purpose
# ---------------------------------------------------------------------------


@router.get("/purposes", response_model=list[PurposeOut])
def list_purposes(conn=Depends(get_db)):
    return lookup_repository.get_purposes(conn)


@router.post("/purposes", response_model=PurposeOut, status_code=201)
def create_purpose(body: PurposeIn, conn=Depends(get_db)):
    return lookup_repository.insert_purpose(conn, body.name, body.description)


@router.put("/purposes/{purpose_id}", response_model=PurposeOut)
def update_purpose(purpose_id: int, body: PurposeIn, conn=Depends(get_db)):
    updated = lookup_repository.update_purpose(conn, purpose_id, body.name, body.description)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Purpose {purpose_id} not found.")
    return updated


@router.delete("/purposes/{purpose_id}", status_code=204)
def delete_purpose(purpose_id: int, conn=Depends(get_db)):
    deleted = lookup_repository.delete_purpose(conn, purpose_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Purpose {purpose_id} not found.")


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
# Project
# ---------------------------------------------------------------------------


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(conn=Depends(get_db)):
    return lookup_repository.get_projects(conn)


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, conn=Depends(get_db)):
    return lookup_repository.insert_project(conn, body.name, body.description)


@router.put("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectIn, conn=Depends(get_db)):
    updated = lookup_repository.update_project(conn, project_id, body.name, body.description)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")
    return updated


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, conn=Depends(get_db)):
    deleted = lookup_repository.delete_project(conn, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found.")


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
