"""Pydantic schemas for ProcessUnit and ProcessUnitType resources."""

from __future__ import annotations

from pydantic import BaseModel


class ProcessUnitTypeIn(BaseModel):
    name: str
    description: str | None = None


class ProcessUnitTypeOut(BaseModel):
    id: int
    name: str
    description: str | None


class ProcessUnitIn(BaseModel):
    site_id: int
    tag: str
    name: str
    description: str | None = None
    process_unit_type_id: int | None = None
    parent_id: int | None = None


class ProcessUnitOut(BaseModel):
    id: int
    site_id: int
    tag: str
    name: str
    description: str | None
    process_unit_type_id: int | None
    process_unit_type_name: str | None
    parent_id: int | None
    parent_name: str | None


class ProcessUnitPatch(BaseModel):
    tag: str | None = None
    name: str | None = None
    description: str | None = None
    process_unit_type_id: int | None = None
    parent_id: int | None = None


class ProcessUnitLookupOut(BaseModel):
    id: int
    name: str
    tag: str
    site_id: int


class ProcessUnitTreeOut(BaseModel):
    id: int
    site_id: int
    tag: str
    name: str
    description: str | None
    process_unit_type_id: int | None
    process_unit_type_name: str | None
    children: list[ProcessUnitTreeOut] = []


ProcessUnitTreeOut.model_rebuild()
