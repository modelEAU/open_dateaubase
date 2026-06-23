"""Pydantic schemas for processing lineage resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProcessingStepDetailOut(BaseModel):
    processing_step_id: int
    name: str
    description: str | None
    method_name: str | None
    method_version: str | None
    operation_kind_id: int | None
    method_parameters: str | None
    executed_at: datetime | None
    executed_by_person_id: int | None


class LineageEdgeOut(BaseModel):
    """A single directed edge in the processing DAG."""

    channel_id: int
    processing_step: ProcessingStepDetailOut
    output_channel_ids: list[int]


class ProcessingStepCreate(BaseModel):
    source_channel_ids: list[int]
    output_channel_id: int
    method_name: str
    method_version: str | None = None
    operation_kind_id: int
    method_parameters: dict = {}
    executed_at: datetime | None = None
    executed_by_person_id: int | None = None


class ProcessingStepOut(BaseModel):
    processing_step_id: int


class LineageTreeOut(BaseModel):
    """Complete lineage tree rooted at a given Channel node."""

    channel_id: int
    parents: list[dict]
    children: list[dict]


class ProvenanceTraitOut(BaseModel):
    operation_kind_id: int
    name: str


class ProvenanceNodeOut(BaseModel):
    """A measurement stream in a provenance graph, fully resolved for display
    and ready to drop onto the Explorer plot (deployment-trace-shaped keys)."""

    stream_id: int
    kind: str  # "channel" | "series"
    label: str
    parameter_name: str | None = None
    unit_name: str | None = None
    value_kind_id: int | None = None
    equipment_identifier: str | None = None
    sampling_point_label: str | None = None
    campaign_name: str | None = None
    provenance_kind_name: str | None = None
    traits: list[ProvenanceTraitOut] = []
    is_derived: bool = False
    is_root: bool = False
    # carry the original id under the key the Explorer expects per kind
    channel_id: int | None = None
    analysis_series_id: int | None = None


class ProvenanceStepOut(BaseModel):
    """A processing step (edge group) in a provenance graph, with full detail."""

    processing_step_id: int
    name: str | None = None
    operation_kind_id: int | None = None
    operation_kind_name: str | None = None
    method_name: str | None = None
    method_version: str | None = None
    method_parameters: str | None = None
    executed_at: datetime | None = None
    executed_by_name: str | None = None
    input_stream_ids: list[int] = []
    output_stream_ids: list[int] = []


class ProvenanceGraphOut(BaseModel):
    """A resolved provenance graph rooted at one stream: nodes + ancestor and
    descendant processing steps."""

    root_id: int
    nodes: list[ProvenanceNodeOut]
    ancestors: list[ProvenanceStepOut]
    descendants: list[ProvenanceStepOut]




class StreamStoryOut(BaseModel):
    """Read-only Stream Story summary (see channel_repository.get_stream_story)."""

    stream_id: int
    record: dict
    location_history: list[dict]
    annotations: list[dict]
