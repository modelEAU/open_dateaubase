"""Service for assembling TimeseriesOut responses.

Handles ValueType dispatch and builds the uniform response format regardless
of whether data lives in Value, ValueVector, ValueMatrix, or ValueImage.
"""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import HTTPException

from ..repositories import metadata_repository, value_repository


def get_timeseries(
    conn: pyodbc.Connection,
    metadata_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> dict:
    """Load metadata context and dispatch to the correct value table."""
    meta = metadata_repository.get_metadata_by_id(conn, metadata_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"MetaData {metadata_id} not found.")

    data = value_repository.get_values_for_metadata(
        conn,
        metadata_id,
        meta.get("value_type_id"),
        from_dt,
        to_dt,
    )

    timestamps = [row["timestamp"] for row in data if row.get("timestamp")]
    return {
        "metadata_id": metadata_id,
        "location": meta.get("location_name"),
        "site": meta.get("site_name"),
        "parameter": meta.get("parameter_name"),
        "unit": meta.get("unit_name"),
        "data_shape": meta.get("value_type_name") or "Scalar",
        "provenance": meta.get("data_provenance"),
        "processing_degree": meta.get("processing_degree"),
        "campaign": meta.get("campaign_name"),
        "from_timestamp": min(timestamps) if timestamps else None,
        "to_timestamp": max(timestamps) if timestamps else None,
        "row_count": len(data),
        "data": data,
    }


def get_timeseries_by_context(
    conn: pyodbc.Connection,
    *,
    location_id: int | None,
    parameter_id: int | None,
    processing_degree: str | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    """Find all matching MetaData entries and return timeseries for each."""
    items, _ = metadata_repository.list_metadata(
        conn,
        location_id=location_id,
        parameter_id=parameter_id,
        processing_degree=processing_degree,
        page=1,
        page_size=50,
    )
    return [
        get_timeseries(conn, item["metadata_id"], from_dt, to_dt) for item in items
    ]


def get_full_context(
    conn: pyodbc.Connection,
    metadata_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> dict:
    """Assemble full context: all processing degrees + events + lineage."""
    from open_dateaubase.lineage import get_full_lineage_tree
    from ..repositories import equipment_repository

    meta = metadata_repository.get_metadata_by_id(conn, metadata_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"MetaData {metadata_id} not found.")

    # All processing degrees for same location + parameter
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.[Metadata_ID], m.[ProcessingDegree],
               COUNT(v.[Timestamp]) AS ValueCount
        FROM [dbo].[MetaData] m
        LEFT JOIN [dbo].[Value] v
            ON v.[Metadata_ID] = m.[Metadata_ID]
           AND (? IS NULL OR v.[Timestamp] >= ?)
           AND (? IS NULL OR v.[Timestamp] <= ?)
        WHERE m.[Sampling_point_ID] = ?
          AND m.[Parameter_ID] = ?
        GROUP BY m.[Metadata_ID], m.[ProcessingDegree]
        ORDER BY m.[ProcessingDegree], m.[Metadata_ID]
        """,
        from_dt, from_dt, to_dt, to_dt,
        meta.get("location_id"),
        meta.get("parameter_id"),
    )
    processing_degrees = [
        {"metadata_id": r[0], "processing_degree": r[1], "value_count": r[2]}
        for r in cursor.fetchall()
    ]

    # Equipment events in time range
    equipment_id = meta.get("equipment_id")
    events = []
    if equipment_id:
        events = equipment_repository.get_equipment_events(conn, equipment_id, from_dt, to_dt)

    # Lineage
    lineage = get_full_lineage_tree(metadata_id, conn)

    return {
        "metadata": meta,
        "all_processing_degrees": processing_degrees,
        "equipment_events": events,
        "lineage": lineage,
    }
