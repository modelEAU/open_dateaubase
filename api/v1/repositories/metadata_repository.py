"""Data access for MetaData with all FK joins resolved."""

from __future__ import annotations

import pyodbc

_METADATA_SELECT = """
    SELECT
        m.[Metadata_ID],
        m.[Parameter_ID],
        p.[Parameter]            AS ParameterName,
        m.[Unit_ID],
        u.[Unit]                 AS UnitName,
        m.[Equipment_ID],
        e.[Identifier]           AS EquipmentIdentifier,
        m.[DataProvenanceKind_ID],
        dp.[Name] AS DataProvenanceKindName,
        m.[ProcessingKind],
        m.[Laboratory_ID],
        lab.[Name]               AS LaboratoryName,
        m.[AnalystPerson_ID],
        CONCAT(an.[FirstName], ' ', an.[LastName]) AS AnalystName,
        m.[ValueKind_ID],
        vt.[Name]
    FROM [dbo].[MetaData] m
    LEFT JOIN [dbo].[Parameter]      p   ON p.[Parameter_ID]       = m.[Parameter_ID]
    LEFT JOIN [dbo].[Unit]           u   ON u.[Unit_ID]            = m.[Unit_ID]
    LEFT JOIN [dbo].[Equipment]      e   ON e.[Equipment_ID]       = m.[Equipment_ID]
    LEFT JOIN [dbo].[DataProvenanceKind] dp  ON dp.[DataProvenanceKind_ID] = m.[DataProvenanceKind_ID]
    LEFT JOIN [dbo].[Laboratory]     lab ON lab.[Laboratory_ID]    = m.[Laboratory_ID]
    LEFT JOIN [dbo].[Person]         an  ON an.[Person_ID]         = m.[AnalystPerson_ID]
    LEFT JOIN [dbo].[ValueKind]      vt  ON vt.[ValueKind_ID]      = m.[ValueKind_ID]
"""


def _row_to_dict(row) -> dict:
    return {
        "metadata_id": row[0],
        "parameter_id": row[1],
        "parameter_name": row[2],
        "unit_id": row[3],
        "unit_name": row[4],
        "equipment_id": row[5],
        "equipment_identifier": row[6],
        "data_provenance_id": row[7],
        "data_provenance": row[8],
        "processing_degree": row[9],
        "laboratory_id": row[10],
        "laboratory_name": row[11],
        "analyst_id": row[12],
        "analyst_name": row[13],
        "value_kind_id": row[14],
        "value_type_name": row[15],
    }


def list_metadata(
    conn: pyodbc.Connection,
    *,
    parameter_id: int | None = None,
    data_provenance_id: int | None = None,
    processing_degree: str | None = None,
    equipment_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict], int]:
    """Return a page of MetaData rows with filters. Returns (items, total)."""
    where_parts = []
    params = []

    if parameter_id is not None:
        where_parts.append("m.[Parameter_ID] = ?")
        params.append(parameter_id)
    if data_provenance_id is not None:
        where_parts.append("m.[DataProvenanceKind_ID] = ?")
        params.append(data_provenance_id)
    if processing_degree is not None:
        where_parts.append("m.[ProcessingKind] = ?")
        params.append(processing_degree)
    if equipment_id is not None:
        where_parts.append("m.[Equipment_ID] = ?")
        params.append(equipment_id)

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    # Count total
    count_sql = f"SELECT COUNT(*) FROM [dbo].[MetaData] m {where_clause}"
    cursor = conn.cursor()
    cursor.execute(count_sql, *params)
    _count_row = cursor.fetchone()
    assert _count_row is not None
    total: int = _count_row[0]

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


def get_parameters_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return all parameters for dropdowns (id + name)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Parameter_ID], [Parameter] FROM [dbo].[Parameter] ORDER BY [Parameter]"
    )
    return [
        {"parameter_id": row[0], "parameter_name": row[1]} for row in cursor.fetchall()
    ]


def get_processing_kinds_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return all processing kinds for dropdowns (id + name)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ProcessingKind_ID], [Name] FROM [dbo].[ProcessingKind] ORDER BY [ProcessingKind_ID]"
    )
    return [
        {"processing_kind_id": row[0], "name": row[1]} for row in cursor.fetchall()
    ]


def list_parameters(conn: pyodbc.Connection) -> list[dict]:
    """Return all parameters (full rows)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Parameter_ID], [Parameter], [Description], [ENVO_IRI]"
        " FROM [dbo].[Parameter] ORDER BY [Parameter_ID]"
    )
    return [
        {
            "parameter_id": row[0],
            "parameter_name": row[1],
            "description": row[2],
            "envo_iri": row[3],
        }
        for row in cursor.fetchall()
    ]


def get_parameter_by_id(conn: pyodbc.Connection, param_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Parameter_ID], [Parameter], [Description], [ENVO_IRI]"
        " FROM [dbo].[Parameter] WHERE [Parameter_ID]=?",
        param_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "parameter_id": row[0],
        "parameter_name": row[1],
        "description": row[2],
        "envo_iri": row[3],
    }


def get_parameter_by_name(conn: pyodbc.Connection, name: str) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Parameter_ID], [Parameter], [Description], [ENVO_IRI], [ValueKind_ID]"
        " FROM [dbo].[Parameter] WHERE [Parameter]=?",
        name,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "parameter_id": row[0],
        "parameter_name": row[1],
        "description": row[2],
        "envo_iri": row[3],
        "value_kind_id": row[4],
    }


def insert_parameter(conn: pyodbc.Connection, data: dict) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Parameter] ([Parameter], [Description], [ENVO_IRI]) VALUES (?, ?, ?)",
        data.get("parameter"),
        data.get("description"),
        data.get("envo_iri"),
    )
    cursor.execute("SELECT @@IDENTITY")
    _row = cursor.fetchone()
    assert _row is not None
    new_id = int(_row[0])
    conn.commit()
    return get_parameter_by_id(conn, new_id)


def update_parameter(conn: pyodbc.Connection, param_id: int, data: dict) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Parameter]"
        " SET [Parameter]=?, [Description]=?, [ENVO_IRI]=?"
        " WHERE [Parameter_ID]=?",
        data.get("parameter"),
        data.get("description"),
        data.get("envo_iri"),
        param_id,
    )
    conn.commit()
    return get_parameter_by_id(conn, param_id)


def delete_parameter(conn: pyodbc.Connection, param_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Parameter] WHERE [Parameter_ID]=?", param_id)
    conn.commit()
    return cursor.rowcount > 0
