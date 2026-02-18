"""Processing lineage endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from api.database import get_db
from ..schemas.lineage import LineageTreeOut, ProcessingDegreeSummaryOut
from ..services import lineage_service

router = APIRouter()


@router.get("/{metadata_id}/forward")
def get_forward_lineage(metadata_id: int, conn=Depends(get_db)):
    """What was this data processed into? Follow outputs forward."""
    return lineage_service.forward_lineage(conn, metadata_id)


@router.get("/{metadata_id}/backward")
def get_backward_lineage(metadata_id: int, conn=Depends(get_db)):
    """Where did this data come from? Trace inputs backward."""
    return lineage_service.backward_lineage(conn, metadata_id)


@router.get("/{metadata_id}/tree", response_model=LineageTreeOut)
def get_lineage_tree(metadata_id: int, conn=Depends(get_db)):
    """Return the complete processing DAG rooted at this MetaData."""
    return lineage_service.full_lineage_tree(conn, metadata_id)


@router.get("/by-location/degrees", response_model=list[ProcessingDegreeSummaryOut])
def get_processing_degrees(
    location_id: int = Query(..., description="Sampling location ID"),
    parameter_id: int = Query(..., description="Parameter ID"),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Show all processing degrees (versions) of a time series at a given location."""
    from open_dateaubase.lineage import get_all_processing_degrees
    from datetime import datetime as dt

    from_effective = from_dt or dt(2000, 1, 1)
    to_effective = to_dt or dt(2100, 1, 1)

    return get_all_processing_degrees(
        sampling_point_id=location_id,
        parameter_id=parameter_id,
        from_dt=from_effective,
        to_dt=to_effective,
        conn=conn,
    )
