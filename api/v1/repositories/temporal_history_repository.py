"""Repository for at-most-one-active temporal history patterns.

Handles both ``SignalPortEquipmentHistory`` and ``SignalPortLocationHistory``
tables, which share the same constraint: at most one row per ``SignalPort_ID``
with ``EndTime IS NULL`` (the active row).

Provides:
  - Close-and-open swap operations (equipment swap, sensor relocation)
  - At-most-one-active enforcement (the filtered unique index in the DB
    is the final guard; this module enforces the invariant at the
    application layer with an explicit check before INSERT)
  - Point-in-time queries ("what was active at time T?")
  - Helper to retrieve Channel IDs associated with a SignalPort
"""

from __future__ import annotations

from datetime import datetime

import pyodbc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_channels_for_port(conn: pyodbc.Connection, signal_port_id: int) -> list[int]:
    """Return all Channel_IDs whose SignalPort_ID matches *signal_port_id*."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Channel_ID] FROM [dbo].[Channel] WHERE [SignalPort_ID] = ?",
        signal_port_id,
    )
    return [row[0] for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# SignalPortEquipmentHistory
# ---------------------------------------------------------------------------


def get_active_equipment_history(
    conn: pyodbc.Connection, signal_port_id: int
) -> dict | None:
    """Return the currently active SignalPortEquipmentHistory row, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            peh.[SignalPortEquipmentHistory_ID],
            peh.[SignalPort_ID],
            peh.[Equipment_ID],
            peh.[StartTime],
            peh.[EndTime],
            peh.[Notes],
            e.[Identifier]
        FROM [dbo].[SignalPortEquipmentHistory] peh
        LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = peh.[Equipment_ID]
        WHERE peh.[SignalPort_ID] = ? AND peh.[EndTime] IS NULL
        """,
        signal_port_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "history_id": row[0],
        "signal_port_id": row[1],
        "equipment_id": row[2],
        "start_time": row[3],
        "end_time": row[4],
        "notes": row[5],
        "equipment_identifier": row[6],
    }


def swap_equipment(
    conn: pyodbc.Connection,
    signal_port_id: int,
    new_equipment_id: int,
    swap_time: datetime,
    notes: str | None = None,
) -> tuple[int, int | None]:
    """Close the current active equipment history row and open a new one.

    Returns ``(new_history_id, closed_history_id)``.  ``closed_history_id`` is
    ``None`` when there was no active row to close (first registration case).

    The swap is atomic within a single transaction.
    """
    cursor = conn.cursor()
    closed_id: int | None = None

    # Close the active row, if any.
    cursor.execute(
        """
        UPDATE [dbo].[SignalPortEquipmentHistory]
        SET [EndTime] = ?
        OUTPUT DELETED.[SignalPortEquipmentHistory_ID]
        WHERE [SignalPort_ID] = ? AND [EndTime] IS NULL
        """,
        swap_time,
        signal_port_id,
    )
    row = cursor.fetchone()
    if row:
        closed_id = row[0]

    # Open the new row.
    cursor.execute(
        """
        INSERT INTO [dbo].[SignalPortEquipmentHistory]
            ([SignalPort_ID], [Equipment_ID], [StartTime], [Notes])
        OUTPUT INSERTED.[SignalPortEquipmentHistory_ID]
        VALUES (?, ?, ?, ?)
        """,
        signal_port_id,
        new_equipment_id,
        swap_time,
        notes,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id, closed_id


def register_equipment_at_port(
    conn: pyodbc.Connection,
    signal_port_id: int,
    equipment_id: int,
    start_time: datetime | None = None,
    notes: str | None = None,
) -> int:
    """Open a new SignalPortEquipmentHistory row (no active row must exist).

    If ``start_time`` is None, uses SYSUTCDATETIME().

    Raises ``ValueError`` if an active row already exists — callers should use
    ``swap_equipment`` instead.

    Returns ``SignalPortEquipmentHistory_ID``.
    """
    active = get_active_equipment_history(conn, signal_port_id)
    if active is not None:
        raise ValueError(
            f"SignalPort {signal_port_id} already has an active equipment history row "
            f"(ID={active['history_id']}, Equipment_ID={active['equipment_id']}). "
            "Use swap_equipment to replace the current equipment."
        )

    cursor = conn.cursor()
    if start_time is None:
        cursor.execute(
            """
            INSERT INTO [dbo].[SignalPortEquipmentHistory]
                ([SignalPort_ID], [Equipment_ID], [StartTime], [Notes])
            OUTPUT INSERTED.[SignalPortEquipmentHistory_ID]
            VALUES (?, ?, SYSUTCDATETIME(), ?)
            """,
            signal_port_id,
            equipment_id,
            notes,
        )
    else:
        cursor.execute(
            """
            INSERT INTO [dbo].[SignalPortEquipmentHistory]
                ([SignalPort_ID], [Equipment_ID], [StartTime], [Notes])
            OUTPUT INSERTED.[SignalPortEquipmentHistory_ID]
            VALUES (?, ?, ?, ?)
            """,
            signal_port_id,
            equipment_id,
            start_time,
            notes,
        )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def get_equipment_at_time(
    conn: pyodbc.Connection, signal_port_id: int, at_time: datetime
) -> dict | None:
    """Return the equipment that was active at ``at_time``, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            peh.[SignalPortEquipmentHistory_ID],
            peh.[Equipment_ID],
            peh.[StartTime],
            peh.[EndTime],
            e.[Identifier],
            e.[SerialNumber]
        FROM [dbo].[SignalPortEquipmentHistory] peh
        LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = peh.[Equipment_ID]
        WHERE peh.[SignalPort_ID] = ?
          AND peh.[StartTime] <= ?
          AND (peh.[EndTime] IS NULL OR peh.[EndTime] > ?)
        """,
        signal_port_id,
        at_time,
        at_time,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "history_id": row[0],
        "equipment_id": row[1],
        "start_time": row[2],
        "end_time": row[3],
        "equipment_identifier": row[4],
        "serial_number": row[5],
    }


# ---------------------------------------------------------------------------
# SignalPortLocationHistory
# ---------------------------------------------------------------------------


def get_active_location_history(
    conn: pyodbc.Connection, signal_port_id: int
) -> dict | None:
    """Return the currently active SignalPortLocationHistory row, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            lh.[SignalPortLocationHistory_ID],
            lh.[SignalPort_ID],
            lh.[SamplingPoint_ID],
            lh.[StartTime],
            lh.[EndTime],
            lh.[Notes],
            sp.[Name]
        FROM [dbo].[SignalPortLocationHistory] lh
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = lh.[SamplingPoint_ID]
        WHERE lh.[SignalPort_ID] = ? AND lh.[EndTime] IS NULL
        """,
        signal_port_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "history_id": row[0],
        "signal_port_id": row[1],
        "sampling_point_id": row[2],
        "start_time": row[3],
        "end_time": row[4],
        "notes": row[5],
        "sampling_point_name": row[6],
    }


def relocate_sensor(
    conn: pyodbc.Connection,
    signal_port_id: int,
    new_sampling_point_id: int,
    start_time: datetime,
    notes: str | None = None,
) -> tuple[int, int | None, list[int]]:
    """Close the current active location history row and open a new one.

    Returns ``(new_history_id, closed_history_id, channel_ids)`` where
    ``channel_ids`` is the list of Channel_IDs affected (needed for the
    auto-annotation).  ``closed_history_id`` is ``None`` when there was no
    active row to close.

    ``start_time`` is required and must equal the physical move time.
    """
    cursor = conn.cursor()
    closed_id: int | None = None

    # Close the active row, if any.
    cursor.execute(
        """
        UPDATE [dbo].[SignalPortLocationHistory]
        SET [EndTime] = ?
        OUTPUT DELETED.[SignalPortLocationHistory_ID]
        WHERE [SignalPort_ID] = ? AND [EndTime] IS NULL
        """,
        start_time,
        signal_port_id,
    )
    row = cursor.fetchone()
    if row:
        closed_id = row[0]

    # Open the new row.
    cursor.execute(
        """
        INSERT INTO [dbo].[SignalPortLocationHistory]
            ([SignalPort_ID], [SamplingPoint_ID], [StartTime], [Notes])
        OUTPUT INSERTED.[SignalPortLocationHistory_ID]
        VALUES (?, ?, ?, ?)
        """,
        signal_port_id,
        new_sampling_point_id,
        start_time,
        notes,
    )
    new_id: int = cursor.fetchone()[0]

    channel_ids = _get_channels_for_port(conn, signal_port_id)
    conn.commit()
    return new_id, closed_id, channel_ids


def get_location_at_time(
    conn: pyodbc.Connection, signal_port_id: int, at_time: datetime
) -> dict | None:
    """Return the SamplingPoint that was active at ``at_time``, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            lh.[SignalPortLocationHistory_ID],
            lh.[SamplingPoint_ID],
            lh.[StartTime],
            lh.[EndTime],
            sp.[Name],
            sp.[Description]
        FROM [dbo].[SignalPortLocationHistory] lh
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = lh.[SamplingPoint_ID]
        WHERE lh.[SignalPort_ID] = ?
          AND lh.[StartTime] <= ?
          AND (lh.[EndTime] IS NULL OR lh.[EndTime] > ?)
        """,
        signal_port_id,
        at_time,
        at_time,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "history_id": row[0],
        "sampling_point_id": row[1],
        "start_time": row[2],
        "end_time": row[3],
        "sampling_point_name": row[4],
        "sampling_point_description": row[5],
    }
