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
        c.[StartDate],
        c.[EndDate],
        c.[Project_ID],
        proj.[name]         AS ProjectName
    FROM [dbo].[Campaign] c
    LEFT JOIN [dbo].[CampaignType] ct   ON ct.[CampaignType_ID]  = c.[CampaignType_ID]
    LEFT JOIN [dbo].[Site]         s    ON s.[Site_ID]           = c.[Site_ID]
    LEFT JOIN [dbo].[Project]      proj ON proj.[Project_ID]     = c.[Project_ID]
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
        "end_date": row[8],
        "project_id": row[9],
        "project_name": row[10],
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
    cursor.execute(_CAMPAIGN_SELECT + where_clause + " ORDER BY c.[Campaign_ID]", *params)
    return [_row_to_dict(row) for row in cursor.fetchall()]


def get_campaign_by_id(conn: pyodbc.Connection, campaign_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(_CAMPAIGN_SELECT + " WHERE c.[Campaign_ID] = ?", campaign_id)
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def get_campaign_context(conn: pyodbc.Connection, campaign_id: int) -> dict:
    """Aggregate full context for a campaign."""
    cursor = conn.cursor()

    # Sampling locations
    cursor.execute(
        """
        SELECT sp.[Sampling_point_ID], sp.[Name], csl.[Role]
        FROM [dbo].[CampaignSamplingLocation] csl
        JOIN [dbo].[SamplingPoints] sp ON sp.[Sampling_point_ID] = csl.[Sampling_point_ID]
        WHERE csl.[Campaign_ID] = ?
        ORDER BY sp.[Sampling_point_ID]
        """,
        campaign_id,
    )
    locations = [{"id": r[0], "name": r[1], "role": r[2]} for r in cursor.fetchall()]

    # Equipment
    cursor.execute(
        """
        SELECT e.[Equipment_ID], e.[identifier], ce.[Role]
        FROM [dbo].[CampaignEquipment] ce
        JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ce.[Equipment_ID]
        WHERE ce.[Campaign_ID] = ?
        ORDER BY e.[Equipment_ID]
        """,
        campaign_id,
    )
    equipment = [{"id": r[0], "identifier": r[1], "role": r[2]} for r in cursor.fetchall()]

    # Parameters
    cursor.execute(
        """
        SELECT p.[Parameter_ID], p.[Parameter]
        FROM [dbo].[CampaignParameter] cp
        JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = cp.[Parameter_ID]
        WHERE cp.[Campaign_ID] = ?
        ORDER BY p.[Parameter_ID]
        """,
        campaign_id,
    )
    parameters = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

    # MetaData count and time range
    cursor.execute(
        """
        SELECT COUNT(*), MIN(v.[Timestamp]), MAX(v.[Timestamp])
        FROM [dbo].[MetaData] m
        LEFT JOIN [dbo].[Value] v ON v.[Metadata_ID] = m.[Metadata_ID]
        WHERE m.[Campaign_ID] = ?
        """,
        campaign_id,
    )
    row = cursor.fetchone()
    metadata_count = row[0] if row else 0
    time_start = row[1] if row else None
    time_end = row[2] if row else None

    return {
        "sampling_locations": locations,
        "equipment": equipment,
        "parameters": parameters,
        "metadata_count": metadata_count,
        "time_range_start": time_start,
        "time_range_end": time_end,
    }
