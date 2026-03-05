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
    where = "WHERE v.[Channel_ID] = ?"
    if from_dt:
        where += " AND v.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND v.[Timestamp] <= ?"
        params.append(to_dt)

    if operational_only:
        where += """
        AND (NOT EXISTS (
            SELECT 1 FROM dbo.Channel statusC
            JOIN dbo.Value sv ON sv.Channel_ID = statusC.Channel_ID
            WHERE statusC.StatusChannel_ID = v.Channel_ID
              AND sv.Timestamp <= v.Timestamp
        )
        OR EXISTS (
            SELECT 1 FROM dbo.Channel statusC
            JOIN dbo.Value sv ON sv.Channel_ID = statusC.Channel_ID
            JOIN dbo.QualityCode qc ON qc.QualityCode_ID = CAST(sv.Value AS INT)
            WHERE statusC.StatusChannel_ID = v.Channel_ID
              AND sv.Timestamp <= v.Timestamp
              AND qc.IsUsable = 1
        ))
        """

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT v.[Timestamp], v.[Value]
        FROM [dbo].[Value] v
        {where}
        ORDER BY v.[Timestamp]
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
    where = "WHERE vv.[Channel_ID] = ?"
    if from_dt:
        where += " AND vv.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND vv.[Timestamp] <= ?"
        params.append(to_dt)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT vv.[Timestamp], vb.[BinIndex], vb.[LowerBound], vb.[UpperBound],
               vv.[Value], vv.[QualityCode]
        FROM [dbo].[ValueVector] vv
        JOIN [dbo].[ValueBin] vb ON vb.[ValueBin_ID] = vv.[ValueBin_ID]
        {where}
        ORDER BY vv.[Timestamp], vb.[BinIndex]
        """,
        *params,
    )
    return [
        {
            "timestamp": row[0],
            "bin_index": row[1],
            "lower_bound": row[2],
            "upper_bound": row[3],
            "value": row[4],
            "quality_code": row[5],
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
    where = "WHERE vm.[Channel_ID] = ?"
    if from_dt:
        where += " AND vm.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND vm.[Timestamp] <= ?"
        params.append(to_dt)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT vm.[Timestamp], rb.[BinIndex] AS RowBinIndex, cb.[BinIndex] AS ColBinIndex,
               vm.[Value], vm.[QualityCode]
        FROM [dbo].[ValueMatrix] vm
        JOIN [dbo].[ValueBin] rb ON rb.[ValueBin_ID] = vm.[RowValueBin_ID]
        JOIN [dbo].[ValueBin] cb ON cb.[ValueBin_ID] = vm.[ColValueBin_ID]
        {where}
        ORDER BY vm.[Timestamp], rb.[BinIndex], cb.[BinIndex]
        """,
        *params,
    )
    return [
        {
            "timestamp": row[0],
            "row_bin_index": row[1],
            "col_bin_index": row[2],
            "value": row[3],
            "quality_code": row[4],
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
    where = "WHERE vi.[Channel_ID] = ?"
    if from_dt:
        where += " AND vi.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND vi.[Timestamp] <= ?"
        params.append(to_dt)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT vi.[Timestamp], vi.[ImageWidth], vi.[ImageHeight],
               vi.[NumberOfChannels], vi.[ImageFormat], vi.[FileSizeBytes],
               vi.[StorageBackend], vi.[StoragePath], vi.[QualityCode]
        FROM [dbo].[ValueImage] vi
        {where}
        ORDER BY vi.[Timestamp]
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
        cursor.execute(
            """
            INSERT INTO [dbo].[Value] ([Channel_ID], [Timestamp], [Value])
            VALUES (?, ?, ?)
            """,
            channel_id,
            v["timestamp"],
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

        for i, value in enumerate(bin_values):
            bin_id = bin_map.get(i)
            if bin_id is None:
                continue  # skip extra values silently
            cursor.execute(
                """
                INSERT INTO [dbo].[ValueVector]
                    (Channel_ID, Timestamp, ValueBin_ID, Value, QualityCode)
                VALUES (?, ?, ?, ?, ?)
                """,
                channel_id,
                timestamp,
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

        for r, row in enumerate(matrix):
            for c, value in enumerate(row):
                row_bin_id = row_map.get(r)
                col_bin_id = col_map.get(c)
                if row_bin_id is None or col_bin_id is None:
                    continue
                cursor.execute(
                    """
                    INSERT INTO [dbo].[ValueMatrix]
                        (Channel_ID, Timestamp, RowValueBin_ID, ColValueBin_ID, Value, QualityCode)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    channel_id,
                    timestamp,
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
    """Insert a row into dbo.ValueImage. Returns the new ValueImage_ID."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[ValueImage]
            ([Channel_ID], [Timestamp], [ImageWidth], [ImageHeight], [NumberOfChannels],
             [ImageFormat], [FileSizeBytes], [StorageBackend], [StoragePath],
             [Thumbnail], [QualityCode])
        VALUES (?, ?, ?, ?, ?, ?, ?, 'FileSystem', ?, ?, ?)
        """,
        channel_id,
        timestamp,
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
    # Get the last inserted identity
    cursor.execute("SELECT @@IDENTITY")
    row = cursor.fetchone()
    return int(row[0]) if row else 0
