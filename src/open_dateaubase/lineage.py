"""Lineage query functions for the open_dateaubase processing provenance graph.

All functions accept a pyodbc connection to an open_dateaubase MSSQL instance.

Graph model (ADR 0004 / ADR 0005):
  * ``ProcessingLineage`` holds only INPUT edges: each row asserts that a
    ``Stream_ID`` (a sensor Channel or a lab AnalysisSeries) was consumed as an
    input by a ``ProcessingStep``. There is no role column.
  * The OUTPUT of a step is a Channel identified by
    ``Channel.ProducedByStep_ID`` pointing back at the step.
  * Each ``ProcessingStep`` carries one ``OperationKind_ID`` (FK → OperationKind),
    replacing the retired ``ProcessingKind`` lookup.
"""

from __future__ import annotations

from datetime import datetime


def get_lineage_forward(stream_id: int, conn) -> list[dict]:
    """Return all processing steps that consumed this Stream as an Input,
    along with the output Channel IDs they produced.

    Args:
        stream_id: The source Stream (Channel or AnalysisSeries) to trace forward.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts, each with keys:
          - processing_step: dict of ProcessingStep columns
          - output_channel_ids: list[int] of Stream_IDs produced by that step
    """
    sql = """
        SELECT
            ps.[ProcessingStep_ID],
            ps.[Name],
            ps.[Description],
            ps.[MethodName],
            ps.[MethodVersion],
            ps.[OperationKind_ID],
            ps.[MethodParameters],
            ps.[ExecutedDateTime],
            ps.[ExecutedByPerson_ID],
            out_c.[Stream_ID]  AS [OutputChannel_ID]
        FROM [dbo].[ProcessingLineage]   AS in_dl
        JOIN [dbo].[ProcessingStep] AS ps
            ON ps.[ProcessingStep_ID] = in_dl.[ProcessingStep_ID]
        JOIN [dbo].[Channel] AS out_c
            ON out_c.[ProducedByStep_ID] = ps.[ProcessingStep_ID]
        WHERE in_dl.[Stream_ID] = ?
        ORDER BY ps.[ProcessingStep_ID], out_c.[Stream_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, stream_id)
    rows = cursor.fetchall()

    # Group output channel IDs by processing step
    steps: dict[int, dict] = {}
    for row in rows:
        step_id = row[0]
        if step_id not in steps:
            steps[step_id] = {
                "processing_step": {
                    "ProcessingStep_ID": row[0],
                    "Name": row[1],
                    "Description": row[2],
                    "MethodName": row[3],
                    "MethodVersion": row[4],
                    "OperationKind_ID": row[5],
                    "MethodParameters": row[6],
                    "ExecutedDateTime": row[7],
                    "ExecutedByPerson_ID": row[8],
                },
                "output_channel_ids": [],
            }
        steps[step_id]["output_channel_ids"].append(row[9])

    return list(steps.values())


def get_lineage_backward(stream_id: int, conn) -> list[dict]:
    """Return all processing steps that produced this Channel as an Output,
    along with the input Stream IDs they consumed.

    Args:
        stream_id: The target Channel (Stream_ID) to trace backward.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts, each with keys:
          - processing_step: dict of ProcessingStep columns
          - input_channel_ids: list[int] of Stream_IDs consumed by that step
    """
    sql = """
        SELECT
            ps.[ProcessingStep_ID],
            ps.[Name],
            ps.[Description],
            ps.[MethodName],
            ps.[MethodVersion],
            ps.[OperationKind_ID],
            ps.[MethodParameters],
            ps.[ExecutedDateTime],
            ps.[ExecutedByPerson_ID],
            in_dl.[Stream_ID]  AS [InputChannel_ID]
        FROM [dbo].[Channel] AS out_c
        JOIN [dbo].[ProcessingStep] AS ps
            ON ps.[ProcessingStep_ID] = out_c.[ProducedByStep_ID]
        JOIN [dbo].[ProcessingLineage]   AS in_dl
            ON in_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
        WHERE out_c.[Stream_ID] = ?
        ORDER BY ps.[ProcessingStep_ID], in_dl.[Stream_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, stream_id)
    rows = cursor.fetchall()

    steps: dict[int, dict] = {}
    for row in rows:
        step_id = row[0]
        if step_id not in steps:
            steps[step_id] = {
                "processing_step": {
                    "ProcessingStep_ID": row[0],
                    "Name": row[1],
                    "Description": row[2],
                    "MethodName": row[3],
                    "MethodVersion": row[4],
                    "OperationKind_ID": row[5],
                    "MethodParameters": row[6],
                    "ExecutedDateTime": row[7],
                    "ExecutedByPerson_ID": row[8],
                },
                "input_channel_ids": [],
            }
        steps[step_id]["input_channel_ids"].append(row[9])

    return list(steps.values())


def get_full_lineage_tree(stream_id: int, conn) -> dict:
    """Return the complete processing chain from raw ancestors to final descendants.

    Uses recursive CTEs to traverse the processing DAG in both directions.
    Edges are reconstructed from ProcessingLineage (input Stream_ID) and
    Channel.ProducedByStep_ID (output channel).

    Args:
        stream_id: The Channel row (Stream_ID) at the root of the tree.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        A tree dict:
          {
            'channel_id': int,
            'parents': list[dict],   # backward lineage (inputs)
            'children': list[dict],  # forward lineage (outputs)
          }
    """
    # Collect all ancestors (backward) using a recursive CTE.
    # A parent edge: out_c was produced by ps; in_dl is an input Stream of ps.
    ancestor_sql = """
        WITH Ancestors AS (
            -- Anchor: direct parents of the seed node
            SELECT
                in_dl.[Stream_ID]         AS [AncestorChannel_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[OperationKind_ID],
                out_c.[Stream_ID]         AS [ChildChannel_ID],
                1                          AS [Depth]
            FROM [dbo].[Channel] AS out_c
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = out_c.[ProducedByStep_ID]
            JOIN [dbo].[ProcessingLineage] AS in_dl
                ON in_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
            WHERE out_c.[Stream_ID] = ?

            UNION ALL

            -- Recursive: walk further up the graph
            SELECT
                in_dl.[Stream_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[OperationKind_ID],
                a.[AncestorChannel_ID],
                a.[Depth] + 1
            FROM Ancestors a
            JOIN [dbo].[Channel] AS out_c
                ON out_c.[Stream_ID] = a.[AncestorChannel_ID]
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = out_c.[ProducedByStep_ID]
            JOIN [dbo].[ProcessingLineage] AS in_dl
                ON in_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
        )
        SELECT DISTINCT [AncestorChannel_ID], [ProcessingStep_ID], [Name],
                        [OperationKind_ID], [ChildChannel_ID], [Depth]
        FROM Ancestors
        ORDER BY [Depth], [AncestorChannel_ID]
    """

    # Collect all descendants (forward).
    # A child edge: in_dl is an input Stream of ps; out_c was produced by ps.
    descendant_sql = """
        WITH Descendants AS (
            SELECT
                out_c.[Stream_ID]         AS [DescendantChannel_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[OperationKind_ID],
                in_dl.[Stream_ID]         AS [ParentChannel_ID],
                1                          AS [Depth]
            FROM [dbo].[ProcessingLineage] AS in_dl
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = in_dl.[ProcessingStep_ID]
            JOIN [dbo].[Channel] AS out_c
                ON out_c.[ProducedByStep_ID] = ps.[ProcessingStep_ID]
            WHERE in_dl.[Stream_ID] = ?

            UNION ALL

            SELECT
                out_c.[Stream_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[OperationKind_ID],
                d.[DescendantChannel_ID],
                d.[Depth] + 1
            FROM Descendants d
            JOIN [dbo].[ProcessingLineage] AS in_dl
                ON in_dl.[Stream_ID] = d.[DescendantChannel_ID]
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = in_dl.[ProcessingStep_ID]
            JOIN [dbo].[Channel] AS out_c
                ON out_c.[ProducedByStep_ID] = ps.[ProcessingStep_ID]
        )
        SELECT DISTINCT [DescendantChannel_ID], [ProcessingStep_ID], [Name],
                        [OperationKind_ID], [ParentChannel_ID], [Depth]
        FROM Descendants
        ORDER BY [Depth], [DescendantChannel_ID]
    """

    cursor = conn.cursor()

    cursor.execute(ancestor_sql, stream_id)
    ancestor_rows = cursor.fetchall()

    cursor.execute(descendant_sql, stream_id)
    descendant_rows = cursor.fetchall()

    parents = [
        {
            "channel_id": row[0],
            "processing_step_id": row[1],
            "processing_step_name": row[2],
            "operation_kind_id": row[3],
            "child_channel_id": row[4],
            "depth": row[5],
        }
        for row in ancestor_rows
    ]

    children = [
        {
            "channel_id": row[0],
            "processing_step_id": row[1],
            "processing_step_name": row[2],
            "operation_kind_id": row[3],
            "parent_channel_id": row[4],
            "depth": row[5],
        }
        for row in descendant_rows
    ]

    return {
        "channel_id": stream_id,
        "parents": parents,
        "children": children,
    }


def get_traits_for_stream(stream_id: int, conn) -> list[dict]:
    """Return the accumulated ChannelTrait set of a single Stream.

    Each Channel carries a many-to-many set of OperationKinds (ADR 0005) that is
    the union of its inputs' traits plus its producing step's OperationKind. Raw
    sensor channels carry a single ``Unprocessed`` trait; lab AnalysisSeries carry
    none.

    Args:
        stream_id: The Stream (Channel or AnalysisSeries) to read traits for.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts ``{operation_kind_id, name}`` ordered by OperationKind_ID
        (possibly empty).
    """
    sql = """
        SELECT ok.[OperationKind_ID], ok.[Name]
        FROM [dbo].[ChannelTrait] ct
        JOIN [dbo].[OperationKind] ok
            ON ok.[OperationKind_ID] = ct.[OperationKind_ID]
        WHERE ct.[Stream_ID] = ?
        ORDER BY ok.[OperationKind_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, stream_id)
    return [
        {"operation_kind_id": row[0], "name": row[1]} for row in cursor.fetchall()
    ]


def get_processing_step_detail(step_id: int, conn) -> dict | None:
    """Return one ProcessingStep with its OperationKind name, executor name, and
    the input / output Stream_IDs it connects.

    Args:
        step_id: ProcessingStep_ID.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        A dict of the step's columns (plus ``operation_kind_name``,
        ``executed_by_name``, ``input_stream_ids``, ``output_stream_ids``), or
        ``None`` if the step does not exist.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            ps.[ProcessingStep_ID],
            ps.[Name],
            ps.[Description],
            ps.[MethodName],
            ps.[MethodVersion],
            ps.[OperationKind_ID],
            ok.[Name]            AS [OperationKindName],
            ps.[MethodParameters],
            ps.[ExecutedDateTime],
            ps.[ExecutedByPerson_ID],
            per.[FirstName],
            per.[LastName]
        FROM [dbo].[ProcessingStep] ps
        JOIN [dbo].[OperationKind] ok
            ON ok.[OperationKind_ID] = ps.[OperationKind_ID]
        LEFT JOIN [dbo].[Person] per
            ON per.[Person_ID] = ps.[ExecutedByPerson_ID]
        WHERE ps.[ProcessingStep_ID] = ?
        """,
        step_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None

    first, last = row[10], row[11]
    executed_by_name = " ".join(p for p in (first, last) if p) or None

    cursor.execute(
        "SELECT [Stream_ID] FROM [dbo].[ProcessingLineage] "
        "WHERE [ProcessingStep_ID] = ? ORDER BY [Stream_ID]",
        step_id,
    )
    input_stream_ids = [r[0] for r in cursor.fetchall()]

    cursor.execute(
        "SELECT [Stream_ID] FROM [dbo].[Channel] "
        "WHERE [ProducedByStep_ID] = ? ORDER BY [Stream_ID]",
        step_id,
    )
    output_stream_ids = [r[0] for r in cursor.fetchall()]

    return {
        "processing_step_id": row[0],
        "name": row[1],
        "description": row[2],
        "method_name": row[3],
        "method_version": row[4],
        "operation_kind_id": row[5],
        "operation_kind_name": row[6],
        "method_parameters": row[7],
        "executed_at": row[8],
        "executed_by_person_id": row[9],
        "executed_by_name": executed_by_name,
        "input_stream_ids": input_stream_ids,
        "output_stream_ids": output_stream_ids,
    }


def get_channel_traits(
    equipment_id: int,
    parameter_id: int,
    from_dt: datetime,
    to_dt: datetime,
    conn,
) -> list[dict]:
    """Return all Channel variants of a sensor time series with their trait set.

    Finds all Channel rows matching the given equipment+parameter combination
    that have observations in the requested time window, and for each reports the
    set of OperationKind names accumulated on it (its ChannelTrait set). Replaces
    the retired ProcessingKind grouping (ADR 0005): a Channel no longer has a
    single processing kind, it has a many-to-many ChannelTrait set.

    Equipment is resolved through the active EquipmentWiringHistory row
    (Channel has no Equipment_ID — equipment is tracked on the physical
    Equipment via wiring/location history).

    Args:
        equipment_id: The equipment (sensor) ID.
        parameter_id: The measured parameter.
        from_dt: Start of the time window (inclusive).
        to_dt: End of the time window (inclusive).
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts, each with keys:
          - channel_id: int (Stream_ID)
          - operation_kind_names: list[str] (the ChannelTrait set, possibly empty)
          - value_count: int (number of observations in the time window)
    """
    sql = """
        SELECT
            c.[Stream_ID],
            COUNT(o.[Observation_ID])  AS [ValueCount]
        FROM [dbo].[Channel] c
        JOIN [dbo].[EquipmentWiringHistory] ewh
            ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
           AND ewh.[ValidTo] IS NULL
        JOIN [dbo].[Observation] o
            ON o.[Channel_ID] = c.[Stream_ID]
           AND o.[Timestamp] >= ?
           AND o.[Timestamp] <= ?
        WHERE ewh.[Equipment_ID] = ?
          AND c.[Parameter_ID] = ?
        GROUP BY c.[Stream_ID]
        ORDER BY c.[Stream_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, from_dt, to_dt, equipment_id, parameter_id)
    rows = cursor.fetchall()

    results: list[dict] = []
    for channel_id, value_count in rows:
        cursor.execute(
            """
            SELECT ok.[Name]
            FROM [dbo].[ChannelTrait] ct
            JOIN [dbo].[OperationKind] ok
                ON ok.[OperationKind_ID] = ct.[OperationKind_ID]
            WHERE ct.[Stream_ID] = ?
            ORDER BY ok.[OperationKind_ID]
            """,
            channel_id,
        )
        operation_kind_names = [r[0] for r in cursor.fetchall()]
        results.append(
            {
                "channel_id": channel_id,
                "operation_kind_names": operation_kind_names,
                "value_count": value_count,
            }
        )

    return results
