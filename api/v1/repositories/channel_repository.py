"""Data access for Channel with all FK joins resolved."""

from __future__ import annotations

from datetime import datetime

import pyodbc

# Channel is the Sensor subtype of Stream (StreamKind discriminator: 1=Sensor,
# 2=Lab). Minting a Stream row yields the shared Stream_ID used as the Channel PK.
STREAM_KIND_SENSOR = 1

_CHANNEL_SELECT = """
    SELECT
        c.[Stream_ID],
        c.[SignalInterface_ID],
        si.[Name]                    AS SignalInterfaceName,
        c.[TagName],
        c.[SignalInterfacePort_ID],
        sip.[PortIdentifier]         AS SignalInterfacePortIdentifier,
        c.[ParentChannel_ID],
        parent.[TagName]             AS ParentChannelTagName,
        c.[ChannelKind_ID],
        cr.[Name]                    AS ChannelKindName,
        c.[Parameter_ID],
        p.[Parameter]                AS ParameterName,
        c.[DataProvenanceKind_ID],
        dp.[Name]                    AS DataProvenanceKindName,
        c.[ProducedByStep_ID],
        c.[ValueKind_ID],
        vt.[Name]                    AS ValueKindName,
        c.[Unit_ID],
        u.[Unit]                     AS UnitName,
        ewh.[Equipment_ID],
        e.[Identifier]               AS EquipmentIdentifier
    FROM [dbo].[vw_ChannelResolved] c
    LEFT JOIN [dbo].[SignalInterface]          si  ON si.[SignalInterface_ID]  = c.[SignalInterface_ID]
    LEFT JOIN [dbo].[SignalInterfacePort]      sip ON sip.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
    LEFT JOIN [dbo].[Channel]                  parent ON parent.[Stream_ID] = c.[ParentChannel_ID]
    LEFT JOIN [dbo].[ChannelKind]              cr  ON cr.[ChannelKind_ID]    = c.[ChannelKind_ID]
    LEFT JOIN [dbo].[Parameter]                p   ON p.[Parameter_ID]       = c.[Parameter_ID]
    LEFT JOIN [dbo].[DataProvenanceKind]       dp  ON dp.[DataProvenanceKind_ID] = c.[DataProvenanceKind_ID]
    LEFT JOIN [dbo].[ValueKind]                vt  ON vt.[ValueKind_ID]      = c.[ValueKind_ID]
    LEFT JOIN [dbo].[Unit]                     u   ON u.[Unit_ID]            = c.[Unit_ID]
    LEFT JOIN [dbo].[EquipmentWiringHistory]   ewh ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
                                                 AND (
                                                      ewh.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
                                                      OR (ewh.[SignalInterfacePort_ID] IS NULL AND c.[SignalInterfacePort_ID] IS NULL)
                                                      OR c.[SignalInterfacePort_ID] IS NULL
                                                     )
                                                 AND ewh.[ValidTo] IS NULL
    LEFT JOIN [dbo].[Equipment]                e   ON e.[Equipment_ID]       = ewh.[Equipment_ID]
"""

_CHANNEL_SELECT_WITH_CAMPAIGN = """
    SELECT
        c.[Stream_ID],
        c.[SignalInterface_ID],
        si.[Name]                    AS SignalInterfaceName,
        c.[TagName],
        c.[SignalInterfacePort_ID],
        sip.[PortIdentifier]         AS SignalInterfacePortIdentifier,
        c.[ParentChannel_ID],
        parent.[TagName]             AS ParentChannelTagName,
        c.[ChannelKind_ID],
        cr.[Name]                    AS ChannelKindName,
        c.[Parameter_ID],
        p.[Parameter]                AS ParameterName,
        c.[DataProvenanceKind_ID],
        dp.[Name]                    AS DataProvenanceKindName,
        c.[ProducedByStep_ID],
        c.[ValueKind_ID],
        vt.[Name]                    AS ValueKindName,
        c.[Unit_ID],
        u.[Unit]                     AS UnitName,
        ewh.[Equipment_ID],
        e.[Identifier]               AS EquipmentIdentifier
    FROM [dbo].[vw_ChannelResolved] c
    LEFT JOIN [dbo].[SignalInterface]          si  ON si.[SignalInterface_ID]  = c.[SignalInterface_ID]
    LEFT JOIN [dbo].[SignalInterfacePort]      sip ON sip.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
    LEFT JOIN [dbo].[Channel]                  parent ON parent.[Stream_ID] = c.[ParentChannel_ID]
    LEFT JOIN [dbo].[ChannelKind]              cr  ON cr.[ChannelKind_ID]    = c.[ChannelKind_ID]
    LEFT JOIN [dbo].[Parameter]                p   ON p.[Parameter_ID]       = c.[Parameter_ID]
    LEFT JOIN [dbo].[DataProvenanceKind]       dp  ON dp.[DataProvenanceKind_ID] = c.[DataProvenanceKind_ID]
    LEFT JOIN [dbo].[ValueKind]                vt  ON vt.[ValueKind_ID]      = c.[ValueKind_ID]
    LEFT JOIN [dbo].[Unit]                     u   ON u.[Unit_ID]            = c.[Unit_ID]
    LEFT JOIN [dbo].[EquipmentWiringHistory]   ewh ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
                                                 AND (
                                                      ewh.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
                                                      OR (ewh.[SignalInterfacePort_ID] IS NULL AND c.[SignalInterfacePort_ID] IS NULL)
                                                      OR c.[SignalInterfacePort_ID] IS NULL
                                                     )
                                                 AND ewh.[ValidTo] IS NULL
    LEFT JOIN [dbo].[Equipment]                e   ON e.[Equipment_ID]       = ewh.[Equipment_ID]
    LEFT JOIN [dbo].[CampaignEquipment]        ce  ON ce.[Equipment_ID]      = e.[Equipment_ID]
"""


def _row_to_dict(row) -> dict:
    return {
        "channel_id": row[0],
        "signal_interface_id": row[1],
        "signal_interface_name": row[2],
        "tag_name": row[3],
        "signal_interface_port_id": row[4],
        "signal_interface_port_identifier": row[5],
        "parent_channel_id": row[6],
        "parent_channel_tag_name": row[7],
        "channel_kind_id": row[8],
        "channel_kind_name": row[9],
        "parameter_id": row[10],
        "parameter_name": row[11],
        "data_provenance_kind_id": row[12],
        "data_provenance_kind_name": row[13],
        "produced_by_step_id": row[14],
        "value_kind_id": row[15],
        "value_kind_name": row[16],
        "unit_id": row[17],
        "unit_name": row[18],
        "equipment_id": row[19],
        "equipment_identifier": row[20],
    }


def list_channels(
    conn: pyodbc.Connection,
    *,
    parameter_id: int | None = None,
    data_provenance_kind_id: int | None = None,
    equipment_id: int | None = None,
    signal_interface_id: int | None = None,
    value_kind_id: int | None = None,
    campaign_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict], int]:
    """Return a page of Channel rows with filters. Returns (items, total)."""
    # When filtering by campaign we join CampaignEquipment via EquipmentWiringHistory
    use_campaign = campaign_id is not None
    base_select = _CHANNEL_SELECT_WITH_CAMPAIGN if use_campaign else _CHANNEL_SELECT

    where_parts = []
    params = []

    if use_campaign:
        where_parts.append("(ce.[Campaign_ID] = ? OR ce.[Campaign_ID] IS NULL)")
        params.append(campaign_id)
    if parameter_id is not None:
        where_parts.append("c.[Parameter_ID] = ?")
        params.append(parameter_id)
    if data_provenance_kind_id is not None:
        where_parts.append("c.[DataProvenanceKind_ID] = ?")
        params.append(data_provenance_kind_id)
    if signal_interface_id is not None:
        where_parts.append("c.[SignalInterface_ID] = ?")
        params.append(signal_interface_id)
    if equipment_id is not None:
        where_parts.append("ewh.[Equipment_ID] = ?")
        params.append(equipment_id)
    if value_kind_id is not None:
        where_parts.append("c.[ValueKind_ID] = ?")
        params.append(value_kind_id)

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    if use_campaign:
        count_sql = (
            f"SELECT COUNT(*) FROM [dbo].[vw_ChannelResolved] c "
            f"LEFT JOIN [dbo].[EquipmentWiringHistory] ewh "
            f"    ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID] "
            f"    AND (ewh.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID] "
            f"         OR (ewh.[SignalInterfacePort_ID] IS NULL AND c.[SignalInterfacePort_ID] IS NULL) "
            f"         OR c.[SignalInterfacePort_ID] IS NULL) "
            f"    AND ewh.[ValidTo] IS NULL "
            f"LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID] "
            f"LEFT JOIN [dbo].[CampaignEquipment] ce "
            f"    ON ce.[Equipment_ID] = e.[Equipment_ID] "
            f"{where_clause}"
        )
    else:
        if equipment_id is not None:
            count_sql = (
                f"SELECT COUNT(*) FROM [dbo].[vw_ChannelResolved] c "
                f"LEFT JOIN [dbo].[EquipmentWiringHistory] ewh "
                f"    ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID] "
                f"    AND (ewh.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID] "
                f"         OR (ewh.[SignalInterfacePort_ID] IS NULL AND c.[SignalInterfacePort_ID] IS NULL) "
                f"         OR c.[SignalInterfacePort_ID] IS NULL) "
                f"    AND ewh.[ValidTo] IS NULL "
                f"{where_clause}"
            )
        else:
            count_sql = f"SELECT COUNT(*) FROM [dbo].[Channel] c {where_clause}"

    cursor = conn.cursor()
    cursor.execute(count_sql, *params)
    _count_row = cursor.fetchone()
    assert _count_row is not None
    total: int = _count_row[0]

    offset = (page - 1) * page_size
    data_sql = (
        base_select
        + f" {where_clause} "
        + "ORDER BY c.[Stream_ID] "
        + f"OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
    )
    cursor.execute(data_sql, *params)
    items = [_row_to_dict(row) for row in cursor.fetchall()]
    return items, total


def get_channel_by_id(conn: pyodbc.Connection, channel_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(_CHANNEL_SELECT + " WHERE c.[Stream_ID] = ?", channel_id)
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def _insert_stream(cursor: pyodbc.Cursor, stream_kind_id: int) -> int:
    """Mint a Stream supertype row and return its new Stream_ID (ADR 0004)."""
    cursor.execute(
        "INSERT INTO [dbo].[Stream] ([StreamKind_ID]) "
        "OUTPUT INSERTED.[Stream_ID] VALUES (?)",
        stream_kind_id,
    )
    return int(cursor.fetchone()[0])


def set_channel_active_port(
    cursor: pyodbc.Cursor,
    channel_id: int,
    port_id: int | None,
    valid_from: datetime | str | None = None,
    gating_note: str | None = None,
) -> tuple[int | None, int | None]:
    """Make ``port_id`` the channel's active ChannelPortHistory row.

    The single writer of the CPH active-row invariant: closes the current
    active row (if any) and opens a new one, in the caller's transaction (does
    NOT commit). No-op when the requested port already matches the active row,
    so it never churns rows. Passing ``port_id=None`` closes the active row
    without opening a new one (the channel becomes untraced).

    Returns ``(new_cph_id, closed_cph_id)``; either may be ``None``.
    """
    cursor.execute(
        "SELECT [ChannelPortHistory_ID], [SignalInterfacePort_ID] "
        "FROM [dbo].[ChannelPortHistory] "
        "WHERE [Channel_ID] = ? AND [ValidTo] IS NULL",
        channel_id,
    )
    active = cursor.fetchone()
    active_port = active[1] if active else None
    if active_port == port_id:
        return None, active[0] if active else None  # already current — no churn

    closed_id: int | None = None
    ts = valid_from
    if active is not None:
        if ts is None:
            cursor.execute(
                "UPDATE [dbo].[ChannelPortHistory] SET [ValidTo] = SYSUTCDATETIME() "
                "OUTPUT DELETED.[ChannelPortHistory_ID] "
                "WHERE [Channel_ID] = ? AND [ValidTo] IS NULL",
                channel_id,
            )
        else:
            cursor.execute(
                "UPDATE [dbo].[ChannelPortHistory] SET [ValidTo] = ? "
                "OUTPUT DELETED.[ChannelPortHistory_ID] "
                "WHERE [Channel_ID] = ? AND [ValidTo] IS NULL",
                ts,
                channel_id,
            )
        closed_id = cursor.fetchone()[0]

    new_id: int | None = None
    if port_id is not None:
        if ts is None:
            cursor.execute(
                "INSERT INTO [dbo].[ChannelPortHistory] "
                "([Channel_ID], [SignalInterfacePort_ID], [ValidFrom], [GatingNote]) "
                "OUTPUT INSERTED.[ChannelPortHistory_ID] "
                "VALUES (?, ?, SYSUTCDATETIME(), ?)",
                channel_id,
                port_id,
                gating_note,
            )
        else:
            cursor.execute(
                "INSERT INTO [dbo].[ChannelPortHistory] "
                "([Channel_ID], [SignalInterfacePort_ID], [ValidFrom], [GatingNote]) "
                "OUTPUT INSERTED.[ChannelPortHistory_ID] "
                "VALUES (?, ?, ?, ?)",
                channel_id,
                port_id,
                ts,
                gating_note,
            )
        new_id = int(cursor.fetchone()[0])
    return new_id, closed_id


def insert_channel(conn: pyodbc.Connection, data: dict) -> dict | None:
    """Insert a new channel and return the created record.

    Channel.Stream_ID is a shared (non-identity) primary key: a Stream row is
    minted first to obtain the id, then the Channel row is inserted with it
    (ADR 0004). The previous ``SELECT @@IDENTITY`` path was invalid under the
    Stream-supertype schema.
    """
    cursor = conn.cursor()
    new_id = _insert_stream(cursor, STREAM_KIND_SENSOR)
    cursor.execute(
        "INSERT INTO [dbo].[Channel] "
        "([Stream_ID], [SignalInterface_ID], [TagName], [ParentChannel_ID], "
        "[ChannelKind_ID], [Parameter_ID], [DataProvenanceKind_ID], [ProducedByStep_ID], [ValueKind_ID], [Unit_ID])"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        new_id,
        data.get("signal_interface_id"),
        data.get("tag_name"),
        data.get("parent_channel_id"),
        data.get("channel_kind_id", 1),  # Default to 'Value' kind
        data.get("parameter_id"),
        data.get("data_provenance_kind_id"),
        data.get("produced_by_step_id"),
        data.get("value_kind_id") or 1,  # Default to Scalar; dict.get's default
        # arg won't fire since model_dump() always includes the key as None.
        data.get("unit_id"),
    )
    # The port is no longer a Channel column (F3): record it as the active
    # ChannelPortHistory row. Only when a port is actually supplied.
    if data.get("signal_interface_port_id") is not None:
        set_channel_active_port(cursor, new_id, data["signal_interface_port_id"])
    conn.commit()
    return get_channel_by_id(conn, new_id)


def update_channel(conn: pyodbc.Connection, channel_id: int, data: dict) -> dict | None:
    """Update an existing channel and return the updated record."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Channel]"
        " SET [SignalInterface_ID]=?, [TagName]=?, [ParentChannel_ID]=?, "
        "[ChannelKind_ID]=?, [Parameter_ID]=?, [DataProvenanceKind_ID]=?, [ProducedByStep_ID]=?, [ValueKind_ID]=?, [Unit_ID]=?"
        " WHERE [Stream_ID]=?",
        data.get("signal_interface_id"),
        data.get("tag_name"),
        data.get("parent_channel_id"),
        data.get("channel_kind_id", 1),
        data.get("parameter_id"),
        data.get("data_provenance_kind_id"),
        data.get("produced_by_step_id"),
        data.get("value_kind_id") or 1,
        data.get("unit_id"),
        channel_id,
    )
    # The port is no longer a Channel column (F3): reflect a provided port change
    # in ChannelPortHistory. Only act when the caller explicitly sent the field
    # (a PATCH that omits it must not clear the port).
    if "signal_interface_port_id" in data:
        set_channel_active_port(cursor, channel_id, data["signal_interface_port_id"])
    conn.commit()
    return get_channel_by_id(conn, channel_id)


def delete_channel(conn: pyodbc.Connection, channel_id: int) -> bool:
    """Delete a channel by ID. Returns True if deleted, False if not found."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Channel] WHERE [Stream_ID]=?", channel_id)
    conn.commit()
    return cursor.rowcount > 0


def find_channel_by_signal_interface_tag(
    conn: pyodbc.Connection,
    *,
    signal_interface_id: int,
    tag_name: str,
    parameter_id: int | None = None,
) -> dict | None:
    """Return a Channel row matching the signal interface + tag (+ optional parameter).

    Returns ``None`` when no match exists.
    """
    cursor = conn.cursor()
    sql = _CHANNEL_SELECT + " WHERE c.[SignalInterface_ID] = ? AND c.[TagName] = ?"
    params = [signal_interface_id, tag_name]
    if parameter_id is not None:
        sql += " AND c.[Parameter_ID] = ?"
        params.append(parameter_id)
    cursor.execute(sql, *params)
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def find_channel_by_identity(
    conn: pyodbc.Connection,
    *,
    signal_interface_id: int | None,
    tag_name: str,
    parameter_id: int,
    data_provenance_id: int,
    produced_by_step_id: int | None = None,
) -> dict | None:
    """Return a Channel row matching the full stream identity.

    Returns ``None`` when no match exists.
    """
    cursor = conn.cursor()
    sql = (
        _CHANNEL_SELECT
        + " WHERE c.[TagName] = ?"
        + "   AND c.[Parameter_ID] = ?"
        + "   AND c.[DataProvenanceKind_ID] = ?"
    )
    params: list = [tag_name, parameter_id, data_provenance_id]
    if signal_interface_id is None:
        sql += "   AND c.[SignalInterface_ID] IS NULL"
    else:
        sql += "   AND c.[SignalInterface_ID] = ?"
        params.append(signal_interface_id)
    if produced_by_step_id is None:
        sql += "   AND c.[ProducedByStep_ID] IS NULL"
    else:
        sql += "   AND c.[ProducedByStep_ID] = ?"
        params.append(produced_by_step_id)
    cursor.execute(sql, *params)
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def find_or_create_channel(
    conn: pyodbc.Connection,
    *,
    signal_interface_id: int,
    tag_name: str,
    parameter_id: int | None = None,
) -> dict | None:
    """Find or create a minimal Channel by (SignalInterface_ID, TagName, Parameter_ID?).

    Returns the existing or newly-created channel dict.
    """
    existing = find_channel_by_signal_interface_tag(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=parameter_id,
    )
    if existing is not None:
        return existing

    data = {
        "signal_interface_id": signal_interface_id,
        "tag_name": tag_name,
        "parameter_id": parameter_id,
        "channel_kind_id": 1,
        "value_kind_id": 1,
    }
    return insert_channel(conn, data)


def get_channel_ids_for_equipment(
    conn: pyodbc.Connection, equipment_id: int
) -> list[int]:
    """Return all Channel_IDs currently associated with *equipment_id* via active wiring.

    Matches the same join semantics used in ``_CHANNEL_SELECT``:
    - SignalInterface_ID must match
    - AND (SignalInterfacePort_ID matches exactly, OR either side is NULL)
    - AND EquipmentWiringHistory.ValidTo IS NULL (active wiring only)
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.[Stream_ID]
        FROM [dbo].[vw_ChannelResolved] c
        JOIN [dbo].[EquipmentWiringHistory] ewh
            ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
            AND (
                ewh.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
                OR (ewh.[SignalInterfacePort_ID] IS NULL AND c.[SignalInterfacePort_ID] IS NULL)
                OR c.[SignalInterfacePort_ID] IS NULL
            )
            AND ewh.[ValidTo] IS NULL
        WHERE ewh.[Equipment_ID] = ?
        """,
        equipment_id,
    )
    return [row[0] for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Stream Story — read-only "what is this stream" summary for the Explore page.
# Works for both Stream subtypes: a sensor Channel or a lab AnalysisSeries.
# ---------------------------------------------------------------------------


def get_stream_story(conn: pyodbc.Connection, stream_id: int) -> dict | None:
    """Summarise one stream: what it records, its data span, where it has been,
    and the annotations on it. Returns None if the stream id is unknown."""
    cur = conn.cursor()

    cur.execute(
        """
        SELECT p.[Parameter], u.[Unit], vk.[Name] AS value_kind, c.[TagName]
        FROM [dbo].[Channel] c
        LEFT JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = c.[Parameter_ID]
        LEFT JOIN [dbo].[Unit] u ON u.[Unit_ID] = c.[Unit_ID]
        LEFT JOIN [dbo].[ValueKind] vk ON vk.[ValueKind_ID] = c.[ValueKind_ID]
        WHERE c.[Stream_ID] = ?
        """,
        stream_id,
    )
    row = cur.fetchone()
    if row is not None:
        kind = "sensor"
        record = {
            "kind": kind, "parameter_name": row[0], "unit_name": row[1],
            "value_kind_name": row[2], "label": row[3],
        }
        cur.execute(
            "SELECT MIN(o.[Timestamp]), MAX(o.[Timestamp]), COUNT(*) "
            "FROM [dbo].[Observation] o WHERE o.[Channel_ID] = ?",
            stream_id,
        )
        srow = cur.fetchone()
        # Location history via the producing equipment's installations.
        cur.execute(
            """
            SELECT DISTINCT sp.[SamplingPoint], elh.[ValidFrom], elh.[ValidTo],
                   e.[Identifier]
            FROM [dbo].[Channel] c
            JOIN [dbo].[EquipmentWiringHistory] ewh
                ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
            JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
            JOIN [dbo].[EquipmentLocationHistory] elh ON elh.[Equipment_ID] = e.[Equipment_ID]
            JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
            WHERE c.[Stream_ID] = ?
            ORDER BY elh.[ValidFrom] DESC
            """,
            stream_id,
        )
        locations = [
            {"location": x[0], "valid_from": x[1], "valid_to": x[2], "equipment": x[3]}
            for x in cur.fetchall()
        ]
    else:
        cur.execute(
            """
            SELECT p.[Parameter], u.[Unit], vk.[Name] AS value_kind, a.[Name],
                   sp.[SamplingPoint]
            FROM [dbo].[AnalysisSeries] a
            LEFT JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = a.[Parameter_ID]
            LEFT JOIN [dbo].[Unit] u ON u.[Unit_ID] = a.[Unit_ID]
            LEFT JOIN [dbo].[ValueKind] vk ON vk.[ValueKind_ID] = a.[ValueKind_ID]
            LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = a.[SamplingPoint_ID]
            WHERE a.[Stream_ID] = ?
            """,
            stream_id,
        )
        row = cur.fetchone()
        if row is None:
            return None
        record = {
            "kind": "lab", "parameter_name": row[0], "unit_name": row[1],
            "value_kind_name": row[2], "label": row[3],
        }
        cur.execute(
            """
            SELECT MIN(o.[Timestamp]), MAX(o.[Timestamp]), COUNT(*)
            FROM [dbo].[Observation] o
            JOIN [dbo].[LabAnalysis] la ON la.[LabAnalysis_ID] = o.[LabAnalysis_ID]
            WHERE la.[AnalysisSeries_ID] = ?
            """,
            stream_id,
        )
        srow = cur.fetchone()
        # A lab series has a single, explicit origin (its sampling point).
        locations = (
            [{"location": row[4], "valid_from": None, "valid_to": None, "equipment": None}]
            if row[4]
            else []
        )

    record["first_point"] = srow[0] if srow else None
    record["last_point"] = srow[1] if srow else None
    record["point_count"] = (srow[2] if srow else 0) or 0

    cur.execute(
        """
        SELECT a.[Annotation_ID], ak.[Name], ak.[Color], a.[Title], a.[Comment],
               a.[StartTime], a.[EndTime]
        FROM [dbo].[Annotation] a
        LEFT JOIN [dbo].[AnnotationKind] ak ON ak.[AnnotationKind_ID] = a.[AnnotationKind_ID]
        WHERE a.[Stream_ID] = ?
        ORDER BY a.[StartTime] DESC
        """,
        stream_id,
    )
    annotations = [
        {"id": x[0], "kind": x[1], "color": x[2], "title": x[3], "comment": x[4],
         "start_time": x[5], "end_time": x[6]}
        for x in cur.fetchall()
    ]

    return {"stream_id": stream_id, "record": record,
            "location_history": locations, "annotations": annotations}


def _pedigree_sampling_point(cur: pyodbc.Cursor, sp_id: int | None):
    """Resolve (sampling_location, process_unit, site) for a sampling point."""
    if sp_id is None:
        return None, None, None
    cur.execute(
        """
        SELECT sp.[SamplingPoint], sp.[LatitudeWGS84], sp.[LongitudeWGS84],
               pu.[ProcessUnit_ID], pu.[Tag], pu.[Name], puk.[Name] AS pu_kind,
               s.[Site_ID], s.[Name], s.[City], s.[Province], s.[Country]
        FROM [dbo].[SamplingPoint] sp
        LEFT JOIN [dbo].[ProcessUnit] pu ON pu.[ProcessUnit_ID] = sp.[ProcessUnit_ID]
        LEFT JOIN [dbo].[ProcessUnitKind] puk ON puk.[ProcessUnitKind_ID] = pu.[ProcessUnitKind_ID]
        LEFT JOIN [dbo].[Site] s ON s.[Site_ID] = sp.[Site_ID]
        WHERE sp.[SamplingPoint_ID] = ?
        """,
        sp_id,
    )
    r = cur.fetchone()
    if r is None:
        return None, None, None
    location = {"sampling_point_id": sp_id, "name": r[0],
                "latitude": r[1], "longitude": r[2]}
    process_unit = (
        {"process_unit_id": r[3], "tag": r[4], "name": r[5], "kind": r[6]}
        if r[3] is not None else None
    )
    site = (
        {"site_id": r[7], "name": r[8], "city": r[9], "province": r[10], "country": r[11]}
        if r[7] is not None else None
    )
    return location, process_unit, site


def _pedigree_campaign(cur: pyodbc.Cursor, campaign_id: int | None):
    """Resolve (campaign, responsible_person, site_fallback) for a campaign."""
    if campaign_id is None:
        return None, None, None
    cur.execute(
        """
        SELECT c.[Name], ck.[Name] AS campaign_kind,
               c.[CampaignStartDateTime], c.[CampaignEndDateTime],
               per.[Person_ID], per.[FirstName], per.[LastName],
               per.[Email], per.[Role], per.[Company]
        FROM [dbo].[Campaign] c
        LEFT JOIN [dbo].[CampaignKind] ck ON ck.[CampaignKind_ID] = c.[CampaignKind_ID]
        LEFT JOIN [dbo].[Person] per ON per.[Person_ID] = c.[ResponsiblePerson_ID]
        WHERE c.[Campaign_ID] = ?
        """,
        campaign_id,
    )
    r = cur.fetchone()
    if r is None:
        return None, None, None
    campaign = {"campaign_id": campaign_id, "name": r[0], "kind": r[1],
                "start": r[2], "end": r[3]}
    person = None
    if r[4] is not None:
        full_name = " ".join(n for n in (r[5], r[6]) if n)
        person = {"person_id": r[4], "name": full_name or None,
                  "email": r[7], "role": r[8], "company": r[9]}
    # Campaign sites are derived from sampling-location membership; use one as a
    # pedigree fallback only when the campaign is unambiguously single-site.
    cur.execute(
        """
        SELECT DISTINCT s.[Site_ID], s.[Name], s.[City], s.[Province], s.[Country]
        FROM [dbo].[CampaignSamplingLocation] csl
        JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = csl.[SamplingPoint_ID]
        JOIN [dbo].[Site] s ON s.[Site_ID] = sp.[Site_ID]
        WHERE csl.[Campaign_ID] = ?
        """,
        campaign_id,
    )
    site_rows = cur.fetchall()
    site_fallback = None
    if len(site_rows) == 1:
        s = site_rows[0]
        site_fallback = {
            "site_id": s[0], "name": s[1], "city": s[2],
            "province": s[3], "country": s[4],
        }
    return campaign, person, site_fallback


def _pedigree_segment(cur, valid_from, valid_to, equipment_identifier,
                      sp_id, campaign_id) -> dict:
    """Assemble one deployment segment (a slice of the stream's life with a
    stable location + campaign)."""
    location, process_unit, site = _pedigree_sampling_point(cur, sp_id)
    campaign, person, site_fallback = _pedigree_campaign(cur, campaign_id)
    return {
        "valid_from": valid_from,
        "valid_to": valid_to,
        "equipment_identifier": equipment_identifier,
        "sampling_location": location,
        "process_unit": process_unit,
        "site": site or site_fallback,
        "campaign": campaign,
        "responsible_person": person,
    }


def get_stream_pedigree(
    conn: pyodbc.Connection,
    stream_id: int,
    *,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> dict | None:
    """Resolve the organizational/spatial *pedigree* of a stream (distinct from
    its processing *provenance*): the time-invariant identity plus a **deployment
    timeline** of where it lived and which campaign owned it over its life.

    The location/campaign of a sensor channel are *historical*: equipment is
    rewired (EquipmentWiringHistory) and moved between sampling points
    (EquipmentLocationHistory) over time, so a single channel's data can span
    several sampling locations and campaigns. The pedigree therefore returns one
    segment per deployment (with its own ValidFrom/ValidTo), not a single
    snapshot. ``from_dt``/``to_dt`` restrict the timeline to segments overlapping
    that window (i.e. the exported time range). A lab AnalysisSeries has a single,
    fixed sampling point + campaign, so it returns exactly one open segment.

    Returns None if the stream id is unknown.
    """
    cur = conn.cursor()

    # --- Identity (time-invariant) --------------------------------------
    cur.execute(
        """
        SELECT p.[Parameter], u.[Unit], vk.[Name] AS value_kind, c.[TagName]
        FROM [dbo].[Channel] c
        LEFT JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = c.[Parameter_ID]
        LEFT JOIN [dbo].[Unit] u ON u.[Unit_ID] = c.[Unit_ID]
        LEFT JOIN [dbo].[ValueKind] vk ON vk.[ValueKind_ID] = c.[ValueKind_ID]
        WHERE c.[Stream_ID] = ?
        """,
        stream_id,
    )
    row = cur.fetchone()
    if row is not None:
        record = {"kind": "sensor", "parameter": row[0], "unit": row[1],
                  "value_kind": row[2], "label": row[3]}

        # Deployment segments: the EWH×ELH temporal join (mirrors
        # list_deployment_traces), one row per EquipmentLocationHistory the
        # producing equipment occupied, restricted to the requested window.
        where = ["ch.[Stream_ID] = ?"]
        params: list = [stream_id]
        if to_dt is not None:
            where.append("elh.[ValidFrom] <= ?")
            params.append(to_dt)
        if from_dt is not None:
            where.append("(elh.[ValidTo] IS NULL OR elh.[ValidTo] >= ?)")
            params.append(from_dt)
        cur.execute(
            f"""
            SELECT DISTINCT elh.[EquipmentLocationHistory_ID], elh.[ValidFrom],
                   elh.[ValidTo], e.[Identifier], elh.[SamplingPoint_ID],
                   elh.[Campaign_ID]
            FROM [dbo].[vw_ChannelResolved] ch
            JOIN [dbo].[EquipmentWiringHistory] ewh
                ON ewh.[SignalInterface_ID] = ch.[SignalInterface_ID]
                AND (
                    ewh.[SignalInterfacePort_ID] = ch.[SignalInterfacePort_ID]
                    OR (ewh.[SignalInterfacePort_ID] IS NULL AND ch.[SignalInterfacePort_ID] IS NULL)
                    OR ch.[SignalInterfacePort_ID] IS NULL
                )
            JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
            JOIN [dbo].[EquipmentLocationHistory] elh
                ON elh.[Equipment_ID] = e.[Equipment_ID]
                AND ewh.[ValidFrom] <= ISNULL(elh.[ValidTo], GETUTCDATE())
                AND (ewh.[ValidTo] IS NULL OR ewh.[ValidTo] >= elh.[ValidFrom])
            WHERE {" AND ".join(where)}
            ORDER BY elh.[ValidFrom]
            """,
            *params,
        )
        seg_rows = cur.fetchall()
        deployments = [
            _pedigree_segment(cur, r[1], r[2], r[3], r[4], r[5]) for r in seg_rows
        ]
    else:
        cur.execute(
            """
            SELECT p.[Parameter], u.[Unit], vk.[Name] AS value_kind, a.[Name],
                   a.[SamplingPoint_ID], a.[Campaign_ID]
            FROM [dbo].[AnalysisSeries] a
            LEFT JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = a.[Parameter_ID]
            LEFT JOIN [dbo].[Unit] u ON u.[Unit_ID] = a.[Unit_ID]
            LEFT JOIN [dbo].[ValueKind] vk ON vk.[ValueKind_ID] = a.[ValueKind_ID]
            WHERE a.[Stream_ID] = ?
            """,
            stream_id,
        )
        row = cur.fetchone()
        if row is None:
            return None
        record = {"kind": "lab", "parameter": row[0], "unit": row[1],
                  "value_kind": row[2], "label": row[3]}
        # Lab series: a single open segment (its fixed sampling point + campaign).
        deployments = [_pedigree_segment(cur, None, None, None, row[4], row[5])]

    return {"stream_id": stream_id, **record, "deployments": deployments}
