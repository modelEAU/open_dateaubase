"""Channel listing and retrieval endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import channel_repository
from ..schemas.common import PaginatedResponse
from ..schemas.channel import ChannelOut

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ChannelOut])
def list_channels(
    parameter_id: int | None = Query(None, description="Filter by parameter ID"),
    data_provenance_id: int | None = Query(None, description="Filter by data provenance ID"),
    processing_degree: str | None = Query(None, description="Filter by processing degree (e.g. 'Raw', 'Cleaned')"),
    equipment_id: int | None = Query(None, description="Filter by equipment ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    conn=Depends(get_db),
):
    """Return a paginated list of Channel rows with all foreign keys resolved."""
    items, total = channel_repository.list_channels(
        conn,
        parameter_id=parameter_id,
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


@router.get("/{channel_id}", response_model=ChannelOut)
def get_channel(channel_id: int, conn=Depends(get_db)):
    """Return a single Channel row by ID."""
    channel = channel_repository.get_channel_by_id(conn, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found.")
    return channel
