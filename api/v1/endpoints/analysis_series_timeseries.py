"""Time series read endpoints for lab AnalysisSeries (Traces).

Parallel to /timeseries/{channel_id} but for the lab source. Timestamps are
sample collection times (ADR 0002), so reads reuse the sensor payload queries
via the analysis-series source filter. Read-only — lab annotation / quality /
event actions are out of scope (see .tasks/lab_explore_plan.md).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, FileResponse

from api.config import settings
from api.database import get_db
from ..schemas.timeseries import AnalysisSeriesTimeseriesOut
from ..services import timeseries_service
from ..repositories import value_repository, ingestion_repository

router = APIRouter()


@router.get("/{analysis_series_id}", response_model=AnalysisSeriesTimeseriesOut)
def get_analysis_series_timeseries(
    analysis_series_id: int,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Return the time series for a lab AnalysisSeries."""
    return timeseries_service.get_analysis_series_timeseries(
        conn, analysis_series_id, from_dt, to_dt
    )


@router.get("/{analysis_series_id}/stats")
def get_analysis_series_stats(
    analysis_series_id: int,
    conn=Depends(get_db),
):
    """Return min/max sample-collection time and measurement count."""
    series = ingestion_repository.get_analysis_series_by_id(conn, analysis_series_id)
    if series is None:
        raise HTTPException(
            status_code=404, detail=f"AnalysisSeries {analysis_series_id} not found."
        )
    return value_repository.get_analysis_series_stats(
        conn, analysis_series_id, series.get("value_kind_id") or 1
    )


@router.get("/{analysis_series_id}/thumbnail/{timestamp}")
def get_analysis_series_thumbnail(
    analysis_series_id: int,
    timestamp: str,
    conn=Depends(get_db),
):
    """Return the JPEG thumbnail bytes for a stored lab image."""
    try:
        ts = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid timestamp format") from exc

    thumbnail = value_repository.get_analysis_series_image_thumbnail(
        conn, analysis_series_id, ts
    )
    if thumbnail is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=thumbnail, media_type="image/jpeg")


@router.get("/{analysis_series_id}/image/{timestamp}")
def get_analysis_series_image_file(
    analysis_series_id: int,
    timestamp: str,
    conn=Depends(get_db),
):
    """Return the full-resolution lab image file from the filesystem."""
    try:
        ts = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid timestamp format") from exc

    meta = value_repository.get_analysis_series_image_metadata_by_timestamp(
        conn, analysis_series_id, ts
    )
    if meta is None:
        raise HTTPException(status_code=404, detail="Image not found")

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
