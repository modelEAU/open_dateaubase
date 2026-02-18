"""Pydantic schemas for data ingestion requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class ValueItem(BaseModel):
    timestamp: datetime
    value: float | None
    quality_code: int | None = None


class SensorIngestRequest(BaseModel):
    """Ingest raw sensor data. Route is resolved via IngestionRoute table."""

    equipment_id: int
    parameter_id: int
    data_provenance_id: int = 1
    processing_degree: str = "Raw"
    values: list[ValueItem]

    @field_validator("values")
    @classmethod
    def values_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("values list must not be empty")
        return v


class LabIngestRequest(BaseModel):
    """Ingest lab measurement data with full laboratory context."""

    sample_id: int | None = None
    parameter_id: int
    unit_id: int
    laboratory_id: int | None = None
    analyst_person_id: int | None = None
    campaign_id: int | None = None
    sampling_point_id: int
    values: list[ValueItem]

    @field_validator("values")
    @classmethod
    def values_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("values list must not be empty")
        return v


class ProcessingInfo(BaseModel):
    method_name: str
    method_version: str | None = None
    processing_type: str
    parameters: dict = {}
    executed_at: datetime | None = None
    executed_by_person_id: int | None = None


class ProcessedOutputSpec(BaseModel):
    processing_degree: str
    values: list[ValueItem]


class ProcessedIngestRequest(BaseModel):
    """Ingest processed data with full lineage tracking."""

    source_metadata_ids: list[int]
    processing: ProcessingInfo
    output: ProcessedOutputSpec

    @field_validator("source_metadata_ids")
    @classmethod
    def sources_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("source_metadata_ids must not be empty")
        return v


class IngestResponse(BaseModel):
    metadata_id: int
    rows_written: int
    processing_step_id: int | None = None
