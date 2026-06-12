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
        "stream_id": row[1],
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
        "stream_kind_id": row[16],
        "observation_id": row[17],
    }


# The annotation anchors to a single Stream_ID. We join Stream so the read path
# can surface StreamKind_ID — the discriminator (Sensor=Channel, Lab=Series) the
# service uses to label the anchor. Column index 16 is the StreamKind_ID.
_ANNOTATION_SELECT = """
    SELECT
        a.[Annotation_ID],
        a.[Stream_ID],
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
        a.[ModifiedDateTime],
        s.[StreamKind_ID],
        a.[Observation_ID]
    FROM [dbo].[Annotation] a
    JOIN [dbo].[AnnotationKind] at
        ON at.[AnnotationKind_ID] = a.[AnnotationKind_ID]
    JOIN [dbo].[Stream] s
        ON s.[Stream_ID] = a.[Stream_ID]
    LEFT JOIN [dbo].[Person] p
        ON p.[Person_ID] = a.[AuthorPerson_ID]
    LEFT JOIN [dbo].[Campaign] c
        ON c.[Campaign_ID] = a.[Campaign_ID]
"""


# ---------------------------------------------------------------------------
# Query 1: Annotations overlapping a time range for a single Stream
#
# A Stream is either a sensor Channel or a lab AnalysisSeries (both share
# Stream_ID as their PK), so the former channel/series split collapses to one
# query filtering on the single Stream_ID anchor.
# ---------------------------------------------------------------------------


def get_annotations_for_stream(
    conn: pyodbc.Connection,
    stream_id: int,
    from_dt: datetime,
    to_dt: datetime,
    annotation_kind_id: int | None = None,
) -> list[dict]:
    where = (
        "WHERE a.[Stream_ID] = ?"
        "  AND a.[StartTime] <= ?"
        "  AND (a.[EndTime] IS NULL OR a.[EndTime] >= ?)"
    )
    params: list = [stream_id, to_dt, from_dt]

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


# Column list shared by both halves of the cross-stream feeds. The first 18
# columns match the _row_to_annotation index contract (0..17); columns 18/19 are
# the enrichment context (LocationName, ParameterName) the service bolts on.
# Both halves now anchor on the single Stream_ID. The sensor half inner-joins
# Channel on Stream_ID (which restricts it to sensor streams) to enrich with the
# channel Parameter; the lab half inner-joins AnalysisSeries on Stream_ID (which
# restricts it to lab streams) for SamplingPoint + Parameter. Column 16 carries
# StreamKind_ID so the read path can label the anchor without re-deriving it.
_FEED_SENSOR_HALF = """
    SELECT
        a.[Annotation_ID],
        a.[Stream_ID],
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
        s.[StreamKind_ID],
        a.[Observation_ID],
        CAST(NULL AS NVARCHAR(100)) AS LocationName,
        par.[Parameter]           AS ParameterName
    FROM [dbo].[Annotation] a
    JOIN [dbo].[AnnotationKind] at
        ON at.[AnnotationKind_ID] = a.[AnnotationKind_ID]
    JOIN [dbo].[Stream] s
        ON s.[Stream_ID] = a.[Stream_ID]
    JOIN [dbo].[Channel] ch
        ON ch.[Stream_ID] = a.[Stream_ID]
    LEFT JOIN [dbo].[Parameter] par
        ON par.[Parameter_ID] = ch.[Parameter_ID]
    LEFT JOIN [dbo].[Person] p
        ON p.[Person_ID] = a.[AuthorPerson_ID]
    LEFT JOIN [dbo].[Campaign] c
        ON c.[Campaign_ID] = a.[Campaign_ID]
    WHERE 1 = 1
"""

_FEED_LAB_HALF = """
    SELECT
        a.[Annotation_ID],
        a.[Stream_ID],
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
        s.[StreamKind_ID],
        a.[Observation_ID],
        sp.[SamplingPoint]        AS LocationName,
        par.[Parameter]           AS ParameterName
    FROM [dbo].[Annotation] a
    JOIN [dbo].[AnnotationKind] at
        ON at.[AnnotationKind_ID] = a.[AnnotationKind_ID]
    JOIN [dbo].[Stream] s
        ON s.[Stream_ID] = a.[Stream_ID]
    JOIN [dbo].[AnalysisSeries] ser
        ON ser.[Stream_ID] = a.[Stream_ID]
    LEFT JOIN [dbo].[SamplingPoint] sp
        ON sp.[SamplingPoint_ID] = ser.[SamplingPoint_ID]
    LEFT JOIN [dbo].[Parameter] par
        ON par.[Parameter_ID] = ser.[Parameter_ID]
    LEFT JOIN [dbo].[Person] p
        ON p.[Person_ID] = a.[AuthorPerson_ID]
    LEFT JOIN [dbo].[Campaign] c
        ON c.[Campaign_ID] = a.[Campaign_ID]
    WHERE 1 = 1
"""


def _feed_row(row) -> dict:
    d = _row_to_annotation(row)
    d["location_name"] = row[18]
    d["parameter_name"] = row[19]
    return d


def get_annotations_by_kind(
    conn: pyodbc.Connection,
    annotation_kind_id: int,
    from_dt: datetime,
    to_dt: datetime,
) -> list[dict]:
    # The kind + time-range filter applies to BOTH halves, so each half carries
    # its own WHERE clause; the UNION ALL combines them and ORDER BY sorts the
    # whole result set.
    time_filter = (
        "  AND a.[AnnotationKind_ID] = ?"
        "  AND a.[StartTime] <= ?"
        "  AND (a.[EndTime] IS NULL OR a.[EndTime] >= ?)"
    )
    sql = (
        _FEED_SENSOR_HALF
        + time_filter
        + "\nUNION ALL\n"
        + _FEED_LAB_HALF
        + time_filter
        + "\nORDER BY [StartTime]"
    )
    # Params repeat once per half (sensor first, then lab).
    params = [annotation_kind_id, to_dt, from_dt, annotation_kind_id, to_dt, from_dt]
    cursor = conn.cursor()
    cursor.execute(sql, *params)
    return [_feed_row(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Query 3: Recent annotations (dashboard feed)
# ---------------------------------------------------------------------------


def get_recent_annotations(
    conn: pyodbc.Connection,
    limit: int = 20,
    annotation_kind_id: int | None = None,
) -> list[dict]:
    # UNION ALL the sensor + lab halves, then apply TOP/ORDER BY to the combined
    # set so the limit and recency ordering span both streams (not per-half).
    kind_filter = ""
    half_params: list = []
    if annotation_kind_id is not None:
        kind_filter = "  AND a.[AnnotationKind_ID] = ?"
        half_params = [annotation_kind_id]

    union = (
        _FEED_SENSOR_HALF + kind_filter + "\nUNION ALL\n" + _FEED_LAB_HALF + kind_filter
    )
    sql = (
        "SELECT TOP (?) * FROM (\n"
        + union
        + "\n) AS feed\n"
        + "ORDER BY feed.[CreatedDateTime] DESC"
    )
    # limit first, then the kind filter for each half (sensor, then lab).
    params: list = [limit, *half_params, *half_params]
    cursor = conn.cursor()
    cursor.execute(sql, *params)
    return [_feed_row(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Query: list all annotations (optional channel filter)
# ---------------------------------------------------------------------------


def list_annotations(
    conn: pyodbc.Connection,
    stream_id: int | None = None,
) -> list[dict]:
    where = " WHERE a.[Stream_ID] = ?" if stream_id is not None else ""
    params: list = [stream_id] if stream_id is not None else []
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
# Observation → anchor resolution (for the point-pin integrity guard)
# ---------------------------------------------------------------------------


def get_observation_anchor(
    conn: pyodbc.Connection, observation_id: int
) -> int | None:
    """Resolve an Observation to the Stream_ID it belongs to.

    A sensor observation carries Channel_ID (= the channel's Stream_ID); a lab
    observation reaches its AnalysisSeries via Observation → LabAnalysis (whose
    AnalysisSeries_ID is the series' Stream_ID). Either way the result is a
    single Stream_ID. Returns ``None`` if the Observation does not exist.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COALESCE(o.[Channel_ID], la.[AnalysisSeries_ID]) AS Stream_ID
        FROM [dbo].[Observation] o
        LEFT JOIN [dbo].[LabAnalysis] la
            ON la.[LabAnalysis_ID] = o.[LabAnalysis_ID]
        WHERE o.[Observation_ID] = ?
        """,
        observation_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return row[0]


# ---------------------------------------------------------------------------
# Query 4: Insert annotation
# ---------------------------------------------------------------------------


def create_annotation(
    conn: pyodbc.Connection,
    *,
    stream_id: int,
    annotation_kind_id: int,
    start_time: datetime,
    end_time: datetime | None,
    author_person_id: int | None,
    campaign_id: int | None,
    equipment_event_id: int | None,
    title: str | None,
    comment: str | None,
    observation_id: int | None = None,
) -> dict:
    """Insert an annotation anchored to a single Stream.

    ``stream_id`` is the non-NULL Stream FK — a sensor Channel or a lab
    AnalysisSeries (both share Stream_ID as their PK), replacing the former
    Channel_ID / AnalysisSeries_ID XOR. ``observation_id`` is the optional
    point pin (one exact Observation).
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[Annotation] (
            [Stream_ID], [AnnotationKind_ID],
            [StartTime], [EndTime],
            [AuthorPerson_ID], [Campaign_ID], [EquipmentEvent_ID],
            [Title], [Comment], [Observation_ID]
        )
        OUTPUT INSERTED.[Annotation_ID], INSERTED.[CreatedDateTime]
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        stream_id,
        annotation_kind_id,
        start_time,
        end_time,
        author_person_id,
        campaign_id,
        equipment_event_id,
        title,
        comment,
        observation_id,
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
    stream_ids: list[int],
    annotation_kind_id: int,
    title: str,
    comment: str,
    start_time: datetime,
) -> list[int]:
    """Create annotations on multiple streams (channels) for an equipment move.

    Returns the list of created Annotation_IDs.
    """
    annotation_ids: list[int] = []
    for stream_id in stream_ids:
        result = create_annotation(
            conn,
            stream_id=stream_id,
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
