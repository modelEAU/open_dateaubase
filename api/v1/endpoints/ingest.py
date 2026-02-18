"""Data ingestion endpoints.

Three paths:
  POST /ingest/sensor   — raw sensor data, route resolved via IngestionRoute
  POST /ingest/lab      — lab measurement data
  POST /ingest/processed — processed data with lineage tracking
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import ingestion_repository, value_repository
from ..schemas.ingestion import (
    IngestResponse,
    LabIngestRequest,
    ProcessedIngestRequest,
    SensorIngestRequest,
)
from ..services import lineage_service, routing_service

router = APIRouter()


@router.post("/sensor", response_model=IngestResponse, status_code=201)
def ingest_sensor(data: SensorIngestRequest, conn=Depends(get_db)):
    """Ingest raw sensor measurements.

    Resolves the MetaData target via the IngestionRoute table using the
    timestamp of the first value in the batch.
    """
    reference_ts = data.values[0].timestamp

    metadata_id = routing_service.resolve_route(
        conn,
        equipment_id=data.equipment_id,
        parameter_id=data.parameter_id,
        data_provenance_id=data.data_provenance_id,
        processing_degree=data.processing_degree,
        timestamp=reference_ts,
    )

    rows = value_repository.insert_scalar_values(
        conn,
        metadata_id,
        [v.model_dump() for v in data.values],
    )

    return IngestResponse(metadata_id=metadata_id, rows_written=rows)


@router.post("/lab", response_model=IngestResponse, status_code=201)
def ingest_lab(data: LabIngestRequest, conn=Depends(get_db)):
    """Ingest laboratory measurement data.

    Finds or creates a MetaData entry with the given lab context,
    then inserts scalar values.
    """
    metadata_id = ingestion_repository.find_or_create_metadata_for_lab(
        conn,
        parameter_id=data.parameter_id,
        unit_id=data.unit_id,
        sampling_point_id=data.sampling_point_id,
        laboratory_id=data.laboratory_id,
        analyst_person_id=data.analyst_person_id,
        campaign_id=data.campaign_id,
        sample_id=data.sample_id,
    )

    rows = value_repository.insert_scalar_values(
        conn,
        metadata_id,
        [v.model_dump() for v in data.values],
    )

    return IngestResponse(metadata_id=metadata_id, rows_written=rows)


@router.post("/processed", response_model=IngestResponse, status_code=201)
def ingest_processed(data: ProcessedIngestRequest, conn=Depends(get_db)):
    """Ingest processed data with full lineage tracking.

    Creates a new MetaData entry (cloning context from the primary source),
    writes processed values, and records a ProcessingStep + DataLineage.
    """
    if not data.source_metadata_ids:
        raise HTTPException(status_code=400, detail="source_metadata_ids must not be empty.")

    primary_source_id = data.source_metadata_ids[0]

    output_metadata_id = ingestion_repository.create_processed_metadata(
        conn,
        source_metadata_id=primary_source_id,
        processing_degree=data.output.processing_degree,
    )

    rows = value_repository.insert_scalar_values(
        conn,
        output_metadata_id,
        [v.model_dump() for v in data.output.values],
    )

    step_id = lineage_service.persist_processing(
        conn,
        source_metadata_ids=data.source_metadata_ids,
        method_name=data.processing.method_name,
        method_version=data.processing.method_version,
        processing_type=data.processing.processing_type,
        parameters=data.processing.parameters,
        executed_at=data.processing.executed_at,
        executed_by_person_id=data.processing.executed_by_person_id,
        output_metadata_id=output_metadata_id,
    )

    return IngestResponse(
        metadata_id=output_metadata_id,
        rows_written=rows,
        processing_step_id=step_id,
    )
