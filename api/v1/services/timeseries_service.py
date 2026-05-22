"""Service for assembling TimeseriesOut responses.

Handles ValueKind dispatch and builds the uniform response format regardless
of whether data lives in Value, ValueVector, ValueMatrix, or ValueImage.
"""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import HTTPException

from ..repositories import channel_repository, value_repository


def get_timeseries(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
    operational_only: bool = False,
) -> dict:
    """Load channel context and dispatch to the correct value table."""
    channel = channel_repository.get_channel_by_id(conn, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found.")

    data = value_repository.get_values_for_metadata(
        conn,
        channel_id,
        channel.get("value_kind_id"),
        from_dt,
        to_dt,
        operational_only=operational_only,
    )

    timestamps = [row["timestamp"] for row in data if row.get("timestamp")]
    return {
        "channel_id": channel_id,
        "location": None,
        "site": None,
        "parameter": channel.get("parameter_name"),
        "unit": channel.get("unit_name"),
        "data_shape": channel.get("value_kind_name") or "Scalar",
        "provenance": channel.get("data_provenance_kind_name"),
        "processing_degree": channel.get("processing_kind_name"),
        "campaign": None,
        "from_timestamp": min(timestamps) if timestamps else None,
        "to_timestamp": max(timestamps) if timestamps else None,
        "row_count": len(data),
        "data": data,
    }


def get_timeseries_by_context(
    conn: pyodbc.Connection,
    *,
    equipment_id: int | None,
    parameter_id: int | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    """Find all matching Channel entries and return timeseries for each."""
    items, _ = channel_repository.list_channels(
        conn,
        equipment_id=equipment_id,
        parameter_id=parameter_id,
        page=1,
        page_size=50,
    )
    return [get_timeseries(conn, item["channel_id"], from_dt, to_dt) for item in items]


def get_full_context(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> dict:
    """Assemble full context: all processing degrees + events + lineage."""
    from open_dateaubase.lineage import get_full_lineage_tree
    from ..repositories import equipment_repository

    channel = channel_repository.get_channel_by_id(conn, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found.")

    # All processing variants for same equipment + parameter
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.[Channel_ID], c.[ProducedByStep_ID],
               COUNT(v.[Timestamp]) AS ValueCount
        FROM [dbo].[Channel] c
        LEFT JOIN [dbo].[Value] v
            ON v.[Channel_ID] = c.[Channel_ID]
           AND (? IS NULL OR v.[Timestamp] >= ?)
           AND (? IS NULL OR v.[Timestamp] <= ?)
        WHERE c.[Equipment_ID] = ?
          AND c.[Parameter_ID] = ?
        GROUP BY c.[Channel_ID], c.[ProducedByStep_ID]
        ORDER BY c.[ProducedByStep_ID], c.[Channel_ID]
        """,
        from_dt,
        from_dt,
        to_dt,
        to_dt,
        channel.get("equipment_id"),
        channel.get("parameter_id"),
    )
    processing_degrees = [
        {"channel_id": r[0], "produced_by_step_id": r[1], "value_count": r[2]}
        for r in cursor.fetchall()
    ]

    # Equipment events in time range
    equipment_id = channel.get("equipment_id")
    events = []
    if equipment_id:
        events = equipment_repository.get_equipment_events(
            conn, equipment_id, from_dt, to_dt
        )

    # Lineage
    lineage = get_full_lineage_tree(channel_id, conn)

    return {
        "channel": channel,
        "all_processing_degrees": processing_degrees,
        "equipment_events": events,
        "lineage": lineage,
    }
