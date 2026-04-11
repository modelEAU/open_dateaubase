"""Data access for value tables — dispatches by ValueType_ID.

ValueType_ID mapping (from schema seed data):
  1 = Scalar   → dbo.Value
  2 = Vector   → dbo.ValueVector
  3 = Matrix   → dbo.ValueMatrix
  4 = Image    → dbo.ValueImage
"""

from __future__ import annotations

from datetime import datetime

import pyodbc

_VALUE_TYPE_SCALAR = 1
_VALUE_TYPE_VECTOR = 2
_VALUE_TYPE_MATRIX = 3
_VALUE_TYPE_IMAGE = 4


def get_scalar_values(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
    operational_only: bool = False,
) -> list[dict]:
    params: list = [channel_id]
    where = "WHERE o.[Channel_ID] = ?"
    if from_dt:
        where += " AND o.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND o.[Timestamp] <= ?"
        params.append(to_dt)

    if operational_only:
        # Navigate to the status channel via SignalPort sub-signal (v3.0.0 pattern).
        # A status channel is one whose SignalPort has SignalPortType=Status and
        # ParentPort_ID pointing to the measurement channel's SignalPort.
        where += """
        AND (NOT EXISTS (
            SELECT 1
            FROM   dbo.Channel       statusC
            JOIN   dbo.SignalPort    sp  ON sp.[SignalPort_ID]      = statusC.[SignalPort_ID]
            JOIN   dbo.SignalPortType spt ON spt.[SignalPortType_ID] = sp.[SignalPortType_ID]
            JOIN   dbo.Observation   so  ON so.[Channel_ID]         = statusC.[Channel_ID]
            JOIN   dbo.Value         sv  ON sv.[Observation_ID]     = so.[Observation_ID]
            WHERE  sp.[ParentPort_ID] = (
                       SELECT c2.[SignalPort_ID] FROM dbo.Channel c2 WHERE c2.[Channel_ID] = o.[Channel_ID]
                   )
              AND  spt.[Name] = N'Status'
              AND  so.[Timestamp] <= o.[Timestamp]
        )
        OR EXISTS (
            SELECT 1
            FROM   dbo.Channel       statusC
            JOIN   dbo.SignalPort    sp  ON sp.[SignalPort_ID]      = statusC.[SignalPort_ID]
            JOIN   dbo.SignalPortType spt ON spt.[SignalPortType_ID] = sp.[SignalPortType_ID]
            JOIN   dbo.Observation   so  ON so.[Channel_ID]         = statusC.[Channel_ID]
            JOIN   dbo.Value         sv  ON sv.[Observation_ID]     = so.[Observation_ID]
            JOIN   dbo.QualityCode   qc  ON qc.[QualityCode_ID]     = CAST(sv.[Value] AS INT)
            WHERE  sp.[ParentPort_ID] = (
                       SELECT c2.[SignalPort_ID] FROM dbo.Channel c2 WHERE c2.[Channel_ID] = o.[Channel_ID]
                   )
              AND  spt.[Name] = N'Status'
              AND  so.[Timestamp] <= o.[Timestamp]
              AND  qc.[IsUsable] = 1
        ))
        """

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT o.[Timestamp], v.[Value]
        FROM [dbo].[Value] v
        JOIN [dbo].[Observation] o ON o.[Observation_ID] = v.[Observation_ID]
        {where}
        ORDER BY o.[Timestamp]
        """,
        *params,
    )
    return [
        {"timestamp": row[0], "value": row[1], "quality_code": None}
        for row in cursor.fetchall()
    ]


def get_vector_values(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    params: list = [channel_id]
    where = "WHERE o.[Channel_ID] = ?"
    if from_dt:
        where += " AND o.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND o.[Timestamp] <= ?"
        params.append(to_dt)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT o.[Timestamp], vb.[BinIndex], vb.[LowerBound], vb.[UpperBound],
               vb.[NominalValue], vv.[Value], vv.[QualityCode]
        FROM [dbo].[ValueVector] vv
        JOIN [dbo].[Observation] o  ON o.[Observation_ID]  = vv.[Observation_ID]
        JOIN [dbo].[ValueBin]    vb ON vb.[ValueBin_ID]    = vv.[ValueBin_ID]
        {where}
        ORDER BY o.[Timestamp], vb.[BinIndex]
        """,
        *params,
    )
    return [
        {
            "timestamp": row[0],
            "bin_index": row[1],
            "lower_bound": row[2],
            "upper_bound": row[3],
            "nominal_value": row[4],
            "value": row[5],
            "quality_code": row[6],
        }
        for row in cursor.fetchall()
    ]


def get_matrix_values(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    params: list = [channel_id]
    where = "WHERE o.[Channel_ID] = ?"
    if from_dt:
        where += " AND o.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND o.[Timestamp] <= ?"
        params.append(to_dt)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT o.[Timestamp],
               rb.[BinIndex] AS RowBinIndex, rb.[LowerBound] AS RowLowerBound,
               rb.[UpperBound] AS RowUpperBound, rb.[NominalValue] AS RowNominalValue,
               cb.[BinIndex] AS ColBinIndex, cb.[LowerBound] AS ColLowerBound,
               cb.[UpperBound] AS ColUpperBound, cb.[NominalValue] AS ColNominalValue,
               vm.[Value], vm.[QualityCode]
        FROM [dbo].[ValueMatrix] vm
        JOIN [dbo].[Observation] o  ON o.[Observation_ID]   = vm.[Observation_ID]
        JOIN [dbo].[ValueBin]    rb ON rb.[ValueBin_ID]     = vm.[RowValueBin_ID]
        JOIN [dbo].[ValueBin]    cb ON cb.[ValueBin_ID]     = vm.[ColValueBin_ID]
        {where}
        ORDER BY o.[Timestamp], rb.[BinIndex], cb.[BinIndex]
        """,
        *params,
    )
    return [
        {
            "timestamp": row[0],
            "row_bin_index": row[1],
            "row_lower_bound": row[2],
            "row_upper_bound": row[3],
            "row_nominal_value": row[4],
            "col_bin_index": row[5],
            "col_lower_bound": row[6],
            "col_upper_bound": row[7],
            "col_nominal_value": row[8],
            "value": row[9],
            "quality_code": row[10],
        }
        for row in cursor.fetchall()
    ]


def get_image_values(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    params: list = [channel_id]
    where = "WHERE o.[Channel_ID] = ?"
    if from_dt:
        where += " AND o.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND o.[Timestamp] <= ?"
        params.append(to_dt)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT o.[Timestamp], vi.[ImageWidth], vi.[ImageHeight],
               vi.[NumberOfChannels], vi.[ImageFormat], vi.[FileSizeBytes],
               vi.[StorageBackend], vi.[StoragePath], vi.[QualityCode]
        FROM [dbo].[ValueImage] vi
        JOIN [dbo].[Observation] o ON o.[Observation_ID] = vi.[Observation_ID]
        {where}
        ORDER BY o.[Timestamp]
        """,
        *params,
    )
    return [
        {
            "timestamp": row[0],
            "image_width": row[1],
            "image_height": row[2],
            "number_of_channels": row[3],
            "image_format": row[4],
            "file_size_bytes": row[5],
            "storage_backend": row[6],
            "storage_path": row[7],
            "quality_code": row[8],
        }
        for row in cursor.fetchall()
    ]


def get_image_thumbnail(
    conn,
    channel_id: int,
    timestamp: datetime,
) -> bytes | None:
    """Return the thumbnail bytes for a specific image, or None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT vi.[Thumbnail]
        FROM [dbo].[ValueImage] vi
        JOIN [dbo].[Observation] o ON o.[Observation_ID] = vi.[Observation_ID]
        WHERE o.[Channel_ID] = ? AND o.[Timestamp] = ?
        """,
        channel_id,
        timestamp,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return bytes(row[0]) if row[0] is not None else None


def get_image_metadata_by_timestamp(
    conn,
    channel_id: int,
    timestamp: datetime,
) -> dict | None:
    """Return storage_path and format for a specific image."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT vi.[StoragePath], vi.[ImageFormat]
        FROM [dbo].[ValueImage] vi
        JOIN [dbo].[Observation] o ON o.[Observation_ID] = vi.[Observation_ID]
        WHERE o.[Channel_ID] = ? AND o.[Timestamp] = ?
        """,
        channel_id,
        timestamp,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {"storage_path": row[0], "image_format": row[1]}


def get_values_for_metadata(
    conn: pyodbc.Connection,
    channel_id: int,
    value_type_id: int | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
    operational_only: bool = False,
) -> list[dict]:
    """Dispatch to the correct value table based on value_type_id."""
    vt = value_type_id or _VALUE_TYPE_SCALAR
    if vt == _VALUE_TYPE_VECTOR:
        return get_vector_values(conn, channel_id, from_dt, to_dt)
    elif vt == _VALUE_TYPE_MATRIX:
        return get_matrix_values(conn, channel_id, from_dt, to_dt)
    elif vt == _VALUE_TYPE_IMAGE:
        return get_image_values(conn, channel_id, from_dt, to_dt)
    else:
        return get_scalar_values(conn, channel_id, from_dt, to_dt, operational_only)


def insert_scalar_values(
    conn: pyodbc.Connection,
    channel_id: int,
    values: list[dict],
) -> int:
    """Insert rows into dbo.Value. Returns rows written."""
    cursor = conn.cursor()
    for v in values:
        # Step 1: create Observation, get ID
        cursor.execute(
            """
            INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
            OUTPUT INSERTED.[Observation_ID]
            VALUES (?, ?, 'Scalar')
            """,
            channel_id,
            v["timestamp"],
        )
        obs_id: int = cursor.fetchone()[0]
        # Step 2: insert scalar payload
        cursor.execute(
            "INSERT INTO [dbo].[Value] ([Observation_ID], [Value]) VALUES (?, ?)",
            obs_id,
            v["value"],
        )
    conn.commit()
    return len(values)


def insert_vector_values(
    conn: pyodbc.Connection,
    channel_id: int,
    binning_axis_id: int,
    observations: list[dict],
) -> int:
    """Insert rows into dbo.ValueVector. Each observation has:
      timestamp: datetime, bin_values: list[float | None], quality_code: int | None
    bin_values[i] maps to ValueBin with BinIndex=i for the given axis.
    """
    cursor = conn.cursor()
    # Fetch all ValueBin_IDs for this axis in order
    cursor.execute(
        """
        SELECT ValueBin_ID, BinIndex FROM [dbo].[ValueBin]
        WHERE ValueBinningAxis_ID = ? ORDER BY BinIndex
        """,
        binning_axis_id,
    )
    bin_map = {row[1]: row[0] for row in cursor.fetchall()}  # BinIndex → ValueBin_ID

    if len(bin_map) == 0:
        raise ValueError(f"No bins found for axis {binning_axis_id}")

    total_rows = 0
    for obs in observations:
        timestamp = obs["timestamp"]
        quality_code = obs.get("quality_code")
        bin_values = obs["bin_values"]

        # Create Observation for this timestamp
        cursor.execute(
            """
            INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
            OUTPUT INSERTED.[Observation_ID]
            VALUES (?, ?, 'Vector')
            """,
            channel_id,
            timestamp,
        )
        obs_id: int = cursor.fetchone()[0]

        # Insert one row per bin (inner loop)
        for i, value in enumerate(bin_values):
            bin_id = bin_map.get(i)
            if bin_id is None:
                continue  # skip extra values silently
            cursor.execute(
                """
                INSERT INTO [dbo].[ValueVector]
                    ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
                VALUES (?, ?, ?, ?)
                """,
                obs_id,
                bin_id,
                value,
                quality_code,
            )
            total_rows += 1

    conn.commit()
    return total_rows


def insert_matrix_values(
    conn: pyodbc.Connection,
    channel_id: int,
    row_axis_id: int,
    col_axis_id: int,
    observations: list[dict],
) -> int:
    """Insert rows into dbo.ValueMatrix. Each observation has:
      timestamp: datetime, matrix: list[list[float | None]], quality_code: int | None
    matrix[r][c] maps to (row_bin at row index r, col_bin at col index c).
    """
    cursor = conn.cursor()

    # Fetch row bins
    cursor.execute(
        """
        SELECT ValueBin_ID, BinIndex FROM [dbo].[ValueBin]
        WHERE ValueBinningAxis_ID = ? ORDER BY BinIndex
        """,
        row_axis_id,
    )
    row_map = {row[1]: row[0] for row in cursor.fetchall()}

    # Fetch col bins
    cursor.execute(
        """
        SELECT ValueBin_ID, BinIndex FROM [dbo].[ValueBin]
        WHERE ValueBinningAxis_ID = ? ORDER BY BinIndex
        """,
        col_axis_id,
    )
    col_map = {row[1]: row[0] for row in cursor.fetchall()}

    total_rows = 0
    for obs in observations:
        timestamp = obs["timestamp"]
        quality_code = obs.get("quality_code")
        matrix = obs["matrix"]

        # Create Observation for this timestamp
        cursor.execute(
            """
            INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
            OUTPUT INSERTED.[Observation_ID]
            VALUES (?, ?, 'Matrix')
            """,
            channel_id,
            obs["timestamp"],
        )
        obs_id: int = cursor.fetchone()[0]

        for r, row in enumerate(matrix):
            for c, value in enumerate(row):
                row_bin_id = row_map.get(r)
                col_bin_id = col_map.get(c)
                if row_bin_id is None or col_bin_id is None:
                    continue
                cursor.execute(
                    """
                    INSERT INTO [dbo].[ValueMatrix]
                        ([Observation_ID], [RowValueBin_ID], [ColValueBin_ID], [Value], [QualityCode])
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    obs_id,
                    row_bin_id,
                    col_bin_id,
                    value,
                    quality_code,
                )
                total_rows += 1

    conn.commit()
    return total_rows


def insert_image_value(
    conn: pyodbc.Connection,
    *,
    channel_id: int,
    timestamp: datetime,
    image_width: int,
    image_height: int,
    number_of_channels: int,
    image_format: str,
    file_size_bytes: int,
    storage_path: str,
    quality_code: int | None,
    thumbnail: bytes | None = None,
) -> int:
    """Insert a row into dbo.ValueImage. Returns the new Observation_ID."""
    cursor = conn.cursor()
    # Step 1: create Observation, get ID
    cursor.execute(
        """
        INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
        OUTPUT INSERTED.[Observation_ID]
        VALUES (?, ?, 'Image')
        """,
        channel_id,
        timestamp,
    )
    obs_id: int = cursor.fetchone()[0]
    # Step 2: insert image payload
    cursor.execute(
        """
        INSERT INTO [dbo].[ValueImage]
            ([Observation_ID], [ImageWidth], [ImageHeight], [NumberOfChannels],
             [ImageFormat], [FileSizeBytes], [StorageBackend], [StoragePath],
             [Thumbnail], [QualityCode])
        VALUES (?, ?, ?, ?, ?, ?, 'FileSystem', ?, ?, ?)
        """,
        obs_id,
        image_width,
        image_height,
        number_of_channels,
        image_format,
        file_size_bytes,
        storage_path,
        thumbnail,
        quality_code,
    )
    conn.commit()
    return obs_id
