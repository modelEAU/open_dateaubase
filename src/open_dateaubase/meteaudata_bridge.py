"""Bridge between open_dateaubase and the metEAUdata processing library.

Provides two public functions:

* ``load_signal_context`` — pull full resolved context for a Channel row
  so that metEAUdata can reconstruct a DataProvenance object without manual
  channel_id strings.

* ``record_processing`` — persist a ProcessingStep + DataLineage rows after
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
            e.[identifier]         AS [EquipmentName],
            -- DataProvenance
            dp.[DataProvenance_Name] AS [DataProvenanceName],
            -- ProcessingDegree
            c.[ProcessingDegree]
        FROM [dbo].[Channel] c
        LEFT JOIN [dbo].[Parameter]      p    ON p.[Parameter_ID]       = c.[Parameter_ID]
        LEFT JOIN [dbo].[Unit]           u    ON u.[Unit_ID]            = c.[Unit_ID]
        LEFT JOIN [dbo].[Equipment]      e    ON e.[Equipment_ID]       = c.[Equipment_ID]
        LEFT JOIN [dbo].[DataProvenance] dp   ON dp.[DataProvenance_ID] = c.[DataProvenance_ID]
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
        processing_degree,
    ) = row

    return {
        "channel_id": ch_id,
        "parameter": {"id": param_id, "name": param_name} if param_id else None,
        "unit": unit_name,
        "equipment": {"id": equip_id, "name": equip_name} if equip_id else None,
        "data_provenance": data_provenance_name,
        "processing_degree": processing_degree,
    }


def record_processing(
    source_metadata_ids: list[int],
    method_name: str,
    method_version: str | None,
    processing_type: str,
    parameters: dict,
    executed_at: datetime,
    executed_by_person_id: int | None,
    output_metadata_id: int,
    conn,
) -> int:
    """Insert a ProcessingStep row and its DataLineage edges.

    Idempotent: if a ProcessingStep with the same MethodName, ProcessingType,
    Parameters (JSON-serialised), ExecutedAt, and the same set of source and
    output channel IDs already exists, the function returns its ID without
    inserting duplicates.

    Args:
        source_metadata_ids: Channel IDs that were consumed as inputs.
        method_name: Machine-readable method identifier (e.g. 'outlier_removal').
        method_version: Library/method version string, or None.
        processing_type: ProcessingType enum value string (e.g. 'Smoothing').
        parameters: Dict of method parameters; serialised to JSON for storage.
        executed_at: UTC datetime when the processing ran.
        executed_by_person_id: Person_ID of the operator, or None.
        output_metadata_id: Channel ID of the result time series.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        The ProcessingStep_ID of the (new or existing) row.
    """
    params_json = json.dumps(parameters, default=str) if parameters else None

    # ----------------------------------------------------------------
    # Idempotency check: look for an existing step with identical
    # fingerprint that already links the same source→output pair.
    # ----------------------------------------------------------------
    check_sql = """
        SELECT DISTINCT ps.[ProcessingStep_ID]
        FROM [dbo].[ProcessingStep] ps
        JOIN [dbo].[DataLineage] out_dl
            ON out_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
           AND out_dl.[Role] = 'Output'
           AND out_dl.[Channel_ID] = ?
        WHERE ps.[MethodName]       = ?
          AND ps.[ProcessingType]   = ?
          AND ISNULL(ps.[Parameters], '')   = ISNULL(?, '')
          AND ISNULL(CONVERT(NVARCHAR(30), ps.[ExecutedAt], 126), '')
            = ISNULL(CONVERT(NVARCHAR(30), CAST(? AS DATETIME2(7)), 126), '')
    """
    cursor = conn.cursor()
    cursor.execute(
        check_sql,
        output_metadata_id,
        method_name,
        processing_type,
        params_json,
        executed_at,
    )
    existing = cursor.fetchone()
    if existing is not None:
        return existing[0]

    # ----------------------------------------------------------------
    # Insert ProcessingStep
    # ----------------------------------------------------------------
    insert_step_sql = """
        INSERT INTO [dbo].[ProcessingStep]
            ([Name], [MethodName], [MethodVersion], [ProcessingType],
             [Parameters], [ExecutedAt], [ExecutedByPerson_ID])
        OUTPUT INSERTED.[ProcessingStep_ID]
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    name = method_name or processing_type or "Processing step"
    cursor.execute(
        insert_step_sql,
        name,
        method_name,
        method_version,
        processing_type,
        params_json,
        executed_at,
        executed_by_person_id,
    )
    step_id: int = cursor.fetchone()[0]

    # ----------------------------------------------------------------
    # Insert DataLineage rows — Inputs
    # ----------------------------------------------------------------
    for src_id in source_metadata_ids:
        cursor.execute(
            "INSERT INTO [dbo].[DataLineage] ([ProcessingStep_ID], [Channel_ID], [Role]) "
            "VALUES (?, ?, 'Input')",
            step_id,
            src_id,
        )

    # ----------------------------------------------------------------
    # Insert DataLineage row — Output
    # ----------------------------------------------------------------
    cursor.execute(
        "INSERT INTO [dbo].[DataLineage] ([ProcessingStep_ID], [Channel_ID], [Role]) "
        "VALUES (?, ?, 'Output')",
        step_id,
        output_metadata_id,
    )

    conn.commit()
    return step_id
