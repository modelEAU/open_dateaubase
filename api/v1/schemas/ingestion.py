"""Pydantic schemas for data ingestion requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class ValueItem(BaseModel):
    timestamp: datetime
    value: float | None
    quality_code: int | None = None


class SensorIngestRequest(BaseModel):
    """Ingest raw sensor data. Channel is resolved (or created) from the stream identity."""

    equipment_id: int
    parameter_id: int
    unit_id: int
    data_provenance_id: int = 1
    processing_degree: str = "Raw"
    values: list[ValueItem]

    @field_validator("values")
    @classmethod
    def values_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("values list must not be empty")
        return v


class LabValueItem(BaseModel):
    """One measured value within a lab analysis."""

    parameter_id: int
    unit_id: int
    value: float | None
    replicate: int = 1
    quality_code: int | None = None


class LabIngestRequest(BaseModel):
    """Ingest lab analysis results into LabAnalysis + LabValue tables."""

    sample_id: int | None = None
    laboratory_id: int | None = None
    analyst_person_id: int | None = None
    procedure_id: int | None = None
    campaign_id: int | None = None
    notes: str | None = None
    values: list[LabValueItem]

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

    source_channel_ids: list[int]
    processing: ProcessingInfo
    output: ProcessedOutputSpec

    @field_validator("source_channel_ids")
    @classmethod
    def sources_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("source_channel_ids must not be empty")
        return v


class IngestResponse(BaseModel):
    channel_id: int
    rows_written: int
    processing_step_id: int | None = None


class LabIngestResponse(BaseModel):
    lab_analysis_id: int
    rows_written: int
