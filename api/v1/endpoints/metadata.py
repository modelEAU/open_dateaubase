"""MetaData listing and retrieval endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import metadata_repository
from ..schemas.common import PaginatedResponse
from ..schemas.metadata import MetadataOut

router = APIRouter()


@router.get("", response_model=PaginatedResponse[MetadataOut])
def list_metadata(
    site_id: int | None = Query(None, description="Filter by site ID"),
    location_id: int | None = Query(None, description="Filter by sampling location ID"),
    parameter_id: int | None = Query(None, description="Filter by parameter ID"),
    campaign_id: int | None = Query(None, description="Filter by campaign ID"),
    data_provenance_id: int | None = Query(None, description="Filter by data provenance ID"),
    processing_degree: str | None = Query(None, description="Filter by processing degree (e.g. 'Raw', 'Cleaned')"),
    equipment_id: int | None = Query(None, description="Filter by equipment ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    conn=Depends(get_db),
):
    """Return a paginated list of MetaData rows with all foreign keys resolved."""
    items, total = metadata_repository.list_metadata(
        conn,
        site_id=site_id,
        location_id=location_id,
        parameter_id=parameter_id,
        campaign_id=campaign_id,
        data_provenance_id=data_provenance_id,
        processing_degree=processing_degree,
        equipment_id=equipment_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get("/{metadata_id}", response_model=MetadataOut)
def get_metadata(metadata_id: int, conn=Depends(get_db)):
    """Return a single MetaData row by ID."""
    meta = metadata_repository.get_metadata_by_id(conn, metadata_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"MetaData {metadata_id} not found.")
    return meta
