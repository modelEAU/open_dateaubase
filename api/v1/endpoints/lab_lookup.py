"""Lab lookup table CRUD endpoints: SampleType and SampleMethod."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import lookup_repository
from ..schemas.metadata import (
    SampleMethodIn,
    SampleMethodOut,
    SampleTypeIn,
    SampleTypeOut,
)

sample_types_router = APIRouter()
sample_methods_router = APIRouter()


# ---------------------------------------------------------------------------
# SampleType
# ---------------------------------------------------------------------------


@sample_types_router.get("", response_model=list[SampleTypeOut])
def list_sample_types(conn=Depends(get_db)):
    """Return all sample types."""
    return lookup_repository.get_sample_types(conn)


@sample_types_router.post("", response_model=SampleTypeOut, status_code=201)
def create_sample_type(body: SampleTypeIn, conn=Depends(get_db)):
    """Create a new SampleType."""
    return lookup_repository.insert_sample_type(conn, body.name, body.description)


@sample_types_router.put("/{sample_type_id}", response_model=SampleTypeOut)
def update_sample_type(sample_type_id: int, body: SampleTypeIn, conn=Depends(get_db)):
    """Update an existing SampleType."""
    updated = lookup_repository.update_sample_type(
        conn, sample_type_id, body.name, body.description
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"SampleType {sample_type_id} not found."
        )
    return updated


@sample_types_router.delete("/{sample_type_id}", status_code=204)
def delete_sample_type(sample_type_id: int, conn=Depends(get_db)):
    """Delete a SampleType by ID."""
    deleted = lookup_repository.delete_sample_type(conn, sample_type_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"SampleType {sample_type_id} not found."
        )


# ---------------------------------------------------------------------------
# SampleMethod
# ---------------------------------------------------------------------------


@sample_methods_router.get("", response_model=list[SampleMethodOut])
def list_sample_methods(conn=Depends(get_db)):
    """Return all sample methods."""
    return lookup_repository.get_sample_methods(conn)


@sample_methods_router.post("", response_model=SampleMethodOut, status_code=201)
def create_sample_method(body: SampleMethodIn, conn=Depends(get_db)):
    """Create a new SampleMethod."""
    return lookup_repository.insert_sample_method(conn, body.name, body.description)


@sample_methods_router.put("/{sample_method_id}", response_model=SampleMethodOut)
def update_sample_method(sample_method_id: int, body: SampleMethodIn, conn=Depends(get_db)):
    """Update an existing SampleMethod."""
    updated = lookup_repository.update_sample_method(
        conn, sample_method_id, body.name, body.description
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"SampleMethod {sample_method_id} not found."
        )
    return updated


@sample_methods_router.delete("/{sample_method_id}", status_code=204)
def delete_sample_method(sample_method_id: int, conn=Depends(get_db)):
    """Delete a SampleMethod by ID."""
    deleted = lookup_repository.delete_sample_method(conn, sample_method_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"SampleMethod {sample_method_id} not found."
        )
