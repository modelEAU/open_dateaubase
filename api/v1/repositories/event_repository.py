"""Data access for Event and EventKind resources."""

from __future__ import annotations

import pyodbc

# ---------------------------------------------------------------------------
# Column list shared by Event read queries
# ---------------------------------------------------------------------------

_EVENT_SELECT = """
    SELECT
        e.[Event_ID],
        e.[EventKind_ID],
        ek.[Name]                         AS EventKindName,
        e.[IsInstantaneous],
        e.[EventDateTimeStart],
        e.[EventDateTimeEnd],
        e.[PerformedByPerson_ID],
        e.[RecordedByPerson_ID],
        e.[Notes],
        e.[Channel_ID],
        e.[Equipment_ID],
        e.[SignalInterface_ID],
        e.[DataAcquisitionSystem_ID],
        e.[SamplingPoint_ID],
        e.[ProcessUnit_ID],
        e.[Site_ID],
        e.[Campaign_ID]
    FROM [dbo].[Event] e
    JOIN [dbo].[EventKind] ek
        ON ek.[EventKind_ID] = e.[EventKind_ID]
"""


def _row_to_event(row) -> dict:
    return {
        "event_id": row[0],
        "event_kind_id": row[1],
        "event_kind_name": row[2],
        "is_instantaneous": bool(row[3]),
        "start_datetime": row[4],
        "end_datetime": row[5],
        "performed_by_person_id": row[6],
        "recorded_by_person_id": row[7],
        "notes": row[8],
        "channel_id": row[9],
        "equipment_id": row[10],
        "signal_interface_id": row[11],
        "data_acquisition_system_id": row[12],
        "sampling_point_id": row[13],
        "process_unit_id": row[14],
        "site_id": row[15],
        "campaign_id": row[16],
    }


# ---------------------------------------------------------------------------
# EventKind queries
# ---------------------------------------------------------------------------


def get_event_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [EventKind_ID], [Name], [Description]
        FROM [dbo].[EventKind]
        ORDER BY [EventKind_ID]
        """
    )
    return [
        {"event_kind_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def insert_event_kind(
    conn: pyodbc.Connection,
    name: str,
    description: str | None,
) -> dict:
    """Insert a new EventKind row and return it."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[EventKind] ([Name], [Description])"
            " OUTPUT inserted.[EventKind_ID], inserted.[Name], inserted.[Description]"
            " VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {"event_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def update_event_kind(
    conn: pyodbc.Connection,
    event_kind_id: int,
    name: str,
    description: str | None,
) -> dict | None:
    """Update an EventKind row and return it, or None if not found."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[EventKind]"
            " SET [Name]=?, [Description]=?"
            " OUTPUT inserted.[EventKind_ID], inserted.[Name], inserted.[Description]"
            " WHERE [EventKind_ID]=?",
            name,
            description,
            event_kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"event_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def delete_event_kind(conn: pyodbc.Connection, event_kind_id: int) -> bool:
    """Delete an EventKind row. Returns True if a row was deleted."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[EventKind] WHERE [EventKind_ID]=?",
            event_kind_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Event queries
# ---------------------------------------------------------------------------

# The 8 arc FK column names in DB notation (used for dynamic WHERE clauses).
_ARC_DB_COLUMNS = {
    "channel_id": "e.[Channel_ID]",
    "equipment_id": "e.[Equipment_ID]",
    "signal_interface_id": "e.[SignalInterface_ID]",
    "data_acquisition_system_id": "e.[DataAcquisitionSystem_ID]",
    "sampling_point_id": "e.[SamplingPoint_ID]",
    "process_unit_id": "e.[ProcessUnit_ID]",
    "site_id": "e.[Site_ID]",
    "campaign_id": "e.[Campaign_ID]",
}


def get_events(
    conn: pyodbc.Connection,
    *,
    channel_id: int | None = None,
    equipment_id: int | None = None,
    signal_interface_id: int | None = None,
    data_acquisition_system_id: int | None = None,
    sampling_point_id: int | None = None,
    process_unit_id: int | None = None,
    site_id: int | None = None,
    campaign_id: int | None = None,
) -> list[dict]:
    """Return events, optionally filtered by any of the 8 arc FK columns."""
    filters = {
        "channel_id": channel_id,
        "equipment_id": equipment_id,
        "signal_interface_id": signal_interface_id,
        "data_acquisition_system_id": data_acquisition_system_id,
        "sampling_point_id": sampling_point_id,
        "process_unit_id": process_unit_id,
        "site_id": site_id,
        "campaign_id": campaign_id,
    }
    where_parts: list[str] = []
    params: list = []
    for key, value in filters.items():
        if value is not None:
            where_parts.append(f"{_ARC_DB_COLUMNS[key]} = ?")
            params.append(value)

    where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    sql = _EVENT_SELECT + where_clause + " ORDER BY e.[EventDateTimeStart] DESC, e.[Event_ID]"
    cursor = conn.cursor()
    cursor.execute(sql, *params)
    return [_row_to_event(row) for row in cursor.fetchall()]


def get_event_by_id(conn: pyodbc.Connection, event_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(_EVENT_SELECT + " WHERE e.[Event_ID] = ?", event_id)
    row = cursor.fetchone()
    return _row_to_event(row) if row else None


def insert_event(conn: pyodbc.Connection, data: dict) -> dict:
    """INSERT INTO [dbo].[Event] from a dict of field values, return the new row."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO [dbo].[Event] (
                [EventKind_ID],
                [IsInstantaneous],
                [EventDateTimeStart],
                [EventDateTimeEnd],
                [PerformedByPerson_ID],
                [RecordedByPerson_ID],
                [Notes],
                [Channel_ID],
                [Equipment_ID],
                [SignalInterface_ID],
                [DataAcquisitionSystem_ID],
                [SamplingPoint_ID],
                [ProcessUnit_ID],
                [Site_ID],
                [Campaign_ID]
            )
            OUTPUT INSERTED.[Event_ID]
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            data.get("event_kind_id"),
            data.get("is_instantaneous", False),
            data.get("start_datetime"),
            data.get("end_datetime"),
            data.get("performed_by_person_id"),
            data.get("recorded_by_person_id"),
            data.get("notes"),
            data.get("channel_id"),
            data.get("equipment_id"),
            data.get("signal_interface_id"),
            data.get("data_acquisition_system_id"),
            data.get("sampling_point_id"),
            data.get("process_unit_id"),
            data.get("site_id"),
            data.get("campaign_id"),
        )
        row = cursor.fetchone()
        conn.commit()
        return get_event_by_id(conn, row[0])  # type: ignore[return-value]
    except Exception:
        conn.rollback()
        raise


def update_event(conn: pyodbc.Connection, event_id: int, data: dict) -> dict | None:
    """Partial update of an Event row from a dict. Only non-None values are applied."""
    # Map Python keys → DB column names
    column_map = {
        "event_kind_id": "[EventKind_ID]",
        "is_instantaneous": "[IsInstantaneous]",
        "start_datetime": "[EventDateTimeStart]",
        "end_datetime": "[EventDateTimeEnd]",
        "performed_by_person_id": "[PerformedByPerson_ID]",
        "recorded_by_person_id": "[RecordedByPerson_ID]",
        "notes": "[Notes]",
        "channel_id": "[Channel_ID]",
        "equipment_id": "[Equipment_ID]",
        "signal_interface_id": "[SignalInterface_ID]",
        "data_acquisition_system_id": "[DataAcquisitionSystem_ID]",
        "sampling_point_id": "[SamplingPoint_ID]",
        "process_unit_id": "[ProcessUnit_ID]",
        "site_id": "[Site_ID]",
        "campaign_id": "[Campaign_ID]",
    }
    set_parts: list[str] = []
    params: list = []
    for key, col in column_map.items():
        if key in data and data[key] is not None:
            set_parts.append(f"{col} = ?")
            params.append(data[key])

    if not set_parts:
        return get_event_by_id(conn, event_id)

    params.append(event_id)
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"UPDATE [dbo].[Event] SET {', '.join(set_parts)} WHERE [Event_ID] = ?",
            *params,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_event_by_id(conn, event_id)


def delete_event(conn: pyodbc.Connection, event_id: int) -> bool:
    """Hard-delete an Event row. Returns True if a row was deleted."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM [dbo].[Event] WHERE [Event_ID] = ?", event_id)
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise
