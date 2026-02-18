"""Pydantic schemas for processing lineage resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProcessingStepOut(BaseModel):
    processing_step_id: int
    name: str
    description: str | None
    method_name: str | None
    method_version: str | None
    processing_type: str | None
    parameters: str | None
    executed_at: datetime | None
    executed_by_person_id: int | None


class LineageEdgeOut(BaseModel):
    """A single directed edge in the processing DAG."""

    metadata_id: int
    processing_step: ProcessingStepOut
    role: str
    output_metadata_ids: list[int]


class LineageTreeOut(BaseModel):
    """Complete lineage tree rooted at a given MetaData node."""

    metadata_id: int
    parents: list[dict]
    children: list[dict]


class ProcessingDegreeSummaryOut(BaseModel):
    """Summary of one version of a time series (one ProcessingDegree)."""

    metadata_id: int
    processing_degree: str | None
    value_count: int
