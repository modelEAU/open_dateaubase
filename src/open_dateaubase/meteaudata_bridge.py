"""Bridge between open_dateaubase and the metEAUdata processing library.

Provides two public functions:

* ``load_signal_context`` — pull full resolved context for a Channel row
  so that metEAUdata can reconstruct a DataProvenance object without manual
  channel_id strings.

* ``record_processing`` — persist a ProcessingStep + ProcessingLineage rows after
  metEAUdata has applied a transformation, closing the full provenance loop.

Both functions accept a plain pyodbc connection and are transport-agnostic:
the caller (e.g. OpenDateaubaseAdapter in meteaudata) manages connection
lifecycle and transaction boundaries.
"""

from __future__ import annotations

import json
from datetime import datetime


def load_signal_context(channel_id: int, conn) -> dict:
    """Load the full resolved context for a Channel row.

    Queries Channel and JOIN-resolves foreign keys (Equipment, Parameter,
    Unit, DataProvenance).

    Args:
        channel_id: Primary key of the Channel row.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        A dict with the following keys (all nullable values may be None):
          channel_id, parameter, unit, equipment, data_provenance,
          processing_degree

    Raises:
        KeyError: If the channel_id does not exist.
    """
    sql = """
        SELECT
            c.[Channel_ID],
            -- Parameter
            p.[Parameter_ID],
            p.[Parameter]          AS [ParameterName],
            -- Unit
            u.[Unit_ID],
            u.[Unit]               AS [UnitName],
            -- Equipment
            e.[Equipment_ID],
            e.[Identifier]         AS [EquipmentName],
            -- DataProvenanceKind
            dp.[Name]              AS [DataProvenanceName],
            -- ProcessingKind (via ProducedByStep_ID → ProcessingStep)
            pk.[Name]              AS [ProcessingKindName]
        FROM [dbo].[Channel] c
        LEFT JOIN [dbo].[Parameter]           p   ON p.[Parameter_ID]          = c.[Parameter_ID]
        LEFT JOIN [dbo].[Unit]                u   ON u.[Unit_ID]               = c.[Unit_ID]
        LEFT JOIN [dbo].[EquipmentWiringHistory] ewh
            ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
            AND ewh.[ValidTo] IS NULL
        LEFT JOIN [dbo].[Equipment]           e   ON e.[Equipment_ID]          = ewh.[Equipment_ID]
        LEFT JOIN [dbo].[DataProvenanceKind]  dp  ON dp.[DataProvenanceKind_ID] = c.[DataProvenanceKind_ID]
        LEFT JOIN [dbo].[ProcessingStep]      ps  ON ps.[ProcessingStep_ID]    = c.[ProducedByStep_ID]
        LEFT JOIN [dbo].[ProcessingKind]      pk  ON pk.[ProcessingKind_ID]    = ps.[ProcessingKind_ID]
        WHERE c.[Channel_ID] = ?
    """
    cursor = conn.cursor()
    cursor.execute(sql, channel_id)
    row = cursor.fetchone()

    if row is None:
        raise KeyError(f"Channel row not found: channel_id={channel_id}")

    (
        ch_id,
        param_id, param_name,
        unit_id, unit_name,
        equip_id, equip_name,
        data_provenance_name,
        processing_kind_name,
    ) = row

    return {
        "channel_id": ch_id,
        "parameter": {"id": param_id, "name": param_name} if param_id else None,
        "unit": unit_name,
        "equipment": {"id": equip_id, "name": equip_name} if equip_id else None,
        "data_provenance": data_provenance_name,
        "processing_kind_name": processing_kind_name,
    }


def record_processing(
    source_metadata_ids: list[int],
    method_name: str,
    method_version: str | None,
    processing_kind_id: int,
    method_parameters: dict,
    executed_at: datetime,
    executed_by_person_id: int | None,
    conn,
) -> int:
    """Insert a ProcessingStep row and its ProcessingLineage input edges.

    Idempotent: if a ProcessingStep with the same fingerprint already exists
    and has the same set of source channels, its ID is returned without inserting
    duplicates.

    Output channels are identified by Channel.ProducedByStep_ID — they are not
    registered as lineage edges here. The caller is responsible for creating the
    output Channel with ProducedByStep_ID pointing to the returned step_id.

    Args:
        source_metadata_ids: Channel IDs that were consumed as inputs.
        method_name: Machine-readable method identifier (e.g. 'outlier_removal').
        method_version: Library/method version string, or None.
        processing_kind_id: FK to ProcessingKind.
        method_parameters: Dict of method parameters; serialised to JSON for storage.
        executed_at: UTC datetime when the processing ran.
        executed_by_person_id: Person_ID of the operator, or None.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        The ProcessingStep_ID of the (new or existing) row.
    """
    params_json = json.dumps(method_parameters, default=str) if method_parameters else None

    # ----------------------------------------------------------------
    # Idempotency check: look for an existing step with identical fingerprint.
    # ----------------------------------------------------------------
    check_sql = """
        SELECT [ProcessingStep_ID]
        FROM [dbo].[ProcessingStep]
        WHERE [MethodName]           = ?
          AND ISNULL([ProcessingKind_ID], 0) = ISNULL(?, 0)
          AND ISNULL([MethodParameters], '')  = ISNULL(?, '')
          AND ISNULL(CONVERT(NVARCHAR(30), [ExecutedDateTime], 126), '')
            = ISNULL(CONVERT(NVARCHAR(30), CAST(? AS DATETIME2(7)), 126), '')
    """
    cursor = conn.cursor()
    cursor.execute(check_sql, method_name, processing_kind_id, params_json, executed_at)
    existing = cursor.fetchone()
    if existing is not None:
        return existing[0]

    # ----------------------------------------------------------------
    # Insert ProcessingStep
    # ----------------------------------------------------------------
    insert_step_sql = """
        INSERT INTO [dbo].[ProcessingStep]
            ([Name], [MethodName], [MethodVersion], [ProcessingKind_ID],
             [MethodParameters], [ExecutedDateTime], [ExecutedByPerson_ID])
        OUTPUT INSERTED.[ProcessingStep_ID]
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    name = method_name or "Processing step"
    cursor.execute(
        insert_step_sql,
        name,
        method_name,
        method_version,
        processing_kind_id,
        params_json,
        executed_at,
        executed_by_person_id,
    )
    step_id: int = cursor.fetchone()[0]

    # ----------------------------------------------------------------
    # Insert ProcessingLineage rows — Inputs only
    # ----------------------------------------------------------------
    for src_id in source_metadata_ids:
        cursor.execute(
            "INSERT INTO [dbo].[ProcessingLineage] ([ProcessingStep_ID], [Channel_ID]) "
            "VALUES (?, ?)",
            step_id,
            src_id,
        )

    conn.commit()
    return step_id
