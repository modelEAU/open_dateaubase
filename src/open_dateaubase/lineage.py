"""Lineage query functions for the open_dateaubase processing provenance graph.

All functions accept a pyodbc connection to an open_dateaubase MSSQL instance.
The ProcessingLineage and ProcessingStep tables are available from schema v2.1.0 onward.
"""

from __future__ import annotations

from datetime import datetime


def get_lineage_forward(channel_id: int, conn) -> list[dict]:
    """Return all processing steps that consumed this Channel as an Input,
    along with the output Channel IDs they produced.

    Args:
        channel_id: The source Channel row to trace forward.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts, each with keys:
          - processing_step: dict of ProcessingStep columns
          - output_channel_ids: list[int] of Channel_IDs produced by that step
    """
    sql = """
        SELECT
            ps.[ProcessingStep_ID],
            ps.[Name],
            ps.[Description],
            ps.[MethodName],
            ps.[MethodVersion],
            ps.[ProcessingType],
            ps.[Parameters],
            ps.[ExecutedDateTime],
            ps.[ExecutedByPerson_ID],
            out_dl.[Channel_ID]  AS [OutputChannel_ID]
        FROM [dbo].[ProcessingLineage]   AS in_dl
        JOIN [dbo].[ProcessingStep] AS ps
            ON ps.[ProcessingStep_ID] = in_dl.[ProcessingStep_ID]
        JOIN [dbo].[ProcessingLineage]   AS out_dl
            ON out_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
           AND out_dl.[RoleInProcessingStep] = 'Output'
        WHERE in_dl.[Channel_ID] = ?
          AND in_dl.[RoleInProcessingStep] = 'Input'
        ORDER BY ps.[ProcessingStep_ID], out_dl.[Channel_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, channel_id)
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
                    "ProcessingType": row[5],
                    "Parameters": row[6],
                    "ExecutedDateTime": row[7],
                    "ExecutedByPerson_ID": row[8],
                },
                "output_channel_ids": [],
            }
        steps[step_id]["output_channel_ids"].append(row[9])

    return list(steps.values())


def get_lineage_backward(channel_id: int, conn) -> list[dict]:
    """Return all processing steps that produced this Channel as an Output,
    along with the input Channel IDs they consumed.

    Args:
        channel_id: The target Channel row to trace backward.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts, each with keys:
          - processing_step: dict of ProcessingStep columns
          - input_channel_ids: list[int] of Channel_IDs consumed by that step
    """
    sql = """
        SELECT
            ps.[ProcessingStep_ID],
            ps.[Name],
            ps.[Description],
            ps.[MethodName],
            ps.[MethodVersion],
            ps.[ProcessingType],
            ps.[Parameters],
            ps.[ExecutedDateTime],
            ps.[ExecutedByPerson_ID],
            in_dl.[Channel_ID]  AS [InputChannel_ID]
        FROM [dbo].[ProcessingLineage]   AS out_dl
        JOIN [dbo].[ProcessingStep] AS ps
            ON ps.[ProcessingStep_ID] = out_dl.[ProcessingStep_ID]
        JOIN [dbo].[ProcessingLineage]   AS in_dl
            ON in_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
           AND in_dl.[RoleInProcessingStep] = 'Input'
        WHERE out_dl.[Channel_ID] = ?
          AND out_dl.[RoleInProcessingStep] = 'Output'
        ORDER BY ps.[ProcessingStep_ID], in_dl.[Channel_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, channel_id)
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
                    "ProcessingType": row[5],
                    "Parameters": row[6],
                    "ExecutedDateTime": row[7],
                    "ExecutedByPerson_ID": row[8],
                },
                "input_channel_ids": [],
            }
        steps[step_id]["input_channel_ids"].append(row[9])

    return list(steps.values())


def get_full_lineage_tree(channel_id: int, conn) -> dict:
    """Return the complete processing chain from raw ancestors to final descendants.

    Uses a recursive CTE to traverse the DataLineage DAG in both directions,
    then assembles a tree rooted at the given channel_id.

    Args:
        channel_id: The Channel row at the root of the tree.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        A tree dict:
          {
            'channel_id': int,
            'processing_step': dict | None,  # step that produced this node (None for raw roots)
            'parents': list[dict],           # backward lineage (inputs)
            'children': list[dict],          # forward lineage (outputs)
          }
    """
    # Collect all ancestors (backward) using a recursive CTE
    ancestor_sql = """
        WITH Ancestors AS (
            -- Anchor: direct parents of the seed node
            SELECT
                in_dl.[Channel_ID]        AS [AncestorChannel_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[ProcessingType],
                out_dl.[Channel_ID]       AS [ChildChannel_ID],
                1                          AS [Depth]
            FROM [dbo].[ProcessingLineage]    AS out_dl
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = out_dl.[ProcessingStep_ID]
            JOIN [dbo].[ProcessingLineage]    AS in_dl
                ON in_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
               AND in_dl.[RoleInProcessingStep] = 'Input'
            WHERE out_dl.[Channel_ID] = ?
              AND out_dl.[RoleInProcessingStep] = 'Output'

            UNION ALL

            -- Recursive: walk further up the graph
            SELECT
                in_dl.[Channel_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[ProcessingType],
                a.[AncestorChannel_ID],
                a.[Depth] + 1
            FROM Ancestors a
            JOIN [dbo].[ProcessingLineage]    AS out_dl
                ON out_dl.[Channel_ID] = a.[AncestorChannel_ID]
               AND out_dl.[RoleInProcessingStep] = 'Output'
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = out_dl.[ProcessingStep_ID]
            JOIN [dbo].[ProcessingLineage]    AS in_dl
                ON in_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
               AND in_dl.[RoleInProcessingStep] = 'Input'
        )
        SELECT DISTINCT [AncestorChannel_ID], [ProcessingStep_ID], [Name],
                        [ProcessingType], [ChildChannel_ID], [Depth]
        FROM Ancestors
        ORDER BY [Depth], [AncestorChannel_ID]
    """

    # Collect all descendants (forward)
    descendant_sql = """
        WITH Descendants AS (
            SELECT
                out_dl.[Channel_ID]       AS [DescendantChannel_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[ProcessingType],
                in_dl.[Channel_ID]        AS [ParentChannel_ID],
                1                          AS [Depth]
            FROM [dbo].[ProcessingLineage]    AS in_dl
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = in_dl.[ProcessingStep_ID]
            JOIN [dbo].[ProcessingLineage]    AS out_dl
                ON out_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
               AND out_dl.[RoleInProcessingStep] = 'Output'
            WHERE in_dl.[Channel_ID] = ?
              AND in_dl.[RoleInProcessingStep] = 'Input'

            UNION ALL

            SELECT
                out_dl.[Channel_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[ProcessingType],
                d.[DescendantChannel_ID],
                d.[Depth] + 1
            FROM Descendants d
            JOIN [dbo].[ProcessingLineage]    AS in_dl
                ON in_dl.[Channel_ID] = d.[DescendantChannel_ID]
               AND in_dl.[RoleInProcessingStep] = 'Input'
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = in_dl.[ProcessingStep_ID]
            JOIN [dbo].[ProcessingLineage]    AS out_dl
                ON out_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
               AND out_dl.[RoleInProcessingStep] = 'Output'
        )
        SELECT DISTINCT [DescendantChannel_ID], [ProcessingStep_ID], [Name],
                        [ProcessingType], [ParentChannel_ID], [Depth]
        FROM Descendants
        ORDER BY [Depth], [DescendantChannel_ID]
    """

    cursor = conn.cursor()

    cursor.execute(ancestor_sql, channel_id)
    ancestor_rows = cursor.fetchall()

    cursor.execute(descendant_sql, channel_id)
    descendant_rows = cursor.fetchall()

    # Build simple node structure
    parents = [
        {
            "channel_id": row[0],
            "processing_step_id": row[1],
            "processing_step_name": row[2],
            "processing_type": row[3],
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
            "processing_type": row[3],
            "parent_channel_id": row[4],
            "depth": row[5],
        }
        for row in descendant_rows
    ]

    return {
        "channel_id": channel_id,
        "parents": parents,
        "children": children,
    }


def get_all_processing_kinds(
    equipment_id: int,
    parameter_id: int,
    from_dt: datetime,
    to_dt: datetime,
    conn,
) -> list[dict]:
    """Return all versions (Raw, Cleaned, Validated, …) of a time series.

    Finds all Channel rows matching the given equipment+parameter combination
    that have values in the requested time window, grouped by ProcessingKind.

    Args:
        equipment_id: The equipment (sensor) ID.
        parameter_id: The measured parameter.
        from_dt: Start of the time window (inclusive).
        to_dt: End of the time window (inclusive).
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts, each with keys:
          - channel_id: int
          - processing_kind_name: str | None
          - value_count: int (number of Value rows in the time window)
    """
    sql = """
        SELECT
            c.[Channel_ID],
            pd.[Name]             AS [ProcessingKindName],
            COUNT(v.[Timestamp])  AS [ValueCount]
        FROM [dbo].[Channel] c
        LEFT JOIN [dbo].[ProcessingKind] pd
            ON pd.[ProcessingKind_ID] = c.[ProcessingKind_ID]
        JOIN [dbo].[Value]   v
            ON v.[Channel_ID] = c.[Channel_ID]
           AND v.[Timestamp] >= ?
           AND v.[Timestamp] <= ?
        WHERE c.[Equipment_ID] = ?
          AND c.[Parameter_ID] = ?
        GROUP BY c.[Channel_ID], pd.[Name]
        ORDER BY pd.[Name], c.[Channel_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, from_dt, to_dt, equipment_id, parameter_id)
    rows = cursor.fetchall()

    return [
        {
            "channel_id": row[0],
            "processing_kind_name": row[1],
            "value_count": row[2],
        }
        for row in rows
    ]
