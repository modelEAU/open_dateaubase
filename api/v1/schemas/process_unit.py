"""Pydantic schemas for ProcessUnit and ProcessUnitKind resources."""

from __future__ import annotations

from pydantic import BaseModel


class ProcessUnitKindIn(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None


class ProcessUnitKindOut(BaseModel):
    process_unit_kind_id: int
    name: str
    description: str | None
    category: str | None = None


class ProcessUnitIn(BaseModel):
    site_id: int
    tag: str
    name: str
    description: str | None = None
    process_unit_kind_id: int | None = None
    treatment_stage_id: int | None = None
    parent_id: int | None = None


class ProcessUnitOut(BaseModel):
    id: int
    site_id: int
    tag: str
    name: str
    description: str | None
    process_unit_kind_id: int | None
    process_unit_kind_name: str | None
    treatment_stage_id: int | None = None
    treatment_stage_name: str | None = None
    parent_id: int | None
    parent_name: str | None


class ProcessUnitPatch(BaseModel):
    tag: str | None = None
    name: str | None = None
    description: str | None = None
    process_unit_kind_id: int | None = None
    treatment_stage_id: int | None = None
    parent_id: int | None = None


class ProcessUnitLookupOut(BaseModel):
    id: int
    name: str
    tag: str
    site_id: int


class TreatmentStageOut(BaseModel):
    treatment_stage_id: int
    name: str
    description: str | None


class ProcessUnitTreeOut(BaseModel):
    id: int
    site_id: int
    tag: str
    name: str
    description: str | None
    process_unit_kind_id: int | None
    process_unit_kind_name: str | None
    treatment_stage_id: int | None = None
    treatment_stage_name: str | None = None
    children: list[ProcessUnitTreeOut] = []


ProcessUnitTreeOut.model_rebuild()
