"""Pydantic schemas for MetaData resources."""

from __future__ import annotations

from pydantic import BaseModel


class SamplingLocationOut(BaseModel):
    id: int
    name: str
    site_id: int | None
    site_name: str | None


class SiteOut(BaseModel):
    id: int
    name: str
    description: str | None
    latitude: float | None
    longitude: float | None


class MetadataOut(BaseModel):
    """Full metadata record with all resolved foreign keys."""

    metadata_id: int
    parameter_id: int | None
    parameter_name: str | None
    unit_id: int | None
    unit_name: str | None
    equipment_id: int | None
    equipment_identifier: str | None
    data_provenance_id: int | None
    data_provenance: str | None
    processing_degree: str | None
    laboratory_id: int | None
    laboratory_name: str | None
    analyst_id: int | None
    analyst_name: str | None
    value_type_id: int | None
    value_type_name: str | None
