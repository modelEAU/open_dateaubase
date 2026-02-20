"""Annotation endpoints.

Three router groups registered in api/v1/router.py:
  - timeseries_router  → prefix /timeseries   (GET/POST /{metadata_id}/annotations)
  - annotations_router → prefix /annotations  (GET/PUT/DELETE /{annotation_id}, /recent, /by-type/{type_name})
  - annotation_types_router → prefix /annotation-types  (GET /)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response

from api.database import get_db
from ..schemas.annotations import (
    AnnotationCreate,
    AnnotationListResponse,
    AnnotationResponse,
    AnnotationTypeListResponse,
    AnnotationUpdate,
)
from ..services import annotation_service

# ---------------------------------------------------------------------------
# Timeseries sub-resource: /timeseries/{metadata_id}/annotations
# ---------------------------------------------------------------------------

timeseries_router = APIRouter()


@timeseries_router.get(
    "/{metadata_id}/annotations",
    response_model=AnnotationListResponse,
)
def list_annotations_for_timeseries(
    metadata_id: int,
    from_dt: datetime = Query(..., alias="from", description="Start of query range (ISO 8601)"),
    to_dt: datetime = Query(..., alias="to", description="End of query range (ISO 8601)"),
    type: str | None = Query(None, description="Filter by annotation type name or ID"),
    conn=Depends(get_db),
):
    """Get all annotations overlapping [from, to] for a specific time series."""
    type_filter: str | int | None = None
    if type is not None:
        try:
            type_filter = int(type)
        except ValueError:
            type_filter = type
    return annotation_service.get_annotations_for_timeseries(
        conn, metadata_id, from_dt, to_dt, type_filter
    )


@timeseries_router.post(
    "/{metadata_id}/annotations",
    response_model=AnnotationResponse,
    status_code=201,
)
def create_annotation(
    metadata_id: int,
    body: AnnotationCreate,
    conn=Depends(get_db),
):
    """Create a new annotation on a time series."""
    return annotation_service.create_annotation(conn, metadata_id, body)


# ---------------------------------------------------------------------------
# Standalone annotation resource: /annotations/...
# ---------------------------------------------------------------------------

annotations_router = APIRouter()


@annotations_router.get("/recent", response_model=AnnotationListResponse)
def get_recent_annotations(
    limit: int = Query(20, ge=1, le=100, description="Number of annotations to return"),
    type: str | None = Query(None, description="Filter by annotation type name or ID"),
    conn=Depends(get_db),
):
    """Dashboard feed of the most recently created annotations across all series."""
    type_filter: str | int | None = None
    if type is not None:
        try:
            type_filter = int(type)
        except ValueError:
            type_filter = type
    return annotation_service.get_recent_annotations(conn, limit, type_filter)


@annotations_router.get("/by-type/{type_name}", response_model=AnnotationListResponse)
def get_annotations_by_type(
    type_name: str,
    from_dt: datetime = Query(..., alias="from", description="Start of query range (ISO 8601)"),
    to_dt: datetime = Query(..., alias="to", description="End of query range (ISO 8601)"),
    conn=Depends(get_db),
):
    """All annotations of a given type across all series in a time range."""
    return annotation_service.get_annotations_by_type(conn, type_name, from_dt, to_dt)


@annotations_router.put("/{annotation_id}", response_model=AnnotationResponse)
def update_annotation(
    annotation_id: int,
    body: AnnotationUpdate,
    conn=Depends(get_db),
):
    """Update an existing annotation (partial update — only provided fields change)."""
    return annotation_service.update_annotation(conn, annotation_id, body)


@annotations_router.delete("/{annotation_id}", status_code=204)
def delete_annotation(
    annotation_id: int,
    conn=Depends(get_db),
):
    """Hard-delete an annotation."""
    annotation_service.delete_annotation(conn, annotation_id)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Annotation types lookup: /annotation-types
# ---------------------------------------------------------------------------

annotation_types_router = APIRouter()


@annotation_types_router.get("", response_model=AnnotationTypeListResponse)
def list_annotation_types(conn=Depends(get_db)):
    """List all available annotation types (for UI dropdowns)."""
    return annotation_service.get_annotation_types(conn)
