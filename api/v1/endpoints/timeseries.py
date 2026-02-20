"""Time series data endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from api.database import get_db
from ..schemas.timeseries import TimeseriesOut
from ..schemas.sensor_status import (
    TimeSeriesOut as TimeSeriesOutWithStatus,
    StatusInterval,
)
from ..services import timeseries_service
from ..services.sensor_status_service import SensorStatusService
from ..repositories.sensor_status_repository import SensorStatusRepository

router = APIRouter()


@router.get("/{metadata_id}", response_model=TimeseriesOut)
def get_timeseries(
    metadata_id: int,
    from_dt: datetime | None = Query(
        None, alias="from", description="Start of time range (ISO 8601)"
    ),
    to_dt: datetime | None = Query(
        None, alias="to", description="End of time range (ISO 8601)"
    ),
    include_status: bool = Query(False, description="Include status band in response"),
    operational_only: bool = Query(
        False, description="Filter to values where sensor was operational"
    ),
    conn=Depends(get_db),
):
    """Return the time series for a MetaData entry, dispatching to the correct value table."""
    result = timeseries_service.get_timeseries(
        conn, metadata_id, from_dt, to_dt, operational_only=operational_only
    )

    if include_status and result:
        status_repo = SensorStatusRepository(conn)
        status_service = SensorStatusService(status_repo)

        query_from = from_dt or result.get("from_timestamp")
        query_to = to_dt or result.get("to_timestamp")

        if query_from and query_to:
            status_band = status_service.get_timeseries_status_band(
                metadata_id, query_from, query_to
            )

            if status_band:
                result["status_band"] = status_band.get("status_intervals", [])
                result["has_status_data"] = status_band.get("has_status_data", False)

    return result


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
