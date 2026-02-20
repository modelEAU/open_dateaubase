"""Data access for Annotation resources."""

from __future__ import annotations

from datetime import datetime

import pyodbc

# ---------------------------------------------------------------------------
# AnnotationType queries
# ---------------------------------------------------------------------------

def get_annotation_types(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [AnnotationType_ID], [AnnotationTypeName], [Description], [Color]
        FROM [dbo].[AnnotationType]
        ORDER BY [AnnotationType_ID]
        """
    )
    return [
        {
            "annotation_type_id": row[0],
            "annotation_type_name": row[1],
            "description": row[2],
            "color": row[3],
        }
        for row in cursor.fetchall()
    ]


def get_annotation_type_by_id(conn: pyodbc.Connection, annotation_type_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [AnnotationType_ID], [AnnotationTypeName], [Description], [Color]
        FROM [dbo].[AnnotationType]
        WHERE [AnnotationType_ID] = ?
        """,
        annotation_type_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "annotation_type_id": row[0],
        "annotation_type_name": row[1],
        "description": row[2],
        "color": row[3],
    }


def get_annotation_type_by_name(conn: pyodbc.Connection, name: str) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [AnnotationType_ID], [AnnotationTypeName], [Description], [Color]
        FROM [dbo].[AnnotationType]
        WHERE [AnnotationTypeName] = ?
        """,
        name,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "annotation_type_id": row[0],
        "annotation_type_name": row[1],
        "description": row[2],
        "color": row[3],
    }


# ---------------------------------------------------------------------------
# Full annotation row → dict (reused by several queries)
# ---------------------------------------------------------------------------

def _row_to_annotation(row) -> dict:
    return {
        "annotation_id": row[0],
        "metadata_id": row[1],
        "annotation_type_id": row[2],
        "annotation_type_name": row[3],
        "color": row[4],
        "start_time": row[5],
        "end_time": row[6],
        "title": row[7],
        "comment": row[8],
        "author_person_id": row[9],
        "author_name": row[10],
        "campaign_id": row[11],
        "campaign_name": row[12],
        "equipment_event_id": row[13],
        "created_at": row[14],
        "modified_at": row[15],
    }


_ANNOTATION_SELECT = """
    SELECT
        a.[Annotation_ID],
        a.[Metadata_ID],
        at.[AnnotationType_ID],
        at.[AnnotationTypeName],
        at.[Color],
        a.[StartTime],
        a.[EndTime],
        a.[Title],
        a.[Comment],
        a.[AuthorPerson_ID],
        CONCAT(p.[First_name], ' ', p.[Last_name]) AS AuthorName,
        a.[Campaign_ID],
        c.[Name]                AS CampaignName,
        a.[EquipmentEvent_ID],
        a.[CreatedAt],
        a.[ModifiedAt]
    FROM [dbo].[Annotation] a
    JOIN [dbo].[AnnotationType] at
        ON at.[AnnotationType_ID] = a.[AnnotationType_ID]
    LEFT JOIN [dbo].[Person] p
        ON p.[Person_ID] = a.[AuthorPerson_ID]
    LEFT JOIN [dbo].[Campaign] c
        ON c.[Campaign_ID] = a.[Campaign_ID]
"""


# ---------------------------------------------------------------------------
# Query 1: Annotations overlapping a time range for a single MetaData entry
# ---------------------------------------------------------------------------

def get_annotations_for_timeseries(
    conn: pyodbc.Connection,
    metadata_id: int,
    from_dt: datetime,
    to_dt: datetime,
    annotation_type_id: int | None = None,
) -> list[dict]:
    where = (
        "WHERE a.[Metadata_ID] = ?"
        "  AND a.[StartTime] <= ?"
        "  AND (a.[EndTime] IS NULL OR a.[EndTime] >= ?)"
    )
    params: list = [metadata_id, to_dt, from_dt]

    if annotation_type_id is not None:
        where += "  AND a.[AnnotationType_ID] = ?"
        params.append(annotation_type_id)

    cursor = conn.cursor()
    cursor.execute(
        _ANNOTATION_SELECT + where + " ORDER BY a.[StartTime], a.[AnnotationType_ID]",
        *params,
    )
    return [_row_to_annotation(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Query 2: Annotations of a given type across all series in a time range
# ---------------------------------------------------------------------------

def get_annotations_by_type(
    conn: pyodbc.Connection,
    annotation_type_id: int,
    from_dt: datetime,
    to_dt: datetime,
) -> list[dict]:
    # Extend _ANNOTATION_SELECT with MetaData join for location/parameter context
    select_with_context = """
    SELECT
        a.[Annotation_ID],
        a.[Metadata_ID],
        at.[AnnotationType_ID],
        at.[AnnotationTypeName],
        at.[Color],
        a.[StartTime],
        a.[EndTime],
        a.[Title],
        a.[Comment],
        a.[AuthorPerson_ID],
        CONCAT(p.[First_name], ' ', p.[Last_name]) AS AuthorName,
        a.[Campaign_ID],
        c.[Name]                  AS CampaignName,
        a.[EquipmentEvent_ID],
        a.[CreatedAt],
        a.[ModifiedAt],
        sp.[Sampling_location]    AS LocationName,
        par.[Parameter]           AS ParameterName
    FROM [dbo].[Annotation] a
    JOIN [dbo].[AnnotationType] at
        ON at.[AnnotationType_ID] = a.[AnnotationType_ID]
    JOIN [dbo].[MetaData] md
        ON md.[Metadata_ID] = a.[Metadata_ID]
    LEFT JOIN [dbo].[SamplingPoints] sp
        ON sp.[Sampling_point_ID] = md.[Sampling_point_ID]
    LEFT JOIN [dbo].[Parameter] par
        ON par.[Parameter_ID] = md.[Parameter_ID]
    LEFT JOIN [dbo].[Person] p
        ON p.[Person_ID] = a.[AuthorPerson_ID]
    LEFT JOIN [dbo].[Campaign] c
        ON c.[Campaign_ID] = a.[Campaign_ID]
    WHERE a.[AnnotationType_ID] = ?
      AND a.[StartTime] <= ?
      AND (a.[EndTime] IS NULL OR a.[EndTime] >= ?)
    ORDER BY a.[StartTime]
    """
    cursor = conn.cursor()
    cursor.execute(select_with_context, annotation_type_id, to_dt, from_dt)
    rows = []
    for row in cursor.fetchall():
        d = _row_to_annotation(row)
        d["location_name"] = row[16]
        d["parameter_name"] = row[17]
        rows.append(d)
    return rows


# ---------------------------------------------------------------------------
# Query 3: Recent annotations (dashboard feed)
# ---------------------------------------------------------------------------

def get_recent_annotations(
    conn: pyodbc.Connection,
    limit: int = 20,
    annotation_type_id: int | None = None,
) -> list[dict]:
    select_with_context = """
    SELECT TOP (?)
        a.[Annotation_ID],
        a.[Metadata_ID],
        at.[AnnotationType_ID],
        at.[AnnotationTypeName],
        at.[Color],
        a.[StartTime],
        a.[EndTime],
        a.[Title],
        a.[Comment],
        a.[AuthorPerson_ID],
        CONCAT(p.[First_name], ' ', p.[Last_name]) AS AuthorName,
        a.[Campaign_ID],
        c.[Name]                  AS CampaignName,
        a.[EquipmentEvent_ID],
        a.[CreatedAt],
        a.[ModifiedAt],
        sp.[Sampling_location]    AS LocationName,
        par.[Parameter]           AS ParameterName
    FROM [dbo].[Annotation] a
    JOIN [dbo].[AnnotationType] at
        ON at.[AnnotationType_ID] = a.[AnnotationType_ID]
    JOIN [dbo].[MetaData] md
        ON md.[Metadata_ID] = a.[Metadata_ID]
    LEFT JOIN [dbo].[SamplingPoints] sp
        ON sp.[Sampling_point_ID] = md.[Sampling_point_ID]
    LEFT JOIN [dbo].[Parameter] par
        ON par.[Parameter_ID] = md.[Parameter_ID]
    LEFT JOIN [dbo].[Person] p
        ON p.[Person_ID] = a.[AuthorPerson_ID]
    LEFT JOIN [dbo].[Campaign] c
        ON c.[Campaign_ID] = a.[Campaign_ID]
    """
    params: list = [limit]
    if annotation_type_id is not None:
        select_with_context += " WHERE a.[AnnotationType_ID] = ?"
        params.append(annotation_type_id)
    select_with_context += " ORDER BY a.[CreatedAt] DESC"

    cursor = conn.cursor()
    cursor.execute(select_with_context, *params)
    rows = []
    for row in cursor.fetchall():
        d = _row_to_annotation(row)
        d["location_name"] = row[16]
        d["parameter_name"] = row[17]
        rows.append(d)
    return rows


# ---------------------------------------------------------------------------
# Single annotation by ID
# ---------------------------------------------------------------------------

def get_annotation_by_id(conn: pyodbc.Connection, annotation_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        _ANNOTATION_SELECT + " WHERE a.[Annotation_ID] = ?",
        annotation_id,
    )
    row = cursor.fetchone()
    return _row_to_annotation(row) if row else None


# ---------------------------------------------------------------------------
# Query 4: Insert annotation
# ---------------------------------------------------------------------------

def create_annotation(
    conn: pyodbc.Connection,
    *,
    metadata_id: int,
    annotation_type_id: int,
    start_time: datetime,
    end_time: datetime | None,
    author_person_id: int | None,
    campaign_id: int | None,
    equipment_event_id: int | None,
    title: str | None,
    comment: str | None,
) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[Annotation] (
            [Metadata_ID], [AnnotationType_ID], [StartTime], [EndTime],
            [AuthorPerson_ID], [Campaign_ID], [EquipmentEvent_ID],
            [Title], [Comment]
        )
        OUTPUT INSERTED.[Annotation_ID], INSERTED.[CreatedAt]
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        metadata_id, annotation_type_id, start_time, end_time,
        author_person_id, campaign_id, equipment_event_id,
        title, comment,
    )
    row = cursor.fetchone()
    conn.commit()
    return {"annotation_id": row[0], "created_at": row[1]}


# ---------------------------------------------------------------------------
# Query 5: Update annotation
# ---------------------------------------------------------------------------

def update_annotation(
    conn: pyodbc.Connection,
    annotation_id: int,
    *,
    annotation_type_id: int | None,
    start_time: datetime | None,
    end_time: datetime | None,
    title: str | None,
    comment: str | None,
) -> dict | None:
    # Build SET clause only for provided fields
    set_parts = ["[ModifiedAt] = SYSUTCDATETIME()"]
    params: list = []

    if annotation_type_id is not None:
        set_parts.append("[AnnotationType_ID] = ?")
        params.append(annotation_type_id)
    if start_time is not None:
        set_parts.append("[StartTime] = ?")
        params.append(start_time)
    if end_time is not None:
        set_parts.append("[EndTime] = ?")
        params.append(end_time)
    if title is not None:
        set_parts.append("[Title] = ?")
        params.append(title)
    if comment is not None:
        set_parts.append("[Comment] = ?")
        params.append(comment)

    params.append(annotation_id)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE [dbo].[Annotation] SET {', '.join(set_parts)} WHERE [Annotation_ID] = ?",
        *params,
    )
    conn.commit()
    return get_annotation_by_id(conn, annotation_id)


# ---------------------------------------------------------------------------
# Query 6: Delete annotation
# ---------------------------------------------------------------------------

def delete_annotation(conn: pyodbc.Connection, annotation_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM [dbo].[Annotation] WHERE [Annotation_ID] = ?",
        annotation_id,
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    return deleted
