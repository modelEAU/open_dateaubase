"""Service for assembling TimeseriesOut responses.

Handles ValueKind dispatch and builds the uniform response format regardless
of whether data lives in Value, ValueVector, ValueMatrix, or ValueImage.
"""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import HTTPException

from ..repositories import channel_repository, value_repository, ingestion_repository

_VALUE_KIND_NAMES = {1: "Scalar", 2: "Vector", 3: "Matrix", 4: "Image"}


def get_analysis_series_timeseries(
    conn: pyodbc.Connection,
    analysis_series_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> dict:
    """Load lab AnalysisSeries context and dispatch to the correct value table.

    Timestamps are sample collection times (ADR 0002), so this reuses the same
    payload reads as the sensor path via the analysis-series source filter."""
    series = ingestion_repository.get_analysis_series_by_id(conn, analysis_series_id)
    if series is None:
        raise HTTPException(
            status_code=404,
            detail=f"AnalysisSeries {analysis_series_id} not found.",
        )

    data = value_repository.get_analysis_series_values_for_metadata(
        conn,
        analysis_series_id,
        series.get("value_kind_id"),
        from_dt,
        to_dt,
    )

    timestamps = [row["timestamp"] for row in data if row.get("timestamp")]
    return {
        "analysis_series_id": analysis_series_id,
        "name": series.get("name"),
        "parameter": series.get("parameter_name"),
        "unit": series.get("unit_name"),
        "sampling_point": series.get("sampling_point_label"),
        "data_shape": _VALUE_KIND_NAMES.get(series.get("value_kind_id") or 1, "Scalar"),
        "from_timestamp": min(timestamps) if timestamps else None,
        "to_timestamp": max(timestamps) if timestamps else None,
        "row_count": len(data),
        "data": data,
    }


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
        # ADR 0005: the retired ProcessingKind scalar is replaced by the
        # accumulated ChannelTrait set (OperationKind names), keyed on Stream_ID.
        "traits": value_repository.get_channel_trait_names(conn, channel_id),
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
        SELECT c.[Stream_ID], c.[ProducedByStep_ID],
               COUNT(v.[Timestamp]) AS ValueCount
        FROM [dbo].[Channel] c
        LEFT JOIN [dbo].[Value] v
            ON v.[Channel_ID] = c.[Stream_ID]
           AND (? IS NULL OR v.[Timestamp] >= ?)
           AND (? IS NULL OR v.[Timestamp] <= ?)
        WHERE c.[Equipment_ID] = ?
          AND c.[Parameter_ID] = ?
        GROUP BY c.[Stream_ID], c.[ProducedByStep_ID]
        ORDER BY c.[ProducedByStep_ID], c.[Stream_ID]
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
