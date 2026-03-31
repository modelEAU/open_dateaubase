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


def generate_tagless_tag(equipment_identifier: str, parameter_name: str) -> str:
    """Generate a deterministic, stable synthetic SignalPort tag for tagless ingest.

    Rule: ``"{equipment_identifier.strip().lower()}/{parameter_name.strip().lower()}"``
    Example: ``"Probe_A "`` + ``" DO "`` → ``"probe_a/do"``
    """
    return f"{equipment_identifier.strip().lower()}/{parameter_name.strip().lower()}"


def find_or_create_equipment_by_identifier(
    conn: pyodbc.Connection, identifier: str
) -> tuple[int, bool]:
    """Find or create an Equipment row by Identifier (case-insensitive, trimmed).

    Returns ``(Equipment_ID, created)`` where *created* is True when a new row was
    inserted.  Logs a WARNING when auto-creating.
    """
    normalised = identifier.strip().lower()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Equipment_ID] FROM [dbo].[Equipment]"
        " WHERE LOWER(LTRIM(RTRIM([Identifier]))) = ?",
        normalised,
    )
    row = cursor.fetchone()
    if row:
        return row[0], False

    stored_identifier = identifier.strip()
    cursor.execute(
        "INSERT INTO [dbo].[Equipment] ([Identifier])"
        " OUTPUT INSERTED.[Equipment_ID] VALUES (?)",
        stored_identifier,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    logger.warning(
        "Equipment identifier=%r not found — auto-created (ID=%d)", stored_identifier, new_id
    )
    return new_id, True


def open_port_equipment_history(
    conn: pyodbc.Connection, signal_port_id: int, equipment_id: int
) -> int:
    """Insert a SignalPortEquipmentHistory row with StartTime=now (UTC) and EndTime=NULL.

    Returns ``SignalPortEquipmentHistory_ID``.
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[SignalPortEquipmentHistory]"
        "    ([SignalPort_ID], [Equipment_ID], [StartTime])"
        " OUTPUT INSERTED.[SignalPortEquipmentHistory_ID]"
        " VALUES (?, ?, SYSUTCDATETIME())",
        signal_port_id,
        equipment_id,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def find_signal_port_by_tag(
    conn: pyodbc.Connection, das_id: int, tag: str
) -> int | None:
    """Return SignalPort_ID for (DAS_ID, tag). None if not found.

    Lookup is case-insensitive and whitespace-trimmed.
    """
    normalised = tag.strip().lower()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalPort_ID] FROM [dbo].[SignalPort]"
        " WHERE [DataAcquisitionSystem_ID] = ?"
        "   AND LOWER(LTRIM(RTRIM([Tag]))) = ?",
        das_id,
        normalised,
    )
    row = cursor.fetchone()
    return row[0] if row else None


def get_parent_port_id(conn: pyodbc.Connection, signal_port_id: int) -> int | None:
    """Return the ParentPort_ID for a SignalPort.

    Returns None when the port is a root port (ParentPort_ID IS NULL) or
    when the port does not exist.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ParentPort_ID] FROM [dbo].[SignalPort] WHERE [SignalPort_ID] = ?",
        signal_port_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return row[0]


def set_parent_port(
    conn: pyodbc.Connection, signal_port_id: int, parent_port_id: int
) -> None:
    """Set ParentPort_ID on a SignalPort.

    Idempotent: no-op if ``ParentPort_ID`` is already set to ``parent_port_id``.
    Raises ``ValueError`` if the port already has a *different* parent.
    """
    existing = get_parent_port_id(conn, signal_port_id)
    if existing == parent_port_id:
        return  # already correct — idempotent
    if existing is not None:
        raise ValueError(
            f"SignalPort {signal_port_id} already has ParentPort_ID={existing}; "
            f"cannot reassign to {parent_port_id}."
        )
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[SignalPort] SET [ParentPort_ID] = ? WHERE [SignalPort_ID] = ?",
        parent_port_id,
        signal_port_id,
    )
    conn.commit()


def get_sub_signals(conn: pyodbc.Connection, parent_port_id: int) -> list[dict]:
    """Return all sub-signal ports whose ParentPort_ID equals *parent_port_id*.

    Each item contains: signal_port_id, tag, is_active, description,
    parent_port_id, signal_port_type_id, signal_port_type_name.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            sp.[SignalPort_ID],
            sp.[Tag],
            sp.[IsActive],
            sp.[Description],
            sp.[ParentPort_ID],
            spt.[SignalPortType_ID],
            spt.[Name] AS [signal_port_type_name]
        FROM [dbo].[SignalPort] sp
        JOIN [dbo].[SignalPortType] spt
            ON spt.[SignalPortType_ID] = sp.[SignalPortType_ID]
        WHERE sp.[ParentPort_ID] = ?
        """,
        parent_port_id,
    )
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def deactivate_signal_port(conn: pyodbc.Connection, signal_port_id: int) -> bool:
    """Set ``IsActive = 0`` on a SignalPort.  Returns True if the row was found."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[SignalPort] SET [IsActive] = 0 WHERE [SignalPort_ID] = ?",
        signal_port_id,
    )
    conn.commit()
    return cursor.rowcount > 0
