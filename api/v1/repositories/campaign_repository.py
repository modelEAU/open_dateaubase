"""Data access for Campaign resources."""

from __future__ import annotations

import pyodbc

_CAMPAIGN_SELECT = """
    SELECT
        c.[Campaign_ID],
        c.[CampaignType_ID],
        ct.[CampaignType_Name],
        c.[Site_ID],
        s.[Name]            AS SiteName,
        c.[Name],
        c.[Description],
        c.[CampaignStartDateTime],
        c.[CampaignEndDateTime]
    FROM [dbo].[Campaign] c
    LEFT JOIN [dbo].[CampaignType] ct ON ct.[CampaignType_ID] = c.[CampaignType_ID]
    LEFT JOIN [dbo].[Site]         s  ON s.[Site_ID]          = c.[Site_ID]
"""


def _row_to_dict(row) -> dict:
    return {
        "campaign_id": row[0],
        "campaign_type_id": row[1],
        "campaign_type_name": row[2],
        "site_id": row[3],
        "site_name": row[4],
        "name": row[5],
        "description": row[6],
        "start_date": row[7],
        "end_date": row[8],  # CampaignEndDateTime
    }


def list_campaigns(
    conn: pyodbc.Connection,
    *,
    site_id: int | None = None,
    campaign_type_id: int | None = None,
) -> list[dict]:
    where_parts = []
    params = []
    if site_id is not None:
        where_parts.append("c.[Site_ID] = ?")
        params.append(site_id)
    if campaign_type_id is not None:
        where_parts.append("c.[CampaignType_ID] = ?")
        params.append(campaign_type_id)

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    cursor = conn.cursor()
    cursor.execute(
        _CAMPAIGN_SELECT + where_clause + " ORDER BY c.[Campaign_ID]", *params
    )
    return [_row_to_dict(row) for row in cursor.fetchall()]


def get_campaign_by_id(conn: pyodbc.Connection, campaign_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(_CAMPAIGN_SELECT + " WHERE c.[Campaign_ID] = ?", campaign_id)
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def insert_campaign(conn: pyodbc.Connection, data: dict) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Campaign]"
        " ([Name], [CampaignType_ID], [Site_ID], [Description], [CampaignStartDateTime], [CampaignEndDateTime])"
        " VALUES (?, ?, ?, ?, ?, ?)",
        data.get("name"),
        data.get("campaign_type_id"),
        data.get("site_id"),
        data.get("description"),
        data.get("start_date"),
        data.get("end_date"),
    )
    cursor.execute("SELECT @@IDENTITY")
    new_id = int(cursor.fetchone()[0])
    conn.commit()
    return get_campaign_by_id(conn, new_id)


def update_campaign(
    conn: pyodbc.Connection, campaign_id: int, data: dict
) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Campaign]"
        " SET [Name]=?, [CampaignType_ID]=?, [Site_ID]=?, [Description]=?,"
        " [CampaignStartDateTime]=?, [CampaignEndDateTime]=?"
        " WHERE [Campaign_ID]=?",
        data.get("name"),
        data.get("campaign_type_id"),
        data.get("site_id"),
        data.get("description"),
        data.get("start_date"),
        data.get("end_date"),
        campaign_id,
    )
    conn.commit()
    return get_campaign_by_id(conn, campaign_id)


def delete_campaign(conn: pyodbc.Connection, campaign_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Campaign] WHERE [Campaign_ID]=?", campaign_id)
    conn.commit()
    return cursor.rowcount > 0


def patch_campaign(
    conn: pyodbc.Connection, campaign_id: int, data: dict
) -> dict | None:
    """Partial update of a campaign - only updates fields that are present in data."""
    existing = get_campaign_by_id(conn, campaign_id)
    if existing is None:
        return None

    fields = []
    values = []

    if "name" in data:
        fields.append("[Name]=?")
        values.append(data.get("name"))
    if "campaign_type_id" in data:
        fields.append("[CampaignType_ID]=?")
        values.append(data.get("campaign_type_id"))
    if "site_id" in data:
        fields.append("[Site_ID]=?")
        values.append(data.get("site_id"))
    if "description" in data:
        fields.append("[Description]=?")
        values.append(data.get("description"))
    if "start_date" in data:
        fields.append("[CampaignStartDateTime]=?")
        values.append(data.get("start_date"))
    if "end_date" in data:
        fields.append("[CampaignEndDateTime]=?")
        values.append(data.get("end_date"))

    if not fields:
        return existing

    values.append(campaign_id)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE [dbo].[Campaign] SET {', '.join(fields)} WHERE [Campaign_ID]=?",
        *values,
    )
    conn.commit()
    return get_campaign_by_id(conn, campaign_id)


def get_campaign_types(conn: pyodbc.Connection) -> list[dict]:
    """Return all campaign types for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [CampaignType_ID], [CampaignType_Name] FROM [dbo].[CampaignType] ORDER BY [CampaignType_Name]"
    )
    return [{"campaign_type_id": row[0], "name": row[1]} for row in cursor.fetchall()]


def get_campaign_context(conn: pyodbc.Connection, campaign_id: int) -> dict:
    """Aggregate full context for a campaign."""
    cursor = conn.cursor()

    # Sampling locations
    cursor.execute(
        """
        SELECT sp.[SamplingPoint_ID], sp.[SamplingPoint], csl.[Role]
        FROM [dbo].[CampaignSamplingLocation] csl
        JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = csl.[SamplingPoint_ID]
        WHERE csl.[Campaign_ID] = ?
        ORDER BY sp.[SamplingPoint_ID]
        """,
        campaign_id,
    )
    locations = [{"id": r[0], "name": r[1], "role": r[2]} for r in cursor.fetchall()]

    # Equipment
    cursor.execute(
        """
        SELECT e.[Equipment_ID], e.[Identifier], ce.[Role]
        FROM [dbo].[CampaignEquipment] ce
        JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ce.[Equipment_ID]
        WHERE ce.[Campaign_ID] = ?
        ORDER BY e.[Equipment_ID]
        """,
        campaign_id,
    )
    equipment = [
        {"id": r[0], "identifier": r[1], "role": r[2]} for r in cursor.fetchall()
    ]

    # Parameters (distinct parameters across channels linked via campaign equipment)
    cursor.execute(
        """
        SELECT DISTINCT p.[Parameter_ID], p.[Parameter]
        FROM [dbo].[Channel] ch
        JOIN [dbo].[CampaignEquipment] ce ON ce.[Equipment_ID] = ch.[Equipment_ID]
        JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = ch.[Parameter_ID]
        WHERE ce.[Campaign_ID] = ?
        ORDER BY p.[Parameter_ID]
        """,
        campaign_id,
    )
    parameters = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

    # Channel count and time range (via CampaignEquipment)
    cursor.execute(
        """
        SELECT COUNT(DISTINCT ch.[Channel_ID]), MIN(v.[Timestamp]), MAX(v.[Timestamp])
        FROM [dbo].[Channel] ch
        JOIN [dbo].[CampaignEquipment] ce ON ce.[Equipment_ID] = ch.[Equipment_ID]
        LEFT JOIN [dbo].[Value] v ON v.[Channel_ID] = ch.[Channel_ID]
        WHERE ce.[Campaign_ID] = ?
        """,
        campaign_id,
    )
    row = cursor.fetchone()
    channel_count = row[0] if row else 0
    time_start = row[1] if row else None
    time_end = row[2] if row else None

    return {
        "sampling_locations": locations,
        "equipment": equipment,
        "parameters": parameters,
        "channel_count": channel_count,
        "time_range_start": time_start,
        "time_range_end": time_end,
    }
