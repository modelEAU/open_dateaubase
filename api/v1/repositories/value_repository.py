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
    metadata_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
    operational_only: bool = False,
) -> list[dict]:
    params: list = [metadata_id]
    where = "WHERE v.[Metadata_ID] = ?"
    if from_dt:
        where += " AND v.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND v.[Timestamp] <= ?"
        params.append(to_dt)

    if operational_only:
        where += """
        AND (EXISTS (
            SELECT 1 FROM dbo.MetaData statusMD
            JOIN dbo.Value sv ON sv.Metadata_ID = statusMD.Metadata_ID
            WHERE statusMD.StatusOfMetaDataID = v.Metadata_ID
              AND sv.Timestamp <= v.Timestamp
        ) = 0
        OR EXISTS (
            SELECT 1 FROM dbo.MetaData statusMD
            JOIN dbo.Value sv ON sv.Metadata_ID = statusMD.Metadata_ID
            JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(sv.Value AS INT)
            WHERE statusMD.StatusOfMetaDataID = v.Metadata_ID
              AND sv.Timestamp <= v.Timestamp
              AND sc.IsOperational = 1
        ))
        """

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT v.[Timestamp], v.[Value], v.[QualityCode]
        FROM [dbo].[Value] v
        {where}
        ORDER BY v.[Timestamp]
        """,
        *params,
    )
    return [
        {"timestamp": row[0], "value": row[1], "quality_code": row[2]}
        for row in cursor.fetchall()
    ]


def get_vector_values(
    conn: pyodbc.Connection,
    metadata_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    params: list = [metadata_id]
    where = "WHERE vv.[Metadata_ID] = ?"
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
    metadata_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    params: list = [metadata_id]
    where = "WHERE vm.[Metadata_ID] = ?"
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
    metadata_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    params: list = [metadata_id]
    where = "WHERE vi.[Metadata_ID] = ?"
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
    metadata_id: int,
    value_type_id: int | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
    operational_only: bool = False,
) -> list[dict]:
    """Dispatch to the correct value table based on value_type_id."""
    vt = value_type_id or _VALUE_TYPE_SCALAR
    if vt == _VALUE_TYPE_VECTOR:
        return get_vector_values(conn, metadata_id, from_dt, to_dt)
    elif vt == _VALUE_TYPE_MATRIX:
        return get_matrix_values(conn, metadata_id, from_dt, to_dt)
    elif vt == _VALUE_TYPE_IMAGE:
        return get_image_values(conn, metadata_id, from_dt, to_dt)
    else:
        return get_scalar_values(conn, metadata_id, from_dt, to_dt, operational_only)


def insert_scalar_values(
    conn: pyodbc.Connection,
    metadata_id: int,
    values: list[dict],
) -> int:
    """Insert rows into dbo.Value. Returns rows written."""
    cursor = conn.cursor()
    for v in values:
        cursor.execute(
            """
            INSERT INTO [dbo].[Value] ([Metadata_ID], [Timestamp], [Value], [QualityCode])
            VALUES (?, ?, ?, ?)
            """,
            metadata_id,
            v["timestamp"],
            v["value"],
            v.get("quality_code"),
        )
    conn.commit()
    return len(values)
