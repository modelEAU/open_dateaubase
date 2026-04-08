"""Data access for Site and SamplingPoints."""

from __future__ import annotations

import pyodbc


def get_all_sites(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.[Site_ID], s.[Name], s.[SiteType_ID], st.[Name] AS SiteTypeName, s.[Description],
               s.[LatitudeWGS84], s.[LongitudeWGS84],
               s.[City], s.[Province], s.[Country]
        FROM [dbo].[Site] s
        LEFT JOIN [dbo].[SiteType] st ON s.[SiteType_ID] = st.[SiteType_ID]
        ORDER BY s.[Site_ID]
        """
    )
    return [
        {
            "id": row[0],
            "name": row[1],
            "site_type_id": row[2],
            "site_type_name": row[3],
            "description": row[4],
            "lat_wgs84": row[5],
            "long_wgs84": row[6],
            "city": row[7],
            "province": row[8],
            "country": row[9],
        }
        for row in cursor.fetchall()
    ]


def get_site_by_id(conn: pyodbc.Connection, site_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.[Site_ID], s.[Name], s.[SiteType_ID], st.[Name] AS SiteTypeName, s.[Description],
               s.[LatitudeWGS84], s.[LongitudeWGS84],
               s.[City], s.[Province], s.[Country]
        FROM [dbo].[Site] s
        LEFT JOIN [dbo].[SiteType] st ON s.[SiteType_ID] = st.[SiteType_ID]
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
        "site_type_id": row[2],
        "site_type_name": row[3],
        "description": row[4],
        "lat_wgs84": row[5],
        "long_wgs84": row[6],
        "city": row[7],
        "province": row[8],
        "country": row[9],
    }


def insert_site(conn: pyodbc.Connection, data: dict) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[Site]
            ([Name], [SiteType_ID], [Description], [LatitudeWGS84], [LongitudeWGS84],
             [City], [Province], [Country])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        data["name"],
        data.get("site_type_id"),
        data.get("description"),
        data.get("lat_wgs84"),
        data.get("long_wgs84"),
        data.get("city"),
        data.get("province"),
        data.get("country"),
    )
    cursor.execute("SELECT @@IDENTITY")
    new_id = int(cursor.fetchone()[0])
    conn.commit()
    return get_site_by_id(conn, new_id)  # type: ignore[return-value]


def update_site(conn: pyodbc.Connection, site_id: int, data: dict) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE [dbo].[Site]
        SET [Name]=?, [SiteType_ID]=?, [Description]=?,
            [LatitudeWGS84]=?, [LongitudeWGS84]=?,
            [City]=?, [Province]=?, [Country]=?
        WHERE [Site_ID]=?
        """,
        data["name"],
        data.get("site_type_id"),
        data.get("description"),
        data.get("lat_wgs84"),
        data.get("long_wgs84"),
        data.get("city"),
        data.get("province"),
        data.get("country"),
        site_id,
    )
    conn.commit()
    return get_site_by_id(conn, site_id)


def delete_site(conn: pyodbc.Connection, site_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM [dbo].[Site] WHERE [Site_ID]=?",
        site_id,
    )
    conn.commit()
    return cursor.rowcount > 0


def patch_site(conn: pyodbc.Connection, site_id: int, data: dict) -> dict | None:
    """Partial update of a site - only updates fields that are present in data."""
    # First check if site exists
    existing = get_site_by_id(conn, site_id)
    if existing is None:
        return None

    # Build dynamic UPDATE query based on provided fields
    fields = []
    values = []

    if "name" in data:
        fields.append("[Name]=?")
        values.append(data["name"])
    if "site_type_id" in data:
        fields.append("[SiteType_ID]=?")
        values.append(data.get("site_type_id"))
    if "description" in data:
        fields.append("[Description]=?")
        values.append(data.get("description"))
    if "lat_wgs84" in data:
        fields.append("[LatitudeWGS84]=?")
        values.append(data.get("lat_wgs84"))
    if "long_wgs84" in data:
        fields.append("[LongitudeWGS84]=?")
        values.append(data.get("long_wgs84"))
    if "city" in data:
        fields.append("[City]=?")
        values.append(data.get("city"))
    if "province" in data:
        fields.append("[Province]=?")
        values.append(data.get("province"))
    if "country" in data:
        fields.append("[Country]=?")
        values.append(data.get("country"))

    if not fields:
        return existing  # No fields to update

    values.append(site_id)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE [dbo].[Site] SET {', '.join(fields)} WHERE [Site_ID]=?",
        *values,
    )
    conn.commit()
    return get_site_by_id(conn, site_id)


def get_all_site_types(conn: pyodbc.Connection) -> list[dict]:
    """Return all site types for dropdowns."""
    cursor = conn.cursor()
    cursor.execute("SELECT [SiteType_ID], [Name], [Description] FROM [dbo].[SiteType] ORDER BY [Name]")
    return [{"id": row[0], "name": row[1], "description": row[2]} for row in cursor.fetchall()]


def get_sites_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return lightweight site list for dropdowns (id, name only)."""
    cursor = conn.cursor()
    cursor.execute("SELECT [Site_ID], [Name] FROM [dbo].[Site] ORDER BY [Name]")
    return [{"site_id": row[0], "name": row[1]} for row in cursor.fetchall()]


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
