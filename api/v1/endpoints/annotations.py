"""Annotation endpoints.

Router groups registered in api/v1/router.py:
  - timeseries_router  → prefix /timeseries   (GET/POST /{channel_id}/annotations)
  - analysis_series_annotations_router → prefix /analysis-series  (GET/POST /{series_id}/annotations)
  - annotations_router → prefix /annotations  (GET/PUT/DELETE /{annotation_id}, /recent, /by-type/{type_name})
  - annotation_kinds_router → prefix /annotation-kinds  (GET /)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from api.database import get_db
from ..repositories import annotation_repository
from ..schemas.annotations import (
    AnnotationCreate,
    AnnotationListResponse,
    AnnotationResponse,
    AnnotationKindListResponse,
    AnnotationKindResponse,
    AnnotationUpdate,
)
from ..services import annotation_service


class AnnotationKindIn(BaseModel):
    name: str
    description: str | None = None
    color: str | None = None

# ---------------------------------------------------------------------------
# Timeseries sub-resource: /timeseries/{channel_id}/annotations
# ---------------------------------------------------------------------------

timeseries_router = APIRouter()


@timeseries_router.get(
    "/{channel_id}/annotations",
    response_model=AnnotationListResponse,
)
def list_annotations_for_timeseries(
    channel_id: int,
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
        conn, channel_id, from_dt, to_dt, type_filter
    )


@timeseries_router.post(
    "/{channel_id}/annotations",
    response_model=AnnotationResponse,
    status_code=201,
)
def create_annotation(
    channel_id: int,
    body: AnnotationCreate,
    conn=Depends(get_db),
):
    """Create a new annotation on a time series."""
    return annotation_service.create_annotation(conn, channel_id, body)


# ---------------------------------------------------------------------------
# AnalysisSeries sub-resource: /analysis-series/{series_id}/annotations (lab arm)
# ---------------------------------------------------------------------------

analysis_series_annotations_router = APIRouter()


@analysis_series_annotations_router.get(
    "/{series_id}/annotations",
    response_model=AnnotationListResponse,
)
def list_annotations_for_series(
    series_id: int,
    from_dt: datetime = Query(..., alias="from", description="Start of query range (ISO 8601)"),
    to_dt: datetime = Query(..., alias="to", description="End of query range (ISO 8601)"),
    type: str | None = Query(None, description="Filter by annotation type name or ID"),
    conn=Depends(get_db),
):
    """Get all annotations overlapping [from, to] for a specific lab AnalysisSeries."""
    type_filter: str | int | None = None
    if type is not None:
        try:
            type_filter = int(type)
        except ValueError:
            type_filter = type
    return annotation_service.get_annotations_for_series(
        conn, series_id, from_dt, to_dt, type_filter
    )


@analysis_series_annotations_router.post(
    "/{series_id}/annotations",
    response_model=AnnotationResponse,
    status_code=201,
)
def create_annotation_for_series(
    series_id: int,
    body: AnnotationCreate,
    conn=Depends(get_db),
):
    """Create a new annotation on a lab AnalysisSeries."""
    return annotation_service.create_annotation_for_series(conn, series_id, body)


# ---------------------------------------------------------------------------
# Standalone annotation resource: /annotations/...
# ---------------------------------------------------------------------------

annotations_router = APIRouter()


@annotations_router.get("", response_model=AnnotationListResponse)
def list_annotations(
    channel_id: int | None = Query(None, description="Filter by channel ID"),
    conn=Depends(get_db),
):
    """List all annotations, optionally filtered by channel."""
    return annotation_service.list_annotations(conn, channel_id)


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
def get_annotations_by_kind(
    type_name: str,
    from_dt: datetime = Query(..., alias="from", description="Start of query range (ISO 8601)"),
    to_dt: datetime = Query(..., alias="to", description="End of query range (ISO 8601)"),
    conn=Depends(get_db),
):
    """All annotations of a given type across all series in a time range."""
    return annotation_service.get_annotations_by_kind(conn, type_name, from_dt, to_dt)


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
# Annotation types lookup: /annotation-kinds
# ---------------------------------------------------------------------------

annotation_kinds_router = APIRouter()


@annotation_kinds_router.get("", response_model=AnnotationKindListResponse)
def list_annotation_kinds(conn=Depends(get_db)):
    """List all available annotation types (for UI dropdowns)."""
    return annotation_service.get_annotation_kinds(conn)


@annotation_kinds_router.post("", response_model=AnnotationKindResponse, status_code=201)
def create_annotation_kind(body: AnnotationKindIn, conn=Depends(get_db)):
    """Create a new AnnotationKind."""
    row = annotation_repository.insert_annotation_kind(
        conn, body.name, body.description, body.color
    )
    return AnnotationKindResponse(
        id=row["annotation_kind_id"],
        name=row["annotation_type_name"],
        description=row.get("description"),
        color=row.get("color"),
    )


@annotation_kinds_router.put("/{annotation_kind_id}", response_model=AnnotationKindResponse)
def update_annotation_kind(
    annotation_kind_id: int, body: AnnotationKindIn, conn=Depends(get_db)
):
    """Update an existing AnnotationKind."""
    row = annotation_repository.update_annotation_kind(
        conn, annotation_kind_id, body.name, body.description, body.color
    )
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"AnnotationKind {annotation_kind_id} not found."
        )
    return AnnotationKindResponse(
        id=row["annotation_kind_id"],
        name=row["annotation_type_name"],
        description=row.get("description"),
        color=row.get("color"),
    )


@annotation_kinds_router.delete("/{annotation_kind_id}", status_code=204)
def delete_annotation_kind(annotation_kind_id: int, conn=Depends(get_db)):
    """Delete an AnnotationKind by ID."""
    deleted = annotation_repository.delete_annotation_kind(conn, annotation_kind_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"AnnotationKind {annotation_kind_id} not found."
        )
    return Response(status_code=204)
