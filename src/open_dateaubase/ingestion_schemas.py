"""Ingest request schemas shared by the API and the Streamlit app.

Lives outside ``api/`` because the app image never copies that directory
(app talks to the API over HTTP only) but does install this package. Only
the scalar lab and sensor requests are here — the vector/matrix variants
stay in ``api/`` since no client builds them.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class SampleCreateRequest(BaseModel):
    """Request to create a new sample."""

    sampling_point_id: int
    sampled_by_person_id: int | None = None
    campaign_id: int | None = None
    sample_datetime_start: datetime
    sample_datetime_end: datetime | None = None
    sample_collection_kind_id: int | None = None
    sample_kind_id: int | None = None
    sample_material_kind_id: int | None = None
    sample_equipment_id: int | None = None
    replicate: int = 1
    description: str | None = None


class LabMeasurementItem(BaseModel):
    """One measurement in a lab experiment.

    Carries both the AnalysisSeries identity (parameter / location / kinds /
    unit / name) used to find-or-create the series, and the per-measurement
    data (sample, value, lab metadata, replicate, quality). The payload value
    is routed to Value / ValueVector / ValueMatrix based on ``value_kind_id``.

    The sample is either one already on record (``sample_id``) or one this
    request creates (``sample_index``, a position in the request's ``samples``)
    — exactly one of the two.
    """

    # Series identity — used to find or create AnalysisSeries
    parameter_id: int
    sampling_point_id: int
    unit_id: int
    value_kind_id: int = 1
    series_name: str
    # Part of series identity as well as analysis provenance: two labs measuring
    # one parameter at one sampling point resolve to two series.
    laboratory_id: int | None = None

    # Measurement
    sample_id: int | None = None
    sample_index: int | None = None
    value: float | list | None
    analyst_person_id: int | None = None
    procedure_id: int | None = None
    analysis_datetime: datetime | None = None
    replicate: int = 1
    quality_code_id: int | None = None
    notes: str | None = None

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        if (self.sample_id is None) == (self.sample_index is None):
            raise ValueError("give exactly one of sample_id or sample_index")


class LabIngestRequest(BaseModel):
    """Ingest one LabExperiment session worth of lab measurements.

    Two modes:
    - New experiment (``experiment_id`` is None): ``name`` and
      ``experiment_datetime`` are required; a new ``LabExperiment`` row is
      created.
    - Existing experiment (``experiment_id`` is set): measurements are appended
      to the existing session; ``name`` / ``experiment_datetime`` /
      ``campaign_id`` / ``description`` / ``created_by_person_id`` are ignored.

    For each measurement: find-or-creates its ``AnalysisSeries``, inserts a
    ``LabAnalysis`` row, and inserts an ``Observation`` routed to the
    appropriate payload table.

    ``samples`` creates the request's samples in the same transaction as its
    measurements, so an import is written whole or not at all. Measurements
    point at them by position through ``sample_index``.
    """

    experiment_id: int | None = None
    name: str | None = None
    experiment_datetime: datetime | None = None
    campaign_id: int | None = None
    description: str | None = None
    created_by_person_id: int | None = None
    lab_panel_id: int | None = None
    samples: list[SampleCreateRequest] = []
    measurements: list[LabMeasurementItem]

    @field_validator("measurements")
    @classmethod
    def measurements_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("measurements list must not be empty")
        return v

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        if self.experiment_id is None:
            if not self.name:
                raise ValueError("name is required when experiment_id is not provided")
            if self.experiment_datetime is None:
                raise ValueError(
                    "experiment_datetime is required when experiment_id is not provided"
                )
        for m in self.measurements:
            if m.sample_index is not None and not 0 <= m.sample_index < len(self.samples):
                raise ValueError(
                    f"sample_index {m.sample_index} is outside this request's "
                    f"{len(self.samples)} sample(s)"
                )


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


class TaglessSensorIngestRequest(BaseModel):
    """Ingest raw sensor data from a direct-connect station (no SCADA tag name).

    ``signal_interface_name`` is the config-declared identity of the physical/logical
    connection point (e.g. matching a label on the DAS). It is authoritative — the
    Channel's tag is still auto-generated as ``"{equipment_name}/{parameter_name}"``
    (lowercased, trimmed) to disambiguate multiple parameters under one interface.
    """

    das_name: str
    equipment_name: str
    parameter_name: str
    unit_name: str
    signal_interface_name: str
    data_provenance_kind_id: int = 1
    strict: bool = False
    values: list[ValueItem]

    @field_validator("values")
    @classmethod
    def values_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("values list must not be empty")
        return v
