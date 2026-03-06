"""Data access for Channel with all FK joins resolved."""

from __future__ import annotations

import pyodbc

_CHANNEL_SELECT = """
    SELECT
        m.[Channel_ID],
        m.[Parameter_ID],
        p.[Parameter]                AS ParameterName,
        m.[Equipment_ID],
        e.[Identifier]               AS EquipmentIdentifier,
        m.[DataProvenance_ID],
        dp.[DataProvenance_Name]     AS DataProvenanceName,
        m.[ProcessingDegree_ID],
        pd.[Name]                    AS ProcessingDegreeName,
        m.[ValueType_ID],
        vt.[ValueType_Name]
    FROM [dbo].[Channel] m
    LEFT JOIN [dbo].[Parameter]       p   ON p.[Parameter_ID]        = m.[Parameter_ID]
    LEFT JOIN [dbo].[Equipment]       e   ON e.[Equipment_ID]        = m.[Equipment_ID]
    LEFT JOIN [dbo].[DataProvenance]  dp  ON dp.[DataProvenance_ID]  = m.[DataProvenance_ID]
    LEFT JOIN [dbo].[ProcessingDegree] pd ON pd.[ProcessingDegree_ID] = m.[ProcessingDegree_ID]
    LEFT JOIN [dbo].[ValueType]       vt  ON vt.[ValueType_ID]       = m.[ValueType_ID]
"""

_CHANNEL_SELECT_WITH_CAMPAIGN = """
    SELECT
        m.[Channel_ID],
        m.[Parameter_ID],
        p.[Parameter]                AS ParameterName,
        m.[Equipment_ID],
        e.[Identifier]               AS EquipmentIdentifier,
        m.[DataProvenance_ID],
        dp.[DataProvenance_Name]     AS DataProvenanceName,
        m.[ProcessingDegree_ID],
        pd.[Name]                    AS ProcessingDegreeName,
        m.[ValueType_ID],
        vt.[ValueType_Name]
    FROM [dbo].[Channel] m
    LEFT JOIN [dbo].[Parameter]       p   ON p.[Parameter_ID]        = m.[Parameter_ID]
    LEFT JOIN [dbo].[Equipment]       e   ON e.[Equipment_ID]        = m.[Equipment_ID]
    LEFT JOIN [dbo].[DataProvenance]  dp  ON dp.[DataProvenance_ID]  = m.[DataProvenance_ID]
    LEFT JOIN [dbo].[ProcessingDegree] pd ON pd.[ProcessingDegree_ID] = m.[ProcessingDegree_ID]
    LEFT JOIN [dbo].[ValueType]       vt  ON vt.[ValueType_ID]       = m.[ValueType_ID]
    JOIN [dbo].[CampaignEquipment]    ce  ON ce.[Equipment_ID]       = m.[Equipment_ID]
"""


def _row_to_dict(row) -> dict:
    return {
        "channel_id": row[0],
        "parameter_id": row[1],
        "parameter_name": row[2],
        "equipment_id": row[3],
        "equipment_identifier": row[4],
        "data_provenance_id": row[5],
        "data_provenance": row[6],
        "processing_degree_id": row[7],
        "processing_degree_name": row[8],
        "value_type_id": row[9],
        "value_type_name": row[10],
    }


def list_channels(
    conn: pyodbc.Connection,
    *,
    parameter_id: int | None = None,
    data_provenance_id: int | None = None,
    processing_degree_id: int | None = None,
    equipment_id: int | None = None,
    value_type_id: int | None = None,
    campaign_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict], int]:
    """Return a page of Channel rows with filters. Returns (items, total)."""
    # When filtering by campaign we join CampaignEquipment (requires non-NULL Equipment_ID)
    use_campaign = campaign_id is not None
    base_select = _CHANNEL_SELECT_WITH_CAMPAIGN if use_campaign else _CHANNEL_SELECT

    where_parts = []
    params = []

    if use_campaign:
        where_parts.append("ce.[Campaign_ID] = ?")
        params.append(campaign_id)
    if parameter_id is not None:
        where_parts.append("m.[Parameter_ID] = ?")
        params.append(parameter_id)
    if data_provenance_id is not None:
        where_parts.append("m.[DataProvenance_ID] = ?")
        params.append(data_provenance_id)
    if processing_degree_id is not None:
        where_parts.append("m.[ProcessingDegree_ID] = ?")
        params.append(processing_degree_id)
    if equipment_id is not None:
        where_parts.append("m.[Equipment_ID] = ?")
        params.append(equipment_id)
    if value_type_id is not None:
        where_parts.append("m.[ValueType_ID] = ?")
        params.append(value_type_id)

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    count_sql = f"SELECT COUNT(*) FROM [dbo].[Channel] m {where_clause}" if not use_campaign else (
        f"SELECT COUNT(*) FROM [dbo].[Channel] m "
        f"JOIN [dbo].[CampaignEquipment] ce ON ce.[Equipment_ID] = m.[Equipment_ID] "
        f"{where_clause}"
    )
    cursor = conn.cursor()
    cursor.execute(count_sql, *params)
    total: int = cursor.fetchone()[0]

    offset = (page - 1) * page_size
    data_sql = (
        base_select
        + f" {where_clause} "
        + "ORDER BY m.[Channel_ID] "
        + f"OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
    )
    cursor.execute(data_sql, *params)
    items = [_row_to_dict(row) for row in cursor.fetchall()]
    return items, total


def get_channel_by_id(conn: pyodbc.Connection, channel_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(_CHANNEL_SELECT + " WHERE m.[Channel_ID] = ?", channel_id)
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def insert_channel(conn: pyodbc.Connection, data: dict) -> dict:
    """Insert a new channel and return the created record."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Channel] ([Parameter_ID], [Equipment_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])"
        " VALUES (?, ?, ?, ?, ?)",
        data.get("parameter_id"),
        data.get("equipment_id"),
        data.get("data_provenance_id"),
        data.get("processing_degree_id"),
        data.get("value_type_id"),
    )
    cursor.execute("SELECT @@IDENTITY")
    new_id = int(cursor.fetchone()[0])
    conn.commit()
    return get_channel_by_id(conn, new_id)


def update_channel(conn: pyodbc.Connection, channel_id: int, data: dict) -> dict | None:
    """Update an existing channel and return the updated record."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Channel]"
        " SET [Parameter_ID]=?, [Equipment_ID]=?, [DataProvenance_ID]=?, [ProcessingDegree_ID]=?, [ValueType_ID]=?"
        " WHERE [Channel_ID]=?",
        data.get("parameter_id"),
        data.get("equipment_id"),
        data.get("data_provenance_id"),
        data.get("processing_degree_id"),
        data.get("value_type_id"),
        channel_id,
    )
    conn.commit()
    return get_channel_by_id(conn, channel_id)


def delete_channel(conn: pyodbc.Connection, channel_id: int) -> bool:
    """Delete a channel by ID. Returns True if deleted, False if not found."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Channel] WHERE [Channel_ID]=?", channel_id)
    conn.commit()
    return cursor.rowcount > 0
