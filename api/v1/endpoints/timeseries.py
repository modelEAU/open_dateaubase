"""Time series data endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from api.database import get_db
from ..schemas.timeseries import TimeseriesOut
from ..services import timeseries_service

router = APIRouter()


@router.get("/{metadata_id}", response_model=TimeseriesOut)
def get_timeseries(
    metadata_id: int,
    from_dt: datetime | None = Query(None, alias="from", description="Start of time range (ISO 8601)"),
    to_dt: datetime | None = Query(None, alias="to", description="End of time range (ISO 8601)"),
    conn=Depends(get_db),
):
    """Return the time series for a MetaData entry, dispatching to the correct value table."""
    return timeseries_service.get_timeseries(conn, metadata_id, from_dt, to_dt)


@router.get("/{metadata_id}/full-context")
def get_full_context(
    metadata_id: int,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Return the full context: all processing degrees, equipment events, lineage."""
    return timeseries_service.get_full_context(conn, metadata_id, from_dt, to_dt)


@router.get("/by-context/search", response_model=list[TimeseriesOut])
def get_timeseries_by_context(
    location_id: int | None = Query(None, description="Sampling location ID"),
    parameter_id: int | None = Query(None, description="Parameter ID"),
    processing_degree: str | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Find all time series matching location + parameter + processing degree."""
    return timeseries_service.get_timeseries_by_context(
        conn,
        location_id=location_id,
        parameter_id=parameter_id,
        processing_degree=processing_degree,
        from_dt=from_dt,
        to_dt=to_dt,
    )
