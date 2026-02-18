"""Data access for Site and SamplingPoints."""

from __future__ import annotations

import pyodbc


def get_all_sites(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.[Site_ID], s.[Name], s.[Description], s.[Latitude], s.[Longitude]
        FROM [dbo].[Site] s
        ORDER BY s.[Site_ID]
        """
    )
    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "latitude": row[3],
            "longitude": row[4],
        }
        for row in cursor.fetchall()
    ]


def get_site_by_id(conn: pyodbc.Connection, site_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.[Site_ID], s.[Name], s.[Description], s.[Latitude], s.[Longitude]
        FROM [dbo].[Site] s
        WHERE s.[Site_ID] = ?
        """,
        site_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "latitude": row[3],
        "longitude": row[4],
    }


def get_sampling_locations_for_site(
    conn: pyodbc.Connection, site_id: int
) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sp.[Sampling_point_ID], sp.[Name], sp.[Description],
               sp.[Site_ID], s.[Name] AS SiteName
        FROM [dbo].[SamplingPoints] sp
        LEFT JOIN [dbo].[Site] s ON s.[Site_ID] = sp.[Site_ID]
        WHERE sp.[Site_ID] = ?
        ORDER BY sp.[Sampling_point_ID]
        """,
        site_id,
    )
    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "site_id": row[3],
            "site_name": row[4],
        }
        for row in cursor.fetchall()
    ]
