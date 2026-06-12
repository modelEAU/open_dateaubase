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


