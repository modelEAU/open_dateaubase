"""Lineage query functions for the open_dateaubase processing provenance graph.

All functions accept a pyodbc connection to an open_dateaubase MSSQL instance.
The DataLineage and ProcessingStep tables are available from schema v1.6.0 onward.
"""

from __future__ import annotations

from datetime import datetime


def get_lineage_forward(metadata_id: int, conn) -> list[dict]:
    """Return all processing steps that consumed this MetaData as an Input,
    along with the output MetaData IDs they produced.

    Args:
        metadata_id: The source MetaData row to trace forward.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts, each with keys:
          - processing_step: dict of ProcessingStep columns
          - output_metadata_ids: list[int] of Metadata_IDs produced by that step
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
            ps.[ExecutedAt],
            ps.[ExecutedByPerson_ID],
            out_dl.[Metadata_ID]  AS [OutputMetadata_ID]
        FROM [dbo].[DataLineage]   AS in_dl
        JOIN [dbo].[ProcessingStep] AS ps
            ON ps.[ProcessingStep_ID] = in_dl.[ProcessingStep_ID]
        JOIN [dbo].[DataLineage]   AS out_dl
            ON out_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
           AND out_dl.[Role] = 'Output'
        WHERE in_dl.[Metadata_ID] = ?
          AND in_dl.[Role] = 'Input'
        ORDER BY ps.[ProcessingStep_ID], out_dl.[Metadata_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, metadata_id)
    rows = cursor.fetchall()

    # Group output metadata IDs by processing step
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
                    "ExecutedAt": row[7],
                    "ExecutedByPerson_ID": row[8],
                },
                "output_metadata_ids": [],
            }
        steps[step_id]["output_metadata_ids"].append(row[9])

    return list(steps.values())


def get_lineage_backward(metadata_id: int, conn) -> list[dict]:
    """Return all processing steps that produced this MetaData as an Output,
    along with the input MetaData IDs they consumed.

    Args:
        metadata_id: The target MetaData row to trace backward.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts, each with keys:
          - processing_step: dict of ProcessingStep columns
          - input_metadata_ids: list[int] of Metadata_IDs consumed by that step
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
            ps.[ExecutedAt],
            ps.[ExecutedByPerson_ID],
            in_dl.[Metadata_ID]  AS [InputMetadata_ID]
        FROM [dbo].[DataLineage]   AS out_dl
        JOIN [dbo].[ProcessingStep] AS ps
            ON ps.[ProcessingStep_ID] = out_dl.[ProcessingStep_ID]
        JOIN [dbo].[DataLineage]   AS in_dl
            ON in_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
           AND in_dl.[Role] = 'Input'
        WHERE out_dl.[Metadata_ID] = ?
          AND out_dl.[Role] = 'Output'
        ORDER BY ps.[ProcessingStep_ID], in_dl.[Metadata_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, metadata_id)
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
                    "ExecutedAt": row[7],
                    "ExecutedByPerson_ID": row[8],
                },
                "input_metadata_ids": [],
            }
        steps[step_id]["input_metadata_ids"].append(row[9])

    return list(steps.values())


def get_full_lineage_tree(metadata_id: int, conn) -> dict:
    """Return the complete processing chain from raw ancestors to final descendants.

    Uses a recursive CTE to traverse the DataLineage DAG in both directions,
    then assembles a tree rooted at the given metadata_id.

    Args:
        metadata_id: The MetaData row at the root of the tree.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        A tree dict:
          {
            'metadata_id': int,
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
                in_dl.[Metadata_ID]       AS [AncestorMetadata_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[ProcessingType],
                out_dl.[Metadata_ID]      AS [ChildMetadata_ID],
                1                          AS [Depth]
            FROM [dbo].[DataLineage]    AS out_dl
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = out_dl.[ProcessingStep_ID]
            JOIN [dbo].[DataLineage]    AS in_dl
                ON in_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
               AND in_dl.[Role] = 'Input'
            WHERE out_dl.[Metadata_ID] = ?
              AND out_dl.[Role] = 'Output'

            UNION ALL

            -- Recursive: walk further up the graph
            SELECT
                in_dl.[Metadata_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[ProcessingType],
                a.[AncestorMetadata_ID],
                a.[Depth] + 1
            FROM Ancestors a
            JOIN [dbo].[DataLineage]    AS out_dl
                ON out_dl.[Metadata_ID] = a.[AncestorMetadata_ID]
               AND out_dl.[Role] = 'Output'
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = out_dl.[ProcessingStep_ID]
            JOIN [dbo].[DataLineage]    AS in_dl
                ON in_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
               AND in_dl.[Role] = 'Input'
        )
        SELECT DISTINCT [AncestorMetadata_ID], [ProcessingStep_ID], [Name],
                        [ProcessingType], [ChildMetadata_ID], [Depth]
        FROM Ancestors
        ORDER BY [Depth], [AncestorMetadata_ID]
    """

    # Collect all descendants (forward)
    descendant_sql = """
        WITH Descendants AS (
            SELECT
                out_dl.[Metadata_ID]      AS [DescendantMetadata_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[ProcessingType],
                in_dl.[Metadata_ID]       AS [ParentMetadata_ID],
                1                          AS [Depth]
            FROM [dbo].[DataLineage]    AS in_dl
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = in_dl.[ProcessingStep_ID]
            JOIN [dbo].[DataLineage]    AS out_dl
                ON out_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
               AND out_dl.[Role] = 'Output'
            WHERE in_dl.[Metadata_ID] = ?
              AND in_dl.[Role] = 'Input'

            UNION ALL

            SELECT
                out_dl.[Metadata_ID],
                ps.[ProcessingStep_ID],
                ps.[Name],
                ps.[ProcessingType],
                d.[DescendantMetadata_ID],
                d.[Depth] + 1
            FROM Descendants d
            JOIN [dbo].[DataLineage]    AS in_dl
                ON in_dl.[Metadata_ID] = d.[DescendantMetadata_ID]
               AND in_dl.[Role] = 'Input'
            JOIN [dbo].[ProcessingStep] AS ps
                ON ps.[ProcessingStep_ID] = in_dl.[ProcessingStep_ID]
            JOIN [dbo].[DataLineage]    AS out_dl
                ON out_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
               AND out_dl.[Role] = 'Output'
        )
        SELECT DISTINCT [DescendantMetadata_ID], [ProcessingStep_ID], [Name],
                        [ProcessingType], [ParentMetadata_ID], [Depth]
        FROM Descendants
        ORDER BY [Depth], [DescendantMetadata_ID]
    """

    cursor = conn.cursor()

    cursor.execute(ancestor_sql, metadata_id)
    ancestor_rows = cursor.fetchall()

    cursor.execute(descendant_sql, metadata_id)
    descendant_rows = cursor.fetchall()

    # Build simple node structure
    parents = [
        {
            "metadata_id": row[0],
            "processing_step_id": row[1],
            "processing_step_name": row[2],
            "processing_type": row[3],
            "child_metadata_id": row[4],
            "depth": row[5],
        }
        for row in ancestor_rows
    ]

    children = [
        {
            "metadata_id": row[0],
            "processing_step_id": row[1],
            "processing_step_name": row[2],
            "processing_type": row[3],
            "parent_metadata_id": row[4],
            "depth": row[5],
        }
        for row in descendant_rows
    ]

    return {
        "metadata_id": metadata_id,
        "parents": parents,
        "children": children,
    }


def get_all_processing_degrees(
    sampling_point_id: int,
    parameter_id: int,
    from_dt: datetime,
    to_dt: datetime,
    conn,
) -> list[dict]:
    """Return all versions (Raw, Cleaned, Validated, …) of a time series.

    Finds all MetaData rows matching the given location+parameter combination
    that have values in the requested time window, grouped by ProcessingDegree.

    Args:
        sampling_point_id: The sampling location.
        parameter_id: The measured parameter.
        from_dt: Start of the time window (inclusive).
        to_dt: End of the time window (inclusive).
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        List of dicts, each with keys:
          - metadata_id: int
          - processing_degree: str | None
          - value_count: int (number of Value rows in the time window)
    """
    sql = """
        SELECT
            m.[Metadata_ID],
            m.[ProcessingDegree],
            COUNT(v.[Timestamp])  AS [ValueCount]
        FROM [dbo].[MetaData] m
        JOIN [dbo].[Value]    v
            ON v.[Metadata_ID] = m.[Metadata_ID]
           AND v.[Timestamp] >= ?
           AND v.[Timestamp] <= ?
        WHERE m.[Sampling_point_ID] = ?
          AND m.[Parameter_ID]      = ?
        GROUP BY m.[Metadata_ID], m.[ProcessingDegree]
        ORDER BY m.[ProcessingDegree], m.[Metadata_ID]
    """
    cursor = conn.cursor()
    cursor.execute(sql, from_dt, to_dt, sampling_point_id, parameter_id)
    rows = cursor.fetchall()

    return [
        {
            "metadata_id": row[0],
            "processing_degree": row[1],
            "value_count": row[2],
        }
        for row in rows
    ]
