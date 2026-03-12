"""v1 API router — mounts all sub-routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter
from .endpoints.auth import router as auth_router

from .endpoints.health import router as health_router
from .endpoints.sites import router as sites_router
from .endpoints.channels import router as channels_router
from .endpoints.timeseries import router as timeseries_router
from .endpoints.campaigns import router as campaigns_router
from .endpoints.equipment import router as equipment_router
from .endpoints.lineage import router as lineage_router
from .endpoints.ingest import router as ingest_router
from .endpoints.annotations import (
    timeseries_router as timeseries_annotations_router,
    annotations_router,
    annotation_types_router,
)
from .endpoints.sensor_status import router as sensor_status_router
from .endpoints.parameters import router as parameters_router
from .endpoints.value_binning import router as value_binning_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(health_router, tags=["health"])
router.include_router(sites_router, prefix="/sites", tags=["sites"])
router.include_router(channels_router, prefix="/channels", tags=["channels"])
router.include_router(timeseries_router, prefix="/timeseries", tags=["timeseries"])
router.include_router(
    timeseries_annotations_router, prefix="/timeseries", tags=["annotations"]
)
router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
router.include_router(equipment_router, prefix="/equipment", tags=["equipment"])
router.include_router(lineage_router, prefix="/lineage", tags=["lineage"])
router.include_router(ingest_router, prefix="/ingest", tags=["ingestion"])
router.include_router(annotations_router, prefix="/annotations", tags=["annotations"])
router.include_router(
    annotation_types_router, prefix="/annotation-types", tags=["annotation-types"]
)
router.include_router(sensor_status_router, tags=["sensor-status"])
router.include_router(parameters_router, prefix="/parameters", tags=["parameters"])
router.include_router(
    value_binning_router, prefix="/value-binning-axes", tags=["value-binning-axes"]
)
