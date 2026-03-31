"""Repository functions for SignalPort, DataAcquisitionSystem, and name-based lookups."""

from __future__ import annotations

import logging

import pyodbc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Name-based lookups (return None on miss — callers raise 422)
# ---------------------------------------------------------------------------


def find_signal_port_type_by_name(conn: pyodbc.Connection, name: str) -> int | None:
    """Return SignalPortType_ID for *name* (case-insensitive, trimmed). None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalPortType_ID] FROM [dbo].[SignalPortType]"
        " WHERE LOWER(LTRIM(RTRIM([Name]))) = ?",
        name.strip().lower(),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def find_parameter_by_name(conn: pyodbc.Connection, name: str) -> int | None:
    """Return Parameter_ID for *name* (case-insensitive, trimmed). None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Parameter_ID] FROM [dbo].[Parameter]"
        " WHERE LOWER(LTRIM(RTRIM([Parameter]))) = ?",
        name.strip().lower(),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def find_unit_by_name(conn: pyodbc.Connection, name: str) -> int | None:
    """Return Unit_ID for *name* (case-insensitive, trimmed). None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Unit_ID] FROM [dbo].[Unit]"
        " WHERE LOWER(LTRIM(RTRIM([Unit]))) = ?",
        name.strip().lower(),
    )
    row = cursor.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Find-or-create helpers (auto-create with warning on miss)
# ---------------------------------------------------------------------------


def find_or_create_das(
    conn: pyodbc.Connection, das_name: str
) -> tuple[int, bool]:
    """Find or create a DataAcquisitionSystem by name (case-insensitive, trimmed).

    Returns ``(DataAcquisitionSystem_ID, created)`` where *created* is True when a
    new row was inserted.  Logs a WARNING when auto-creating.
    """
    normalised = das_name.strip().lower()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [DataAcquisitionSystem_ID] FROM [dbo].[DataAcquisitionSystem]"
        " WHERE LOWER(LTRIM(RTRIM([Name]))) = ?",
        normalised,
    )
    row = cursor.fetchone()
    if row:
        return row[0], False

    stored_name = das_name.strip()
    cursor.execute(
        "INSERT INTO [dbo].[DataAcquisitionSystem] ([Name])"
        " OUTPUT INSERTED.[DataAcquisitionSystem_ID] VALUES (?)",
        stored_name,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    logger.warning(
        "DataAcquisitionSystem %r not found — auto-created (ID=%d)", stored_name, new_id
    )
    return new_id, True


def find_or_create_signal_port(
    conn: pyodbc.Connection,
    das_id: int,
    tag: str,
    signal_port_type_id: int,
) -> tuple[int, bool]:
    """Find or create a SignalPort by (DAS_ID, tag) with case-insensitive tag lookup.

    Returns ``(SignalPort_ID, created)`` where *created* is True when a new row was
    inserted.  Logs a WARNING when auto-creating.  The tag is stored case-preserved
    (only the lookup is normalised).
    """
    normalised_tag = tag.strip().lower()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalPort_ID] FROM [dbo].[SignalPort]"
        " WHERE [DataAcquisitionSystem_ID] = ?"
        "   AND LOWER(LTRIM(RTRIM([Tag]))) = ?",
        das_id,
        normalised_tag,
    )
    row = cursor.fetchone()
    if row:
        return row[0], False

    stored_tag = tag.strip()
    cursor.execute(
        "INSERT INTO [dbo].[SignalPort]"
        "    ([DataAcquisitionSystem_ID], [Tag], [SignalPortType_ID])"
        " OUTPUT INSERTED.[SignalPort_ID]"
        " VALUES (?, ?, ?)",
        das_id,
        stored_tag,
        signal_port_type_id,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    logger.warning(
        "SignalPort tag=%r (DAS ID=%d) not found — auto-created (ID=%d)",
        stored_tag,
        das_id,
        new_id,
    )
    return new_id, True


# ---------------------------------------------------------------------------
# Port management
# ---------------------------------------------------------------------------


def deactivate_signal_port(conn: pyodbc.Connection, signal_port_id: int) -> bool:
    """Set ``IsActive = 0`` on a SignalPort.  Returns True if the row was found."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[SignalPort] SET [IsActive] = 0 WHERE [SignalPort_ID] = ?",
        signal_port_id,
    )
    conn.commit()
    return cursor.rowcount > 0
