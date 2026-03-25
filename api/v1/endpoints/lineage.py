"""Processing lineage endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from api.database import get_db
from ..schemas.lineage import (
    LineageTreeOut,
    ProcessingDegreeSummaryOut,
    ProcessingStepCreate,
    ProcessingStepOut,
)
from ..services import lineage_service

router = APIRouter()


@router.post("/steps", response_model=ProcessingStepOut, status_code=201)
def record_processing_step(
    body: ProcessingStepCreate,
    conn=Depends(get_db),
):
    """Record a processing step and its data lineage without ingesting any values.

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
        processing_type=body.processing_type,
        parameters=body.parameters,
        executed_at=body.executed_at,
        executed_by_person_id=body.executed_by_person_id,
        output_metadata_id=body.output_channel_id,
    )
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


@router.get("/by-equipment/degrees", response_model=list[ProcessingDegreeSummaryOut])
def get_processing_degrees(
    equipment_id: int = Query(..., description="Equipment ID"),
    parameter_id: int = Query(..., description="Parameter ID"),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Show all processing degrees (versions) of a time series for a given equipment."""
    from open_dateaubase.lineage import get_all_processing_degrees
    from datetime import datetime as dt

    from_effective = from_dt or dt(2000, 1, 1)
    to_effective = to_dt or dt(2100, 1, 1)

    return get_all_processing_degrees(
        equipment_id=equipment_id,
        parameter_id=parameter_id,
        from_dt=from_effective,
        to_dt=to_effective,
        conn=conn,
    )
