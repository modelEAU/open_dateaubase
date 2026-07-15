"""Time series data endpoints."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, FileResponse

from api.config import settings
from api.database import get_db
from ..schemas.timeseries import TimeseriesOut, QualityCodePatch, BulkQualityCodeResult
from ..schemas.sensor_status import (
    TimeSeriesOut as TimeSeriesOutWithStatus,
    StatusInterval,
)
from ..services import timeseries_service
from ..services.sensor_status_service import SensorStatusService
from ..repositories.sensor_status_repository import SensorStatusRepository
from ..repositories import value_repository, channel_repository

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


@router.get("/{channel_id}/stats")
def get_channel_stats(
    channel_id: int,
    conn=Depends(get_db),
):
    """Return min/max timestamp and observation count without loading data rows."""
    channel = channel_repository.get_channel_by_id(conn, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found.")
    value_kind_id = channel.get("value_kind_id") or 1
    return value_repository.get_channel_stats(conn, channel_id, value_kind_id)


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
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Find all time series matching equipment + parameter."""
    return timeseries_service.get_timeseries_by_context(
        conn,
        equipment_id=equipment_id,
        parameter_id=parameter_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )


@router.patch("/{channel_id}/quality-code", response_model=BulkQualityCodeResult)
def bulk_set_quality_code(
    channel_id: int,
    body: QualityCodePatch,
    conn=Depends(get_db),
):
    """Bulk-assign a quality code to all value rows for a channel within a time range."""
    channel = channel_repository.get_channel_by_id(conn, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found.")

    updated = value_repository.bulk_set_quality_code(
        conn,
        channel_id=channel_id,
        value_kind_id=channel.get("value_kind_id") or 1,
        from_dt=body.start_time,
        to_dt=body.end_time,
        quality_code=body.quality_code_id,
    )
    return {"updated_count": updated}


# Images are addressed by Observation_ID, which is unique per picture. Sensor and
# lab images share these two routes: the source (channel vs analysis series) is
# already resolved by the listing that hands out the observation ids.
@router.get("/images/{observation_id}/thumbnail")
def get_image_thumbnail(
    observation_id: int,
    conn=Depends(get_db),
):
    """Return the JPEG thumbnail bytes for a stored image (from DB Thumbnail column)."""
    thumbnail = value_repository.get_image_thumbnail(conn, observation_id)
    if thumbnail is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=thumbnail, media_type="image/jpeg")


@router.get("/images/{observation_id}/file")
def get_image_file(
    observation_id: int,
    conn=Depends(get_db),
):
    """Return the full-resolution image file for a stored image (from filesystem)."""
    meta = value_repository.get_image_metadata(conn, observation_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # storage_path is relative to upload_base_dir (e.g., "images/{channel_id}/{filename}")
    abs_path = Path(settings.upload_base_dir) / meta["storage_path"]
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
