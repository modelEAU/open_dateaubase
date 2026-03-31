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

    das_name: str
    tag: str
    signal_port_type: str = "value"
    parameter_name: str
    unit_name: str
    data_provenance_id: int = 1
    processing_degree_id: int = 1
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
    processing_degree_id: int
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
    warnings: list[str] = []


class LabIngestResponse(BaseModel):
    lab_analysis_id: int
    rows_written: int


class ImageIngestResponse(BaseModel):
    channel_id: int
    value_image_id: int
    storage_path: str


class SampleCreateRequest(BaseModel):
    """Request to create a new sample."""

    sampling_point_id: int
    sampled_by_person_id: int | None = None
    campaign_id: int | None = None
    sample_datetime_start: datetime
    sample_datetime_end: datetime | None = None
    description: str | None = None


class SampleCreateResponse(BaseModel):
    """Response after creating a sample."""

    sample_id: int


class VectorObservation(BaseModel):
    timestamp: datetime
    bin_values: list[float | None]  # length must equal axis.number_of_bins
    quality_code: int | None = None


class VectorSensorIngestRequest(BaseModel):
    das_name: str
    tag: str
    signal_port_type: str = "value"
    parameter_name: str
    unit_name: str
    binning_axis_id: int
    data_provenance_id: int = 1
    processing_degree_id: int = 1
    observations: list[VectorObservation]

    @field_validator("observations")
    @classmethod
    def obs_not_empty(cls, v):
        if not v:
            raise ValueError("observations must not be empty")
        return v


class MatrixObservation(BaseModel):
    timestamp: datetime
    matrix: list[
        list[float | None]
    ]  # [row][col], ragged rows allowed (padded with None)
    quality_code: int | None = None


class MatrixSensorIngestRequest(BaseModel):
    das_name: str
    tag: str
    signal_port_type: str = "value"
    parameter_name: str
    unit_name: str
    row_axis_id: int
    col_axis_id: int
    data_provenance_id: int = 1
    processing_degree_id: int = 1
    observations: list[MatrixObservation]

    @field_validator("observations")
    @classmethod
    def obs_not_empty(cls, v):
        if not v:
            raise ValueError("observations must not be empty")
        return v

    @field_validator("col_axis_id")
    @classmethod
    def axes_must_differ(cls, v: int, info) -> int:
        row_axis_id = info.data.get("row_axis_id")
        if row_axis_id is not None and v == row_axis_id:
            raise ValueError("row_axis_id and col_axis_id must be different")
        return v


class SignalPortDeactivateResponse(BaseModel):
    signal_port_id: int
    deactivated: bool
