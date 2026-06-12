"""Pydantic schemas for MetaData resources."""

from __future__ import annotations

import json

from pydantic import BaseModel, field_validator

_ALLOWED_GEOJSON_TYPES = {"Polygon", "MultiPolygon"}


def _validate_geojson_polygon(v: str | None) -> str | None:
    if v is None:
        return v
    try:
        data = json.loads(v)
    except json.JSONDecodeError as exc:
        raise ValueError("GeometryGeoJSON must be valid JSON") from exc

    geom_type = data.get("type")
    if geom_type == "FeatureCollection":
        for feature in data.get("features", []):
            geom = feature.get("geometry") or {}
            t = geom.get("type")
            if t not in _ALLOWED_GEOJSON_TYPES:
                raise ValueError(
                    f"All geometries must be Polygon or MultiPolygon; found '{t}'"
                )
    elif geom_type == "Feature":
        geom = data.get("geometry") or {}
        t = geom.get("type")
        if t not in _ALLOWED_GEOJSON_TYPES:
            raise ValueError(
                f"Geometry must be Polygon or MultiPolygon; found '{t}'"
            )
    elif geom_type in _ALLOWED_GEOJSON_TYPES:
        pass
    else:
        raise ValueError(
            f"GeoJSON type must be Polygon, MultiPolygon, Feature, or FeatureCollection; found '{geom_type}'"
        )
    return v


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
    site_kind_id: int | None
    site_kind_name: str | None
    description: str | None
    lat_wgs84: float | None
    long_wgs84: float | None
    city: str | None
    province: str | None
    country: str | None


class SiteIn(BaseModel):
    name: str
    site_kind_id: int | None = None
    watershed_id: int | None = None
    description: str | None = None
    lat_wgs84: float | None = None
    long_wgs84: float | None = None
    city: str | None = None
    province: str | None = None
    country: str | None = None


class SitePatch(BaseModel):
    """Partial update schema for Site - all fields optional."""

    name: str | None = None
    site_kind_id: int | None = None
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


class SiteKindOut(BaseModel):
    """Lookup model for SiteKind."""

    id: int
    name: str
    description: str | None


class SiteKindIn(BaseModel):
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


class SampleKindOut(BaseModel):
    sample_kind_id: int
    name: str
    description: str | None


class SampleKindIn(BaseModel):
    name: str
    description: str | None = None


class SampleCollectionKindOut(BaseModel):
    sample_collection_kind_id: int
    name: str
    description: str | None


class SampleCollectionKindIn(BaseModel):
    name: str
    description: str | None = None


class BinKindOut(BaseModel):
    bin_kind_id: int
    name: str
    description: str | None


class OperationKindOut(BaseModel):
    operation_kind_id: int
    name: str
    description: str | None


class DasKindOut(BaseModel):
    das_kind_id: int
    name: str
    description: str | None


class ControllerKindOut(BaseModel):
    controller_kind_id: int
    name: str
    description: str | None


class CampaignKindOut(BaseModel):
    campaign_kind_id: int
    name: str
    description: str | None


class CampaignKindIn(BaseModel):
    name: str
    description: str | None = None


class EquipmentEventKindOut(BaseModel):
    equipment_event_kind_id: int
    name: str
    description: str | None


class EquipmentEventKindIn(BaseModel):
    name: str
    description: str | None = None


class ChannelKindOut(BaseModel):
    channel_kind_id: int
    name: str
    description: str | None


class ProcessUnitKindOut(BaseModel):
    process_unit_kind_id: int
    name: str
    description: str | None


class ProcessUnitKindIn(BaseModel):
    name: str
    description: str | None = None


class ProcedureKindOut(BaseModel):
    procedure_kind_id: int
    name: str
    description: str | None


class ProcedureKindIn(BaseModel):
    name: str
    description: str | None = None


class ProcedureOut(BaseModel):
    procedure_id: int
    procedure_name: str | None
    procedure_kind_id: int | None
    description: str | None
    procedure_location: str | None


class ProcedureIn(BaseModel):
    procedure_name: str | None = None
    procedure_kind_id: int | None = None
    description: str | None = None
    procedure_location: str | None = None


class LandUseIn(BaseModel):
    commercial: float | None = None
    green_spaces: float | None = None
    industrial: float | None = None
    institutional: float | None = None
    residential: float | None = None
    agricultural: float | None = None
    recreational: float | None = None


class LandUseOut(BaseModel):
    watershed_id: int
    commercial: float | None
    green_spaces: float | None
    industrial: float | None
    institutional: float | None
    residential: float | None
    agricultural: float | None
    recreational: float | None


class WatershedOut(BaseModel):
    watershed_id: int
    name: str | None
    description: str | None
    surface_area: float | None
    concentration_time: int | None
    impervious_surface: float | None
    parent_watershed_id: int | None
    geometry_geojson: str | None


class WatershedIn(BaseModel):
    name: str | None = None
    description: str | None = None
    surface_area: float | None = None
    concentration_time: int | None = None
    impervious_surface: float | None = None
    parent_watershed_id: int | None = None
    geometry_geojson: str | None = None

    @field_validator("geometry_geojson")
    @classmethod
    def validate_geojson(cls, v: str | None) -> str | None:
        return _validate_geojson_polygon(v)


class MetadataOut(BaseModel):
    """Full metadata record with all resolved foreign keys."""

    metadata_id: int
    parameter_id: int | None
    parameter_name: str | None
    unit_id: int | None
    unit_name: str | None
    equipment_id: int | None
    equipment_identifier: str | None
    data_provenance_kind_id: int | None
    data_provenance: str | None
    processing_degree: str | None
    laboratory_id: int | None
    laboratory_name: str | None
    analyst_id: int | None
    analyst_name: str | None
    value_kind_id: int | None
    value_kind_name: str | None
