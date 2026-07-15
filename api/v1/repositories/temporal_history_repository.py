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


def _assert_valid_from_ok(
    cursor: pyodbc.Cursor,
    table: str,
    entity_col: str,
    entity_id: int,
    valid_from: datetime,
) -> None:
    """Reject a backdated ``valid_from`` that would overlap existing history (F7).

    The swap helpers open the new active row at ``valid_from`` (ValidTo NULL) and
    close the prior active row at ``valid_from``. That is only coherent when
    ``valid_from`` falls strictly after the active row's start and outside every
    closed ``[ValidFrom, ValidTo)`` interval. A unique filtered index already
    guarantees one *open* row, but nothing stops a backdated insert from inverting
    the row it closes or landing inside an old interval — this is that guard.

    ``table``/``entity_col`` are fixed internal identifiers (never user input).
    """
    cursor.execute(
        f"""
        SELECT TOP 1 [ValidFrom], [ValidTo]
        FROM [dbo].[{table}]
        WHERE [{entity_col}] = ?
          AND (
                ([ValidTo] IS NULL AND [ValidFrom] >= ?)
             OR ([ValidTo] IS NOT NULL AND [ValidFrom] <= ? AND ? < [ValidTo])
              )
        """,
        entity_id,
        valid_from,
        valid_from,
        valid_from,
    )
    row = cursor.fetchone()
    if row is not None:
        raise ValueError(
            f"valid_from {valid_from} conflicts with an existing {table} interval "
            f"[{row[0]}, {row[1]}) for {entity_col}={entity_id}: the new active row "
            "would overlap or invert history. Use a timestamp strictly after the "
            "current active row's start and outside any past interval."
        )


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
    # F8: reject a rewire to the interface+port already active — no churn row.
    active = get_active_wiring_for_equipment(conn, equipment_id)
    if (
        active is not None
        and active["signal_interface_id"] == new_signal_interface_id
        and active["signal_interface_port_id"] == new_signal_interface_port_id
    ):
        raise ValueError(
            f"Equipment {equipment_id} is already wired to SignalInterface "
            f"{new_signal_interface_id} (port {new_signal_interface_port_id}); "
            "nothing to rewire."
        )

    cursor = conn.cursor()
    closed_id: int | None = None

    # F7: a backdated swap_time must not overlap or invert existing history.
    _assert_valid_from_ok(
        cursor, "EquipmentWiringHistory", "Equipment_ID", equipment_id, swap_time
    )

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
        # No start_time → "now", which is after all existing rows; no overlap risk.
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
        # F7: a backdated first row must not land inside any closed interval.
        _assert_valid_from_ok(
            cursor, "EquipmentWiringHistory", "Equipment_ID", equipment_id, start_time
        )
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
    campaign_id: int | None = None,
    notes: str | None = None,
) -> tuple[int, int | None]:
    """Close the current active location history row and open a new one.

    Returns ``(new_history_id, closed_history_id)``.  ``closed_history_id`` is
    ``None`` when there was no active row to close.

    ``start_time`` is required and must equal the physical move time.
    ``campaign_id`` is required by the schema (Campaign_ID NOT NULL).
    """
    # F8: reject a relocate to the SamplingPoint already active — no churn row.
    active = get_active_location_for_equipment(conn, equipment_id)
    if active is not None and active["sampling_point_id"] == new_sampling_point_id:
        raise ValueError(
            f"Equipment {equipment_id} is already located at SamplingPoint "
            f"{new_sampling_point_id}; nothing to relocate."
        )

    cursor = conn.cursor()
    closed_id: int | None = None

    # F7: a backdated start_time must not overlap or invert existing history.
    _assert_valid_from_ok(
        cursor, "EquipmentLocationHistory", "Equipment_ID", equipment_id, start_time
    )

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
            ([Equipment_ID], [SamplingPoint_ID], [ValidFrom], [Campaign_ID], [Notes])
        OUTPUT INSERTED.[EquipmentLocationHistory_ID]
        VALUES (?, ?, ?, ?, ?)
        """,
        equipment_id,
        new_sampling_point_id,
        start_time,
        campaign_id,
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

    # F7: a backdated start_time must not overlap or invert existing history.
    _assert_valid_from_ok(
        cursor, "EquipmentLocationHistory", "Equipment_ID", equipment_id, start_time
    )

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
    # F8: reject a redeploy to the Site already active — no churn row.
    active = get_active_das_deployment(conn, das_id)
    if active is not None and active["site_id"] == site_id:
        raise ValueError(
            f"DAS {das_id} is already deployed at Site {site_id}; "
            "nothing to redeploy."
        )

    cursor = conn.cursor()
    closed_id: int | None = None

    # F7: a backdated valid_from must not overlap or invert existing history.
    _assert_valid_from_ok(
        cursor, "DASLocationHistory", "DataAcquisitionSystem_ID", das_id, valid_from
    )

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


def list_deployment_traces(
    conn: pyodbc.Connection,
    *,
    sampling_point_id: int | None = None,
    campaign_id: int | None = None,
    parameter_id: int | None = None,
    value_kind_id: int | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> list[dict]:
    """Return Deployment Trace lookup rows for the Data Explorer picker.

    Each row is one EquipmentLocationHistory record joined with the channels
    that were wired to that equipment during the deployment period, plus
    SamplingPoint and Campaign metadata.

    Channels that have no EquipmentWiringHistory (imported but not yet linked
    to a deployment) are included as a UNION when no campaign/location filter
    is active.  Those rows have NULL deployment fields and is_deployed=False.

    Time-range filter: returns deployments that overlapped [from_dt, to_dt].
    """
    deployed_where_parts = ["1=1"]
    params: list = []

    if sampling_point_id is not None:
        deployed_where_parts.append("elh.[SamplingPoint_ID] = ?")
        params.append(sampling_point_id)
    if campaign_id is not None:
        deployed_where_parts.append("elh.[Campaign_ID] = ?")
        params.append(campaign_id)
    if parameter_id is not None:
        deployed_where_parts.append("ch.[Parameter_ID] = ?")
        params.append(parameter_id)
    if value_kind_id is not None:
        deployed_where_parts.append("ch.[ValueKind_ID] = ?")
        params.append(value_kind_id)
    if to_dt is not None:
        deployed_where_parts.append("elh.[ValidFrom] <= ?")
        params.append(to_dt)
    if from_dt is not None:
        deployed_where_parts.append("(elh.[ValidTo] IS NULL OR elh.[ValidTo] >= ?)")
        params.append(from_dt)

    deployed_where = " AND ".join(deployed_where_parts)

    # Orphaned channels (no wiring history) are shown when no campaign/location
    # filter is active — they have no deployment context to match against.
    include_orphaned = sampling_point_id is None and campaign_id is None

    # Orphaned filter: channels with no ELH for their equipment (never placed at a location).
    # Uses NOT EXISTS to handle both: channels with no EWH at all, and channels whose
    # equipment has EWH but has never been given an EquipmentLocationHistory row.
    orphaned_extra_parts: list[str] = []
    orphaned_params: list = []
    if parameter_id is not None:
        orphaned_extra_parts.append("ch.[Parameter_ID] = ?")
        orphaned_params.append(parameter_id)
    if value_kind_id is not None:
        orphaned_extra_parts.append("ch.[ValueKind_ID] = ?")
        orphaned_params.append(value_kind_id)

    orphaned_extra = ""
    if orphaned_extra_parts:
        orphaned_extra = "AND " + " AND ".join(orphaned_extra_parts)

    union_sql = ""
    if include_orphaned:
        union_sql = f"""
        UNION ALL
        SELECT DISTINCT
            NULL                        AS EquipmentLocationHistory_ID,
            ch.[Stream_ID],
            e.[Equipment_ID],
            COALESCE(e.[Identifier], si.[Name]) AS equipment_identifier,
            NULL                        AS SamplingPoint_ID,
            NULL                        AS sampling_point_label,
            p.[Parameter_ID],
            p.[Parameter]               AS parameter_name,
            ch.[ValueKind_ID],
            NULL                        AS Campaign_ID,
            NULL                        AS campaign_name,
            NULL                        AS ValidFrom,
            NULL                        AS ValidTo,
            0                           AS is_deployed
        FROM [dbo].[vw_ChannelResolved] ch
        JOIN [dbo].[SignalInterface] si ON si.[SignalInterface_ID] = ch.[SignalInterface_ID]
        JOIN [dbo].[Parameter]       p  ON p.[Parameter_ID]        = ch.[Parameter_ID]
        LEFT JOIN [dbo].[EquipmentWiringHistory] ewh
            ON ewh.[SignalInterface_ID] = ch.[SignalInterface_ID]
            AND (
                ewh.[SignalInterfacePort_ID] = ch.[SignalInterfacePort_ID]
                OR (ewh.[SignalInterfacePort_ID] IS NULL AND ch.[SignalInterfacePort_ID] IS NULL)
                OR ch.[SignalInterfacePort_ID] IS NULL
            )
            AND ewh.[ValidTo] IS NULL
        LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
        WHERE NOT EXISTS (
            SELECT 1
            FROM [dbo].[EquipmentWiringHistory] ewh2
            JOIN [dbo].[EquipmentLocationHistory] elh2
                ON elh2.[Equipment_ID] = ewh2.[Equipment_ID]
            WHERE ewh2.[SignalInterface_ID] = ch.[SignalInterface_ID]
              AND (
                  ewh2.[SignalInterfacePort_ID] = ch.[SignalInterfacePort_ID]
                  OR (ewh2.[SignalInterfacePort_ID] IS NULL AND ch.[SignalInterfacePort_ID] IS NULL)
                  OR ch.[SignalInterfacePort_ID] IS NULL
              )
        )
        {orphaned_extra}
        """
        params.extend(orphaned_params)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT DISTINCT
            elh.[EquipmentLocationHistory_ID],
            ch.[Stream_ID],
            e.[Equipment_ID],
            e.[Identifier]          AS equipment_identifier,
            sp.[SamplingPoint_ID],
            sp.[SamplingPoint]      AS sampling_point_label,
            p.[Parameter_ID],
            p.[Parameter]           AS parameter_name,
            ch.[ValueKind_ID],
            c.[Campaign_ID],
            c.[Name]                AS campaign_name,
            elh.[ValidFrom],
            elh.[ValidTo],
            1                       AS is_deployed
        FROM [dbo].[EquipmentLocationHistory] elh
        JOIN [dbo].[Equipment]       e   ON e.[Equipment_ID]      = elh.[Equipment_ID]
        JOIN [dbo].[SamplingPoint]   sp  ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
        JOIN [dbo].[Campaign]        c   ON c.[Campaign_ID]       = elh.[Campaign_ID]
        JOIN [dbo].[EquipmentWiringHistory] ewh
            ON ewh.[Equipment_ID] = elh.[Equipment_ID]
            AND ewh.[ValidFrom]  <= ISNULL(elh.[ValidTo], GETUTCDATE())
            AND (ewh.[ValidTo] IS NULL OR ewh.[ValidTo] >= elh.[ValidFrom])
        JOIN [dbo].[vw_ChannelResolved] ch
            ON ch.[SignalInterface_ID] = ewh.[SignalInterface_ID]
            AND (
                ewh.[SignalInterfacePort_ID] = ch.[SignalInterfacePort_ID]
                OR (ewh.[SignalInterfacePort_ID] IS NULL AND ch.[SignalInterfacePort_ID] IS NULL)
                OR ch.[SignalInterfacePort_ID] IS NULL
            )
        JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = ch.[Parameter_ID]
        WHERE {deployed_where}
        {union_sql}
        ORDER BY is_deployed DESC, campaign_name, sampling_point_label, parameter_name
        """,
        *params,
    )
    rows = cursor.fetchall()
    return [
        {
            "equipment_location_history_id": r[0],
            "channel_id": r[1],
            "equipment_id": r[2],
            "equipment_identifier": r[3],
            "sampling_point_id": r[4],
            "sampling_point_label": r[5],
            "parameter_id": r[6],
            "parameter_name": r[7],
            "value_kind_id": r[8],
            "campaign_id": r[9],
            "campaign_name": r[10],
            "valid_from": r[11],
            "valid_to": r[12],
            "is_deployed": bool(r[13]),
        }
        for r in rows
    ]


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


def get_das_move_equipment_conflicts(
    conn: pyodbc.Connection, das_id: int, new_site_id: int
) -> list[dict]:
    """Equipment that would be left stranded if this DAS moves to ``new_site_id``
    (consistency audit F1).

    Returns the equipment currently wired (active EquipmentWiringHistory) to one
    of this DAS's SignalInterfaces whose active location is at a SamplingPoint in
    a *different* Site than ``new_site_id``. The DAS-move flow surfaces this list
    so the user can relocate those equipment in the same step rather than leaving
    a silent location/DAS mismatch (which ``vw_DeploymentCoherence`` would then
    report). Empty list = the move is coherent.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT
            e.[Equipment_ID],
            e.[Identifier]          AS equipment_identifier,
            sp.[SamplingPoint_ID],
            sp.[SamplingPoint]      AS sampling_point_name,
            sp.[Site_ID]            AS current_site_id,
            s.[Name]                AS current_site_name
        FROM [dbo].[EquipmentWiringHistory] ewh
        JOIN [dbo].[SignalInterface] si
            ON si.[SignalInterface_ID] = ewh.[SignalInterface_ID]
            AND si.[DataAcquisitionSystem_ID] = ?
        JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
        JOIN [dbo].[EquipmentLocationHistory] elh
            ON elh.[Equipment_ID] = e.[Equipment_ID] AND elh.[ValidTo] IS NULL
        JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
        LEFT JOIN [dbo].[Site] s ON s.[Site_ID] = sp.[Site_ID]
        WHERE ewh.[ValidTo] IS NULL
          AND sp.[Site_ID] <> ?
        """,
        das_id,
        new_site_id,
    )
    return [
        {
            "equipment_id": row[0],
            "equipment_identifier": row[1],
            "sampling_point_id": row[2],
            "sampling_point_name": row[3],
            "current_site_id": row[4],
            "current_site_name": row[5],
        }
        for row in cursor.fetchall()
    ]


def get_active_campaign_deployment(
    conn: pyodbc.Connection, equipment_id: int
) -> dict | None:
    """The still-active campaign whose deployment placed this equipment, if any
    (consistency audit F13).

    Physical configuration is shared across campaigns, so reconfiguring equipment
    (relocate/rewire) that was placed by a campaign whose run has not ended will
    close that campaign's deployment. This returns that campaign so the caller can
    warn before acting. ``None`` when the equipment's active location row has no
    campaign provenance, or that campaign has already ended.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            c.[Campaign_ID],
            c.[Name]                            AS campaign_name,
            elh.[EquipmentLocationHistory_ID],
            elh.[SamplingPoint_ID],
            sp.[SamplingPoint]                  AS sampling_point_name
        FROM [dbo].[EquipmentLocationHistory] elh
        JOIN [dbo].[Campaign] c ON c.[Campaign_ID] = elh.[Campaign_ID]
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
        WHERE elh.[Equipment_ID] = ?
          AND elh.[ValidTo] IS NULL
          AND (c.[CampaignEndDateTime] IS NULL OR c.[CampaignEndDateTime] > SYSUTCDATETIME())
        """,
        equipment_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "campaign_id": row[0],
        "campaign_name": row[1],
        "equipment_location_history_id": row[2],
        "sampling_point_id": row[3],
        "sampling_point_name": row[4],
    }


# ---------------------------------------------------------------------------
# Stream provenance (where is this stream coming from?)
# ---------------------------------------------------------------------------


def get_stream_location_at(
    conn: pyodbc.Connection, stream_id: int, at_time: datetime
) -> dict | None:
    """Return the SamplingPoint a Stream was sourced from at ``at_time``.

    Two stream subtypes, two paths:
      - AnalysisSeries (lab): SamplingPoint_ID is a direct FK, not temporal.
      - Channel (sensor): Channel -> ChannelPortHistory@t -> port
        -> EquipmentWiringHistory@t -> Equipment
        -> EquipmentLocationHistory@t -> SamplingPoint.

    All three channel hops are temporal, so this cannot go through
    ``vw_ChannelResolved`` — that view pins the port to the *currently* open
    ChannelPortHistory row, which is wrong for any ``at_time`` in the past.

    ``source`` reports which path resolved: "analysis_series", "wiring", or
    None when the stream exists but has no location at ``at_time`` (channel
    never wired, or wired equipment never placed).

    Returns None when ``stream_id`` matches no Channel and no AnalysisSeries.
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            a.[SamplingPoint_ID],
            sp.[SamplingPoint],
            sp.[Site_ID],
            s.[Name]
        FROM [dbo].[AnalysisSeries] a
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = a.[SamplingPoint_ID]
        LEFT JOIN [dbo].[Site] s ON s.[Site_ID] = sp.[Site_ID]
        WHERE a.[Stream_ID] = ?
        """,
        stream_id,
    )
    row = cursor.fetchone()
    if row is not None:
        return {
            "stream_id": stream_id,
            "source": "analysis_series",
            "inherited_from_stream_id": None,
            "sampling_point_id": row[0],
            "sampling_point_name": row[1],
            "site_id": row[2],
            "site_name": row[3],
            "equipment_id": None,
            "equipment_identifier": None,
            "history_id": None,
            "valid_from": None,
            "valid_to": None,
        }

    # LEFT JOINs throughout: an unwired channel still returns a row, so a NULL
    # result here means "no such stream" rather than "no location".
    #
    # Derived channels (::outlier_free, ::smoothed, ...) carry no wiring of
    # their own — they inherit the location of the raw channel they descend
    # from. The recursive CTE walks ParentChannel_ID up to the root, and the
    # ORDER BY takes the nearest ancestor that actually resolves to a
    # SamplingPoint, falling back to the depth-0 row (all NULLs) if none do.
    cursor.execute(
        """
        WITH ancestry AS (
            SELECT
                c.[Stream_ID],
                c.[ParentChannel_ID],
                c.[SignalInterface_ID],
                0 AS depth
            FROM [dbo].[Channel] c
            WHERE c.[Stream_ID] = ?
            UNION ALL
            SELECT
                p.[Stream_ID],
                p.[ParentChannel_ID],
                p.[SignalInterface_ID],
                a.depth + 1
            FROM [dbo].[Channel] p
            JOIN ancestry a ON p.[Stream_ID] = a.[ParentChannel_ID]
        )
        SELECT TOP 1
            ewh.[Equipment_ID],
            e.[Identifier],
            elh.[EquipmentLocationHistory_ID],
            elh.[SamplingPoint_ID],
            sp.[SamplingPoint],
            sp.[Site_ID],
            s.[Name],
            elh.[ValidFrom],
            elh.[ValidTo],
            ch.[Stream_ID] AS resolved_stream_id
        FROM ancestry ch
        LEFT JOIN [dbo].[ChannelPortHistory] cph
            ON cph.[Channel_ID] = ch.[Stream_ID]
            AND cph.[ValidFrom] <= ?
            AND (cph.[ValidTo] IS NULL OR cph.[ValidTo] > ?)
        LEFT JOIN [dbo].[EquipmentWiringHistory] ewh
            ON ewh.[SignalInterface_ID] = ch.[SignalInterface_ID]
            AND (
                ewh.[SignalInterfacePort_ID] = cph.[SignalInterfacePort_ID]
                OR (ewh.[SignalInterfacePort_ID] IS NULL AND cph.[SignalInterfacePort_ID] IS NULL)
                OR cph.[SignalInterfacePort_ID] IS NULL
            )
            AND ewh.[ValidFrom] <= ?
            AND (ewh.[ValidTo] IS NULL OR ewh.[ValidTo] > ?)
        LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
        LEFT JOIN [dbo].[EquipmentLocationHistory] elh
            ON elh.[Equipment_ID] = ewh.[Equipment_ID]
            AND elh.[ValidFrom] <= ?
            AND (elh.[ValidTo] IS NULL OR elh.[ValidTo] > ?)
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
        LEFT JOIN [dbo].[Site] s ON s.[Site_ID] = sp.[Site_ID]
        ORDER BY
            CASE WHEN elh.[SamplingPoint_ID] IS NULL THEN 1 ELSE 0 END,
            ch.depth,
            CASE WHEN ewh.[SignalInterfacePort_ID] = cph.[SignalInterfacePort_ID]
                 THEN 0 ELSE 1 END,
            elh.[EquipmentLocationHistory_ID] DESC
        """,
        stream_id,
        at_time,
        at_time,
        at_time,
        at_time,
        at_time,
        at_time,
    )
    row = cursor.fetchone()
    if row is None:
        return None

    resolved_stream_id = row[9]
    return {
        "stream_id": stream_id,
        "source": "wiring" if row[3] is not None else None,
        "inherited_from_stream_id": (
            resolved_stream_id if row[3] is not None and resolved_stream_id != stream_id else None
        ),
        "sampling_point_id": row[3],
        "sampling_point_name": row[4],
        "site_id": row[5],
        "site_name": row[6],
        "equipment_id": row[0],
        "equipment_identifier": row[1],
        "history_id": row[2],
        "valid_from": row[7],
        "valid_to": row[8],
    }
