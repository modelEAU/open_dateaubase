"""Data ingestion endpoints.

Three paths:
  POST /ingest/sensor    — raw sensor data, channel resolved/created via stream identity
  POST /ingest/lab       — lab analysis data (LabAnalysis + LabValue tables)
  POST /ingest/processed — processed data with lineage tracking
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import ingestion_repository, lookup_repository, value_repository
from ..schemas.ingestion import (
    IngestResponse,
    LabIngestRequest,
    LabIngestResponse,
    ProcessedIngestRequest,
    SensorIngestRequest,
)
from ..services import lineage_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Lookup endpoints (for form dropdowns)
# ---------------------------------------------------------------------------


@router.get("/lookup/units")
def get_units_lookup(conn=Depends(get_db)):
    """Return units list for dropdowns."""
    return lookup_repository.get_units_lookup(conn)


@router.post("/lookup/units", status_code=201)
def create_unit(body: dict, conn=Depends(get_db)):
    """Create a new unit."""
    unit_name = (body.get("unit") or "").strip()
    if not unit_name:
        raise HTTPException(status_code=422, detail="unit field is required")
    return lookup_repository.insert_unit(conn, unit_name)


@router.put("/lookup/units/{unit_id}")
def update_unit(unit_id: int, body: dict, conn=Depends(get_db)):
    """Update a unit."""
    unit_name = (body.get("unit") or "").strip()
    if not unit_name:
        raise HTTPException(status_code=422, detail="unit field is required")
    updated = lookup_repository.update_unit(conn, unit_id, unit_name)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Unit {unit_id} not found.")
    return updated


@router.delete("/lookup/units/{unit_id}", status_code=204)
def delete_unit(unit_id: int, conn=Depends(get_db)):
    """Delete a unit."""
    if not lookup_repository.delete_unit(conn, unit_id):
        raise HTTPException(status_code=404, detail=f"Unit {unit_id} not found.")


@router.get("/lookup/laboratories")
def get_laboratories_lookup(conn=Depends(get_db)):
    """Return laboratories list for dropdowns."""
    return lookup_repository.get_laboratories_lookup(conn)


@router.get("/lookup/procedures")
def get_procedures_lookup(conn=Depends(get_db)):
    """Return procedures list for dropdowns."""
    return lookup_repository.get_procedures_lookup(conn)


@router.get("/lookup/samples")
def get_samples_lookup(conn=Depends(get_db)):
    """Return samples list for dropdowns (most recent first)."""
    return lookup_repository.get_samples_lookup(conn)


@router.get("/lookup/sampling-points")
def get_sampling_points_lookup(conn=Depends(get_db)):
    """Return sampling points list for dropdowns."""
    return lookup_repository.get_sampling_points_lookup(conn)


@router.get("/lookup/equipment-events")
def get_equipment_events_lookup(conn=Depends(get_db)):
    """Return equipment events list for dropdowns."""
    return lookup_repository.get_equipment_events_lookup(conn)


@router.get("/lookup/data-provenance")
def get_data_provenance_lookup(conn=Depends(get_db)):
    """Return data provenance types for dropdowns."""
    return lookup_repository.get_data_provenance_lookup(conn)


# ---------------------------------------------------------------------------
# Ingest endpoints
# ---------------------------------------------------------------------------


@router.post("/sensor", response_model=IngestResponse, status_code=201)
def ingest_sensor(data: SensorIngestRequest, conn=Depends(get_db)):
    """Ingest raw sensor measurements.

    Resolves (or creates) the Channel via the UNIQUE stream identity:
    (equipment_id, parameter_id, data_provenance_id, processing_degree).
    No pre-configuration is required.
    """
    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        equipment_id=data.equipment_id,
        parameter_id=data.parameter_id,
        unit_id=data.unit_id,
        data_provenance_id=data.data_provenance_id,
        processing_degree_id=data.processing_degree_id,
    )

    rows = value_repository.insert_scalar_values(
        conn,
        channel_id,
        [v.model_dump() for v in data.values],
    )

    return IngestResponse(channel_id=channel_id, rows_written=rows)


@router.post("/lab", response_model=LabIngestResponse, status_code=201)
def ingest_lab(data: LabIngestRequest, conn=Depends(get_db)):
    """Ingest laboratory analysis results.

    Creates one LabAnalysis record plus one LabValue row per measurement.
    sample_id is required when associating with a physical sample.
    """
    lab_analysis_id = ingestion_repository.insert_lab_analysis(
        conn,
        sample_id=data.sample_id,
        laboratory_id=data.laboratory_id,
        analyst_person_id=data.analyst_person_id,
        procedure_id=data.procedure_id,
        campaign_id=data.campaign_id,
        notes=data.notes,
    )

    rows = 0
    for item in data.values:
        ingestion_repository.insert_lab_value(
            conn,
            lab_analysis_id=lab_analysis_id,
            parameter_id=item.parameter_id,
            unit_id=item.unit_id,
            value=item.value,
            replicate=item.replicate,
            quality_code=item.quality_code,
        )
        rows += 1

    return LabIngestResponse(lab_analysis_id=lab_analysis_id, rows_written=rows)


@router.post("/processed", response_model=IngestResponse, status_code=201)
def ingest_processed(data: ProcessedIngestRequest, conn=Depends(get_db)):
    """Ingest processed data with full lineage tracking.

    Derives the output channel from the primary source (cloning stream identity
    with a new ProcessingDegree), writes processed values, and records a
    ProcessingStep + DataLineage.
    """
    if not data.source_channel_ids:
        raise HTTPException(
            status_code=400, detail="source_channel_ids must not be empty."
        )

    primary_source_id = data.source_channel_ids[0]

    output_channel_id = ingestion_repository.find_or_create_derived_metadata(
        conn,
        source_channel_id=primary_source_id,
        processing_degree_id=data.output.processing_degree_id,
    )

    rows = value_repository.insert_scalar_values(
        conn,
        output_channel_id,
        [v.model_dump() for v in data.output.values],
    )

    step_id = lineage_service.persist_processing(
        conn,
        source_metadata_ids=data.source_channel_ids,
        method_name=data.processing.method_name,
        method_version=data.processing.method_version,
        processing_type=data.processing.processing_type,
        parameters=data.processing.parameters,
        executed_at=data.processing.executed_at,
        executed_by_person_id=data.processing.executed_by_person_id,
        output_metadata_id=output_channel_id,
    )

    return IngestResponse(
        channel_id=output_channel_id,
        rows_written=rows,
        processing_step_id=step_id,
    )
