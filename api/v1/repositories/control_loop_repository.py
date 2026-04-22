"""Repository functions for ControlLoop, ControlLoopPort, and ControlLoopApplication."""

from __future__ import annotations

import logging
from datetime import datetime

import pyodbc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ControlLoop
# ---------------------------------------------------------------------------


def list_control_loops(conn: pyodbc.Connection) -> list[dict]:
    """Return all ControlLoop rows ordered by ControlLoop_ID."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ControlLoop_ID], [Name], [ControllerType],"
        "       [FallbackControlLoop_ID], [AlgorithmReference], [Description]"
        " FROM [dbo].[ControlLoop]"
        " ORDER BY [ControlLoop_ID]"
    )
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def create_control_loop(
    conn: pyodbc.Connection,
    name: str,
    controller_type: str,
    fallback_control_loop_id: int | None = None,
    algorithm_reference: str | None = None,
    description: str | None = None,
) -> int:
    """Insert a ControlLoop row and return its ControlLoop_ID."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[ControlLoop]"
        "    ([Name], [ControllerType], [FallbackControlLoop_ID],"
        "     [AlgorithmReference], [Description])"
        " OUTPUT INSERTED.[ControlLoop_ID]"
        " VALUES (?, ?, ?, ?, ?)",
        name,
        controller_type,
        fallback_control_loop_id,
        algorithm_reference,
        description,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def get_control_loop(conn: pyodbc.Connection, loop_id: int) -> dict | None:
    """Return a ControlLoop row as a dict, or None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ControlLoop_ID], [Name], [ControllerType],"
        "       [FallbackControlLoop_ID], [AlgorithmReference], [Description]"
        " FROM [dbo].[ControlLoop]"
        " WHERE [ControlLoop_ID] = ?",
        loop_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))


# ---------------------------------------------------------------------------
# ControlLoopPort
# ---------------------------------------------------------------------------


def add_loop_port(
    conn: pyodbc.Connection,
    loop_id: int,
    channel_id: int,
    role_id: int,
) -> int:
    """Associate a Channel with a ControlLoop via a role.

    Returns ControlLoopPort_ID.
    Raises pyodbc.IntegrityError if (ControlLoop_ID, Channel_ID) already exists.
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[ControlLoopPort]"
        "    ([ControlLoop_ID], [Channel_ID], [ControlLoopPortRole_ID])"
        " OUTPUT INSERTED.[ControlLoopPort_ID]"
        " VALUES (?, ?, ?)",
        loop_id,
        channel_id,
        role_id,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def get_loop_ports(conn: pyodbc.Connection, loop_id: int) -> list[dict]:
    """Return all ControlLoopPort rows for a loop, joined with role name."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            lp.[ControlLoopPort_ID],
            lp.[ControlLoop_ID],
            lp.[Channel_ID],
            lp.[ControlLoopPortRole_ID],
            r.[Name] AS [role_name]
        FROM [dbo].[ControlLoopPort] lp
        JOIN [dbo].[ControlLoopPortRole] r
            ON r.[ControlLoopPortRole_ID] = lp.[ControlLoopPortRole_ID]
        WHERE lp.[ControlLoop_ID] = ?
        """,
        loop_id,
    )
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# ControlLoopApplication
# ---------------------------------------------------------------------------


def open_application(
    conn: pyodbc.Connection,
    loop_id: int,
    start_time: datetime,
    parameters: str | None = None,
    applied_by_person_id: int | None = None,
    notes: str | None = None,
) -> int:
    """Insert a new active ControlLoopApplication (EndTime = NULL).

    Raises ValueError if there is already an active Application for this loop.
    Returns ControlLoopApplication_ID.
    """
    # Guard: at most one active row per loop
    active = get_active_application(conn, loop_id)
    if active is not None:
        raise ValueError(
            f"ControlLoop {loop_id} already has an active Application "
            f"(ID={active['ControlLoopApplication_ID']}). "
            "Call retune or close the active Application first."
        )
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[ControlLoopApplication]"
        "    ([ControlLoop_ID], [StartTime], [EndTime],"
        "     [Parameters], [AppliedByPerson_ID], [Notes])"
        " OUTPUT INSERTED.[ControlLoopApplication_ID]"
        " VALUES (?, ?, NULL, ?, ?, ?)",
        loop_id,
        start_time,
        parameters,
        applied_by_person_id,
        notes,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def close_application(
    conn: pyodbc.Connection,
    application_id: int,
    end_time: datetime,
) -> None:
    """Set EndTime on a ControlLoopApplication row."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[ControlLoopApplication]"
        " SET [EndTime] = ?"
        " WHERE [ControlLoopApplication_ID] = ?",
        end_time,
        application_id,
    )
    conn.commit()


def retune(
    conn: pyodbc.Connection,
    loop_id: int,
    start_time: datetime,
    parameters: str | None = None,
    applied_by_person_id: int | None = None,
    notes: str | None = None,
) -> tuple[int, int | None]:
    """Close the active Application (if any) and open a new one.

    Returns ``(new_application_id, closed_application_id)``.
    ``closed_application_id`` is None when there was no previously active row.
    """
    active = get_active_application(conn, loop_id)
    closed_id: int | None = None

    if active is not None:
        closed_id = active["ControlLoopApplication_ID"]
        close_application(conn, closed_id, end_time=start_time)

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[ControlLoopApplication]"
        "    ([ControlLoop_ID], [StartTime], [EndTime],"
        "     [Parameters], [AppliedByPerson_ID], [Notes])"
        " OUTPUT INSERTED.[ControlLoopApplication_ID]"
        " VALUES (?, ?, NULL, ?, ?, ?)",
        loop_id,
        start_time,
        parameters,
        applied_by_person_id,
        notes,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id, closed_id


def get_active_application(conn: pyodbc.Connection, loop_id: int) -> dict | None:
    """Return the active (EndTime IS NULL) Application for a loop, or None."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ControlLoopApplication_ID], [ControlLoop_ID], [StartTime],"
        "       [EndTime], [Parameters], [AppliedByPerson_ID], [Notes]"
        " FROM [dbo].[ControlLoopApplication]"
        " WHERE [ControlLoop_ID] = ? AND [EndTime] IS NULL",
        loop_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))


def get_application_at(
    conn: pyodbc.Connection, loop_id: int, at_time: datetime
) -> dict | None:
    """Return the Application row whose window covers *at_time*.

    A row covers *at_time* when ``StartTime <= at_time AND (EndTime IS NULL OR EndTime > at_time)``.
    Returns None when no row covers the requested timestamp.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ControlLoopApplication_ID], [ControlLoop_ID], [StartTime],"
        "       [EndTime], [Parameters], [AppliedByPerson_ID], [Notes]"
        " FROM [dbo].[ControlLoopApplication]"
        " WHERE [ControlLoop_ID] = ?"
        "   AND [StartTime] <= ?"
        "   AND ([EndTime] IS NULL OR [EndTime] > ?)",
        loop_id,
        at_time,
        at_time,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------


def get_fallback_chain(conn: pyodbc.Connection, loop_id: int) -> list[dict]:
    """Return the full fallback chain starting from *loop_id*.

    The first element is the loop itself; each subsequent element is the loop
    referenced by ``FallbackControlLoop_ID``, traversed until NULL.
    Returns an empty list when *loop_id* does not exist.
    """
    chain: list[dict] = []
    current_id: int | None = loop_id

    while current_id is not None:
        row = get_control_loop(conn, current_id)
        if row is None:
            break
        chain.append(row)
        current_id = row["FallbackControlLoop_ID"]

    return chain


# ---------------------------------------------------------------------------
# Lookup helper
# ---------------------------------------------------------------------------


def find_role_by_name(conn: pyodbc.Connection, name: str) -> int | None:
    """Return ControlLoopPortRole_ID for *name* (case-insensitive). None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ControlLoopPortRole_ID] FROM [dbo].[ControlLoopPortRole]"
        " WHERE LOWER(LTRIM(RTRIM([Name]))) = ?",
        name.strip().lower(),
    )
    row = cursor.fetchone()
    return row[0] if row else None
