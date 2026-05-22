"""Channel listing, retrieval, and write endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import (
    channel_repository,
    ingestion_repository,
    lookup_repository,
    signal_interface_repository,
)
from ..schemas.common import PaginatedResponse
from ..schemas.channel import (
    ChannelOut,
    ChannelIn,
    ChannelDerivedIn,
    ChannelDerivedOut,
    ChannelPortHistoryIn,
    ChannelPortHistoryOut,
    ChannelProvisionIn,
    ChannelResolveIn,
    ChannelResolveOut,
    ChannelKindLookupOut,
    EquipmentLookupOut,
    ParameterLookupOut,
)
from ..repositories.equipment_repository import get_equipment_lookup
from ..repositories.metadata_repository import get_parameters_lookup

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
        produced_by_step_id=body.produced_by_step_id,
    )
    return ChannelDerivedOut(channel_id=channel_id)


@router.get("", response_model=PaginatedResponse[ChannelOut])
def list_channels(
    parameter_id: int | None = Query(None, description="Filter by parameter ID"),
    data_provenance_id: int | None = Query(
        None, description="Filter by data provenance ID"
    ),
    equipment_id: int | None = Query(
        None,
        description="Filter by equipment ID (resolved via active EquipmentWiringHistory)",
    ),
    signal_interface_id: int | None = Query(
        None, description="Filter by signal interface ID"
    ),
    value_kind_id: int | None = Query(
        None, description="Filter by value type (1=Scalar,2=Vector,3=Matrix,4=Image)"
    ),
    campaign_id: int | None = Query(
        None, description="Filter to channels whose equipment is in this campaign"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    conn=Depends(get_db),
):
    """Return a paginated list of Channel rows with all foreign keys resolved."""
    items, total = channel_repository.list_channels(
        conn,
        parameter_id=parameter_id,
        data_provenance_kind_id=data_provenance_id,
        equipment_id=equipment_id,
        signal_interface_id=signal_interface_id,
        value_kind_id=value_kind_id,
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


@router.post("/resolve", response_model=ChannelResolveOut, status_code=200)
def resolve_channel(body: ChannelResolveIn, conn=Depends(get_db)):
    """Resolve a channel by its natural keys (signal interface name + tag + optional parameter).

    If ``create_missing`` is True and no channel exists, a minimal channel row is
    created with default ChannelKind_ID=1 (Value) and ValueKind_ID=1 (Scalar).
    """
    signal_interface_id = signal_interface_repository.find_signal_interface_by_name(
        conn, body.signal_interface_name
    )
    if signal_interface_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"SignalInterface {body.signal_interface_name!r} not found.",
        )

    parameter_id = None
    if body.parameter_name is not None:
        parameter_id = signal_interface_repository.find_parameter_by_name(
            conn, body.parameter_name
        )
        if parameter_id is None:
            raise HTTPException(
                status_code=422,
                detail=f"Parameter {body.parameter_name!r} not found.",
            )

    channel = channel_repository.find_channel_by_signal_interface_tag(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=body.tag_name,
        parameter_id=parameter_id,
    )

    if channel is None:
        if not body.create_missing:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Channel not found for SignalInterface {body.signal_interface_name!r}, "
                    f"tag {body.tag_name!r}"
                    f"{(', parameter ' + body.parameter_name) if body.parameter_name else ''}."
                ),
            )
        channel = channel_repository.find_or_create_channel(
            conn,
            signal_interface_id=signal_interface_id,
            tag_name=body.tag_name,
            parameter_id=parameter_id,
        )

    if channel is None:
        raise HTTPException(status_code=500, detail="Failed to create channel.")

    return ChannelResolveOut(channel_id=channel["channel_id"])


@router.post("/provision", response_model=ChannelOut, status_code=201)
def provision_channel(body: ChannelProvisionIn, conn=Depends(get_db)):
    """Find or create a Channel by name-based fields (used by L5X loader).

    Resolves parameter_name → Parameter_ID and unit_name → Unit_ID server-side.
    Idempotent: returns the existing channel if one matches (signal_interface_id, tag_name).
    """
    parameter_id = None
    if body.parameter_name:
        parameter_id = signal_interface_repository.find_parameter_by_name(
            conn, body.parameter_name
        )
    unit_id = None
    if body.unit_name:
        unit_id = signal_interface_repository.find_unit_by_name(conn, body.unit_name)
    channel_kind_id = (
        signal_interface_repository.find_channel_role_by_name(conn, body.channel_role) or 1
    )
    existing = channel_repository.find_channel_by_signal_interface_tag(
        conn, signal_interface_id=body.signal_interface_id, tag_name=body.tag_name
    )
    if existing:
        return existing
    data = {
        "signal_interface_id": body.signal_interface_id,
        "tag_name": body.tag_name,
        "signal_interface_port_id": body.signal_interface_port_id,
        "parent_channel_id": body.parent_channel_id,
        "channel_kind_id": channel_kind_id,
        "parameter_id": parameter_id,
        "unit_id": unit_id,
        "data_provenance_kind_id": body.data_provenance_kind_id,
        "produced_by_step_id": body.produced_by_step_id,
        "value_kind_id": body.value_kind_id,
    }
    return channel_repository.insert_channel(conn, data)


@router.post("/{channel_id}/port-history", response_model=ChannelPortHistoryOut, status_code=201)
def open_channel_port_history(
    channel_id: int,
    body: ChannelPortHistoryIn,
    conn=Depends(get_db),
):
    """Open a ChannelPortHistory row linking a channel to a port for a time period."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[ChannelPortHistory]"
        "    ([Channel_ID], [SignalInterfacePort_ID], [ValidFrom], [GatingNote])"
        " OUTPUT INSERTED.[ChannelPortHistory_ID], INSERTED.[Channel_ID],"
        "   INSERTED.[SignalInterfacePort_ID],"
        "   CONVERT(VARCHAR(50), INSERTED.[ValidFrom], 127),"
        "   INSERTED.[GatingNote]"
        " VALUES (?, ?, ?, ?)",
        channel_id,
        body.signal_interface_port_id,
        body.valid_from,
        body.gating_note,
    )
    row = cursor.fetchone()
    conn.commit()
    return ChannelPortHistoryOut(
        channel_port_history_id=row[0],
        channel_id=row[1],
        signal_interface_port_id=row[2],
        valid_from=str(row[3]),
        gating_note=row[4],
    )


@router.get("/lookup/equipment", response_model=list[EquipmentLookupOut])
def list_equipment_lookup(conn=Depends(get_db)):
    """Return equipment for dropdowns."""
    return get_equipment_lookup(conn)


@router.get("/lookup/parameters", response_model=list[ParameterLookupOut])
def list_parameters_lookup(conn=Depends(get_db)):
    """Return parameters for dropdowns."""
    return get_parameters_lookup(conn)


@router.get("/lookup/channel-kinds", response_model=list[ChannelKindLookupOut])
def list_channel_roles(conn=Depends(get_db)):
    """Return channel roles for dropdowns."""
    return lookup_repository.get_channel_kinds(conn)
