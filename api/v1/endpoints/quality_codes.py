"""QualityCode CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import lookup_repository
from ..schemas.metadata import QualityCodeIn, QualityCodeOut

router = APIRouter()


@router.get("", response_model=list[QualityCodeOut])
def list_quality_codes(conn=Depends(get_db)):
    """Return all quality codes."""
    return lookup_repository.get_quality_codes(conn)


@router.post("", response_model=QualityCodeOut, status_code=201)
def create_quality_code(body: QualityCodeIn, conn=Depends(get_db)):
    """Create a new QualityCode."""
    return lookup_repository.insert_quality_code(
        conn, body.name, body.description, body.is_usable
    )


@router.put("/{qc_id}", response_model=QualityCodeOut)
def update_quality_code(qc_id: int, body: QualityCodeIn, conn=Depends(get_db)):
    """Update an existing QualityCode."""
    updated = lookup_repository.update_quality_code(
        conn, qc_id, body.name, body.description, body.is_usable
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"QualityCode {qc_id} not found.")
    return updated


@router.delete("/{qc_id}", status_code=204)
def delete_quality_code(qc_id: int, conn=Depends(get_db)):
    """Delete a QualityCode by ID."""
    deleted = lookup_repository.delete_quality_code(conn, qc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"QualityCode {qc_id} not found.")
