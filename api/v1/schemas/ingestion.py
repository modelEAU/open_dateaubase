"""Pydantic schemas for data ingestion requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from open_dateaubase.ingestion_schemas import (
    LabIngestRequest,
    LabMeasurementItem,
    SampleCreateRequest,
    SensorIngestRequest,
    TaglessSensorIngestRequest,
    ValueItem,
)

__all__ = [
    "LabIngestRequest",
    "LabMeasurementItem",
    "SampleCreateRequest",
    "SensorIngestRequest",
    "TaglessSensorIngestRequest",
    "ValueItem",
]


class ProcessingInfo(BaseModel):
    method_name: str
    method_version: str | None = None
    operation_kind_id: int
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


class AnalysisSeriesLookupItem(BaseModel):
    """Brief AnalysisSeries info for dropdowns."""

    analysis_series_id: int
    name: str
    parameter_id: int
    parameter_name: str
    sampling_point_id: int
    sampling_point_label: str
    unit_id: int
    unit_name: str
    value_kind_id: int
    campaign_id: int | None = None
    campaign_name: str | None = None


class AnalysisSeriesCreateRequest(BaseModel):
    """Request to create a new AnalysisSeries."""

    name: str
    parameter_id: int
    sampling_point_id: int
    unit_id: int
    value_kind_id: int = 1
    laboratory_id: int | None = None
    campaign_id: int | None = None


class LabExperimentLookupItem(BaseModel):
    """Brief LabExperiment info for dropdowns."""

    lab_experiment_id: int
    name: str
    experiment_datetime: datetime
    series_count: int


class LabPanelCreateRequest(BaseModel):
    """Request to create a new LabPanel."""

    name: str
    description: str | None = None
    created_by_person_id: int | None = None
    default_sample_collection_kind_id: int | None = None
    default_sample_equipment_id: int | None = None
    default_sample_kind_id: int | None = None
    default_sample_material_kind_id: int | None = None
    series_ids: list[int]


class LabPanelPatchRequest(BaseModel):
    """Partial update for a LabPanel. Only sent fields are updated."""

    name: str | None = None
    description: str | None = None
    default_sample_collection_kind_id: int | None = None
    default_sample_equipment_id: int | None = None
    default_sample_kind_id: int | None = None
    default_sample_material_kind_id: int | None = None
    series_ids: list[int] | None = None


class LabPanelSeriesAddRequest(BaseModel):
    """Request to add a series to an existing panel."""

    analysis_series_id: int


class LabPanelResponse(BaseModel):
    """Panel info returned by lookup endpoints."""

    lab_panel_id: int
    name: str
    description: str | None = None
    created_by_person_id: int | None = None
    default_sample_collection_kind_id: int | None = None
    default_sample_equipment_id: int | None = None
    default_sample_kind_id: int | None = None
    default_sample_material_kind_id: int | None = None
    series_count: int


class LabPanelDetailResponse(BaseModel):
    """Panel with its full series list."""

    lab_panel_id: int
    name: str
    description: str | None = None
    default_sample_collection_kind_id: int | None = None
    default_sample_equipment_id: int | None = None
    default_sample_kind_id: int | None = None
    default_sample_material_kind_id: int | None = None
    series: list[AnalysisSeriesLookupItem]


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
    signal_interface_name: str
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
    signal_interface_name: str
    data_provenance_kind_id: int = 1
    value_kind_id: int = 1
    # Backdate a newly-opened EquipmentWiringHistory row to this timestamp (e.g.
    # the importer's min_timestamp floor) so location/equipment views cover the
    # data that will be ingested, rather than starting at the resolve moment.
    wiring_valid_from: datetime | None = None


class ChannelResolveResponse(BaseModel):
    channel_id: int
    warnings: list[str] = []


class ChannelDeactivateResponse(BaseModel):
    channel_id: int
    deactivated: bool
