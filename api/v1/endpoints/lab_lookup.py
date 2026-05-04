"""Lab lookup table CRUD endpoints: SampleKind and SampleCollectionKind."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import lookup_repository
from ..schemas.metadata import (
    SampleCollectionKindIn,
    SampleCollectionKindOut,
    SampleKindIn,
    SampleKindOut,
)

sample_kinds_router = APIRouter()
sample_collection_kinds_router = APIRouter()


# ---------------------------------------------------------------------------
# SampleKind
# ---------------------------------------------------------------------------


@sample_kinds_router.get("", response_model=list[SampleKindOut])
def list_sample_kinds(conn=Depends(get_db)):
    """Return all sample types."""
    return lookup_repository.get_sample_kinds(conn)


@sample_kinds_router.post("", response_model=SampleKindOut, status_code=201)
def create_sample_kind(body: SampleKindIn, conn=Depends(get_db)):
    """Create a new SampleKind."""
    return lookup_repository.insert_sample_kind(conn, body.name, body.description)


@sample_kinds_router.put("/{sample_kind_id}", response_model=SampleKindOut)
def update_sample_kind(sample_kind_id: int, body: SampleKindIn, conn=Depends(get_db)):
    """Update an existing SampleKind."""
    updated = lookup_repository.update_sample_kind(
        conn, sample_kind_id, body.name, body.description
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"SampleKind {sample_kind_id} not found."
        )
    return updated


@sample_kinds_router.delete("/{sample_kind_id}", status_code=204)
def delete_sample_kind(sample_kind_id: int, conn=Depends(get_db)):
    """Delete a SampleKind by ID."""
    deleted = lookup_repository.delete_sample_kind(conn, sample_kind_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"SampleKind {sample_kind_id} not found."
        )


# ---------------------------------------------------------------------------
# SampleCollectionKind
# ---------------------------------------------------------------------------


@sample_collection_kinds_router.get("", response_model=list[SampleCollectionKindOut])
def list_sample_collection_kinds(conn=Depends(get_db)):
    """Return all sample collection kinds."""
    return lookup_repository.get_sample_collection_kinds(conn)


@sample_collection_kinds_router.post("", response_model=SampleCollectionKindOut, status_code=201)
def create_sample_collection_kind(body: SampleCollectionKindIn, conn=Depends(get_db)):
    """Create a new SampleCollectionKind."""
    return lookup_repository.insert_sample_collection_kind(conn, body.name, body.description)


@sample_collection_kinds_router.put("/{sample_collection_kind_id}", response_model=SampleCollectionKindOut)
def update_sample_collection_kind(sample_collection_kind_id: int, body: SampleCollectionKindIn, conn=Depends(get_db)):
    """Update an existing SampleCollectionKind."""
    updated = lookup_repository.update_sample_collection_kind(
        conn, sample_collection_kind_id, body.name, body.description
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"SampleCollectionKind {sample_collection_kind_id} not found."
        )
    return updated


@sample_collection_kinds_router.delete("/{sample_collection_kind_id}", status_code=204)
def delete_sample_collection_kind(sample_collection_kind_id: int, conn=Depends(get_db)):
    """Delete a SampleCollectionKind by ID."""
    deleted = lookup_repository.delete_sample_collection_kind(conn, sample_collection_kind_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"SampleCollectionKind {sample_collection_kind_id} not found."
        )
