"""v1 API router — mounts all sub-routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from .endpoints.auth import router as auth_router
from .endpoints.audit import router as audit_router
from .endpoints.health import router as health_router
from .endpoints.sites import router as sites_router
from .endpoints.channels import router as channels_router
from .endpoints.timeseries import router as timeseries_router
from .endpoints.campaigns import router as campaigns_router
from .endpoints.equipment import router as equipment_router
from .endpoints.equipment_move import router as equipment_move_router
from .endpoints.das_move import router as das_move_router
from .endpoints.lineage import router as lineage_router
from .endpoints.ingest import router as ingest_router
from .endpoints.annotations import (
    timeseries_router as timeseries_annotations_router,
    annotations_router,
    annotation_kinds_router,
)
from .endpoints.sensor_status import router as sensor_status_router
from .endpoints.parameters import router as parameters_router
from .endpoints.signal_interfaces import router as signal_interfaces_router
from .endpoints.signal_interface_ports import router as signal_interface_ports_router
from .endpoints.value_binning import router as value_binning_router
from .endpoints.control_loops import router as control_loops_router
from .endpoints.persons import router as persons_router
from .endpoints.quality_codes import router as quality_codes_router
from .endpoints.lab_lookup import (
    sample_kinds_router,
    sample_collection_kinds_router,
)
from .endpoints.process_units import (
    process_unit_kinds_router,
    process_units_router,
)
from .endpoints.vocab import router as vocab_router
from .endpoints.convert import router as convert_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(audit_router, prefix="/audit", tags=["audit"])
router.include_router(health_router, tags=["health"])
router.include_router(sites_router, prefix="/sites", tags=["sites"])
router.include_router(channels_router, prefix="/channels", tags=["channels"])
router.include_router(timeseries_router, prefix="/timeseries", tags=["timeseries"])
router.include_router(
    timeseries_annotations_router, prefix="/timeseries", tags=["annotations"]
)
router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
router.include_router(equipment_router, prefix="/equipment", tags=["equipment"])
router.include_router(
    equipment_move_router, prefix="/equipment", tags=["equipment-move"]
)
router.include_router(das_move_router, prefix="/das", tags=["das-move"])
router.include_router(lineage_router, prefix="/lineage", tags=["lineage"])
router.include_router(ingest_router, prefix="/ingest", tags=["ingestion"])
router.include_router(annotations_router, prefix="/annotations", tags=["annotations"])
router.include_router(
    annotation_kinds_router, prefix="/annotation-kinds", tags=["annotation-types"]
)
router.include_router(sensor_status_router, tags=["sensor-status"])
router.include_router(parameters_router, prefix="/parameters", tags=["parameters"])
router.include_router(
    signal_interfaces_router, prefix="/signal-interfaces", tags=["signal-interfaces"]
)
router.include_router(
    signal_interface_ports_router,
    prefix="/signal-interface-ports",
    tags=["signal-interface-ports"],
)
router.include_router(
    value_binning_router, prefix="/value-binning-axes", tags=["value-binning-axes"]
)
router.include_router(
    control_loops_router, prefix="/control-loops", tags=["control-loops"]
)
router.include_router(persons_router, prefix="/persons", tags=["persons"])
router.include_router(
    quality_codes_router, prefix="/quality-codes", tags=["quality-codes"]
)
router.include_router(
    sample_kinds_router, prefix="/sample-kinds", tags=["sample-types"]
)
router.include_router(
    sample_collection_kinds_router, prefix="/sample-collection-kinds", tags=["sample-methods"]
)
router.include_router(
    process_unit_kinds_router, prefix="/process-unit-kinds", tags=["process-units"]
)
router.include_router(
    process_units_router, prefix="/process-units", tags=["process-units"]
)
router.include_router(vocab_router, prefix="/vocab", tags=["vocabulary"])
router.include_router(convert_router, tags=["conversion"])
