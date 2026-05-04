"""Data access for Annotation resources."""

from __future__ import annotations

from datetime import datetime

import pyodbc

# ---------------------------------------------------------------------------
# AnnotationKind queries
# ---------------------------------------------------------------------------


def get_annotation_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [AnnotationKind_ID], [Name], [Description], [Color]
        FROM [dbo].[AnnotationKind]
        ORDER BY [AnnotationKind_ID]
        """
    )
    return [
        {
            "annotation_kind_id": row[0],
            "annotation_type_name": row[1],
            "description": row[2],
            "color": row[3],
        }
        for row in cursor.fetchall()
    ]


def get_annotation_kind_by_id(
    conn: pyodbc.Connection, annotation_kind_id: int
) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [AnnotationKind_ID], [Name], [Description], [Color]
        FROM [dbo].[AnnotationKind]
        WHERE [AnnotationKind_ID] = ?
        """,
        annotation_kind_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "annotation_kind_id": row[0],
        "annotation_type_name": row[1],
        "description": row[2],
        "color": row[3],
    }


def get_annotation_kind_by_name(conn: pyodbc.Connection, name: str) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [AnnotationKind_ID], [Name], [Description], [Color]
        FROM [dbo].[AnnotationKind]
        WHERE [Name] = ?
        """,
        name,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "annotation_kind_id": row[0],
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
        "channel_id": row[1],
        "annotation_kind_id": row[2],
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
        "created_datetime": row[14],
        "modified_datetime": row[15],
    }


_ANNOTATION_SELECT = """
    SELECT
        a.[Annotation_ID],
        a.[Channel_ID],
        at.[AnnotationKind_ID],
        at.[Name],
        at.[Color],
        a.[StartTime],
        a.[EndTime],
        a.[Title],
        a.[Comment],
        a.[AuthorPerson_ID],
        CONCAT(p.[FirstName], ' ', p.[LastName]) AS AuthorName,
        a.[Campaign_ID],
        c.[Name]                AS CampaignName,
        a.[EquipmentEvent_ID],
        a.[CreatedDateTime],
        a.[ModifiedDateTime]
    FROM [dbo].[Annotation] a
    JOIN [dbo].[AnnotationKind] at
        ON at.[AnnotationKind_ID] = a.[AnnotationKind_ID]
    LEFT JOIN [dbo].[Person] p
        ON p.[Person_ID] = a.[AuthorPerson_ID]
    LEFT JOIN [dbo].[Campaign] c
        ON c.[Campaign_ID] = a.[Campaign_ID]
"""


# ---------------------------------------------------------------------------
# Query 1: Annotations overlapping a time range for a single Channel entry
# ---------------------------------------------------------------------------


def get_annotations_for_timeseries(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime,
    to_dt: datetime,
    annotation_kind_id: int | None = None,
) -> list[dict]:
    where = (
        "WHERE a.[Channel_ID] = ?"
        "  AND a.[StartTime] <= ?"
        "  AND (a.[EndTime] IS NULL OR a.[EndTime] >= ?)"
    )
    params: list = [channel_id, to_dt, from_dt]

    if annotation_kind_id is not None:
        where += "  AND a.[AnnotationKind_ID] = ?"
        params.append(annotation_kind_id)

    cursor = conn.cursor()
    cursor.execute(
        _ANNOTATION_SELECT + where + " ORDER BY a.[StartTime], a.[AnnotationKind_ID]",
        *params,
    )
    return [_row_to_annotation(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Query 2: Annotations of a given type across all series in a time range
# ---------------------------------------------------------------------------


def get_annotations_by_kind(
    conn: pyodbc.Connection,
    annotation_kind_id: int,
    from_dt: datetime,
    to_dt: datetime,
) -> list[dict]:
    # Extend _ANNOTATION_SELECT with Channel join for parameter context
    select_with_context = """
    SELECT
        a.[Annotation_ID],
        a.[Channel_ID],
        at.[AnnotationKind_ID],
        at.[Name],
        at.[Color],
        a.[StartTime],
        a.[EndTime],
        a.[Title],
        a.[Comment],
        a.[AuthorPerson_ID],
        CONCAT(p.[FirstName], ' ', p.[LastName]) AS AuthorName,
        a.[Campaign_ID],
        c.[Name]                  AS CampaignName,
        a.[EquipmentEvent_ID],
        a.[CreatedDateTime],
        a.[ModifiedDateTime],
        NULL                      AS LocationName,
        par.[Parameter]           AS ParameterName
    FROM [dbo].[Annotation] a
    JOIN [dbo].[AnnotationKind] at
        ON at.[AnnotationKind_ID] = a.[AnnotationKind_ID]
    JOIN [dbo].[Channel] ch
        ON ch.[Channel_ID] = a.[Channel_ID]
    LEFT JOIN [dbo].[Parameter] par
        ON par.[Parameter_ID] = ch.[Parameter_ID]
    LEFT JOIN [dbo].[Person] p
        ON p.[Person_ID] = a.[AuthorPerson_ID]
    LEFT JOIN [dbo].[Campaign] c
        ON c.[Campaign_ID] = a.[Campaign_ID]
    WHERE a.[AnnotationKind_ID] = ?
      AND a.[StartTime] <= ?
      AND (a.[EndTime] IS NULL OR a.[EndTime] >= ?)
    ORDER BY a.[StartTime]
    """
    cursor = conn.cursor()
    cursor.execute(select_with_context, annotation_kind_id, to_dt, from_dt)
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
    annotation_kind_id: int | None = None,
) -> list[dict]:
    select_with_context = """
    SELECT TOP (?)
        a.[Annotation_ID],
        a.[Channel_ID],
        at.[AnnotationKind_ID],
        at.[Name],
        at.[Color],
        a.[StartTime],
        a.[EndTime],
        a.[Title],
        a.[Comment],
        a.[AuthorPerson_ID],
        CONCAT(p.[FirstName], ' ', p.[LastName]) AS AuthorName,
        a.[Campaign_ID],
        c.[Name]                  AS CampaignName,
        a.[EquipmentEvent_ID],
        a.[CreatedDateTime],
        a.[ModifiedDateTime],
        NULL                      AS LocationName,
        par.[Parameter]           AS ParameterName
    FROM [dbo].[Annotation] a
    JOIN [dbo].[AnnotationKind] at
        ON at.[AnnotationKind_ID] = a.[AnnotationKind_ID]
    JOIN [dbo].[Channel] ch
        ON ch.[Channel_ID] = a.[Channel_ID]
    LEFT JOIN [dbo].[Parameter] par
        ON par.[Parameter_ID] = ch.[Parameter_ID]
    LEFT JOIN [dbo].[Person] p
        ON p.[Person_ID] = a.[AuthorPerson_ID]
    LEFT JOIN [dbo].[Campaign] c
        ON c.[Campaign_ID] = a.[Campaign_ID]
    """
    params: list = [limit]
    if annotation_kind_id is not None:
        select_with_context += " WHERE a.[AnnotationKind_ID] = ?"
        params.append(annotation_kind_id)
    select_with_context += " ORDER BY a.[CreatedDateTime] DESC"

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
# Query: list all annotations (optional channel filter)
# ---------------------------------------------------------------------------


def list_annotations(
    conn: pyodbc.Connection,
    channel_id: int | None = None,
) -> list[dict]:
    where = " WHERE a.[Channel_ID] = ?" if channel_id is not None else ""
    params: list = [channel_id] if channel_id is not None else []
    cursor = conn.cursor()
    cursor.execute(
        _ANNOTATION_SELECT + where + " ORDER BY a.[StartTime] DESC, a.[Annotation_ID]",
        *params,
    )
    return [_row_to_annotation(row) for row in cursor.fetchall()]


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
    channel_id: int,
    annotation_kind_id: int,
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
            [Channel_ID], [AnnotationKind_ID], [StartTime], [EndTime],
            [AuthorPerson_ID], [Campaign_ID], [EquipmentEvent_ID],
            [Title], [Comment]
        )
        OUTPUT INSERTED.[Annotation_ID], INSERTED.[CreatedDateTime]
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        channel_id,
        annotation_kind_id,
        start_time,
        end_time,
        author_person_id,
        campaign_id,
        equipment_event_id,
        title,
        comment,
    )
    row = cursor.fetchone()
    conn.commit()
    return {"annotation_id": row[0], "created_datetime": row[1]}


# ---------------------------------------------------------------------------
# Query 5: Update annotation
# ---------------------------------------------------------------------------


def update_annotation(
    conn: pyodbc.Connection,
    annotation_id: int,
    *,
    annotation_kind_id: int | None,
    start_time: datetime | None,
    end_time: datetime | None,
    title: str | None,
    comment: str | None,
) -> dict | None:
    set_parts = ["[ModifiedDateTime] = SYSUTCDATETIME()"]
    params: list = []

    if annotation_kind_id is not None:
        set_parts.append("[AnnotationKind_ID] = ?")
        params.append(annotation_kind_id)
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


# ---------------------------------------------------------------------------
# AnnotationKind write operations
# ---------------------------------------------------------------------------


def insert_annotation_kind(
    conn: pyodbc.Connection,
    name: str,
    description: str | None,
    color: str | None = None,
) -> dict:
    """Insert a new AnnotationKind row and return it."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[AnnotationKind] ([Name], [Description], [Color])"
            " OUTPUT inserted.[AnnotationKind_ID], inserted.[Name],"
            "        inserted.[Description], inserted.[Color]"
            " VALUES (?, ?, ?)",
            name,
            description,
            color,
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "annotation_kind_id": row[0],
            "annotation_type_name": row[1],
            "description": row[2],
            "color": row[3],
        }
    except Exception:
        conn.rollback()
        raise


def update_annotation_kind(
    conn: pyodbc.Connection,
    annotation_kind_id: int,
    name: str,
    description: str | None,
    color: str | None = None,
) -> dict | None:
    """Update an AnnotationKind row and return it, or None if not found."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[AnnotationKind]"
            " SET [Name]=?, [Description]=?, [Color]=?"
            " OUTPUT inserted.[AnnotationKind_ID], inserted.[Name],"
            "        inserted.[Description], inserted.[Color]"
            " WHERE [AnnotationKind_ID]=?",
            name,
            description,
            color,
            annotation_kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {
            "annotation_kind_id": row[0],
            "annotation_type_name": row[1],
            "description": row[2],
            "color": row[3],
        }
    except Exception:
        conn.rollback()
        raise


def delete_annotation_kind(conn: pyodbc.Connection, annotation_kind_id: int) -> bool:
    """Delete an AnnotationKind row. Returns True if a row was deleted."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[AnnotationKind] WHERE [AnnotationKind_ID]=?",
            annotation_kind_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


def create_equipment_move_annotations(
    conn: pyodbc.Connection,
    *,
    channel_ids: list[int],
    annotation_kind_id: int,
    title: str,
    comment: str,
    start_time: datetime,
) -> list[int]:
    """Create annotations on multiple channels for an equipment move.

    Returns the list of created Annotation_IDs.
    """
    annotation_ids: list[int] = []
    for channel_id in channel_ids:
        result = create_annotation(
            conn,
            channel_id=channel_id,
            annotation_kind_id=annotation_kind_id,
            start_time=start_time,
            end_time=None,
            author_person_id=None,
            campaign_id=None,
            equipment_event_id=None,
            title=title,
            comment=comment,
        )
        annotation_ids.append(result["annotation_id"])
    return annotation_ids
