"""Data access for value tables — dispatches by ValueKind_ID.

ValueKind_ID mapping (from schema seed data):
  1 = Scalar   → dbo.Value
  2 = Vector   → dbo.ValueVector
  3 = Matrix   → dbo.ValueMatrix
  4 = Image    → dbo.ValueImage
"""

from __future__ import annotations

from datetime import datetime, timezone

import pyodbc

_VALUE_TYPE_SCALAR = 1
_VALUE_TYPE_VECTOR = 2
_VALUE_TYPE_MATRIX = 3
_VALUE_TYPE_IMAGE = 4


def _utc_naive(dt: datetime) -> datetime:
    """Convert any datetime to a naive UTC datetime for MSSQL DATETIME2 columns.

    MSSQL DATETIME2 has no timezone concept. Passing a tz-aware Python datetime
    to pyodbc with MSSQL ODBC 18 can produce incorrect stored values. We always
    convert to UTC then strip tzinfo so the stored value is unambiguously UTC.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# ---------------------------------------------------------------------------
# Observation source specs
#
# Sensor and lab reads are identical except for how the Observation is filtered
# to its source: sensors key on Observation.Channel_ID; lab observations carry
# Channel_ID = NULL and reach their AnalysisSeries via LabAnalysis. Since lab
# ingest now stores the sample collection time directly in Observation.Timestamp
# (ADR 0002), there is no extra Sample join and the timestamp/payload/return
# shape are shared. Each spec is (source_join, source_where, params).
# ---------------------------------------------------------------------------


def get_channel_trait_names(conn: pyodbc.Connection, channel_id: int) -> list[str]:
    """Return a channel's accumulated ChannelTrait set as OperationKind names.

    ADR 0005 retired the single ProcessingKind string in favour of the
    ChannelTrait set (the union of operations applied across a channel's
    lineage). Keyed on Stream_ID — a Channel's PK is now Stream_ID — so the
    channel_id passed here is the channel's Stream_ID value. Returns [] for a
    channel with no traits (e.g. a lab AnalysisSeries, which carries none).
    Mirrors meteaudata_bridge.load_signal_context's trait_names query.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ok.[Name]
        FROM [dbo].[ChannelTrait] ct
        JOIN [dbo].[OperationKind] ok ON ok.[OperationKind_ID] = ct.[OperationKind_ID]
        WHERE ct.[Stream_ID] = ?
        """,
        channel_id,
    )
    return [row[0] for row in cursor.fetchall()]


def _channel_source(channel_id: int) -> tuple[str, str, list]:
    return "", "o.[Channel_ID] = ?", [channel_id]


def _analysis_series_source(analysis_series_id: int) -> tuple[str, str, list]:
    return (
        "JOIN [dbo].[LabAnalysis] la ON la.[LabAnalysis_ID] = o.[LabAnalysis_ID]",
        "la.[AnalysisSeries_ID] = ?",
        [analysis_series_id],
    )


def _scalar_values_by_source(
    conn: pyodbc.Connection,
    source_join: str,
    source_where: str,
    params: list,
    from_dt: datetime | None,
    to_dt: datetime | None,
    operational_only: bool = False,
) -> list[dict]:
    where = f"WHERE {source_where}"
    if from_dt:
        where += " AND o.[Timestamp] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND o.[Timestamp] <= ?"
        params.append(to_dt)

    if operational_only:
        # Navigate to the status channel via ChannelKind (v4.0.0 pattern).
        # A status channel is one whose ChannelKind.Name = 'Status' and
        # ParentChannel_ID pointing to the measurement channel.
        where += """
        AND (NOT EXISTS (
            SELECT 1
            FROM   dbo.Channel       statusC
            JOIN   dbo.ChannelKind   cr  ON cr.[ChannelKind_ID]  = statusC.[ChannelKind_ID]
            JOIN   dbo.Observation   so  ON so.[Channel_ID]     = statusC.[Stream_ID]
            JOIN   dbo.Value         sv  ON sv.[Observation_ID] = so.[Observation_ID]
            WHERE  statusC.[ParentChannel_ID] = o.[Channel_ID]
              AND  cr.[Name] = N'Status'
              AND  so.[Timestamp] <= o.[Timestamp]
        )
        OR EXISTS (
            SELECT 1
            FROM   dbo.Channel       statusC
            JOIN   dbo.ChannelKind   cr  ON cr.[ChannelKind_ID]  = statusC.[ChannelKind_ID]
            JOIN   dbo.Observation   so  ON so.[Channel_ID]     = statusC.[Stream_ID]
            JOIN   dbo.Value         sv  ON sv.[Observation_ID] = so.[Observation_ID]
            JOIN   dbo.QualityCode   qc  ON qc.[QualityCode_ID] = CAST(sv.[Value] AS INT)
            WHERE  statusC.[ParentChannel_ID] = o.[Channel_ID]
              AND  cr.[Name] = N'Status'
              AND  so.[Timestamp] <= o.[Timestamp]
              AND  qc.[IsUsable] = 1
        ))
        """

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT o.[Timestamp], v.[Value], v.[QualityCode], o.[Observation_ID]
        FROM [dbo].[Value] v
        JOIN [dbo].[Observation] o ON o.[Observation_ID] = v.[Observation_ID]
        {source_join}
        {where}
        ORDER BY o.[Timestamp]
        """,
        *params,
    )
    return [
        {"timestamp": row[0], "value": row[1], "quality_code": row[2], "observation_id": row[3]}
        for row in cursor.fetchall()
    ]


def get_scalar_values(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
    operational_only: bool = False,
) -> list[dict]:
    join, where, params = _channel_source(channel_id)
    return _scalar_values_by_source(
        conn, join, where, params, from_dt, to_dt, operational_only
    )


def get_analysis_series_scalar_values(
    conn: pyodbc.Connection,
    analysis_series_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    join, where, params = _analysis_series_source(analysis_series_id)
    return _scalar_values_by_source(conn, join, where, params, from_dt, to_dt)


def _vector_values_by_source(
    conn: pyodbc.Connection,
    source_join: str,
    source_where: str,
    params: list,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    where = f"WHERE {source_where}"
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
               vb.[NominalValue], vv.[Value], vv.[QualityCode],
               vba.[Name], au.[Unit]
        FROM [dbo].[ValueVector] vv
        JOIN [dbo].[Observation] o  ON o.[Observation_ID]  = vv.[Observation_ID]
        JOIN [dbo].[ValueBin]    vb ON vb.[ValueBin_ID]    = vv.[ValueBin_ID]
        JOIN [dbo].[ValueBinningAxis] vba ON vba.[ValueBinningAxis_ID] = vb.[ValueBinningAxis_ID]
        LEFT JOIN [dbo].[Unit] au ON au.[Unit_ID] = vba.[Unit_ID]
        {source_join}
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
            "axis_name": row[7],
            "axis_unit": row[8],
        }
        for row in cursor.fetchall()
    ]


def get_vector_values(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    join, where, params = _channel_source(channel_id)
    return _vector_values_by_source(conn, join, where, params, from_dt, to_dt)


def get_analysis_series_vector_values(
    conn: pyodbc.Connection,
    analysis_series_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    join, where, params = _analysis_series_source(analysis_series_id)
    return _vector_values_by_source(conn, join, where, params, from_dt, to_dt)


def _matrix_values_by_source(
    conn: pyodbc.Connection,
    source_join: str,
    source_where: str,
    params: list,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    where = f"WHERE {source_where}"
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
               vm.[Value], vm.[QualityCode],
               rba.[Name] AS RowAxisName, ru.[Unit] AS RowAxisUnit,
               cba.[Name] AS ColAxisName, cu.[Unit] AS ColAxisUnit
        FROM [dbo].[ValueMatrix] vm
        JOIN [dbo].[Observation] o  ON o.[Observation_ID]   = vm.[Observation_ID]
        JOIN [dbo].[ValueBin]    rb ON rb.[ValueBin_ID]     = vm.[RowValueBin_ID]
        JOIN [dbo].[ValueBin]    cb ON cb.[ValueBin_ID]     = vm.[ColValueBin_ID]
        JOIN [dbo].[ValueBinningAxis] rba ON rba.[ValueBinningAxis_ID] = rb.[ValueBinningAxis_ID]
        JOIN [dbo].[ValueBinningAxis] cba ON cba.[ValueBinningAxis_ID] = cb.[ValueBinningAxis_ID]
        LEFT JOIN [dbo].[Unit] ru ON ru.[Unit_ID] = rba.[Unit_ID]
        LEFT JOIN [dbo].[Unit] cu ON cu.[Unit_ID] = cba.[Unit_ID]
        {source_join}
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
            "row_axis_name": row[11],
            "row_axis_unit": row[12],
            "col_axis_name": row[13],
            "col_axis_unit": row[14],
        }
        for row in cursor.fetchall()
    ]


def get_matrix_values(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    join, where, params = _channel_source(channel_id)
    return _matrix_values_by_source(conn, join, where, params, from_dt, to_dt)


def get_analysis_series_matrix_values(
    conn: pyodbc.Connection,
    analysis_series_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    join, where, params = _analysis_series_source(analysis_series_id)
    return _matrix_values_by_source(conn, join, where, params, from_dt, to_dt)


def _image_values_by_source(
    conn: pyodbc.Connection,
    source_join: str,
    source_where: str,
    params: list,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    where = f"WHERE {source_where}"
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
        {source_join}
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


def get_image_values(
    conn: pyodbc.Connection,
    channel_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    join, where, params = _channel_source(channel_id)
    return _image_values_by_source(conn, join, where, params, from_dt, to_dt)


def get_analysis_series_image_values(
    conn: pyodbc.Connection,
    analysis_series_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    join, where, params = _analysis_series_source(analysis_series_id)
    return _image_values_by_source(conn, join, where, params, from_dt, to_dt)


def _image_thumbnail_by_source(
    conn, source_join: str, source_where: str, params: list, timestamp: datetime
) -> bytes | None:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT vi.[Thumbnail]
        FROM [dbo].[ValueImage] vi
        JOIN [dbo].[Observation] o ON o.[Observation_ID] = vi.[Observation_ID]
        {source_join}
        WHERE {source_where} AND o.[Timestamp] = ?
        """,
        *params,
        timestamp,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return bytes(row[0]) if row[0] is not None else None


def get_image_thumbnail(
    conn,
    channel_id: int,
    timestamp: datetime,
) -> bytes | None:
    """Return the thumbnail bytes for a specific image, or None if not found."""
    join, where, params = _channel_source(channel_id)
    return _image_thumbnail_by_source(conn, join, where, params, timestamp)


def get_analysis_series_image_thumbnail(
    conn, analysis_series_id: int, timestamp: datetime
) -> bytes | None:
    """Thumbnail bytes for a lab image at a sample-collection timestamp."""
    join, where, params = _analysis_series_source(analysis_series_id)
    return _image_thumbnail_by_source(conn, join, where, params, timestamp)


def _image_metadata_by_source(
    conn, source_join: str, source_where: str, params: list, timestamp: datetime
) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT vi.[StoragePath], vi.[ImageFormat]
        FROM [dbo].[ValueImage] vi
        JOIN [dbo].[Observation] o ON o.[Observation_ID] = vi.[Observation_ID]
        {source_join}
        WHERE {source_where} AND o.[Timestamp] = ?
        """,
        *params,
        timestamp,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {"storage_path": row[0], "image_format": row[1]}


def get_image_metadata_by_timestamp(
    conn,
    channel_id: int,
    timestamp: datetime,
) -> dict | None:
    """Return storage_path and format for a specific image."""
    join, where, params = _channel_source(channel_id)
    return _image_metadata_by_source(conn, join, where, params, timestamp)


def get_analysis_series_image_metadata_by_timestamp(
    conn, analysis_series_id: int, timestamp: datetime
) -> dict | None:
    """storage_path + format for a lab image at a sample-collection timestamp."""
    join, where, params = _analysis_series_source(analysis_series_id)
    return _image_metadata_by_source(conn, join, where, params, timestamp)


def get_values_for_metadata(
    conn: pyodbc.Connection,
    channel_id: int,
    value_kind_id: int | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
    operational_only: bool = False,
) -> list[dict]:
    """Dispatch to the correct value table based on value_kind_id."""
    vt = value_kind_id or _VALUE_TYPE_SCALAR
    if vt == _VALUE_TYPE_VECTOR:
        return get_vector_values(conn, channel_id, from_dt, to_dt)
    elif vt == _VALUE_TYPE_MATRIX:
        return get_matrix_values(conn, channel_id, from_dt, to_dt)
    elif vt == _VALUE_TYPE_IMAGE:
        return get_image_values(conn, channel_id, from_dt, to_dt)
    else:
        return get_scalar_values(conn, channel_id, from_dt, to_dt, operational_only)


def get_analysis_series_values_for_metadata(
    conn: pyodbc.Connection,
    analysis_series_id: int,
    value_kind_id: int | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    """Dispatch a lab AnalysisSeries read to the correct value table.

    Mirrors get_values_for_metadata for the lab source. No operational_only
    (lab has no status channels)."""
    vt = value_kind_id or _VALUE_TYPE_SCALAR
    if vt == _VALUE_TYPE_VECTOR:
        return get_analysis_series_vector_values(conn, analysis_series_id, from_dt, to_dt)
    elif vt == _VALUE_TYPE_MATRIX:
        return get_analysis_series_matrix_values(conn, analysis_series_id, from_dt, to_dt)
    elif vt == _VALUE_TYPE_IMAGE:
        return get_analysis_series_image_values(conn, analysis_series_id, from_dt, to_dt)
    else:
        return get_analysis_series_scalar_values(conn, analysis_series_id, from_dt, to_dt)


def insert_scalar_values(
    conn: pyodbc.Connection,
    channel_id: int,
    values: list[dict],
) -> int:
    """Bulk-insert rows into dbo.Observation + dbo.Value. Returns rows written.

    Uses a temp staging table. Rows with (channel_id, timestamp) already in
    Observation are deleted from the stage before inserting, making the call
    idempotent. Safe to call on overlapping windows (concurrent schedulers,
    manual backfills, etc.).
    """
    if not values:
        return 0

    cursor = conn.cursor()
    cursor.fast_executemany = True

    cursor.execute("IF OBJECT_ID('tempdb..#obs_stage') IS NOT NULL DROP TABLE #obs_stage")
    cursor.execute("""
        CREATE TABLE #obs_stage (
            row_num  INT            NOT NULL,
            ts       DATETIME2      NOT NULL,
            val      FLOAT              NULL,
            qc       INT                NULL
        )
    """)

    cursor.executemany(
        "INSERT INTO #obs_stage (row_num, ts, val, qc) VALUES (?, ?, ?, ?)",
        [
            (i, _utc_naive(v["timestamp"]), v["value"], v.get("quality_code"))
            for i, v in enumerate(values)
        ],
    )

    # Remove any rows that already exist in Observation so the INSERT below
    # never hits the unique constraint regardless of the call pattern.
    cursor.execute(
        """
        DELETE s FROM #obs_stage s
        WHERE EXISTS (
            SELECT 1 FROM [dbo].[Observation] o
            WHERE o.[Channel_ID] = ? AND o.[Timestamp] = s.ts AND o.[ValueKind_ID] = 1
        )
        """,
        channel_id,
    )

    cursor.execute("SELECT row_num FROM #obs_stage ORDER BY row_num")
    remaining = [row[0] for row in cursor.fetchall()]

    if not remaining:
        conn.commit()
        cursor.execute("DROP TABLE #obs_stage")
        return 0

    cursor.execute(
        """
        INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [ValueKind_ID])
        OUTPUT INSERTED.[Observation_ID]
        SELECT ?, ts, 1 FROM #obs_stage ORDER BY row_num
        """,
        channel_id,
    )
    obs_ids = [row[0] for row in cursor.fetchall()]

    cursor.executemany(
        "INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (?, ?, ?)",
        [
            (obs_ids[j], values[remaining[j]]["value"], values[remaining[j]].get("quality_code"))
            for j in range(len(obs_ids))
        ],
    )
    conn.commit()
    cursor.execute("DROP TABLE #obs_stage")
    return len(obs_ids)


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

    # Insert Observations one-by-one (OUTPUT INSERTED needed for IDs), then
    # bulk-insert all ValueVector rows in a single executemany call.
    all_vv_rows: list[tuple] = []
    for obs in observations:
        timestamp = obs["timestamp"]
        quality_code = obs.get("quality_code")
        bin_values = obs["bin_values"]

        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM [dbo].[Observation]
                WHERE [Channel_ID] = ? AND [Timestamp] = ? AND [ValueKind_ID] = 2
            )
            INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [ValueKind_ID])
            OUTPUT INSERTED.[Observation_ID]
            VALUES (?, ?, 2)
            """,
            channel_id,
            _utc_naive(timestamp),
            channel_id,
            _utc_naive(timestamp),
        )
        row = cursor.fetchone()
        if row is None:
            continue  # already exists, skip this observation
        obs_id: int = row[0]

        for i, value in enumerate(bin_values):
            bin_id = bin_map.get(i)
            if bin_id is None:
                continue
            all_vv_rows.append((obs_id, bin_id, value, quality_code))

    if all_vv_rows:
        cursor.fast_executemany = True
        cursor.executemany(
            """
            INSERT INTO [dbo].[ValueVector]
                ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
            VALUES (?, ?, ?, ?)
            """,
            all_vv_rows,
        )

    conn.commit()
    return len(all_vv_rows)


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

        # Create Observation for this timestamp, skipping if already exists.
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM [dbo].[Observation]
                WHERE [Channel_ID] = ? AND [Timestamp] = ? AND [ValueKind_ID] = 3
            )
            INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [ValueKind_ID])
            OUTPUT INSERTED.[Observation_ID]
            VALUES (?, ?, 3)
            """,
            channel_id,
            _utc_naive(obs["timestamp"]),
            channel_id,
            _utc_naive(obs["timestamp"]),
        )
        row = cursor.fetchone()
        if row is None:
            continue  # already exists, skip
        obs_id: int = row[0]

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
    # Step 1: create Observation, get ID — skip if already exists
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM [dbo].[Observation]
            WHERE [Channel_ID] = ? AND [Timestamp] = ? AND [ValueKind_ID] = 4
        )
        INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [ValueKind_ID])
        OUTPUT INSERTED.[Observation_ID]
        VALUES (?, ?, 4)
        """,
        channel_id,
        _utc_naive(timestamp),
        channel_id,
        _utc_naive(timestamp),
    )
    row = cursor.fetchone()
    if row is None:
        return -1  # already exists
    obs_id: int = row[0]
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


def insert_lab_image_value(
    conn: pyodbc.Connection,
    *,
    lab_analysis_id: int,
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
    """Insert a lab-linked image observation. Returns the new Observation_ID.

    Unlike insert_image_value(), sets Channel_ID=NULL and LabAnalysis_ID so the
    Observation satisfies the XOR constraint for lab observations.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID])
        OUTPUT INSERTED.[Observation_ID]
        VALUES (NULL, ?, ?, 4)
        """,
        lab_analysis_id,
        _utc_naive(timestamp),
    )
    obs_id: int = cursor.fetchone()[0]
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


_BULK_QC_SQL: dict[int, str] = {
    _VALUE_TYPE_SCALAR: """
        UPDATE v
        SET    v.[QualityCode] = ?
        FROM   [dbo].[Value] v
        JOIN   [dbo].[Observation] o ON o.[Observation_ID] = v.[Observation_ID]
        WHERE  o.[Channel_ID] = ?
          AND  o.[Timestamp] >= ?
          AND  o.[Timestamp] <= ?
    """,
    _VALUE_TYPE_VECTOR: """
        UPDATE vv
        SET    vv.[QualityCode] = ?
        FROM   [dbo].[ValueVector] vv
        JOIN   [dbo].[Observation] o ON o.[Observation_ID] = vv.[Observation_ID]
        WHERE  o.[Channel_ID] = ?
          AND  o.[Timestamp] >= ?
          AND  o.[Timestamp] <= ?
    """,
    _VALUE_TYPE_MATRIX: """
        UPDATE vm
        SET    vm.[QualityCode] = ?
        FROM   [dbo].[ValueMatrix] vm
        JOIN   [dbo].[Observation] o ON o.[Observation_ID] = vm.[Observation_ID]
        WHERE  o.[Channel_ID] = ?
          AND  o.[Timestamp] >= ?
          AND  o.[Timestamp] <= ?
    """,
    _VALUE_TYPE_IMAGE: """
        UPDATE vi
        SET    vi.[QualityCode] = ?
        FROM   [dbo].[ValueImage] vi
        JOIN   [dbo].[Observation] o ON o.[Observation_ID] = vi.[Observation_ID]
        WHERE  o.[Channel_ID] = ?
          AND  o.[Timestamp] >= ?
          AND  o.[Timestamp] <= ?
    """,
}


_STATS_TABLE = {
    _VALUE_TYPE_SCALAR: "[dbo].[Value]",
    _VALUE_TYPE_VECTOR: "[dbo].[ValueVector]",
    _VALUE_TYPE_MATRIX: "[dbo].[ValueMatrix]",
    _VALUE_TYPE_IMAGE: "[dbo].[ValueImage]",
}


def _stats_by_source(
    conn: pyodbc.Connection,
    value_kind_id: int,
    source_join: str,
    source_where: str,
    params: list,
) -> tuple:
    vt = value_kind_id if value_kind_id in _STATS_TABLE else _VALUE_TYPE_SCALAR
    # Vector/matrix have multiple rows per observation; COUNT DISTINCT gives measurement count.
    table = _STATS_TABLE[vt]
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT MIN(o.[Timestamp]), MAX(o.[Timestamp]),
               COUNT(DISTINCT o.[Observation_ID])
        FROM {table} v
        JOIN [dbo].[Observation] o ON o.[Observation_ID] = v.[Observation_ID]
        {source_join}
        WHERE {source_where}
        """,
        *params,
    )
    row = cursor.fetchone()
    return (row[0], row[1], row[2] or 0) if row else (None, None, 0)


def get_channel_stats(
    conn: pyodbc.Connection,
    channel_id: int,
    value_kind_id: int,
) -> dict:
    """Return min/max timestamp and observation count for a channel without loading data."""
    join, where, params = _channel_source(channel_id)
    min_ts, max_ts, count = _stats_by_source(
        conn, value_kind_id, join, where, params
    )
    return {
        "channel_id": channel_id,
        "min_timestamp": min_ts,
        "max_timestamp": max_ts,
        "row_count": count,
    }


def get_analysis_series_stats(
    conn: pyodbc.Connection,
    analysis_series_id: int,
    value_kind_id: int,
) -> dict:
    """min/max sample-collection time + measurement count for a lab series."""
    join, where, params = _analysis_series_source(analysis_series_id)
    min_ts, max_ts, count = _stats_by_source(
        conn, value_kind_id, join, where, params
    )
    return {
        "analysis_series_id": analysis_series_id,
        "min_timestamp": min_ts,
        "max_timestamp": max_ts,
        "row_count": count,
    }


def bulk_set_quality_code(
    conn: pyodbc.Connection,
    channel_id: int,
    value_kind_id: int,
    from_dt: datetime,
    to_dt: datetime,
    quality_code: int,
) -> int:
    """Set QualityCode on all value rows for a channel within [from_dt, to_dt].

    For vector/matrix types every payload row per matched observation is updated
    (one QualityCode stored on each bin row).  Returns the row count updated.
    """
    vt = value_kind_id if value_kind_id in _BULK_QC_SQL else _VALUE_TYPE_SCALAR
    cursor = conn.cursor()
    cursor.execute(_BULK_QC_SQL[vt], quality_code, channel_id, from_dt, to_dt)
    updated = cursor.rowcount
    conn.commit()
    return updated
