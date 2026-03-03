"""Data access for Site and SamplingPoints."""

from __future__ import annotations

import pyodbc


def get_all_sites(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.[Site_ID], s.[Name], s.[Type], s.[Description],
               s.[LatitudeWGS84], s.[LongitudeWGS84],
               s.[City], s.[Province], s.[Country]
        FROM [dbo].[Site] s
        ORDER BY s.[Site_ID]
        """
    )
    return [
        {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "description": row[3],
            "lat_wgs84": row[4],
            "long_wgs84": row[5],
            "city": row[6],
            "province": row[7],
            "country": row[8],
        }
        for row in cursor.fetchall()
    ]


def get_site_by_id(conn: pyodbc.Connection, site_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.[Site_ID], s.[Name], s.[Type], s.[Description],
               s.[LatitudeWGS84], s.[LongitudeWGS84],
               s.[City], s.[Province], s.[Country]
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
        "type": row[2],
        "description": row[3],
        "lat_wgs84": row[4],
        "long_wgs84": row[5],
        "city": row[6],
        "province": row[7],
        "country": row[8],
    }


def get_sampling_locations_for_site(
    conn: pyodbc.Connection, site_id: int
) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sp.[SamplingPoint_ID], sp.[SamplingPoint], sp.[Description],
               sp.[LatitudeWGS84], sp.[LongitudeWGS84], sp.[Site_ID], s.[Name] AS SiteName
        FROM [dbo].[SamplingPoint] sp
        LEFT JOIN [dbo].[Site] s ON s.[Site_ID] = sp.[Site_ID]
        WHERE sp.[Site_ID] = ?
        ORDER BY sp.[SamplingPoint_ID]
        """,
        site_id,
    )
    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "latitude": row[3],
            "longitude": row[4],
            "site_id": row[5],
            "site_name": row[6],
        }
        for row in cursor.fetchall()
    ]
