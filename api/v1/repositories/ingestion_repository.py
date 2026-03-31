"""Data access for ingestion operations."""

from __future__ import annotations

from datetime import datetime

import pyodbc


def find_or_create_sensor_metadata(
    conn: pyodbc.Connection,
    *,
    signal_port_id: int,
    parameter_id: int,
    unit_id: int | None = None,
    data_provenance_id: int,
    processing_degree_id: int,
    value_type_id: int = 1,
) -> int:
    """Find or create a Channel row for a sensor stream. Returns Channel_ID.

    Uses the UNIQUE sensor stream constraint:
    (SignalPort_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID) WHERE both are NOT NULL.

    On first ingest, a new row is created automatically — no pre-configuration needed.
    Subsequent calls for the same stream return the existing Channel_ID.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM [dbo].[Channel]
            WHERE [SignalPort_ID] = ?
              AND [Parameter_ID] = ?
              AND [DataProvenance_ID] = ?
              AND [ProcessingDegree_ID] = ?
        )
        INSERT INTO [dbo].[Channel]
            ([SignalPort_ID], [Parameter_ID], [DataProvenance_ID],
             [ProcessingDegree_ID], [ValueType_ID])
        VALUES (?, ?, ?, ?, ?)
        """,
        signal_port_id,
        parameter_id,
        data_provenance_id,
        processing_degree_id,
        signal_port_id,
        parameter_id,
        data_provenance_id,
        processing_degree_id,
        value_type_id,
    )
    conn.commit()
    cursor.execute(
        """
        SELECT [Channel_ID] FROM [dbo].[Channel]
        WHERE [SignalPort_ID] = ?
          AND [Parameter_ID] = ?
          AND [DataProvenance_ID] = ?
          AND [ProcessingDegree_ID] = ?
        """,
        signal_port_id,
        parameter_id,
        data_provenance_id,
        processing_degree_id,
    )
    return cursor.fetchone()[0]


def find_or_create_derived_metadata(
    conn: pyodbc.Connection,
    *,
    source_channel_id: int,
    processing_degree_id: int,
) -> int:
    """Find or create a Channel row for a processed output stream.

    Clones identity fields (Equipment, Parameter, Unit, DataProvenance, ValueType)
    from the source Channel row and applies the new ProcessingDegree_ID.
    """
    from fastapi import HTTPException

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [SignalPort_ID], [Parameter_ID], [DataProvenance_ID], [ValueType_ID]
        FROM [dbo].[Channel]
        WHERE [Channel_ID] = ?
        """,
        source_channel_id,
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Source channel {source_channel_id} not found.",
        )
    signal_port_id, parameter_id, data_provenance_id, value_type_id = row
    return find_or_create_sensor_metadata(
        conn,
        signal_port_id=signal_port_id,
        parameter_id=parameter_id,
        unit_id=None,
        data_provenance_id=data_provenance_id,
        processing_degree_id=processing_degree_id,
        value_type_id=value_type_id or 1,
    )


def insert_lab_analysis(
    conn: pyodbc.Connection,
    *,
    sample_id: int,
    laboratory_id: int | None,
    analyst_person_id: int | None,
    procedure_id: int | None,
    campaign_id: int | None,
    notes: str | None,
) -> int:
    """Insert a LabAnalysis row. Returns LabAnalysis_ID."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[LabAnalysis]
            ([Sample_ID], [Laboratory_ID], [AnalystPerson_ID], [Procedure_ID],
             [Campaign_ID], [Notes])
        OUTPUT INSERTED.[LabAnalysis_ID]
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        sample_id,
        laboratory_id,
        analyst_person_id,
        procedure_id,
        campaign_id,
        notes,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def insert_lab_value(
    conn: pyodbc.Connection,
    *,
    lab_analysis_id: int,
    parameter_id: int,
    unit_id: int | None = None,
    value: float,
    replicate: int = 1,
    quality_code: int | None = None,
) -> int:
    """Insert a LabValue row. Returns LabValue_ID."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[LabValue]
            ([LabAnalysis_ID], [Parameter_ID], [LabResult], [Replicate], [QualityCode_ID])
        OUTPUT INSERTED.[LabValue_ID]
        VALUES (?, ?, ?, ?, ?)
        """,
        lab_analysis_id,
        parameter_id,
        value,
        replicate,
        quality_code,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def upsert_channel_axis(
    conn: pyodbc.Connection,
    channel_id: int,
    axis_role: int,
    binning_axis_id: int,
) -> None:
    """Create or update a ChannelAxis row. AxisRole: 0=primary/row, 1=col."""
    cursor = conn.cursor()
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM [dbo].[ChannelAxis]
            WHERE [Channel_ID] = ? AND [AxisRole] = ?
        )
        INSERT INTO [dbo].[ChannelAxis]
            ([Channel_ID], [AxisRole], [ValueBinningAxis_ID])
        VALUES (?, ?, ?)
        """,
        channel_id,
        axis_role,
        channel_id,
        axis_role,
        binning_axis_id,
    )
    conn.commit()


def get_last_timestamp_for_channel(
    conn: pyodbc.Connection,
    *,
    channel_id: int,
) -> datetime | None:
    """Return the most recent Timestamp in dbo.Observation for the given Channel_ID, or None."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT TOP 1 [Timestamp]
        FROM [dbo].[Observation]
        WHERE [Channel_ID] = ?
        ORDER BY [Timestamp] DESC
        """,
        channel_id,
    )
    row = cursor.fetchone()
    return row[0] if row else None


def insert_sample(
    conn: pyodbc.Connection,
    *,
    sampling_point_id: int,
    sampled_by_person_id: int | None,
    campaign_id: int | None,
    sample_datetime_start: datetime,
    sample_datetime_end: datetime | None,
    description: str | None,
) -> int:
    """Insert a Sample row. Returns Sample_ID."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[Sample]
            ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID],
             [SampleDateTimeStart], [SampleDateTimeEnd], [Description])
        VALUES (?, ?, ?, ?, ?, ?)
        SELECT @@IDENTITY
        """,
        sampling_point_id,
        sampled_by_person_id,
        campaign_id,
        sample_datetime_start,
        sample_datetime_end,
        description,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id
