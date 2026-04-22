"""Data access for ingestion operations."""

from __future__ import annotations

import logging
from datetime import datetime

import pyodbc

logger = logging.getLogger(__name__)


def find_or_create_sensor_metadata(
    conn: pyodbc.Connection,
    *,
    signal_interface_id: int,
    tag_name: str,
    parameter_id: int,
    unit_id: int | None = None,
    data_provenance_id: int,
    processing_degree_id: int,
    value_type_id: int = 1,
    parent_channel_id: int | None = None,
    channel_role_id: int = 1,
) -> int:
    """Find or create a Channel row for a sensor stream. Returns Channel_ID.

    Uses the UNIQUE sensor stream constraint:
    (SignalInterface_ID, TagName, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID).

    On first ingest, a new row is created with Unit_ID stored on the Channel.
    On subsequent calls for the same stream, the existing Channel_ID is returned.
    A warning is logged if the caller provides a unit_id that differs from the
    stored Channel.Unit_ID — the stored value is authoritative.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM [dbo].[Channel]
            WHERE [SignalInterface_ID] = ?
              AND [TagName] = ?
              AND [Parameter_ID] = ?
              AND [DataProvenance_ID] = ?
              AND [ProcessingDegree_ID] = ?
        )
        INSERT INTO [dbo].[Channel]
            ([SignalInterface_ID], [TagName], [Parameter_ID], [DataProvenance_ID],
             [ProcessingDegree_ID], [ValueType_ID], [Unit_ID], [ParentChannel_ID], [ChannelRole_ID])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        signal_interface_id,
        tag_name,
        parameter_id,
        data_provenance_id,
        processing_degree_id,
        signal_interface_id,
        tag_name,
        parameter_id,
        data_provenance_id,
        processing_degree_id,
        value_type_id,
        unit_id,
        parent_channel_id,
        channel_role_id,
    )
    conn.commit()
    cursor.execute(
        """
        SELECT [Channel_ID], [Unit_ID] FROM [dbo].[Channel]
        WHERE [SignalInterface_ID] = ?
          AND [TagName] = ?
          AND [Parameter_ID] = ?
          AND [DataProvenance_ID] = ?
          AND [ProcessingDegree_ID] = ?
        """,
        signal_interface_id,
        tag_name,
        parameter_id,
        data_provenance_id,
        processing_degree_id,
    )
    row = cursor.fetchone()
    channel_id, stored_unit_id = row[0], row[1]
    if unit_id is not None and stored_unit_id is not None and unit_id != stored_unit_id:
        logger.warning(
            "Unit mismatch for Channel %d: stored Unit_ID=%d but caller provided Unit_ID=%d. "
            "The stored value is authoritative — check your import config.",
            channel_id,
            stored_unit_id,
            unit_id,
        )
    return channel_id


def find_or_create_derived_metadata(
    conn: pyodbc.Connection,
    *,
    source_channel_id: int,
    processing_degree_id: int,
) -> int:
    """Find or create a Channel row for a processed output stream.

    Clones identity fields (SignalInterface_ID, TagName, Parameter, Unit, DataProvenance, ValueType)
    from the source Channel row and applies the new ProcessingDegree_ID.
    The new channel becomes a child of the source channel (ParentChannel_ID).
    """
    from fastapi import HTTPException

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [SignalInterface_ID], [TagName], [Parameter_ID], [DataProvenance_ID],
               [ValueType_ID], [Unit_ID]
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
    (
        signal_interface_id,
        tag_name,
        parameter_id,
        data_provenance_id,
        value_type_id,
        unit_id,
    ) = row
    return find_or_create_sensor_metadata(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=parameter_id,
        unit_id=unit_id,
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
