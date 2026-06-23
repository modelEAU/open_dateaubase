"""Processing lineage endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from fastapi import HTTPException

from api.database import get_db
from ..repositories import channel_repository
from ..schemas.lineage import (
    LineageTreeOut,
    ProcessingStepCreate,
    ProcessingStepOut,
    ProvenanceGraphOut,
    StreamStoryOut,
)
from ..services import lineage_service

router = APIRouter()


@router.post("/steps", response_model=ProcessingStepOut, status_code=201)
def record_processing_step(
    body: ProcessingStepCreate,
    conn=Depends(get_db),
):
    """Record a processing step and its data lineage without ingesting any values.

    Creates the ProcessingStep and input ProcessingLineage edges, then sets
    ProducedByStep_ID on the output channel (body.output_channel_id).

    Use this when:
    - You processed data in batches and want to record lineage once at the end.
    - A QC algorithm ran but produced no output values.
    - You need to retry lineage recording independently of data ingestion.
    """
    step_id = lineage_service.persist_processing(
        conn,
        source_metadata_ids=body.source_channel_ids,
        method_name=body.method_name,
        method_version=body.method_version,
        operation_kind_id=body.operation_kind_id,
        method_parameters=body.method_parameters,
        executed_at=body.executed_at,
        executed_by_person_id=body.executed_by_person_id,
    )
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Channel] SET [ProducedByStep_ID] = ? WHERE [Stream_ID] = ?",
        step_id,
        body.output_channel_id,
    )
    conn.commit()
    return ProcessingStepOut(processing_step_id=step_id)


@router.get("/{channel_id}/forward")
def get_forward_lineage(channel_id: int, conn=Depends(get_db)):
    """What was this data processed into? Follow outputs forward."""
    return lineage_service.forward_lineage(conn, channel_id)


@router.get("/{channel_id}/backward")
def get_backward_lineage(channel_id: int, conn=Depends(get_db)):
    """Where did this data come from? Trace inputs backward."""
    return lineage_service.backward_lineage(conn, channel_id)


@router.get("/{channel_id}/tree", response_model=LineageTreeOut)
def get_lineage_tree(channel_id: int, conn=Depends(get_db)):
    """Return the complete processing DAG rooted at this Channel."""
    return lineage_service.full_lineage_tree(conn, channel_id)


@router.get("/streams/{stream_id}/provenance", response_model=ProvenanceGraphOut)
def get_stream_provenance(stream_id: int, conn=Depends(get_db)):
    """Return a fully-resolved provenance graph rooted at this Stream.

    Composes the lineage DAG with per-node label resolution (parameter, unit,
    equipment / sampling point, provenance kind, accumulated traits) and per-step
    detail (operation kind, method, parameters, who/when, inputs/outputs) so the
    Data Explorer's Provenance panel needs only one round trip.
    """
    return lineage_service.resolved_provenance(conn, stream_id)


@router.get("/streams/{stream_id}/story", response_model=StreamStoryOut)
def get_stream_story(stream_id: int, conn=Depends(get_db)):
    """Read-only Stream Story summary: what the stream records, its data span,
    where it has been, and its annotations. Powers the Explore stream-story panel."""
    story = channel_repository.get_stream_story(conn, stream_id)
    if story is None:
        raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found.")
    return story


