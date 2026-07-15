"""Stream provenance endpoints.

GET /streams/{stream_id}/location-at — the SamplingPoint a stream was sourced
from at a given instant, for both stream subtypes (sensor Channel and lab
AnalysisSeries).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import temporal_history_repository
from ..schemas.streams import StreamLocationAtTimeResponse

router = APIRouter()


@router.get("/{stream_id}/location-at", response_model=StreamLocationAtTimeResponse)
def get_stream_location_at_time(
    stream_id: int,
    at_time: datetime | None = Query(
        None, alias="at", description="ISO 8601 timestamp; defaults to now (UTC)"
    ),
    conn=Depends(get_db),
):
    """Return the sampling point this stream was coming from at ``at``."""
    at_time = at_time or datetime.now(timezone.utc)
    row = temporal_history_repository.get_stream_location_at(conn, stream_id, at_time)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found.")
    return StreamLocationAtTimeResponse(at_time=at_time, **row)
