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
    channel_kind: str = "value"
    parent_tag: str | None = None
    parameter_name: str
    unit_name: str
    data_provenance_kind_id: int = 1
    strict: bool = False
    values: list[ValueItem]

    @field_validator("values")
    @classmethod
    def values_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("values list must not be empty")
        return v


class LabMeasurementItem(BaseModel):
    """One measurement in a lab experiment.

    Carries both the AnalysisSeries identity (parameter / location / kinds /
    unit / name) used to find-or-create the series, and the per-measurement
    data (sample, value, lab metadata, replicate, quality). The payload value
    is routed to Value / ValueVector / ValueMatrix based on ``value_kind_id``.
    """

    # Series identity — used to find or create AnalysisSeries
    parameter_id: int
    sampling_point_id: int
    unit_id: int
    value_kind_id: int = 1
    processing_kind_id: int = 1
    series_name: str

    # Measurement
    sample_id: int
    value: float | list | None
    laboratory_id: int | None = None
    analyst_person_id: int | None = None
    procedure_id: int | None = None
    analysis_datetime: datetime | None = None
    replicate: int = 1
    quality_code_id: int | None = None
    notes: str | None = None


class LabIngestRequest(BaseModel):
    """Ingest one LabExperiment session worth of lab measurements.

    Creates a single ``LabExperiment`` row, then for each measurement
    find-or-creates its ``AnalysisSeries``, inserts a ``LabAnalysis`` row, and
    inserts an ``Observation`` routed to the appropriate payload table.
    """

    name: str
    experiment_datetime: datetime
    campaign_id: int | None = None
    description: str | None = None
    created_by_person_id: int | None = None
    measurements: list[LabMeasurementItem]

    @field_validator("measurements")
    @classmethod
    def measurements_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("measurements list must not be empty")
        return v


class ProcessingInfo(BaseModel):
    method_name: str
    method_version: str | None = None
    processing_kind_id: int
    method_parameters: dict = {}
    executed_at: datetime | None = None
    executed_by_person_id: int | None = None


class ProcessedOutputSpec(BaseModel):
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
    lab_experiment_id: int
    rows_written: int


class ImageIngestResponse(BaseModel):
    channel_id: int
    value_image_id: int
    storage_path: str


class LabImageIngestResponse(BaseModel):
    lab_experiment_id: int
    rows_written: int
    storage_paths: list[str]


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
    channel_kind: str = "value"
    parameter_name: str
    unit_name: str
    binning_axis_id: int
    data_provenance_kind_id: int = 1
    strict: bool = False
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


class TaglessVectorSensorIngestRequest(BaseModel):
    das_name: str
    equipment_name: str
    parameter_name: str
    unit_name: str
    binning_axis_id: int
    data_provenance_kind_id: int = 1
    strict: bool = False
    observations: list[VectorObservation]

    @field_validator("observations")
    @classmethod
    def obs_not_empty(cls, v):
        if not v:
            raise ValueError("observations must not be empty")
        return v


class MatrixSensorIngestRequest(BaseModel):
    das_name: str
    tag: str
    channel_kind: str = "value"
    parameter_name: str
    unit_name: str
    row_axis_id: int
    col_axis_id: int
    data_provenance_kind_id: int = 1
    strict: bool = False
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


class TaglessSensorIngestRequest(BaseModel):
    """Ingest raw sensor data from a direct-connect station (no SCADA tag name).

    A synthetic tag is auto-generated as
    ``"{equipment_name}/{parameter_name}"`` (lowercased, trimmed).
    This tag is deterministic and stable across repeated runs.
    """

    das_name: str
    equipment_name: str
    parameter_name: str
    unit_name: str
    data_provenance_kind_id: int = 1
    strict: bool = False
    values: list[ValueItem]

    @field_validator("values")
    @classmethod
    def values_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("values list must not be empty")
        return v


class SensorChannelResolveRequest(BaseModel):
    """Resolve (or create) a tagged sensor channel. Returns channel_id with no data write."""

    das_name: str
    tag: str
    channel_kind: str = "value"
    parent_tag: str | None = None
    parameter_name: str
    unit_name: str
    data_provenance_kind_id: int = 1
    value_kind_id: int = 1


class TaglessSensorChannelResolveRequest(BaseModel):
    """Resolve (or create) a tagless sensor channel. Returns channel_id with no data write."""

    das_name: str
    equipment_name: str
    parameter_name: str
    unit_name: str
    data_provenance_kind_id: int = 1
    value_kind_id: int = 1


class ChannelResolveResponse(BaseModel):
    channel_id: int
    warnings: list[str] = []


class ChannelDeactivateResponse(BaseModel):
    channel_id: int
    deactivated: bool
