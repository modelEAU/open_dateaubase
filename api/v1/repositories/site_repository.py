"""Data access for Site and SamplingPoints."""

from __future__ import annotations

import pyodbc


def get_all_sites(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.[Site_ID], s.[Name], s.[SiteKind_ID], st.[Name] AS SiteKindName, s.[Description],
               s.[LatitudeWGS84], s.[LongitudeWGS84],
               s.[City], s.[Province], s.[Country]
        FROM [dbo].[Site] s
        LEFT JOIN [dbo].[SiteKind] st ON s.[SiteKind_ID] = st.[SiteKind_ID]
        ORDER BY s.[Site_ID]
        """
    )
    return [
        {
            "id": row[0],
            "name": row[1],
            "site_kind_id": row[2],
            "site_kind_name": row[3],
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
        SELECT s.[Site_ID], s.[Name], s.[SiteKind_ID], st.[Name] AS SiteKindName, s.[Description],
               s.[LatitudeWGS84], s.[LongitudeWGS84],
               s.[City], s.[Province], s.[Country]
        FROM [dbo].[Site] s
        LEFT JOIN [dbo].[SiteKind] st ON s.[SiteKind_ID] = st.[SiteKind_ID]
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
        "site_kind_id": row[2],
        "site_kind_name": row[3],
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
            ([Name], [SiteKind_ID], [Watershed_ID], [Description], [LatitudeWGS84], [LongitudeWGS84],
             [City], [Province], [Country])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        data["name"],
        data.get("site_kind_id"),
        data.get("watershed_id"),
        data.get("description"),
        data.get("lat_wgs84"),
        data.get("long_wgs84"),
        data.get("city"),
        data.get("province"),
        data.get("country"),
    )
    cursor.execute("SELECT @@IDENTITY")
    _row = cursor.fetchone()
    assert _row is not None
    new_id = int(_row[0])
    conn.commit()
    return get_site_by_id(conn, new_id)  # type: ignore[return-value]


def update_site(conn: pyodbc.Connection, site_id: int, data: dict) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE [dbo].[Site]
        SET [Name]=?, [SiteKind_ID]=?, [Description]=?,
            [LatitudeWGS84]=?, [LongitudeWGS84]=?,
            [City]=?, [Province]=?, [Country]=?
        WHERE [Site_ID]=?
        """,
        data["name"],
        data.get("site_kind_id"),
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
    if "site_kind_id" in data:
        fields.append("[SiteKind_ID]=?")
        values.append(data.get("site_kind_id"))
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


def get_all_site_kinds(conn: pyodbc.Connection) -> list[dict]:
    """Return all site kinds for dropdowns."""
    cursor = conn.cursor()
    cursor.execute("SELECT [SiteKind_ID], [Name], [Description] FROM [dbo].[SiteKind] ORDER BY [Name]")
    return [{"id": row[0], "name": row[1], "description": row[2]} for row in cursor.fetchall()]


def get_site_kind_by_id(conn: pyodbc.Connection, site_kind_id: int) -> dict | None:
    """Return a single SiteKind by ID."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SiteKind_ID], [Name], [Description] FROM [dbo].[SiteKind] WHERE [SiteKind_ID]=?",
        site_kind_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "description": row[2]}


def insert_site_kind(conn: pyodbc.Connection, name: str, description: str | None) -> dict:
    """Insert a new SiteKind row and return it."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[SiteKind] ([Name], [Description])"
            " OUTPUT inserted.[SiteKind_ID], inserted.[Name], inserted.[Description]"
            " VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        assert row is not None
        conn.commit()
        return {"id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def update_site_kind(
    conn: pyodbc.Connection, site_kind_id: int, name: str, description: str | None
) -> dict | None:
    """Update a SiteKind row and return it, or None if not found."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[SiteKind]"
            " SET [Name]=?, [Description]=?"
            " OUTPUT inserted.[SiteKind_ID], inserted.[Name], inserted.[Description]"
            " WHERE [SiteKind_ID]=?",
            name,
            description,
            site_kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def delete_site_kind(conn: pyodbc.Connection, site_kind_id: int) -> bool:
    """Delete a SiteKind row. Returns True if a row was deleted."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[SiteKind] WHERE [SiteKind_ID]=?",
            site_kind_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


def get_sites_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return lightweight site list for dropdowns (id, name only)."""
    cursor = conn.cursor()
    cursor.execute("SELECT [Site_ID], [Name] FROM [dbo].[Site] ORDER BY [Name]")
    return [{"site_id": row[0], "name": row[1]} for row in cursor.fetchall()]


def insert_sampling_location(
    conn: pyodbc.Connection, site_id: int, data: dict
) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [Description],
                                           [LatitudeWGS84], [LongitudeWGS84], [ProcessUnit_ID])
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        site_id,
        data["name"],
        data.get("description"),
        data.get("latitude"),
        data.get("longitude"),
        data.get("process_unit_id"),
    )
    cursor.execute("SELECT @@IDENTITY")
    _row = cursor.fetchone()
    assert _row is not None
    new_id = int(_row[0])
    conn.commit()
    rows = get_sampling_locations_for_site(conn, site_id)
    match = next((r for r in rows if r["id"] == new_id), None)
    return match or {
        "id": new_id,
        "name": data["name"],
        "description": data.get("description"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "site_id": site_id,
        "site_name": None,
        "process_unit_id": data.get("process_unit_id"),
    }


def get_sampling_locations_for_site(
    conn: pyodbc.Connection, site_id: int
) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sp.[SamplingPoint_ID], sp.[SamplingPoint], sp.[Description],
               sp.[LatitudeWGS84], sp.[LongitudeWGS84], sp.[Site_ID], s.[Name] AS SiteName,
               sp.[ProcessUnit_ID], sp.[PicturePath]
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
            "process_unit_id": row[7],
            "picture_path": row[8],
        }
        for row in cursor.fetchall()
    ]


def get_all_sampling_locations(
    conn: pyodbc.Connection,
    site_id: int | None = None,
    process_unit_id: int | None = None,
) -> list[dict]:
    cursor = conn.cursor()
    where_clauses = []
    params: list = []
    if site_id is not None:
        where_clauses.append("sp.[Site_ID] = ?")
        params.append(site_id)
    if process_unit_id is not None:
        where_clauses.append("sp.[ProcessUnit_ID] = ?")
        params.append(process_unit_id)
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    cursor.execute(
        f"""
        SELECT sp.[SamplingPoint_ID], sp.[SamplingPoint], sp.[Description],
               sp.[LatitudeWGS84], sp.[LongitudeWGS84], sp.[Site_ID], s.[Name] AS SiteName,
               sp.[ProcessUnit_ID], sp.[PicturePath]
        FROM [dbo].[SamplingPoint] sp
        LEFT JOIN [dbo].[Site] s ON s.[Site_ID] = sp.[Site_ID]
        {where_sql}
        ORDER BY sp.[SamplingPoint_ID]
        """,
        *params,
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
            "process_unit_id": row[7],
            "picture_path": row[8],
        }
        for row in cursor.fetchall()
    ]


def update_sampling_location(
    conn: pyodbc.Connection, sp_id: int, data: dict
) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE [dbo].[SamplingPoint]
        SET [SamplingPoint]=?, [Description]=?, [LatitudeWGS84]=?, [LongitudeWGS84]=?,
            [ProcessUnit_ID]=?
        WHERE [SamplingPoint_ID]=?
        """,
        data["name"],
        data.get("description"),
        data.get("latitude"),
        data.get("longitude"),
        data.get("process_unit_id"),
        sp_id,
    )
    conn.commit()
    if cursor.rowcount == 0:
        return None
    rows = get_all_sampling_locations(conn)
    return next((r for r in rows if r["id"] == sp_id), None)


def delete_sampling_location(conn: pyodbc.Connection, sp_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM [dbo].[SamplingPoint] WHERE [SamplingPoint_ID]=?", sp_id
    )
    conn.commit()
    return cursor.rowcount > 0


def update_sampling_location_picture(
    conn: pyodbc.Connection, sp_id: int, path: str | None
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[SamplingPoint] SET [PicturePath]=? WHERE [SamplingPoint_ID]=?",
        path,
        sp_id,
    )
    conn.commit()
