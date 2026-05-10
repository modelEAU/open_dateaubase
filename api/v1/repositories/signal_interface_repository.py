"""Repository functions for SignalInterface, SignalInterfacePort, DataAcquisitionSystem, and related lookups."""

from __future__ import annotations

import logging

import pyodbc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Name-based lookups (return None on miss — callers raise 422)
# ---------------------------------------------------------------------------


def find_channel_kind_by_name(conn: pyodbc.Connection, name: str) -> int | None:
    """Return ChannelKind_ID for *name* (case-insensitive, trimmed). None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ChannelKind_ID] FROM [dbo].[ChannelKind]"
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
        "SELECT [Unit_ID] FROM [dbo].[Unit] WHERE LOWER(LTRIM(RTRIM([Unit]))) = ?",
        name.strip().lower(),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def find_signal_interface_by_name(conn: pyodbc.Connection, name: str) -> int | None:
    """Return SignalInterface_ID for *name* (case-insensitive, trimmed). None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterface_ID] FROM [dbo].[SignalInterface]"
        " WHERE LOWER(LTRIM(RTRIM([Name]))) = ?",
        name.strip().lower(),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def find_signal_interface_by_das_and_name(
    conn: pyodbc.Connection, das_id: int, name: str
) -> int | None:
    """Return SignalInterface_ID for *(das_id, name)* (case-insensitive, trimmed). None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterface_ID] FROM [dbo].[SignalInterface]"
        " WHERE [DataAcquisitionSystem_ID] = ?"
        "   AND LOWER(LTRIM(RTRIM([Name]))) = ?",
        das_id,
        name.strip().lower(),
    )
    row = cursor.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Find-or-create helpers (auto-create with warning on miss)
# ---------------------------------------------------------------------------


def find_or_create_das(conn: pyodbc.Connection, das_name: str) -> tuple[int, bool]:
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
    _row = cursor.fetchone()
    assert _row is not None
    new_id: int = _row[0]
    conn.commit()
    logger.warning(
        "DataAcquisitionSystem %r not found — auto-created (ID=%d)", stored_name, new_id
    )
    return new_id, True


def find_or_create_signal_interface(
    conn: pyodbc.Connection,
    das_id: int,
    name: str,
) -> tuple[int, bool]:
    """Find or create a SignalInterface by (DAS_ID, name) with case-insensitive name lookup.

    Returns ``(SignalInterface_ID, created)`` where *created* is True when a new row was
    inserted.  Logs a WARNING when auto-creating.  The name is stored case-preserved
    (only the lookup is normalised).
    """
    normalised_name = name.strip().lower()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterface_ID] FROM [dbo].[SignalInterface]"
        " WHERE [DataAcquisitionSystem_ID] = ?"
        "   AND LOWER(LTRIM(RTRIM([Name]))) = ?",
        das_id,
        normalised_name,
    )
    row = cursor.fetchone()
    if row:
        return row[0], False

    stored_name = name.strip()
    cursor.execute(
        "INSERT INTO [dbo].[SignalInterface]"
        "    ([DataAcquisitionSystem_ID], [Name])"
        " OUTPUT INSERTED.[SignalInterface_ID]"
        " VALUES (?, ?)",
        das_id,
        stored_name,
    )
    _row = cursor.fetchone()
    assert _row is not None
    new_id: int = _row[0]
    conn.commit()
    logger.warning(
        "SignalInterface name=%r (DAS ID=%d) not found — auto-created (ID=%d)",
        stored_name,
        das_id,
        new_id,
    )
    return new_id, True


def find_or_create_signal_interface_port(
    conn: pyodbc.Connection,
    signal_interface_id: int,
    port_identifier: str,
) -> tuple[int, bool]:
    """Find or create a SignalInterfacePort by (SignalInterface_ID, PortIdentifier).

    Returns ``(SignalInterfacePort_ID, created)`` where *created* is True when a new row was
    inserted.  Logs a WARNING when auto-creating.  The identifier is stored case-preserved
    (only the lookup is normalised).
    """
    normalised_id = port_identifier.strip().lower()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterfacePort_ID] FROM [dbo].[SignalInterfacePort]"
        " WHERE [SignalInterface_ID] = ?"
        "   AND LOWER(LTRIM(RTRIM([PortIdentifier]))) = ?",
        signal_interface_id,
        normalised_id,
    )
    row = cursor.fetchone()
    if row:
        return row[0], False

    stored_id = port_identifier.strip()
    cursor.execute(
        "INSERT INTO [dbo].[SignalInterfacePort]"
        "    ([SignalInterface_ID], [PortIdentifier])"
        " OUTPUT INSERTED.[SignalInterfacePort_ID]"
        " VALUES (?, ?)",
        signal_interface_id,
        stored_id,
    )
    _row = cursor.fetchone()
    assert _row is not None
    new_id: int = _row[0]
    conn.commit()
    logger.warning(
        "SignalInterfacePort identifier=%r (Interface ID=%d) not found — auto-created (ID=%d)",
        stored_id,
        signal_interface_id,
        new_id,
    )
    return new_id, True


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
    _row = cursor.fetchone()
    assert _row is not None
    new_id: int = _row[0]
    conn.commit()
    logger.warning(
        "Equipment identifier=%r not found — auto-created (ID=%d)",
        stored_identifier,
        new_id,
    )
    return new_id, True


# ---------------------------------------------------------------------------
# Equipment wiring history
# ---------------------------------------------------------------------------


def find_active_equipment_wiring(
    conn: pyodbc.Connection,
    equipment_id: int,
) -> tuple[int, int | None] | None:
    """Return the active (ValidTo IS NULL) wiring for an equipment.

    Returns ``(signal_interface_id, signal_interface_port_id)`` or None
    if no active wiring exists.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterface_ID], [SignalInterfacePort_ID]"
        " FROM [dbo].[EquipmentWiringHistory]"
        " WHERE [Equipment_ID] = ? AND [ValidTo] IS NULL",
        equipment_id,
    )
    row = cursor.fetchone()
    return (row[0], row[1]) if row else None


def open_equipment_wiring_history(
    conn: pyodbc.Connection,
    equipment_id: int,
    signal_interface_id: int,
    signal_interface_port_id: int | None,
) -> int:
    """Insert an EquipmentWiringHistory row with ValidFrom=now (UTC) and ValidTo=NULL.

    Returns ``EquipmentWiringHistory_ID``.
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[EquipmentWiringHistory]"
        "    ([Equipment_ID], [SignalInterface_ID], [SignalInterfacePort_ID], [ValidFrom])"
        " OUTPUT INSERTED.[EquipmentWiringHistory_ID]"
        " VALUES (?, ?, ?, SYSUTCDATETIME())",
        equipment_id,
        signal_interface_id,
        signal_interface_port_id,
    )
    _row = cursor.fetchone()
    assert _row is not None
    new_id: int = _row[0]
    conn.commit()
    return new_id


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def generate_tagless_tagname(equipment_identifier: str, parameter_name: str) -> str:
    """Generate a deterministic, stable synthetic tag name for tagless ingest.

    Rule: ``"{equipment_identifier.strip().lower()}/{parameter_name.strip().lower()}"``
    Example: ``"Probe_A "`` + ``" DO "`` → ``"probe_a/do"``
    """
    return f"{equipment_identifier.strip().lower()}/{parameter_name.strip().lower()}"


# ---------------------------------------------------------------------------
# DataAcquisitionSystem CRUD
# ---------------------------------------------------------------------------


def list_das(conn: pyodbc.Connection) -> list[dict]:
    """Return all DataAcquisitionSystem rows ordered by name."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT d.[DataAcquisitionSystem_ID], d.[Name], d.[Description],"
        "       d.[DataAcquisitionSystemKind_ID], k.[Name] AS [das_kind_name]"
        " FROM [dbo].[DataAcquisitionSystem] d"
        " LEFT JOIN [dbo].[DataAcquisitionSystemKind] k"
        "   ON k.[DataAcquisitionSystemKind_ID] = d.[DataAcquisitionSystemKind_ID]"
        " ORDER BY d.[Name]"
    )
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def insert_das(
    conn: pyodbc.Connection,
    name: str,
    description: str | None = None,
    das_kind_id: int | None = None,
) -> dict:
    """Create a new DataAcquisitionSystem row and return a dict with all fields."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[DataAcquisitionSystem]"
            "    ([Name], [Description], [DataAcquisitionSystemKind_ID])"
            " OUTPUT INSERTED.[DataAcquisitionSystem_ID], INSERTED.[Name],"
            "        INSERTED.[Description], INSERTED.[DataAcquisitionSystemKind_ID]"
            " VALUES (?, ?, ?)",
            name.strip(),
            description,
            das_kind_id,
        )
        row = cursor.fetchone()
        assert row is not None
        conn.commit()
        return {
            "das_id": row[0],
            "name": row[1],
            "description": row[2],
            "das_kind_id": row[3],
            "das_kind_name": None,
        }
    except Exception:
        conn.rollback()
        raise


def update_das(
    conn: pyodbc.Connection,
    das_id: int,
    name: str,
    description: str | None,
    das_kind_id: int | None = None,
) -> dict | None:
    """Update a DataAcquisitionSystem row and return a dict with all fields, or None if not found."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[DataAcquisitionSystem]"
            " SET [Name]=?, [Description]=?, [DataAcquisitionSystemKind_ID]=?"
            " OUTPUT INSERTED.[DataAcquisitionSystem_ID], INSERTED.[Name],"
            "        INSERTED.[Description], INSERTED.[DataAcquisitionSystemKind_ID]"
            " WHERE [DataAcquisitionSystem_ID]=?",
            name.strip(),
            description,
            das_kind_id,
            das_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {
            "das_id": row[0],
            "name": row[1],
            "description": row[2],
            "das_kind_id": row[3],
            "das_kind_name": None,
        }
    except Exception:
        conn.rollback()
        raise


def delete_das(conn: pyodbc.Connection, das_id: int) -> bool:
    """Delete a DataAcquisitionSystem row. Returns True if a row was deleted."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[DataAcquisitionSystem] WHERE [DataAcquisitionSystem_ID]=?",
            das_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# SignalInterface CRUD
# ---------------------------------------------------------------------------

_SELECT_SIGNAL_INTERFACE = """
    SELECT
        si.[SignalInterface_ID],
        si.[DataAcquisitionSystem_ID],
        si.[Name],
        si.[Manufacturer],
        si.[Model],
        si.[SerialNumber],
        si.[Description],
        si.[IsActive],
        das.[Name] AS [das_name]
    FROM [dbo].[SignalInterface] si
    JOIN [dbo].[DataAcquisitionSystem] das
        ON das.[DataAcquisitionSystem_ID] = si.[DataAcquisitionSystem_ID]
"""


def list_signal_interfaces_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return a lightweight list of all SignalInterfaces for dropdowns.

    Includes ``das_name`` so callers can build ``DAS › name`` labels without
    a second round-trip.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT si.[SignalInterface_ID], si.[Name], das.[Name] AS [das_name]"
        " FROM [dbo].[SignalInterface] si"
        " JOIN [dbo].[DataAcquisitionSystem] das"
        "     ON das.[DataAcquisitionSystem_ID] = si.[DataAcquisitionSystem_ID]"
        " ORDER BY das.[Name], si.[Name]"
    )
    return [
        {"signal_interface_id": row[0], "name": row[1], "das_name": row[2]}
        for row in cursor.fetchall()
    ]


def list_signal_interfaces(
    conn: pyodbc.Connection,
    *,
    das_id: int | None = None,
    is_active: bool | None = None,
    equipment_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict], int]:
    """Return paginated SignalInterface rows with DAS name and type name resolved.

    Returns ``(items, total_count)`` where *items* is the page slice and
    *total_count* is the number of rows matching the applied filters.
    """
    where_clauses: list[str] = []
    params: list = []

    if das_id is not None:
        where_clauses.append("si.[DataAcquisitionSystem_ID] = ?")
        params.append(das_id)
    if is_active is not None:
        where_clauses.append("si.[IsActive] = ?")
        params.append(1 if is_active else 0)
    if equipment_id is not None:
        where_clauses.append(
            "EXISTS ("
            "  SELECT 1 FROM [dbo].[EquipmentWiringHistory] ewh"
            "  WHERE ewh.[SignalInterface_ID] = si.[SignalInterface_ID]"
            "    AND ewh.[Equipment_ID] = ?"
            "    AND ewh.[ValidTo] IS NULL"
            ")"
        )
        params.append(equipment_id)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cursor = conn.cursor()

    # Total count
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[SignalInterface] si" + where_sql,
        *params,
    )
    _count_row = cursor.fetchone()
    assert _count_row is not None
    total: int = _count_row[0]

    # Paginated rows
    offset = (page - 1) * page_size
    cursor.execute(
        _SELECT_SIGNAL_INTERFACE
        + where_sql
        + " ORDER BY si.[SignalInterface_ID]"
        + " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        *(params + [offset, page_size]),
    )
    cols = [col[0] for col in cursor.description]
    items = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return items, total


def get_signal_interface_by_id(
    conn: pyodbc.Connection, signal_interface_id: int
) -> dict | None:
    """Return a single SignalInterface row with DAS and type names resolved, or None."""
    cursor = conn.cursor()
    cursor.execute(
        _SELECT_SIGNAL_INTERFACE + " WHERE si.[SignalInterface_ID] = ?",
        signal_interface_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))


def create_signal_interface(
    conn: pyodbc.Connection,
    *,
    das_id: int,
    name: str,
    manufacturer: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
    description: str | None = None,
) -> int:
    """Insert a SignalInterface row and return the new SignalInterface_ID."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[SignalInterface]"
            "    ([DataAcquisitionSystem_ID], [Name],"
            "     [Manufacturer], [Model], [SerialNumber], [Description])"
            " OUTPUT INSERTED.[SignalInterface_ID]"
            " VALUES (?, ?, ?, ?, ?, ?)",
            das_id,
            name.strip(),
            manufacturer,
            model,
            serial_number,
            description,
        )
        _row = cursor.fetchone()
        assert _row is not None
        new_id: int = _row[0]
        conn.commit()
        return new_id
    except Exception:
        conn.rollback()
        raise


def patch_signal_interface(
    conn: pyodbc.Connection,
    signal_interface_id: int,
    data: dict,
) -> dict | None:
    """Update only the keys present in *data* on a SignalInterface row.

    Supported keys: ``description``, ``is_active``, ``manufacturer``, ``model``, ``serial_number``.
    Returns the updated row via :func:`get_signal_interface_by_id`, or None when the
    interface does not exist.
    """
    column_map = {
        "description": "[Description]",
        "is_active": "[IsActive]",
        "manufacturer": "[Manufacturer]",
        "model": "[Model]",
        "serial_number": "[SerialNumber]",
    }
    set_clauses: list[str] = []
    params: list = []

    for key, col in column_map.items():
        if key in data and data[key] is not None:
            set_clauses.append(f"{col} = ?")
            value = data[key]
            if key == "is_active":
                value = 1 if value else 0
            params.append(value)

    if not set_clauses:
        return get_signal_interface_by_id(conn, signal_interface_id)

    params.append(signal_interface_id)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[SignalInterface] SET "
            + ", ".join(set_clauses)
            + " WHERE [SignalInterface_ID] = ?",
            *params,
        )
        conn.commit()
        return get_signal_interface_by_id(conn, signal_interface_id)
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# SignalInterfacePort CRUD
# ---------------------------------------------------------------------------

_SELECT_SIGNAL_INTERFACE_PORT = """
    SELECT
        sip.[SignalInterfacePort_ID],
        sip.[SignalInterface_ID],
        sip.[PortIdentifier],
        sip.[Description],
        sip.[IsActive],
        si.[Name] AS [signal_interface_name]
    FROM [dbo].[SignalInterfacePort] sip
    JOIN [dbo].[SignalInterface] si
        ON si.[SignalInterface_ID] = sip.[SignalInterface_ID]
"""


def list_signal_interface_ports(
    conn: pyodbc.Connection,
    *,
    signal_interface_id: int | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict], int]:
    """Return paginated SignalInterfacePort rows with kind and interface names resolved.

    Returns ``(items, total_count)`` where *items* is the page slice and
    *total_count* is the number of rows matching the applied filters.
    """
    where_clauses: list[str] = []
    params: list = []

    if signal_interface_id is not None:
        where_clauses.append("sip.[SignalInterface_ID] = ?")
        params.append(signal_interface_id)
    if is_active is not None:
        where_clauses.append("sip.[IsActive] = ?")
        params.append(1 if is_active else 0)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cursor = conn.cursor()

    # Total count
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[SignalInterfacePort] sip" + where_sql,
        *params,
    )
    _count_row = cursor.fetchone()
    assert _count_row is not None
    total: int = _count_row[0]

    # Paginated rows
    offset = (page - 1) * page_size
    cursor.execute(
        _SELECT_SIGNAL_INTERFACE_PORT
        + where_sql
        + " ORDER BY sip.[SignalInterfacePort_ID]"
        + " OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        *(params + [offset, page_size]),
    )
    cols = [col[0] for col in cursor.description]
    items = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return items, total


def get_signal_interface_port_by_id(
    conn: pyodbc.Connection, signal_interface_port_id: int
) -> dict | None:
    """Return a single SignalInterfacePort row with kind and interface names resolved, or None."""
    cursor = conn.cursor()
    cursor.execute(
        _SELECT_SIGNAL_INTERFACE_PORT + " WHERE sip.[SignalInterfacePort_ID] = ?",
        signal_interface_port_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))


def create_signal_interface_port(
    conn: pyodbc.Connection,
    *,
    signal_interface_id: int,
    port_identifier: str,
    description: str | None = None,
) -> int:
    """Insert a SignalInterfacePort row and return the new SignalInterfacePort_ID."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[SignalInterfacePort]"
            "    ([SignalInterface_ID], [PortIdentifier], [Description])"
            " OUTPUT INSERTED.[SignalInterfacePort_ID]"
            " VALUES (?, ?, ?)",
            signal_interface_id,
            port_identifier.strip(),
            description,
        )
        _row = cursor.fetchone()
        assert _row is not None
        new_id: int = _row[0]
        conn.commit()
        return new_id
    except Exception:
        conn.rollback()
        raise


def patch_signal_interface_port(
    conn: pyodbc.Connection,
    signal_interface_port_id: int,
    data: dict,
) -> dict | None:
    """Update only the keys present in *data* on a SignalInterfacePort row.

    Supported keys: ``description``, ``is_active``.
    Returns the updated row via :func:`get_signal_interface_port_by_id`, or None when the
    port does not exist.
    """
    column_map = {
        "description": "[Description]",
        "is_active": "[IsActive]",
    }
    set_clauses: list[str] = []
    params: list = []

    for key, col in column_map.items():
        if key in data and data[key] is not None:
            set_clauses.append(f"{col} = ?")
            value = data[key]
            if key == "is_active":
                value = 1 if value else 0
            params.append(value)

    if not set_clauses:
        return get_signal_interface_port_by_id(conn, signal_interface_port_id)

    params.append(signal_interface_port_id)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[SignalInterfacePort] SET "
            + ", ".join(set_clauses)
            + " WHERE [SignalInterfacePort_ID] = ?",
            *params,
        )
        conn.commit()
        return get_signal_interface_port_by_id(conn, signal_interface_port_id)
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Lookup tables (read-only — fixed seeded IDs)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Delete helpers
# ---------------------------------------------------------------------------


def delete_signal_interface(conn: pyodbc.Connection, signal_interface_id: int) -> bool:
    """Delete a SignalInterface row. Returns True if a row was deleted."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[SignalInterface] WHERE [SignalInterface_ID]=?",
            signal_interface_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


def delete_signal_interface_port(
    conn: pyodbc.Connection, signal_interface_port_id: int
) -> bool:
    """Delete a SignalInterfacePort row. Returns True if a row was deleted."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[SignalInterfacePort] WHERE [SignalInterfacePort_ID]=?",
            signal_interface_port_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Ingest compatibility stubs (deprecated — will be removed in Phase 5)
# ---------------------------------------------------------------------------


def find_signal_port_type_by_name(conn: pyodbc.Connection, name: str) -> int | None:
    """Deprecated stub — maps to ChannelKind lookup for backward compatibility.

    Old signal_port_type values (value, status, alarm, uncertainty) now map
    to ChannelKind names.
    """
    return find_channel_kind_by_name(conn, name)


def find_or_create_signal_port(
    conn: pyodbc.Connection,
    das_id: int,
    tag: str,
    signal_port_type_id: int,
) -> tuple[int, bool]:
    """Deprecated stub."""
    raise NotImplementedError(
        "find_or_create_signal_port is deprecated. Use find_or_create_signal_interface_port."
    )


def find_signal_port_by_tag(
    conn: pyodbc.Connection, das_id: int, tag: str
) -> int | None:
    """Deprecated stub."""
    raise NotImplementedError(
        "find_signal_port_by_tag is deprecated. SignalPort table has been removed."
    )


def set_parent_port(conn: pyodbc.Connection, port_id: int, parent_port_id: int) -> None:
    """Deprecated stub."""
    raise NotImplementedError(
        "set_parent_port is deprecated. Use ParentChannel_ID on Channel instead."
    )


def open_port_equipment_history(
    conn: pyodbc.Connection, port_id: int, equipment_id: int
) -> int:
    """Deprecated stub."""
    raise NotImplementedError(
        "open_port_equipment_history is deprecated. Use open_equipment_wiring_history."
    )


def deactivate_signal_port(conn: pyodbc.Connection, signal_port_id: int) -> bool:
    """Deprecated stub."""
    raise NotImplementedError(
        "deactivate_signal_port is deprecated. SignalPort table has been removed."
    )


def generate_tagless_tag(equipment_identifier: str, parameter_name: str) -> str:
    """Deprecated alias for generate_tagless_tagname."""
    return generate_tagless_tagname(equipment_identifier, parameter_name)


# ---------------------------------------------------------------------------
# Lookup tables (read-only — fixed seeded IDs)
# ---------------------------------------------------------------------------


def list_channel_kinds(conn: pyodbc.Connection) -> list[dict]:
    """Return all ChannelKind rows ordered by ID."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ChannelKind_ID], [Name], [Description]"
        " FROM [dbo].[ChannelKind] ORDER BY [ChannelKind_ID]"
    )
    return [
        {"channel_kind_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]
