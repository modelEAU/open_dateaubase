"""Repository for at-most-one-active temporal history patterns.

Handles both ``EquipmentWiringHistory`` and ``EquipmentLocationHistory``
tables, which share the same constraint: at most one row per ``Equipment_ID``
with ``ValidTo IS NULL`` (the active row).

Provides:
  - Close-and-open swap operations (equipment rewire, sensor relocation)
  - At-most-one-active enforcement (the filtered unique index in the DB
    is the final guard; this module enforces the invariant at the
    application layer with an explicit check before INSERT)
  - Point-in-time queries ("what was active at time T?")
"""

from __future__ import annotations

from datetime import datetime

import pyodbc


# ---------------------------------------------------------------------------
# EquipmentWiringHistory
# ---------------------------------------------------------------------------


def get_active_wiring_for_equipment(
    conn: pyodbc.Connection, equipment_id: int
) -> dict | None:
    """Return the currently active EquipmentWiringHistory row, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            ewh.[EquipmentWiringHistory_ID],
            ewh.[Equipment_ID],
            ewh.[SignalInterface_ID],
            ewh.[SignalInterfacePort_ID],
            ewh.[ValidFrom],
            ewh.[ValidTo],
            ewh.[Note],
            si.[Name] AS [signal_interface_name],
            e.[Identifier] AS [equipment_identifier]
        FROM [dbo].[EquipmentWiringHistory] ewh
        JOIN [dbo].[SignalInterface] si ON si.[SignalInterface_ID] = ewh.[SignalInterface_ID]
        LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
        WHERE ewh.[Equipment_ID] = ? AND ewh.[ValidTo] IS NULL
        """,
        equipment_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "history_id": row[0],
        "equipment_id": row[1],
        "signal_interface_id": row[2],
        "signal_interface_port_id": row[3],
        "valid_from": row[4],
        "valid_to": row[5],
        "note": row[6],
        "signal_interface_name": row[7],
        "equipment_identifier": row[8],
    }


def rewire_equipment(
    conn: pyodbc.Connection,
    equipment_id: int,
    new_signal_interface_id: int,
    new_signal_interface_port_id: int | None,
    swap_time: datetime,
    note: str | None = None,
) -> tuple[int, int | None]:
    """Close the current active wiring history row and open a new one.

    Returns ``(new_history_id, closed_history_id)``.  ``closed_history_id`` is
    ``None`` when there was no active row to close (first registration case).

    The swap is atomic within a single transaction.
    """
    cursor = conn.cursor()
    closed_id: int | None = None

    # Close the active row, if any.
    cursor.execute(
        """
        UPDATE [dbo].[EquipmentWiringHistory]
        SET [ValidTo] = ?
        OUTPUT DELETED.[EquipmentWiringHistory_ID]
        WHERE [Equipment_ID] = ? AND [ValidTo] IS NULL
        """,
        swap_time,
        equipment_id,
    )
    row = cursor.fetchone()
    if row:
        closed_id = row[0]

    # Open the new row.
    cursor.execute(
        """
        INSERT INTO [dbo].[EquipmentWiringHistory]
            ([Equipment_ID], [SignalInterface_ID], [SignalInterfacePort_ID], [ValidFrom], [Note])
        OUTPUT INSERTED.[EquipmentWiringHistory_ID]
        VALUES (?, ?, ?, ?, ?)
        """,
        equipment_id,
        new_signal_interface_id,
        new_signal_interface_port_id,
        swap_time,
        note,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id, closed_id


def register_equipment_at_interface(
    conn: pyodbc.Connection,
    equipment_id: int,
    signal_interface_id: int,
    signal_interface_port_id: int | None,
    start_time: datetime | None = None,
    note: str | None = None,
) -> int:
    """Open a new EquipmentWiringHistory row (no active row must exist).

    If ``start_time`` is None, uses SYSUTCDATETIME().

    Raises ``ValueError`` if an active row already exists — callers should use
    ``rewire_equipment`` instead.

    Returns ``EquipmentWiringHistory_ID``.
    """
    active = get_active_wiring_for_equipment(conn, equipment_id)
    if active is not None:
        raise ValueError(
            f"Equipment {equipment_id} already has an active wiring history row "
            f"(ID={active['history_id']}, SignalInterface_ID={active['signal_interface_id']}). "
            "Use rewire_equipment to replace the current wiring."
        )

    cursor = conn.cursor()
    if start_time is None:
        cursor.execute(
            """
            INSERT INTO [dbo].[EquipmentWiringHistory]
                ([Equipment_ID], [SignalInterface_ID], [SignalInterfacePort_ID], [ValidFrom], [Note])
            OUTPUT INSERTED.[EquipmentWiringHistory_ID]
            VALUES (?, ?, ?, SYSUTCDATETIME(), ?)
            """,
            equipment_id,
            signal_interface_id,
            signal_interface_port_id,
            note,
        )
    else:
        cursor.execute(
            """
            INSERT INTO [dbo].[EquipmentWiringHistory]
                ([Equipment_ID], [SignalInterface_ID], [SignalInterfacePort_ID], [ValidFrom], [Note])
            OUTPUT INSERTED.[EquipmentWiringHistory_ID]
            VALUES (?, ?, ?, ?, ?)
            """,
            equipment_id,
            signal_interface_id,
            signal_interface_port_id,
            start_time,
            note,
        )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def get_wiring_at_time(
    conn: pyodbc.Connection, equipment_id: int, at_time: datetime
) -> dict | None:
    """Return the wiring that was active at ``at_time``, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            ewh.[EquipmentWiringHistory_ID],
            ewh.[Equipment_ID],
            ewh.[SignalInterface_ID],
            ewh.[SignalInterfacePort_ID],
            ewh.[ValidFrom],
            ewh.[ValidTo],
            si.[Name] AS [signal_interface_name],
            e.[Identifier] AS [equipment_identifier]
        FROM [dbo].[EquipmentWiringHistory] ewh
        JOIN [dbo].[SignalInterface] si ON si.[SignalInterface_ID] = ewh.[SignalInterface_ID]
        LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
        WHERE ewh.[Equipment_ID] = ?
          AND ewh.[ValidFrom] <= ?
          AND (ewh.[ValidTo] IS NULL OR ewh.[ValidTo] > ?)
        """,
        equipment_id,
        at_time,
        at_time,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "history_id": row[0],
        "equipment_id": row[1],
        "signal_interface_id": row[2],
        "signal_interface_port_id": row[3],
        "valid_from": row[4],
        "valid_to": row[5],
        "signal_interface_name": row[6],
        "equipment_identifier": row[7],
    }


# ---------------------------------------------------------------------------
# EquipmentLocationHistory
# ---------------------------------------------------------------------------


def get_active_location_for_equipment(
    conn: pyodbc.Connection, equipment_id: int
) -> dict | None:
    """Return the currently active EquipmentLocationHistory row, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            elh.[EquipmentLocationHistory_ID],
            elh.[Equipment_ID],
            elh.[SamplingPoint_ID],
            elh.[ValidFrom],
            elh.[ValidTo],
            elh.[Notes],
            sp.[SamplingPoint] AS [sampling_point_name]
        FROM [dbo].[EquipmentLocationHistory] elh
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
        WHERE elh.[Equipment_ID] = ? AND elh.[ValidTo] IS NULL
        """,
        equipment_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "history_id": row[0],
        "equipment_id": row[1],
        "sampling_point_id": row[2],
        "valid_from": row[3],
        "valid_to": row[4],
        "notes": row[5],
        "sampling_point_name": row[6],
    }


def relocate_equipment(
    conn: pyodbc.Connection,
    equipment_id: int,
    new_sampling_point_id: int,
    start_time: datetime,
    notes: str | None = None,
) -> tuple[int, int | None]:
    """Close the current active location history row and open a new one.

    Returns ``(new_history_id, closed_history_id)``.  ``closed_history_id`` is
    ``None`` when there was no active row to close.

    ``start_time`` is required and must equal the physical move time.
    """
    cursor = conn.cursor()
    closed_id: int | None = None

    # Close the active row, if any.
    cursor.execute(
        """
        UPDATE [dbo].[EquipmentLocationHistory]
        SET [ValidTo] = ?
        OUTPUT DELETED.[EquipmentLocationHistory_ID]
        WHERE [Equipment_ID] = ? AND [ValidTo] IS NULL
        """,
        start_time,
        equipment_id,
    )
    row = cursor.fetchone()
    if row:
        closed_id = row[0]

    # Open the new row.
    cursor.execute(
        """
        INSERT INTO [dbo].[EquipmentLocationHistory]
            ([Equipment_ID], [SamplingPoint_ID], [ValidFrom], [Notes])
        OUTPUT INSERTED.[EquipmentLocationHistory_ID]
        VALUES (?, ?, ?, ?)
        """,
        equipment_id,
        new_sampling_point_id,
        start_time,
        notes,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id, closed_id


def open_location_for_campaign(
    conn: pyodbc.Connection,
    equipment_id: int,
    sampling_point_id: int,
    start_time: datetime,
    campaign_id: int,
    notes: str | None = None,
) -> tuple[int, int | None]:
    """Close any active EquipmentLocationHistory row and open a new one
    tagged with ``Campaign_ID``.

    Caller owns the transaction — this function does NOT commit. Use this
    inside a multi-step deployment transaction (see
    ``campaign_repository.create_campaign_deployment``); for standalone moves
    use :func:`relocate_equipment`, which commits internally and does not
    record a Campaign_ID.

    Returns ``(new_history_id, closed_history_id)``; ``closed_history_id`` is
    ``None`` when there was no active row to close.
    """
    cursor = conn.cursor()
    closed_id: int | None = None

    cursor.execute(
        """
        UPDATE [dbo].[EquipmentLocationHistory]
        SET [ValidTo] = ?
        OUTPUT DELETED.[EquipmentLocationHistory_ID]
        WHERE [Equipment_ID] = ? AND [ValidTo] IS NULL
        """,
        start_time,
        equipment_id,
    )
    row = cursor.fetchone()
    if row:
        closed_id = row[0]

    cursor.execute(
        """
        INSERT INTO [dbo].[EquipmentLocationHistory]
            ([Equipment_ID], [SamplingPoint_ID], [ValidFrom], [Campaign_ID], [Notes])
        OUTPUT INSERTED.[EquipmentLocationHistory_ID]
        VALUES (?, ?, ?, ?, ?)
        """,
        equipment_id,
        sampling_point_id,
        start_time,
        campaign_id,
        notes,
    )
    new_id: int = cursor.fetchone()[0]
    return new_id, closed_id


def get_location_at_time(
    conn: pyodbc.Connection, equipment_id: int, at_time: datetime
) -> dict | None:
    """Return the SamplingPoint that was active at ``at_time``, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            elh.[EquipmentLocationHistory_ID],
            elh.[Equipment_ID],
            elh.[SamplingPoint_ID],
            elh.[ValidFrom],
            elh.[ValidTo],
            sp.[SamplingPoint] AS [sampling_point_name],
            sp.[Description] AS [sampling_point_description]
        FROM [dbo].[EquipmentLocationHistory] elh
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
        WHERE elh.[Equipment_ID] = ?
          AND elh.[ValidFrom] <= ?
          AND (elh.[ValidTo] IS NULL OR elh.[ValidTo] > ?)
        """,
        equipment_id,
        at_time,
        at_time,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "history_id": row[0],
        "equipment_id": row[1],
        "sampling_point_id": row[2],
        "valid_from": row[3],
        "valid_to": row[4],
        "sampling_point_name": row[5],
        "sampling_point_description": row[6],
    }


# ---------------------------------------------------------------------------
# DASLocationHistory
# ---------------------------------------------------------------------------


def get_active_das_deployment(
    conn: pyodbc.Connection, das_id: int
) -> dict | None:
    """Return the currently active DASLocationHistory row, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            dlh.[DASLocationHistory_ID],
            dlh.[DataAcquisitionSystem_ID],
            dlh.[Site_ID],
            dlh.[Campaign_ID],
            dlh.[ValidFrom],
            dlh.[ValidTo],
            dlh.[Notes],
            s.[Name] AS [site_name],
            c.[Name] AS [campaign_name]
        FROM [dbo].[DASLocationHistory] dlh
        LEFT JOIN [dbo].[Site] s ON s.[Site_ID] = dlh.[Site_ID]
        LEFT JOIN [dbo].[Campaign] c ON c.[Campaign_ID] = dlh.[Campaign_ID]
        WHERE dlh.[DataAcquisitionSystem_ID] = ? AND dlh.[ValidTo] IS NULL
        """,
        das_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "history_id": row[0],
        "das_id": row[1],
        "site_id": row[2],
        "campaign_id": row[3],
        "valid_from": row[4],
        "valid_to": row[5],
        "notes": row[6],
        "site_name": row[7],
        "campaign_name": row[8],
    }


def deploy_das(
    conn: pyodbc.Connection,
    das_id: int,
    site_id: int,
    valid_from: datetime,
    campaign_id: int | None = None,
    notes: str | None = None,
) -> tuple[int, int | None]:
    """Close any active DASLocationHistory row and open a new deployment.

    Returns ``(new_history_id, closed_history_id)``.  ``closed_history_id``
    is ``None`` when there was no active row (first deployment).

    The swap is atomic within a single transaction.
    """
    cursor = conn.cursor()
    closed_id: int | None = None

    # Close the active row, if any.
    cursor.execute(
        """
        UPDATE [dbo].[DASLocationHistory]
        SET [ValidTo] = ?
        OUTPUT DELETED.[DASLocationHistory_ID]
        WHERE [DataAcquisitionSystem_ID] = ? AND [ValidTo] IS NULL
        """,
        valid_from,
        das_id,
    )
    row = cursor.fetchone()
    if row:
        closed_id = row[0]

    # Open the new row.
    cursor.execute(
        """
        INSERT INTO [dbo].[DASLocationHistory]
            ([DataAcquisitionSystem_ID], [Site_ID], [Campaign_ID], [ValidFrom], [Notes])
        OUTPUT INSERTED.[DASLocationHistory_ID]
        VALUES (?, ?, ?, ?, ?)
        """,
        das_id,
        site_id,
        campaign_id,
        valid_from,
        notes,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id, closed_id


def get_das_conflict(
    conn: pyodbc.Connection, das_id: int, site_id: int
) -> dict | None:
    """Return the active deployment if the DAS is currently at a *different* site.

    Returns ``None`` if the DAS has no active deployment, or if the active
    deployment is already at ``site_id`` (shared-site use is fine).
    """
    active = get_active_das_deployment(conn, das_id)
    if active is None:
        return None
    if active["site_id"] == site_id:
        return None
    return active
