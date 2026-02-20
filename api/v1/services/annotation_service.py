"""Business logic for annotation operations."""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import HTTPException

from ..repositories import annotation_repository, metadata_repository
from ..schemas.annotations import AnnotationCreate, AnnotationUpdate


def _resolve_annotation_type(conn: pyodbc.Connection, annotation_type: str | int) -> dict:
    """Resolve annotation_type (name or ID) to a full AnnotationType dict. Raises 404 if not found."""
    if isinstance(annotation_type, int):
        at = annotation_repository.get_annotation_type_by_id(conn, annotation_type)
    else:
        at = annotation_repository.get_annotation_type_by_name(conn, annotation_type)

    if at is None:
        raise HTTPException(
            status_code=404,
            detail=f"AnnotationType '{annotation_type}' not found.",
        )
    return at


def _build_annotation_response(row: dict) -> dict:
    """Convert a flat annotation repository row into the nested response shape."""
    author = None
    if row.get("author_person_id") is not None:
        author = {
            "person_id": row["author_person_id"],
            "name": row.get("author_name") or "",
        }
    return {
        "annotation_id": row["annotation_id"],
        "metadata_id": row["metadata_id"],
        "type": {
            "id": row["annotation_type_id"],
            "name": row["annotation_type_name"],
            "color": row.get("color"),
        },
        "start_time": row["start_time"],
        "end_time": row.get("end_time"),
        "title": row.get("title"),
        "comment": row.get("comment"),
        "author": author,
        "campaign_id": row.get("campaign_id"),
        "campaign_name": row.get("campaign_name"),
        "equipment_event_id": row.get("equipment_event_id"),
        "created_at": row["created_at"],
        "modified_at": row.get("modified_at"),
    }


def get_annotation_types(conn: pyodbc.Connection) -> dict:
    rows = annotation_repository.get_annotation_types(conn)
    return {
        "annotation_types": [
            {
                "id": r["annotation_type_id"],
                "name": r["annotation_type_name"],
                "description": r.get("description"),
                "color": r.get("color"),
            }
            for r in rows
        ]
    }


def get_annotations_for_timeseries(
    conn: pyodbc.Connection,
    metadata_id: int,
    from_dt: datetime,
    to_dt: datetime,
    type_filter: str | int | None = None,
) -> dict:
    meta = metadata_repository.get_metadata_by_id(conn, metadata_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"MetaData {metadata_id} not found.")

    annotation_type_id: int | None = None
    if type_filter is not None:
        at = _resolve_annotation_type(conn, type_filter)
        annotation_type_id = at["annotation_type_id"]

    rows = annotation_repository.get_annotations_for_timeseries(
        conn, metadata_id, from_dt, to_dt, annotation_type_id
    )
    return {
        "metadata_id": metadata_id,
        "query_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
        "annotations": [_build_annotation_response(r) for r in rows],
        "count": len(rows),
    }


def create_annotation(
    conn: pyodbc.Connection,
    metadata_id: int,
    data: AnnotationCreate,
) -> dict:
    meta = metadata_repository.get_metadata_by_id(conn, metadata_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"MetaData {metadata_id} not found.")

    at = _resolve_annotation_type(conn, data.annotation_type)

    created = annotation_repository.create_annotation(
        conn,
        metadata_id=metadata_id,
        annotation_type_id=at["annotation_type_id"],
        start_time=data.start_time,
        end_time=data.end_time,
        author_person_id=data.author_person_id,
        campaign_id=data.campaign_id,
        equipment_event_id=data.equipment_event_id,
        title=data.title,
        comment=data.comment,
    )

    return {
        "annotation_id": created["annotation_id"],
        "metadata_id": metadata_id,
        "type": {
            "id": at["annotation_type_id"],
            "name": at["annotation_type_name"],
            "color": at.get("color"),
        },
        "start_time": data.start_time,
        "end_time": data.end_time,
        "title": data.title,
        "created_at": created["created_at"],
    }


def update_annotation(
    conn: pyodbc.Connection,
    annotation_id: int,
    data: AnnotationUpdate,
) -> dict:
    existing = annotation_repository.get_annotation_by_id(conn, annotation_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Annotation {annotation_id} not found.")

    annotation_type_id: int | None = None
    if data.annotation_type is not None:
        at = _resolve_annotation_type(conn, data.annotation_type)
        annotation_type_id = at["annotation_type_id"]

    updated = annotation_repository.update_annotation(
        conn,
        annotation_id,
        annotation_type_id=annotation_type_id,
        start_time=data.start_time,
        end_time=data.end_time,
        title=data.title,
        comment=data.comment,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Annotation {annotation_id} not found after update.")

    return _build_annotation_response(updated)


def delete_annotation(conn: pyodbc.Connection, annotation_id: int) -> None:
    existing = annotation_repository.get_annotation_by_id(conn, annotation_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Annotation {annotation_id} not found.")
    annotation_repository.delete_annotation(conn, annotation_id)


def get_recent_annotations(
    conn: pyodbc.Connection,
    limit: int = 20,
    type_filter: str | int | None = None,
) -> dict:
    annotation_type_id: int | None = None
    if type_filter is not None:
        at = _resolve_annotation_type(conn, type_filter)
        annotation_type_id = at["annotation_type_id"]

    rows = annotation_repository.get_recent_annotations(conn, limit, annotation_type_id)
    annotations = []
    for r in rows:
        item = _build_annotation_response(r)
        item["location"] = r.get("location_name")
        item["variable"] = r.get("parameter_name")
        annotations.append(item)

    return {"annotations": annotations, "count": len(annotations)}


def get_annotations_by_type(
    conn: pyodbc.Connection,
    type_name: str,
    from_dt: datetime,
    to_dt: datetime,
) -> dict:
    at = annotation_repository.get_annotation_type_by_name(conn, type_name)
    if at is None:
        raise HTTPException(status_code=404, detail=f"AnnotationType '{type_name}' not found.")

    rows = annotation_repository.get_annotations_by_type(
        conn, at["annotation_type_id"], from_dt, to_dt
    )
    annotations = []
    for r in rows:
        item = _build_annotation_response(r)
        item["location"] = r.get("location_name")
        item["variable"] = r.get("parameter_name")
        annotations.append(item)

    return {"annotations": annotations, "count": len(annotations)}
