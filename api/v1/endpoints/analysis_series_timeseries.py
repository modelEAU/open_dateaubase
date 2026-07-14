"""Time series read endpoints for lab AnalysisSeries (Traces).

Parallel to /timeseries/{channel_id} but for the lab source. Timestamps are
sample collection times (ADR 0002), so reads reuse the sensor payload queries
via the analysis-series source filter. Read-only — lab annotation / quality /
event actions are out of scope (see .tasks/lab_explore_plan.md).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

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
