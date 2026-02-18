"""Data access for ingestion operations."""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import HTTPException


class RouteNotFound(Exception):
    pass


class RouteAmbiguous(Exception):
    pass


def resolve_ingestion_route(
    conn: pyodbc.Connection,
    equipment_id: int,
    parameter_id: int,
    data_provenance_id: int,
    processing_degree: str,
    timestamp: datetime,
) -> int:
    """Find the active IngestionRoute and return its Metadata_ID.

    Raises:
        RouteNotFound: No active route for this combination.
        RouteAmbiguous: Multiple active routes found.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [Metadata_ID], [IngestionRoute_ID]
        FROM [dbo].[IngestionRoute]
        WHERE [Equipment_ID] = ?
          AND [Parameter_ID] = ?
          AND [DataProvenance_ID] = ?
          AND [ProcessingDegree] = ?
          AND [ValidFrom] <= ?
          AND ([ValidTo] IS NULL OR [ValidTo] > ?)
        """,
        equipment_id,
        parameter_id,
        data_provenance_id,
        processing_degree,
        timestamp,
        timestamp,
    )
    rows = cursor.fetchall()
    if not rows:
        # Get hint: list any routes for this equipment+parameter
        cursor.execute(
            """
            SELECT [IngestionRoute_ID], [DataProvenance_ID], [ProcessingDegree],
                   [ValidFrom], [ValidTo]
            FROM [dbo].[IngestionRoute]
            WHERE [Equipment_ID] = ? AND [Parameter_ID] = ?
            """,
            equipment_id,
            parameter_id,
        )
        existing = cursor.fetchall()
        hint = (
            f" Active routes: {existing}" if existing else " No routes exist for this equipment+parameter."
        )
        raise RouteNotFound(
            f"No active IngestionRoute for Equipment={equipment_id}, Parameter={parameter_id}, "
            f"DataProvenance={data_provenance_id}, ProcessingDegree='{processing_degree}', "
            f"timestamp={timestamp}.{hint}"
        )
    if len(rows) > 1:
        route_ids = [r[1] for r in rows]
        raise RouteAmbiguous(
            f"Multiple active IngestionRoutes for Equipment={equipment_id}, "
            f"Parameter={parameter_id}: route IDs {route_ids}. "
            "Please close overlapping routes."
        )
    return rows[0][0]


def find_or_create_metadata_for_lab(
    conn: pyodbc.Connection,
    *,
    parameter_id: int,
    unit_id: int,
    sampling_point_id: int,
    laboratory_id: int | None,
    analyst_person_id: int | None,
    campaign_id: int | None,
    sample_id: int | None,
) -> int:
    """Find an existing lab MetaData row or create a new one. Returns Metadata_ID."""
    cursor = conn.cursor()

    where_parts = [
        "m.[Parameter_ID] = ?",
        "m.[Unit_ID] = ?",
        "m.[Sampling_point_ID] = ?",
        "m.[DataProvenance_ID] = 2",  # Laboratory
    ]
    params: list = [parameter_id, unit_id, sampling_point_id]

    if laboratory_id is not None:
        where_parts.append("m.[Laboratory_ID] = ?")
        params.append(laboratory_id)
    if analyst_person_id is not None:
        where_parts.append("m.[AnalystPerson_ID] = ?")
        params.append(analyst_person_id)
    if campaign_id is not None:
        where_parts.append("m.[Campaign_ID] = ?")
        params.append(campaign_id)
    if sample_id is not None:
        where_parts.append("m.[Sample_ID] = ?")
        params.append(sample_id)

    cursor.execute(
        f"SELECT TOP 1 [Metadata_ID] FROM [dbo].[MetaData] m WHERE {' AND '.join(where_parts)}",
        *params,
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    # Create new MetaData row
    cursor.execute(
        """
        INSERT INTO [dbo].[MetaData]
            ([Parameter_ID], [Unit_ID], [Sampling_point_ID], [DataProvenance_ID],
             [Laboratory_ID], [AnalystPerson_ID], [Campaign_ID], [Sample_ID],
             [ProcessingDegree])
        OUTPUT INSERTED.[Metadata_ID]
        VALUES (?, ?, ?, 2, ?, ?, ?, ?, 'Raw')
        """,
        parameter_id,
        unit_id,
        sampling_point_id,
        laboratory_id,
        analyst_person_id,
        campaign_id,
        sample_id,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def create_processed_metadata(
    conn: pyodbc.Connection,
    *,
    source_metadata_id: int,
    processing_degree: str,
) -> int:
    """Create a MetaData row for processed output, cloning context from the source."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[MetaData]
            ([Parameter_ID], [Unit_ID], [Sampling_point_ID], [Equipment_ID],
             [DataProvenance_ID], [Campaign_ID], [ValueType_ID], [ProcessingDegree])
        OUTPUT INSERTED.[Metadata_ID]
        SELECT [Parameter_ID], [Unit_ID], [Sampling_point_ID], [Equipment_ID],
               [DataProvenance_ID], [Campaign_ID], [ValueType_ID], ?
        FROM [dbo].[MetaData]
        WHERE [Metadata_ID] = ?
        """,
        processing_degree,
        source_metadata_id,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id
