"""Data access for Channel with all FK joins resolved."""

from __future__ import annotations

import pyodbc

_CHANNEL_SELECT = """
    SELECT
        m.[Channel_ID],
        m.[Parameter_ID],
        p.[Parameter]                AS ParameterName,
        m.[Unit_ID],
        u.[Unit]                     AS UnitName,
        m.[Equipment_ID],
        e.[identifier]               AS EquipmentIdentifier,
        m.[DataProvenance_ID],
        dp.[DataProvenance_Name]     AS DataProvenanceName,
        m.[ProcessingDegree_ID],
        pd.[ProcessingDegree_Name]   AS ProcessingDegreeName,
        m.[ValueType_ID],
        vt.[ValueType_Name]
    FROM [dbo].[Channel] m
    LEFT JOIN [dbo].[Parameter]       p   ON p.[Parameter_ID]        = m.[Parameter_ID]
    LEFT JOIN [dbo].[Unit]            u   ON u.[Unit_ID]             = m.[Unit_ID]
    LEFT JOIN [dbo].[Equipment]       e   ON e.[Equipment_ID]        = m.[Equipment_ID]
    LEFT JOIN [dbo].[DataProvenance]  dp  ON dp.[DataProvenance_ID]  = m.[DataProvenance_ID]
    LEFT JOIN [dbo].[ProcessingDegree] pd ON pd.[ProcessingDegree_ID] = m.[ProcessingDegree_ID]
    LEFT JOIN [dbo].[ValueType]       vt  ON vt.[ValueType_ID]       = m.[ValueType_ID]
"""


def _row_to_dict(row) -> dict:
    return {
        "channel_id": row[0],
        "parameter_id": row[1],
        "parameter_name": row[2],
        "unit_id": row[3],
        "unit_name": row[4],
        "equipment_id": row[5],
        "equipment_identifier": row[6],
        "data_provenance_id": row[7],
        "data_provenance": row[8],
        "processing_degree_id": row[9],
        "processing_degree_name": row[10],
        "value_type_id": row[11],
        "value_type_name": row[12],
    }


def list_channels(
    conn: pyodbc.Connection,
    *,
    parameter_id: int | None = None,
    data_provenance_id: int | None = None,
    processing_degree_id: int | None = None,
    equipment_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict], int]:
    """Return a page of Channel rows with filters. Returns (items, total)."""
    where_parts = []
    params = []

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

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    count_sql = f"SELECT COUNT(*) FROM [dbo].[Channel] m {where_clause}"
    cursor = conn.cursor()
    cursor.execute(count_sql, *params)
    total: int = cursor.fetchone()[0]

    offset = (page - 1) * page_size
    data_sql = (
        _CHANNEL_SELECT
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
