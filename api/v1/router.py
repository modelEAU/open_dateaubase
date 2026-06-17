"""v1 API router — mounts all sub-routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .endpoints.auth import get_current_user, router as auth_router
from .endpoints.audit import router as audit_router
from .endpoints.health import router as health_router
from .endpoints.sites import router as sites_router
from .endpoints.channels import router as channels_router
from .endpoints.timeseries import router as timeseries_router
from .endpoints.analysis_series_timeseries import (
    router as analysis_series_timeseries_router,
)
from .endpoints.campaigns import router as campaigns_router
from .endpoints.equipment import router as equipment_router
from .endpoints.equipment_move import router as equipment_move_router
from .endpoints.das_move import router as das_move_router
from .endpoints.lineage import router as lineage_router
from .endpoints.ingest import router as ingest_router
from .endpoints.lab import router as lab_router
from .endpoints.annotations import (
    timeseries_router as timeseries_annotations_router,
    analysis_series_annotations_router,
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
from .endpoints.deployment_traces import router as deployment_traces_router

router = APIRouter()

# Public routes: login/signup must be reachable without a token; health is for
# liveness probes. /auth/me stays protected via its own endpoint dependency.
public_router = APIRouter()
public_router.include_router(auth_router, prefix="/auth", tags=["auth"])
public_router.include_router(health_router, tags=["health"])

# Everything else requires a valid bearer token (user JWT or service token).
# Secure by default: new sub-routers added below are protected unless they are
# explicitly moved to public_router above.
protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(audit_router, prefix="/audit", tags=["audit"])
protected.include_router(sites_router, prefix="/sites", tags=["sites"])
protected.include_router(channels_router, prefix="/channels", tags=["channels"])
protected.include_router(timeseries_router, prefix="/timeseries", tags=["timeseries"])
protected.include_router(
    analysis_series_timeseries_router,
    prefix="/analysis-series",
    tags=["analysis-series-timeseries"],
)
protected.include_router(
    analysis_series_annotations_router,
    prefix="/analysis-series",
    tags=["annotations"],
)
protected.include_router(
    timeseries_annotations_router, prefix="/timeseries", tags=["annotations"]
)
protected.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
protected.include_router(equipment_router, prefix="/equipment", tags=["equipment"])
protected.include_router(
    equipment_move_router, prefix="/equipment", tags=["equipment-move"]
)
protected.include_router(das_move_router, prefix="/das", tags=["das-move"])
protected.include_router(lineage_router, prefix="/lineage", tags=["lineage"])
protected.include_router(ingest_router, prefix="/ingest", tags=["ingestion"])
protected.include_router(lab_router, prefix="/ingest/lab", tags=["ingestion-lab"])
protected.include_router(annotations_router, prefix="/annotations", tags=["annotations"])
protected.include_router(
    annotation_kinds_router, prefix="/annotation-kinds", tags=["annotation-types"]
)
protected.include_router(sensor_status_router, tags=["sensor-status"])
protected.include_router(parameters_router, prefix="/parameters", tags=["parameters"])
protected.include_router(
    signal_interfaces_router, prefix="/signal-interfaces", tags=["signal-interfaces"]
)
protected.include_router(
    signal_interface_ports_router,
    prefix="/signal-interface-ports",
    tags=["signal-interface-ports"],
)
protected.include_router(
    value_binning_router, prefix="/value-binning-axes", tags=["value-binning-axes"]
)
protected.include_router(
    control_loops_router, prefix="/control-loops", tags=["control-loops"]
)
protected.include_router(persons_router, prefix="/persons", tags=["persons"])
protected.include_router(
    quality_codes_router, prefix="/quality-codes", tags=["quality-codes"]
)
protected.include_router(
    sample_kinds_router, prefix="/sample-kinds", tags=["sample-types"]
)
protected.include_router(
    sample_collection_kinds_router, prefix="/sample-collection-kinds", tags=["sample-methods"]
)
protected.include_router(
    process_unit_kinds_router, prefix="/process-unit-kinds", tags=["process-units"]
)
protected.include_router(
    process_units_router, prefix="/process-units", tags=["process-units"]
)
protected.include_router(vocab_router, prefix="/vocab", tags=["vocabulary"])
protected.include_router(convert_router, tags=["conversion"])
protected.include_router(
    deployment_traces_router, prefix="/deployment-traces", tags=["deployment-traces"]
)

# Mount the public and protected groups onto the v1 router.
router.include_router(public_router)
router.include_router(protected)
