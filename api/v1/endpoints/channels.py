"""Channel listing, retrieval, and write endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import channel_repository, ingestion_repository
from ..schemas.common import PaginatedResponse
from ..schemas.channel import (
    ChannelOut,
    ChannelIn,
    ChannelDerivedIn,
    ChannelDerivedOut,
    EquipmentLookupOut,
    ParameterLookupOut,
    ProcessingDegreeLookupOut,
)
from ..repositories.equipment_repository import get_equipment_lookup
from ..repositories.metadata_repository import (
    get_parameters_lookup,
    get_processing_degrees_lookup,
)

router = APIRouter()


@router.post("/derived", response_model=ChannelDerivedOut, status_code=200)
def provision_derived_channel(
    body: ChannelDerivedIn,
    conn=Depends(get_db),
):
    """Find or create an output Channel for a processed data stream.

    Idempotent: calling with the same inputs always returns the same channel_id.
    Use this before batch-ingesting processed data so you can reuse the channel
    across many ingest calls without re-specifying all identity fields.
    """
    channel_id = ingestion_repository.find_or_create_derived_metadata(
        conn,
        source_channel_id=body.source_channel_id,
        processing_degree_id=body.processing_degree_id,
    )
    return ChannelDerivedOut(channel_id=channel_id)


@router.get("", response_model=PaginatedResponse[ChannelOut])
def list_channels(
    parameter_id: int | None = Query(None, description="Filter by parameter ID"),
    data_provenance_id: int | None = Query(
        None, description="Filter by data provenance ID"
    ),
    processing_degree_id: int | None = Query(
        None, description="Filter by processing degree ID (1=Raw, 2=Cleaned, etc.)"
    ),
    equipment_id: int | None = Query(None, description="Filter by equipment ID"),
    value_type_id: int | None = Query(None, description="Filter by value type (1=Scalar,2=Vector,3=Matrix,4=Image)"),
    campaign_id: int | None = Query(None, description="Filter to channels whose equipment is in this campaign"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    conn=Depends(get_db),
):
    """Return a paginated list of Channel rows with all foreign keys resolved."""
    items, total = channel_repository.list_channels(
        conn,
        parameter_id=parameter_id,
        data_provenance_id=data_provenance_id,
        processing_degree_id=processing_degree_id,
        equipment_id=equipment_id,
        value_type_id=value_type_id,
        campaign_id=campaign_id,
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


@router.post("", response_model=ChannelOut, status_code=201)
def create_channel(body: ChannelIn, conn=Depends(get_db)):
    """Create a new channel."""
    return channel_repository.insert_channel(conn, body.model_dump())


@router.put("/{channel_id}", response_model=ChannelOut)
def update_channel(channel_id: int, body: ChannelIn, conn=Depends(get_db)):
    """Update an existing channel."""
    updated = channel_repository.update_channel(conn, channel_id, body.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found.")
    return updated


@router.delete("/{channel_id}", status_code=204)
def delete_channel(channel_id: int, conn=Depends(get_db)):
    """Delete a channel by ID."""
    if not channel_repository.delete_channel(conn, channel_id):
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found.")


@router.get("/lookup/equipment", response_model=list[EquipmentLookupOut])
def list_equipment_lookup(conn=Depends(get_db)):
    """Return equipment for dropdowns."""
    return get_equipment_lookup(conn)


@router.get("/lookup/parameters", response_model=list[ParameterLookupOut])
def list_parameters_lookup(conn=Depends(get_db)):
    """Return parameters for dropdowns."""
    return get_parameters_lookup(conn)


@router.get(
    "/lookup/processing-degrees", response_model=list[ProcessingDegreeLookupOut]
)
def list_processing_degrees_lookup(conn=Depends(get_db)):
    """Return processing degrees for dropdowns."""
    return get_processing_degrees_lookup(conn)
