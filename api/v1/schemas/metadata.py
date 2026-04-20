"""Pydantic schemas for MetaData resources."""

from __future__ import annotations

from pydantic import BaseModel


class SamplingLocationIn(BaseModel):
    name: str
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    process_unit_id: int | None = None


class SamplingLocationOut(BaseModel):
    id: int
    name: str
    description: str | None
    latitude: float | None
    longitude: float | None
    site_id: int | None
    site_name: str | None
    process_unit_id: int | None = None
    picture_path: str | None = None


class SiteOut(BaseModel):
    id: int
    name: str
    site_type_id: int | None
    site_type_name: str | None
    description: str | None
    lat_wgs84: float | None
    long_wgs84: float | None
    city: str | None
    province: str | None
    country: str | None


class SiteIn(BaseModel):
    name: str
    site_type_id: int | None = None
    description: str | None = None
    lat_wgs84: float | None = None
    long_wgs84: float | None = None
    city: str | None = None
    province: str | None = None
    country: str | None = None


class SitePatch(BaseModel):
    """Partial update schema for Site - all fields optional."""

    name: str | None = None
    site_type_id: int | None = None
    description: str | None = None
    lat_wgs84: float | None = None
    long_wgs84: float | None = None
    city: str | None = None
    province: str | None = None
    country: str | None = None


class SiteLookupOut(BaseModel):
    """Lightweight site info for dropdowns."""

    site_id: int
    name: str


class SiteTypeOut(BaseModel):
    """Lookup model for SiteType."""

    id: int
    name: str
    description: str | None


class SiteTypeIn(BaseModel):
    name: str
    description: str | None = None


class QualityCodeOut(BaseModel):
    quality_code_id: int
    name: str
    description: str | None
    is_usable: bool


class QualityCodeIn(BaseModel):
    name: str
    description: str | None = None
    is_usable: bool = True


class SampleTypeOut(BaseModel):
    sample_type_id: int
    name: str
    description: str | None


class SampleTypeIn(BaseModel):
    name: str
    description: str | None = None


class SampleMethodOut(BaseModel):
    sample_method_id: int
    name: str
    description: str | None


class SampleMethodIn(BaseModel):
    name: str
    description: str | None = None


class BinModeOut(BaseModel):
    bin_mode_id: int
    name: str
    description: str | None


class SignalPortTypeOut(BaseModel):
    signal_port_type_id: int
    name: str
    description: str | None


class ProcessingDegreeOut(BaseModel):
    processing_degree_id: int
    name: str


class CampaignTypeIn(BaseModel):
    name: str


class EquipmentEventTypeOut(BaseModel):
    equipment_event_type_id: int
    name: str


class EquipmentEventTypeIn(BaseModel):
    name: str


class PurposeOut(BaseModel):
    purpose_id: int
    name: str | None
    description: str | None


class PurposeIn(BaseModel):
    name: str | None = None
    description: str | None = None


class ProcedureOut(BaseModel):
    procedure_id: int
    procedure_name: str | None
    procedure_type: str | None
    description: str | None
    procedure_location: str | None


class ProcedureIn(BaseModel):
    procedure_name: str | None = None
    procedure_type: str | None = None
    description: str | None = None
    procedure_location: str | None = None


class ProjectOut(BaseModel):
    project_id: int
    name: str | None
    description: str | None


class ProjectIn(BaseModel):
    name: str | None = None
    description: str | None = None


class WatershedOut(BaseModel):
    watershed_id: int
    name: str | None
    description: str | None
    surface_area: float | None
    concentration_time: int | None
    impervious_surface: float | None


class WatershedIn(BaseModel):
    name: str | None = None
    description: str | None = None
    surface_area: float | None = None
    concentration_time: int | None = None
    impervious_surface: float | None = None


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
