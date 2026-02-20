"""Sensor status API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..schemas.sensor_status import (
    EquipmentStatusResponse,
    EquipmentStatusHistoryResponse,
    StatusCodeListResponse,
    TimeSeriesStatusBand,
)
from ..services.sensor_status_service import SensorStatusService
from ..repositories.sensor_status_repository import SensorStatusRepository

router = APIRouter()


def get_status_repo(conn=Depends(get_db)):
    """Dependency to get sensor status repository."""
    return SensorStatusRepository(conn)


def get_status_service(repo=Depends(get_status_repo)):
    """Dependency to get sensor status service."""
    return SensorStatusService(repo)


@router.get("/status-codes", response_model=StatusCodeListResponse)
def list_status_codes(service=Depends(get_status_service)):
    """List all sensor status codes for UI dropdowns."""
    codes = service.get_all_status_codes()
    return {"status_codes": codes}


@router.get("/equipment/{equipment_id}/status", response_model=EquipmentStatusResponse)
def get_equipment_status(
    equipment_id: int,
    at: Optional[datetime] = Query(
        None, description="Point in time to query (ISO 8601)"
    ),
    service=Depends(get_status_service),
):
    """Get the full health picture of a sensor: device-level status plus all per-channel statuses."""
    result = service.get_equipment_status(equipment_id, at=at)
    if result is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return result


@router.get(
    "/equipment/{equipment_id}/status/history",
    response_model=EquipmentStatusHistoryResponse,
)
def get_equipment_status_history(
    equipment_id: int,
    from_dt: datetime = Query(..., description="Start of range (ISO 8601)"),
    to_dt: datetime = Query(..., description="End of range (ISO 8601)"),
    channel: Optional[str] = Query(
        None, description="Filter to a specific parameter name"
    ),
    service=Depends(get_status_service),
):
    """Get status transitions over a time range for the whole sensor."""
    result = service.get_equipment_status_history(
        equipment_id, from_dt, to_dt, channel=channel
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return result


@router.get("/timeseries/{metadata_id}/status", response_model=TimeSeriesStatusBand)
def get_timeseries_status(
    metadata_id: int,
    from_dt: datetime = Query(..., description="Start of range (ISO 8601)"),
    to_dt: datetime = Query(..., description="End of range (ISO 8601)"),
    service=Depends(get_status_service),
):
    """Get the status band for a specific measurement channel over a time range."""
    result = service.get_timeseries_status_band(metadata_id, from_dt, to_dt)
    if result is None:
        raise HTTPException(status_code=404, detail="MetaData entry not found")
    return result
