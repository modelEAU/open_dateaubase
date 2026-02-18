"""Data access for MetaData with all FK joins resolved."""

from __future__ import annotations

import pyodbc

_METADATA_SELECT = """
    SELECT
        m.[Metadata_ID],
        m.[Parameter_ID],
        p.[Parameter]           AS ParameterName,
        m.[Unit_ID],
        u.[Unit]                AS UnitName,
        m.[Sampling_point_ID],
        sp.[Name]               AS LocationName,
        sp.[Site_ID],
        s.[Name]                AS SiteName,
        m.[Equipment_ID],
        e.[identifier]          AS EquipmentIdentifier,
        m.[Campaign_ID],
        c.[Name]                AS CampaignName,
        ct.[CampaignType_Name]  AS CampaignTypeName,
        m.[DataProvenance_ID],
        dp.[DataProvenance_Name] AS DataProvenanceName,
        m.[ProcessingDegree],
        m.[Laboratory_ID],
        lab.[Name]              AS LaboratoryName,
        m.[AnalystPerson_ID],
        CONCAT(an.[First_name], ' ', an.[Last_name]) AS AnalystName,
        m.[Contact_ID],
        CONCAT(co.[First_name], ' ', co.[Last_name]) AS ContactName,
        m.[Project_ID],
        proj.[name]             AS ProjectName,
        m.[Purpose_ID],
        pur.[Purpose]           AS PurposeName,
        m.[ValueType_ID],
        vt.[ValueType_Name],
        m.[StartDate],
        m.[EndDate]
    FROM [dbo].[MetaData] m
    LEFT JOIN [dbo].[Parameter]       p    ON p.[Parameter_ID]      = m.[Parameter_ID]
    LEFT JOIN [dbo].[Unit]            u    ON u.[Unit_ID]           = m.[Unit_ID]
    LEFT JOIN [dbo].[SamplingPoints]  sp   ON sp.[Sampling_point_ID] = m.[Sampling_point_ID]
    LEFT JOIN [dbo].[Site]            s    ON s.[Site_ID]           = sp.[Site_ID]
    LEFT JOIN [dbo].[Equipment]       e    ON e.[Equipment_ID]      = m.[Equipment_ID]
    LEFT JOIN [dbo].[Campaign]        c    ON c.[Campaign_ID]       = m.[Campaign_ID]
    LEFT JOIN [dbo].[CampaignType]    ct   ON ct.[CampaignType_ID]  = c.[CampaignType_ID]
    LEFT JOIN [dbo].[DataProvenance]  dp   ON dp.[DataProvenance_ID] = m.[DataProvenance_ID]
    LEFT JOIN [dbo].[Laboratory]      lab  ON lab.[Laboratory_ID]   = m.[Laboratory_ID]
    LEFT JOIN [dbo].[Person]          an   ON an.[Person_ID]        = m.[AnalystPerson_ID]
    LEFT JOIN [dbo].[Person]          co   ON co.[Person_ID]        = m.[Contact_ID]
    LEFT JOIN [dbo].[Project]         proj ON proj.[Project_ID]     = m.[Project_ID]
    LEFT JOIN [dbo].[Purpose]         pur  ON pur.[Purpose_ID]      = m.[Purpose_ID]
    LEFT JOIN [dbo].[ValueType]       vt   ON vt.[ValueType_ID]     = m.[ValueType_ID]
"""


def _row_to_dict(row) -> dict:
    return {
        "metadata_id": row[0],
        "parameter_id": row[1],
        "parameter_name": row[2],
        "unit_id": row[3],
        "unit_name": row[4],
        "location_id": row[5],
        "location_name": row[6],
        "site_id": row[7],
        "site_name": row[8],
        "equipment_id": row[9],
        "equipment_identifier": row[10],
        "campaign_id": row[11],
        "campaign_name": row[12],
        "campaign_type": row[13],
        "data_provenance_id": row[14],
        "data_provenance": row[15],
        "processing_degree": row[16],
        "laboratory_id": row[17],
        "laboratory_name": row[18],
        "analyst_id": row[19],
        "analyst_name": row[20],
        "contact_id": row[21],
        "contact_name": row[22],
        "project_id": row[23],
        "project_name": row[24],
        "purpose_id": row[25],
        "purpose_name": row[26],
        "value_type_id": row[27],
        "value_type_name": row[28],
        "start_date": row[29],
        "end_date": row[30],
    }


def list_metadata(
    conn: pyodbc.Connection,
    *,
    site_id: int | None = None,
    location_id: int | None = None,
    parameter_id: int | None = None,
    campaign_id: int | None = None,
    data_provenance_id: int | None = None,
    processing_degree: str | None = None,
    equipment_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict], int]:
    """Return a page of MetaData rows with filters. Returns (items, total)."""
    where_parts = []
    params = []

    if site_id is not None:
        where_parts.append("sp.[Site_ID] = ?")
        params.append(site_id)
    if location_id is not None:
        where_parts.append("m.[Sampling_point_ID] = ?")
        params.append(location_id)
    if parameter_id is not None:
        where_parts.append("m.[Parameter_ID] = ?")
        params.append(parameter_id)
    if campaign_id is not None:
        where_parts.append("m.[Campaign_ID] = ?")
        params.append(campaign_id)
    if data_provenance_id is not None:
        where_parts.append("m.[DataProvenance_ID] = ?")
        params.append(data_provenance_id)
    if processing_degree is not None:
        where_parts.append("m.[ProcessingDegree] = ?")
        params.append(processing_degree)
    if equipment_id is not None:
        where_parts.append("m.[Equipment_ID] = ?")
        params.append(equipment_id)

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    # Count total
    count_sql = f"""
        SELECT COUNT(*)
        FROM [dbo].[MetaData] m
        LEFT JOIN [dbo].[SamplingPoints] sp ON sp.[Sampling_point_ID] = m.[Sampling_point_ID]
        {where_clause}
    """
    cursor = conn.cursor()
    cursor.execute(count_sql, *params)
    total: int = cursor.fetchone()[0]

    # Paginated rows
    offset = (page - 1) * page_size
    data_sql = (
        _METADATA_SELECT
        + f" {where_clause} "
        + "ORDER BY m.[Metadata_ID] "
        + f"OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
    )
    cursor.execute(data_sql, *params)
    items = [_row_to_dict(row) for row in cursor.fetchall()]
    return items, total


def get_metadata_by_id(conn: pyodbc.Connection, metadata_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(_METADATA_SELECT + " WHERE m.[Metadata_ID] = ?", metadata_id)
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None
