"""v1 API router — mounts all sub-routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from .endpoints.health import router as health_router
from .endpoints.sites import router as sites_router
from .endpoints.metadata import router as metadata_router
from .endpoints.timeseries import router as timeseries_router
from .endpoints.campaigns import router as campaigns_router
from .endpoints.equipment import router as equipment_router
from .endpoints.lineage import router as lineage_router
from .endpoints.ingest import router as ingest_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(sites_router, prefix="/sites", tags=["sites"])
router.include_router(metadata_router, prefix="/metadata", tags=["metadata"])
router.include_router(timeseries_router, prefix="/timeseries", tags=["timeseries"])
router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
router.include_router(equipment_router, prefix="/equipment", tags=["equipment"])
router.include_router(lineage_router, prefix="/lineage", tags=["lineage"])
router.include_router(ingest_router, prefix="/ingest", tags=["ingestion"])
