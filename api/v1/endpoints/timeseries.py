"""Time series data endpoints."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, FileResponse

from api.config import settings
from api.database import get_db
from ..schemas.timeseries import TimeseriesOut
from ..schemas.sensor_status import (
    TimeSeriesOut as TimeSeriesOutWithStatus,
    StatusInterval,
)
from ..services import timeseries_service
from ..services.sensor_status_service import SensorStatusService
from ..repositories.sensor_status_repository import SensorStatusRepository
from ..repositories import value_repository

router = APIRouter()


@router.get("/{channel_id}", response_model=TimeseriesOut)
def get_timeseries(
    channel_id: int,
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
    """Return the time series for a Channel entry, dispatching to the correct value table."""
    result = timeseries_service.get_timeseries(
        conn, channel_id, from_dt, to_dt, operational_only=operational_only
    )

    if include_status and result:
        status_repo = SensorStatusRepository(conn)
        status_service = SensorStatusService(status_repo)

        query_from = from_dt or result.get("from_timestamp")
        query_to = to_dt or result.get("to_timestamp")

        if query_from and query_to:
            status_band = status_service.get_timeseries_status_band(
                channel_id, query_from, query_to
            )

            if status_band:
                result["status_band"] = status_band.get("status_intervals", [])
                result["has_status_data"] = status_band.get("has_status_data", False)

    return result


@router.get("/{channel_id}/full-context")
def get_full_context(
    channel_id: int,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Return the full context: all processing degrees, equipment events, lineage."""
    return timeseries_service.get_full_context(conn, channel_id, from_dt, to_dt)


@router.get("/by-context/search", response_model=list[TimeseriesOut])
def get_timeseries_by_context(
    equipment_id: int | None = Query(None, description="Equipment ID"),
    parameter_id: int | None = Query(None, description="Parameter ID"),
    processing_degree_id: int | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Find all time series matching equipment + parameter + processing degree."""
    return timeseries_service.get_timeseries_by_context(
        conn,
        equipment_id=equipment_id,
        parameter_id=parameter_id,
        processing_degree_id=processing_degree_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )


@router.get("/{channel_id}/thumbnail/{timestamp}")
def get_image_thumbnail(
    channel_id: int,
    timestamp: str,
    conn=Depends(get_db),
):
    """Return the JPEG thumbnail bytes for a stored image (from DB Thumbnail column)."""
    try:
        ts = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid timestamp format") from exc

    thumbnail = value_repository.get_image_thumbnail(conn, channel_id, ts)
    if thumbnail is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=thumbnail, media_type="image/jpeg")


@router.get("/{channel_id}/image/{timestamp}")
def get_image_file(
    channel_id: int,
    timestamp: str,
    conn=Depends(get_db),
):
    """Return the full-resolution image file for a stored image (from filesystem)."""
    try:
        ts = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid timestamp format") from exc

    meta = value_repository.get_image_metadata_by_timestamp(conn, channel_id, ts)
    if meta is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # storage_path is relative to upload_dir (e.g., "images/{channel_id}/{filename}")
    abs_path = Path(settings.upload_dir).parent / meta["storage_path"]
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    fmt = (meta["image_format"] or "jpeg").lower()
    media_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "tiff": "image/tiff",
        "bmp": "image/bmp",
        "gif": "image/gif",
    }
    media_type = media_type_map.get(fmt, "application/octet-stream")
    return FileResponse(str(abs_path), media_type=media_type)
