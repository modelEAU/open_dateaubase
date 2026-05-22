"""Data access for Channel with all FK joins resolved."""

from __future__ import annotations

import pyodbc

_CHANNEL_SELECT = """
    SELECT
        c.[Channel_ID],
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
    FROM [dbo].[Channel] c
    LEFT JOIN [dbo].[SignalInterface]          si  ON si.[SignalInterface_ID]  = c.[SignalInterface_ID]
    LEFT JOIN [dbo].[SignalInterfacePort]      sip ON sip.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
    LEFT JOIN [dbo].[Channel]                  parent ON parent.[Channel_ID] = c.[ParentChannel_ID]
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
        c.[Channel_ID],
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
    FROM [dbo].[Channel] c
    LEFT JOIN [dbo].[SignalInterface]          si  ON si.[SignalInterface_ID]  = c.[SignalInterface_ID]
    LEFT JOIN [dbo].[SignalInterfacePort]      sip ON sip.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
    LEFT JOIN [dbo].[Channel]                  parent ON parent.[Channel_ID] = c.[ParentChannel_ID]
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
            f"SELECT COUNT(*) FROM [dbo].[Channel] c "
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
                f"SELECT COUNT(*) FROM [dbo].[Channel] c "
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
        + "ORDER BY c.[Channel_ID] "
        + f"OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
    )
    cursor.execute(data_sql, *params)
    items = [_row_to_dict(row) for row in cursor.fetchall()]
    return items, total


def get_channel_by_id(conn: pyodbc.Connection, channel_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(_CHANNEL_SELECT + " WHERE c.[Channel_ID] = ?", channel_id)
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def insert_channel(conn: pyodbc.Connection, data: dict) -> dict | None:
    """Insert a new channel and return the created record."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Channel] "
        "([SignalInterface_ID], [TagName], [SignalInterfacePort_ID], [ParentChannel_ID], "
        "[ChannelKind_ID], [Parameter_ID], [DataProvenanceKind_ID], [ProducedByStep_ID], [ValueKind_ID], [Unit_ID])"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        data.get("signal_interface_id"),
        data.get("tag_name"),
        data.get("signal_interface_port_id"),
        data.get("parent_channel_id"),
        data.get("channel_kind_id", 1),  # Default to 'Value' kind
        data.get("parameter_id"),
        data.get("data_provenance_kind_id"),
        data.get("produced_by_step_id"),
        data.get("value_kind_id", 1),  # Default to Scalar
        data.get("unit_id"),
    )
    cursor.execute("SELECT @@IDENTITY")
    _row = cursor.fetchone()
    assert _row is not None
    new_id = int(_row[0])
    conn.commit()
    return get_channel_by_id(conn, new_id)


def update_channel(conn: pyodbc.Connection, channel_id: int, data: dict) -> dict | None:
    """Update an existing channel and return the updated record."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Channel]"
        " SET [SignalInterface_ID]=?, [TagName]=?, [SignalInterfacePort_ID]=?, [ParentChannel_ID]=?, "
        "[ChannelKind_ID]=?, [Parameter_ID]=?, [DataProvenanceKind_ID]=?, [ProducedByStep_ID]=?, [ValueKind_ID]=?, [Unit_ID]=?"
        " WHERE [Channel_ID]=?",
        data.get("signal_interface_id"),
        data.get("tag_name"),
        data.get("signal_interface_port_id"),
        data.get("parent_channel_id"),
        data.get("channel_kind_id", 1),
        data.get("parameter_id"),
        data.get("data_provenance_kind_id"),
        data.get("produced_by_step_id"),
        data.get("value_kind_id"),
        data.get("unit_id"),
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
        SELECT c.[Channel_ID]
        FROM [dbo].[Channel] c
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
