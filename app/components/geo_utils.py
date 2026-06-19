"""Shared GeoJSON utilities for watershed boundary validation and area calc.

Consolidates the previously-duplicated ``_ALLOWED_GEOM_TYPES`` / validation
helpers from ``app/pages/site_wizard.py`` and ``app/pages/watersheds.py``,
and adds geodesic surface-area computation via ``pyproj.Geod``.

Public API:

- ``ALLOWED_GEOM_TYPES``: the set of accepted GeoJSON geometry type strings.
- ``validate_geojson(raw)`` → ``(parsed_dict | None, error_message | None)``.
- ``geojson_area_ha(geojson)`` → ``float`` (hectares, WGS-84 geodesic).
"""

from __future__ import annotations

import json
from typing import Any

from pyproj import Geod
from shapely.geometry import shape

ALLOWED_GEOM_TYPES: frozenset[str] = frozenset({"Polygon", "MultiPolygon"})

_GEOD = Geod(ellps="WGS84")


def validate_geojson(raw: str) -> tuple[dict | None, str | None]:
    """Parse and validate a GeoJSON string.

    Returns ``(parsed_dict, None)`` on success, ``(None, error_message)`` on
    failure. Accepts top-level ``Polygon``/``MultiPolygon`` geometries, plus
    ``Feature`` and ``FeatureCollection`` wrapping the same.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"

    top = data.get("type")
    if top == "FeatureCollection":
        for f in data.get("features", []):
            geom = f.get("geometry") or {}
            t = geom.get("type")
            if t not in ALLOWED_GEOM_TYPES:
                return None, f"All geometries must be Polygon or MultiPolygon; found '{t}'"
    elif top == "Feature":
        geom = data.get("geometry") or {}
        t = geom.get("type")
        if t not in ALLOWED_GEOM_TYPES:
            return None, f"Geometry must be Polygon or MultiPolygon; found '{t}'"
    elif top in ALLOWED_GEOM_TYPES:
        pass
    else:
        return (
            None,
            f"GeoJSON type must be Polygon, MultiPolygon, Feature, or FeatureCollection; found '{top}'",
        )

    return data, None


def _iter_polygon_geoms(geojson: dict) -> list[dict]:
    """Yield every Polygon/MultiPolygon geometry contained in ``geojson``."""
    top = geojson.get("type")
    if top in ALLOWED_GEOM_TYPES:
        return [geojson]
    if top == "Feature":
        geom = geojson.get("geometry") or {}
        return [geom] if geom.get("type") in ALLOWED_GEOM_TYPES else []
    if top == "FeatureCollection":
        out: list[dict] = []
        for f in geojson.get("features", []):
            geom = f.get("geometry") or {}
            if geom.get("type") in ALLOWED_GEOM_TYPES:
                out.append(geom)
        return out
    return []


def maybe_prefill_area(
    uploaded: Any,
    parsed: dict | None,
    *,
    target_key: str,
    sentinel_key: str,
) -> bool:
    """Prefill ``st.session_state[target_key]`` with the computed area in
    hectares when a new file is uploaded.

    Compares the uploaded file's identity against ``sentinel_key`` in
    session_state so the prefill only fires the first time a given file is
    seen — subsequent reruns won't clobber manual edits.

    Returns True if a prefill happened (caller should ``st.rerun()`` so the
    form picks up the new value).
    """
    import streamlit as st

    if uploaded is None or parsed is None:
        return False
    file_id = getattr(uploaded, "file_id", None) or (
        getattr(uploaded, "name", ""),
        getattr(uploaded, "size", 0),
    )
    if st.session_state.get(sentinel_key) == file_id:
        return False
    try:
        area = geojson_area_ha(parsed)
    except Exception:
        return False
    st.session_state[target_key] = round(area, 2)
    st.session_state[sentinel_key] = file_id
    return True


def geojson_bounds(geojson: dict[str, Any]) -> list[list[float]] | None:
    """Return [[south, west], [north, east]] bounds, or None if no geometry."""
    from shapely.ops import unary_union

    geoms = [shape(g) for g in _iter_polygon_geoms(geojson)]
    if not geoms:
        return None
    b = unary_union(geoms).bounds  # (minx, miny, maxx, maxy)
    return [[b[1], b[0]], [b[3], b[2]]]


def geojson_area_ha(geojson: dict[str, Any]) -> float:
    """Return the total geodesic surface area in hectares (WGS-84).

    Handles Polygon, MultiPolygon, Feature, and FeatureCollection inputs.
    Sums absolute areas across all contained polygon geometries (so a
    FeatureCollection with several polygons returns the combined area).
    Returns ``0.0`` if the input contains no valid polygon geometries.
    """
    total_m2 = 0.0
    for geom in _iter_polygon_geoms(geojson):
        shp = shape(geom)
        # geometry_area_perimeter returns (area, perimeter); sign depends on
        # ring orientation, so take the absolute value.
        area_m2, _ = _GEOD.geometry_area_perimeter(shp)
        total_m2 += abs(area_m2)
    return total_m2 / 10_000.0  # m² → ha


def normalize_geojson_for_folium(geojson: dict[str, Any]) -> dict[str, Any]:
    """Normalize a GeoJSON dict so folium renders it without errors.

    Folium's default ``setStyle`` callback accesses
    ``feature.properties.style``, which fails when a bare Feature with
    ``null`` properties is passed (e.g. no ``"style"`` key). The handler
    also assumes a FeatureCollection.

    This helper ensures the data is always a FeatureCollection whose
    features each have a ``style`` property.
    """
    top = geojson.get("type")
    if top == "FeatureCollection":
        features = geojson.get("features", [])
    elif top == "Feature":
        features = [geojson]
    elif top in ALLOWED_GEOM_TYPES:
        features = [{"type": "Feature", "properties": {}, "geometry": geojson}]
    else:
        return geojson

    normalized_features: list[dict[str, Any]] = []
    for f in features:
        props = f.get("properties")
        if props is None:
            props = {}
        normalized_features.append(
            {**f, "properties": {**props, "style": props.get("style", {})}}
        )

    return {
        "type": "FeatureCollection",
        "features": normalized_features,
    }
