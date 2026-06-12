"""Data access for ingestion operations."""

from __future__ import annotations

import logging
from datetime import datetime

import pyodbc

logger = logging.getLogger(__name__)

# Stream subtype discriminators (StreamKind lookup seed rows).
_STREAM_KIND_SENSOR = 1  # "Sensor" → Channel
_STREAM_KIND_LAB = 2  # "Lab" → AnalysisSeries
# OperationKind seed rows.
_OPERATION_KIND_UNPROCESSED = 1  # "Unprocessed" — raw channel trait


def _insert_stream(cursor: pyodbc.Cursor, stream_kind_id: int) -> int:
    """Insert a Stream supertype row and return its new Stream_ID.

    Every Channel (and AnalysisSeries) is identified by a shared Stream_ID:
    a Stream row is inserted first to mint the ID, then the subtype row is
    inserted with that Stream_ID as its primary key (ADR 0004).
    """
    cursor.execute(
        """
        INSERT INTO [dbo].[Stream] ([StreamKind_ID])
        OUTPUT INSERTED.[Stream_ID]
        VALUES (?)
        """,
        stream_kind_id,
    )
    return int(cursor.fetchone()[0])


def _write_channel_traits(
    cursor: pyodbc.Cursor, stream_id: int, operation_kind_ids: set[int]
) -> None:
    """Insert one ChannelTrait(Stream_ID, OperationKind_ID) row per distinct id.

    The trait set is the denormalized, immutable cache of operations applied to
    a Channel across its lineage (ADR 0005). Idempotent per (Stream_ID,
    OperationKind_ID) via the NOT EXISTS guard.
    """
    for operation_kind_id in sorted(operation_kind_ids):
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM [dbo].[ChannelTrait]
                WHERE [Stream_ID] = ? AND [OperationKind_ID] = ?
            )
            INSERT INTO [dbo].[ChannelTrait] ([Stream_ID], [OperationKind_ID])
            VALUES (?, ?)
            """,
            stream_id,
            operation_kind_id,
            stream_id,
            operation_kind_id,
        )


def _get_channel_trait_set(cursor: pyodbc.Cursor, stream_id: int) -> set[int]:
    """Return the set of OperationKind_IDs in a Channel's ChannelTrait set."""
    cursor.execute(
        """
        SELECT [OperationKind_ID] FROM [dbo].[ChannelTrait]
        WHERE [Stream_ID] = ?
        """,
        stream_id,
    )
    return {int(r[0]) for r in cursor.fetchall()}


def _get_step_input_trait_union(cursor: pyodbc.Cursor, step_id: int) -> set[int]:
    """Union the ChannelTrait sets of every input stream of a ProcessingStep.

    The producing step's input edges live in ProcessingLineage (one row per
    consumed Stream_ID, written by ``record_processing``). Reading the union
    straight from the DAG keeps ChannelTrait a deterministic projection of the
    lineage and makes the trait computation correct for multi-input transforms
    (PCA, sensor fusion, lab-series-fed gap-filling) — not just the primary
    source (ADR 0005). Returns an empty set if no input edges are recorded yet.
    """
    cursor.execute(
        """
        SELECT DISTINCT ct.[OperationKind_ID]
        FROM [dbo].[ProcessingLineage] pl
        JOIN [dbo].[ChannelTrait] ct ON ct.[Stream_ID] = pl.[Stream_ID]
        WHERE pl.[ProcessingStep_ID] = ?
        """,
        step_id,
    )
    return {int(r[0]) for r in cursor.fetchall()}


def find_or_create_sensor_metadata(
    conn: pyodbc.Connection,
    *,
    signal_interface_id: int,
    tag_name: str,
    parameter_id: int,
    unit_id: int | None = None,
    data_provenance_id: int,
    value_kind_id: int = 1,
    parent_channel_id: int | None = None,
    channel_kind_id: int = 1,
) -> int:
    """Find or create a Channel row for a raw sensor stream. Returns Stream_ID.

    Uses the UNIQUE sensor stream constraint:
    (SignalInterface_ID, TagName, Parameter_ID, DataProvenanceKind_ID, ProducedByStep_ID IS NULL).

    On first ingest, a Stream row (StreamKind=Sensor) is inserted to mint the
    Stream_ID, then a Channel row is created with that Stream_ID as its primary
    key and Unit_ID stored, followed by a single Unprocessed ChannelTrait.
    On subsequent calls for the same stream, the existing Stream_ID is returned.
    A warning is logged if the caller provides a unit_id that differs from the
    stored Channel.Unit_ID — the stored value is authoritative.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [Stream_ID], [Unit_ID] FROM [dbo].[Channel]
        WHERE [SignalInterface_ID] = ?
          AND [TagName] = ?
          AND [Parameter_ID] = ?
          AND [DataProvenanceKind_ID] = ?
          AND [ProducedByStep_ID] IS NULL
        """,
        signal_interface_id,
        tag_name,
        parameter_id,
        data_provenance_id,
    )
    row = cursor.fetchone()
    if row is not None:
        stream_id, stored_unit_id = int(row[0]), row[1]
        if (
            unit_id is not None
            and stored_unit_id is not None
            and unit_id != stored_unit_id
        ):
            logger.warning(
                "Unit mismatch for Channel %d: stored Unit_ID=%d but caller provided Unit_ID=%d. "
                "The stored value is authoritative — check your import config.",
                stream_id,
                stored_unit_id,
                unit_id,
            )
        return stream_id

    stream_id = _insert_stream(cursor, _STREAM_KIND_SENSOR)
    cursor.execute(
        """
        INSERT INTO [dbo].[Channel]
            ([Stream_ID], [SignalInterface_ID], [TagName], [Parameter_ID],
             [DataProvenanceKind_ID], [ValueKind_ID], [Unit_ID],
             [ParentChannel_ID], [ChannelKind_ID])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        stream_id,
        signal_interface_id,
        tag_name,
        parameter_id,
        data_provenance_id,
        value_kind_id,
        unit_id,
        parent_channel_id,
        channel_kind_id,
    )
    _write_channel_traits(cursor, stream_id, {_OPERATION_KIND_UNPROCESSED})
    conn.commit()
    return stream_id


def find_or_create_derived_metadata(
    conn: pyodbc.Connection,
    *,
    source_channel_id: int,
    produced_by_step_id: int | None,
) -> int:
    """Find or create a Channel row for a processed output stream. Returns Stream_ID.

    ``source_channel_id`` is a Stream_ID identifying the input Channel. Inherits
    TagName and Parameter_ID from the source channel. SignalInterface_ID is set to
    NULL (derived channels have no physical source). DataProvenanceKind_ID is set
    to 7 (Derived). ProducedByStep_ID distinguishes independently-processed
    variants.

    On creation, a Stream row (StreamKind=Sensor) is inserted to mint the
    Stream_ID, then the Channel row is inserted with that Stream_ID as its PK, and
    the ChannelTrait set is written as the union of the source channel's existing
    traits and the producing ProcessingStep's OperationKind (ADR 0005).
    """
    from fastapi import HTTPException

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [TagName], [Parameter_ID], [ValueKind_ID], [Unit_ID]
        FROM [dbo].[Channel]
        WHERE [Stream_ID] = ?
        """,
        source_channel_id,
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Source channel {source_channel_id} not found.",
        )
    tag_name, parameter_id, value_kind_id, unit_id = row

    _DERIVED_PROVENANCE_KIND_ID = 7  # "Derived" seed row

    if produced_by_step_id is None:
        step_filter = "[ProducedByStep_ID] IS NULL"
        step_params: list = []
    else:
        step_filter = "[ProducedByStep_ID] = ?"
        step_params = [produced_by_step_id]

    cursor.execute(
        f"""
        SELECT [Stream_ID] FROM [dbo].[Channel]
        WHERE [SignalInterface_ID] IS NULL
          AND [TagName] = ?
          AND [Parameter_ID] = ?
          AND [DataProvenanceKind_ID] = ?
          AND {step_filter}
        """,
        tag_name,
        parameter_id,
        _DERIVED_PROVENANCE_KIND_ID,
        *step_params,
    )
    existing = cursor.fetchone()
    if existing is not None:
        return int(existing[0])

    stream_id = _insert_stream(cursor, _STREAM_KIND_SENSOR)
    cursor.execute(
        """
        INSERT INTO [dbo].[Channel]
            ([Stream_ID], [SignalInterface_ID], [TagName], [Parameter_ID],
             [DataProvenanceKind_ID], [ProducedByStep_ID], [ValueKind_ID],
             [Unit_ID], [ParentChannel_ID])
        VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?)
        """,
        stream_id,
        tag_name,
        parameter_id,
        _DERIVED_PROVENANCE_KIND_ID,
        produced_by_step_id,
        value_kind_id or 1,
        unit_id,
        source_channel_id,
    )

    # Trait set = union(all input channels' traits) ∪ {producing step's OperationKind}.
    # The full input set comes from the step's ProcessingLineage edges (multi-input
    # transforms inherit every input's traits, not just the primary source — ADR 0005).
    # The primary source is always included explicitly so the trait set is still
    # correct if lineage edges were not recorded for this step (e.g. the direct
    # provision endpoint), preserving the single-input behaviour as a floor.
    trait_ids = _get_channel_trait_set(cursor, source_channel_id)
    if produced_by_step_id is not None:
        trait_ids |= _get_step_input_trait_union(cursor, produced_by_step_id)
        cursor.execute(
            """
            SELECT [OperationKind_ID] FROM [dbo].[ProcessingStep]
            WHERE [ProcessingStep_ID] = ?
            """,
            produced_by_step_id,
        )
        step_row = cursor.fetchone()
        if step_row is not None and step_row[0] is not None:
            trait_ids.add(int(step_row[0]))
    _write_channel_traits(cursor, stream_id, trait_ids)

    conn.commit()
    return stream_id


def find_or_create_analysis_series(
    conn: pyodbc.Connection,
    *,
    parameter_id: int,
    sampling_point_id: int,
    value_kind_id: int,
    unit_id: int,
    name: str,
    campaign_id: int | None = None,
) -> int:
    """Find or create an AnalysisSeries row. Returns Stream_ID.

    Uses the UNIQUE identity constraint:
    UQ_AnalysisSeries_Identity (Parameter_ID, SamplingPoint_ID, ValueKind_ID).

    AnalysisSeries is the Lab subtype of Stream (table-per-type inheritance): its
    primary key is a shared Stream_ID. On first measurement, a Stream row
    (StreamKind=Lab) is inserted to mint the Stream_ID, then an AnalysisSeries row
    is created with that Stream_ID as its PK and Unit_ID / Name stored. On
    subsequent calls for the same series identity, the existing Stream_ID is
    returned and Unit_ID / Name are NOT updated (immutable for the series).
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [Stream_ID]
        FROM [dbo].[AnalysisSeries]
        WHERE [Parameter_ID] = ?
          AND [SamplingPoint_ID] = ?
          AND [ValueKind_ID] = ?
        """,
        parameter_id,
        sampling_point_id,
        value_kind_id,
    )
    row = cursor.fetchone()
    if row is not None:
        return int(row[0])

    stream_id = _insert_stream(cursor, _STREAM_KIND_LAB)
    cursor.execute(
        """
        INSERT INTO [dbo].[AnalysisSeries]
            ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID],
             [ValueKind_ID], [Unit_ID], [Campaign_ID])
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        stream_id,
        name,
        parameter_id,
        sampling_point_id,
        value_kind_id,
        unit_id,
        campaign_id,
    )
    conn.commit()
    return stream_id


def lab_experiment_exists(conn: pyodbc.Connection, experiment_id: int) -> bool:
    """Return True if a LabExperiment row with the given ID exists."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM [dbo].[LabExperiment] WHERE [LabExperiment_ID] = ?",
        experiment_id,
    )
    return cursor.fetchone() is not None


def insert_lab_experiment(
    conn: pyodbc.Connection,
    *,
    name: str,
    experiment_datetime: datetime,
    campaign_id: int | None = None,
    description: str | None = None,
    created_by_person_id: int | None = None,
    lab_panel_id: int | None = None,
) -> int:
    """Insert a LabExperiment row. Returns LabExperiment_ID."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[LabExperiment]
            ([Name], [Campaign_ID], [ExperimentDateTime], [Description], [CreatedByPerson_ID], [LabPanel_ID])
        OUTPUT INSERTED.[LabExperiment_ID]
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        name,
        campaign_id,
        experiment_datetime,
        description,
        created_by_person_id,
        lab_panel_id,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def insert_lab_analysis(
    conn: pyodbc.Connection,
    *,
    lab_experiment_id: int,
    analysis_series_id: int,
    sample_id: int,
    laboratory_id: int | None = None,
    analyst_person_id: int | None = None,
    procedure_id: int | None = None,
    analysis_datetime: datetime | None = None,
    replicate: int = 1,
    quality_code_id: int | None = None,
    notes: str | None = None,
) -> int:
    """Insert a LabAnalysis row. Returns LabAnalysis_ID.

    Uses the column DEFAULT (SYSUTCDATETIME()) when ``analysis_datetime`` is None
    by omitting the column from the INSERT.
    """
    cursor = conn.cursor()
    if analysis_datetime is None:
        cursor.execute(
            """
            INSERT INTO [dbo].[LabAnalysis]
                ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate],
                 [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [Procedure_ID], [Notes])
            OUTPUT INSERTED.[LabAnalysis_ID]
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            lab_experiment_id,
            analysis_series_id,
            sample_id,
            replicate,
            quality_code_id,
            laboratory_id,
            analyst_person_id,
            procedure_id,
            notes,
        )
    else:
        cursor.execute(
            """
            INSERT INTO [dbo].[LabAnalysis]
                ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate],
                 [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [Procedure_ID],
                 [AnalysisDateTime], [Notes])
            OUTPUT INSERTED.[LabAnalysis_ID]
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            lab_experiment_id,
            analysis_series_id,
            sample_id,
            replicate,
            quality_code_id,
            laboratory_id,
            analyst_person_id,
            procedure_id,
            analysis_datetime,
            notes,
        )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


def upsert_analysis_series_axis(
    conn: pyodbc.Connection,
    analysis_series_id: int,
    axis_role: int,
    binning_axis_id: int,
) -> None:
    """Create or update an AnalysisSeriesAxis row. AxisRole: 0=primary/row, 1=col."""
    cursor = conn.cursor()
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM [dbo].[AnalysisSeriesAxis]
            WHERE [AnalysisSeries_ID] = ? AND [AxisRole] = ?
        )
        INSERT INTO [dbo].[AnalysisSeriesAxis]
            ([AnalysisSeries_ID], [AxisRole], [ValueBinningAxis_ID])
        VALUES (?, ?, ?)
        """,
        analysis_series_id,
        axis_role,
        analysis_series_id,
        axis_role,
        binning_axis_id,
    )
    conn.commit()


def _get_analysis_series_axes(
    cursor: pyodbc.Cursor, analysis_series_id: int
) -> dict[int, int]:
    """Return mapping AxisRole → ValueBinningAxis_ID for the given series."""
    cursor.execute(
        """
        SELECT [AxisRole], [ValueBinningAxis_ID]
        FROM [dbo].[AnalysisSeriesAxis]
        WHERE [AnalysisSeries_ID] = ?
        """,
        analysis_series_id,
    )
    return {int(r[0]): int(r[1]) for r in cursor.fetchall()}


def _get_value_bins(cursor: pyodbc.Cursor, binning_axis_id: int) -> dict[int, int]:
    """Return mapping BinIndex → ValueBin_ID for a binning axis."""
    cursor.execute(
        """
        SELECT [ValueBin_ID], [BinIndex] FROM [dbo].[ValueBin]
        WHERE [ValueBinningAxis_ID] = ? ORDER BY [BinIndex]
        """,
        binning_axis_id,
    )
    return {int(r[1]): int(r[0]) for r in cursor.fetchall()}


def insert_lab_observation(
    conn: pyodbc.Connection,
    *,
    lab_analysis_id: int,
    analysis_series_id: int,
    timestamp: datetime,
    value_kind_id: int,
    value: float | list | None,
    quality_code: int | None = None,
) -> int:
    """Insert an Observation row for a lab analysis and route payload to the
    appropriate value table.

    - ``value_kind_id=1`` (Scalar): ``value`` is ``float | None`` → ``Value``
    - ``value_kind_id=2`` (Vector): ``value`` is ``list[float | None]`` →
      ``ValueVector`` (axes resolved from ``AnalysisSeriesAxis``)
    - ``value_kind_id=3`` (Matrix): ``value`` is ``list[list[float | None]]``
      → ``ValueMatrix`` (row + col axes from ``AnalysisSeriesAxis``)

    The Observation row is written with ``Channel_ID = NULL`` and
    ``LabAnalysis_ID = lab_analysis_id``, satisfying the XOR CHECK constraint.

    Returns Observation_ID.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[Observation]
            ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID])
        OUTPUT INSERTED.[Observation_ID]
        VALUES (NULL, ?, ?, ?)
        """,
        lab_analysis_id,
        timestamp,
        value_kind_id,
    )
    obs_id: int = cursor.fetchone()[0]

    if value_kind_id == 1:
        scalar_value = value if (value is None or isinstance(value, (int, float))) else None
        cursor.execute(
            "INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (?, ?, ?)",
            obs_id,
            scalar_value,
            quality_code,
        )
    elif value_kind_id == 2:
        if not isinstance(value, list):
            raise ValueError("vector lab observation requires a list value")
        axes = _get_analysis_series_axes(cursor, analysis_series_id)
        axis_id = axes.get(0)
        if axis_id is None:
            raise ValueError(
                f"AnalysisSeries {analysis_series_id} has no AxisRole=0; cannot ingest vector"
            )
        bin_map = _get_value_bins(cursor, axis_id)
        for i, bin_val in enumerate(value):
            bin_id = bin_map.get(i)
            if bin_id is None:
                continue
            cursor.execute(
                """
                INSERT INTO [dbo].[ValueVector]
                    ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
                VALUES (?, ?, ?, ?)
                """,
                obs_id,
                bin_id,
                bin_val,
                quality_code,
            )
    elif value_kind_id == 3:
        if not isinstance(value, list):
            raise ValueError("matrix lab observation requires a list-of-lists value")
        axes = _get_analysis_series_axes(cursor, analysis_series_id)
        row_axis_id = axes.get(0)
        col_axis_id = axes.get(1)
        if row_axis_id is None or col_axis_id is None:
            raise ValueError(
                f"AnalysisSeries {analysis_series_id} missing AxisRole 0 or 1; cannot ingest matrix"
            )
        row_map = _get_value_bins(cursor, row_axis_id)
        col_map = _get_value_bins(cursor, col_axis_id)
        for r, row in enumerate(value):
            if not isinstance(row, list):
                continue
            for c, cell_val in enumerate(row):
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
                    cell_val,
                    quality_code,
                )
    else:
        raise ValueError(
            f"unsupported value_kind_id={value_kind_id} for lab observation"
        )

    conn.commit()
    return obs_id


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


def get_sample_collection_time(
    conn: pyodbc.Connection,
    *,
    sample_id: int,
) -> datetime:
    """Return Sample.SampleDateTimeStart (collection time) for a Sample_ID.

    This is the real-world moment the water was sampled — the time anchor for
    lab Observations. Raises HTTPException(404) if the sample does not exist.
    """
    from fastapi import HTTPException

    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SampleDateTimeStart] FROM [dbo].[Sample] WHERE [Sample_ID] = ?",
        sample_id,
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found.")
    return row[0]


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
    sample_collection_kind_id: int | None = None,
    sample_equipment_id: int | None = None,
    description: str | None,
) -> int:
    """Insert a Sample row. Returns Sample_ID."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[Sample]
            ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID],
             [SampleDateTimeStart], [SampleDateTimeEnd],
             [SampleCollectionKind_ID], [SampleEquipment_ID],
             [Description])
        OUTPUT INSERTED.[Sample_ID]
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        sampling_point_id,
        sampled_by_person_id,
        campaign_id,
        sample_datetime_start,
        sample_datetime_end,
        sample_collection_kind_id,
        sample_equipment_id,
        description,
    )
    new_id: int = cursor.fetchone()[0]
    conn.commit()
    return new_id


# ---------------------------------------------------------------------------
# Lab experiment / series / template lookups
# ---------------------------------------------------------------------------


def list_lab_experiments_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return recent LabExperiments with series count for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT TOP 50
            le.[LabExperiment_ID],
            le.[Name],
            le.[ExperimentDateTime],
            (SELECT COUNT(DISTINCT la.[AnalysisSeries_ID])
             FROM [dbo].[LabAnalysis] la
             WHERE la.[LabExperiment_ID] = le.[LabExperiment_ID]) AS [SeriesCount]
        FROM [dbo].[LabExperiment] le
        ORDER BY le.[ExperimentDateTime] DESC
        """
    )
    return [
        {
            "lab_experiment_id": r[0],
            "name": r[1],
            "experiment_datetime": r[2],
            "series_count": r[3],
        }
        for r in cursor.fetchall()
    ]


def get_lab_experiment_series(
    conn: pyodbc.Connection, lab_experiment_id: int
) -> list[dict]:
    """Return distinct AnalysisSeries used in a LabExperiment."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT
            as_.[Stream_ID],
            as_.[Name],
            as_.[Parameter_ID],
            p.[Parameter] AS [ParameterName],
            as_.[SamplingPoint_ID],
            COALESCE(sp.[SamplingPoint], 'Point ' + CAST(sp.[SamplingPoint_ID] AS NVARCHAR)) AS [SamplingPointLabel],
            as_.[Unit_ID],
            u.[Unit],
            as_.[ValueKind_ID]
        FROM [dbo].[LabAnalysis] la
        JOIN [dbo].[AnalysisSeries] as_ ON la.[AnalysisSeries_ID] = as_.[Stream_ID]
        JOIN [dbo].[Parameter] p ON as_.[Parameter_ID] = p.[Parameter_ID]
        JOIN [dbo].[SamplingPoint] sp ON as_.[SamplingPoint_ID] = sp.[SamplingPoint_ID]
        JOIN [dbo].[Unit] u ON as_.[Unit_ID] = u.[Unit_ID]
        WHERE la.[LabExperiment_ID] = ?
        """,
        lab_experiment_id,
    )
    return [
        {
            "analysis_series_id": r[0],
            "name": r[1],
            "parameter_id": r[2],
            "parameter_name": r[3],
            "sampling_point_id": r[4],
            "sampling_point_label": r[5],
            "unit_id": r[6],
            "unit_name": r[7],
            "value_kind_id": r[8],
        }
        for r in cursor.fetchall()
    ]


def list_analysis_series_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return all AnalysisSeries for dropdown."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            as_.[Stream_ID],
            as_.[Name],
            as_.[Parameter_ID],
            p.[Parameter] AS [ParameterName],
            as_.[SamplingPoint_ID],
            COALESCE(sp.[SamplingPoint], 'Point ' + CAST(sp.[SamplingPoint_ID] AS NVARCHAR)) AS [SamplingPointLabel],
            as_.[Unit_ID],
            u.[Unit],
            as_.[ValueKind_ID],
            as_.[Campaign_ID],
            c.[Name] AS [CampaignName]
        FROM [dbo].[AnalysisSeries] as_
        JOIN [dbo].[Parameter] p ON as_.[Parameter_ID] = p.[Parameter_ID]
        JOIN [dbo].[SamplingPoint] sp ON as_.[SamplingPoint_ID] = sp.[SamplingPoint_ID]
        JOIN [dbo].[Unit] u ON as_.[Unit_ID] = u.[Unit_ID]
        LEFT JOIN [dbo].[Campaign] c ON c.[Campaign_ID] = as_.[Campaign_ID]
        ORDER BY as_.[Name]
        """
    )
    return [
        {
            "analysis_series_id": r[0],
            "name": r[1],
            "parameter_id": r[2],
            "parameter_name": r[3],
            "sampling_point_id": r[4],
            "sampling_point_label": r[5],
            "unit_id": r[6],
            "unit_name": r[7],
            "value_kind_id": r[8],
            "campaign_id": r[9],
            "campaign_name": r[10],
        }
        for r in cursor.fetchall()
    ]


def get_analysis_series_by_id(
    conn: pyodbc.Connection, analysis_series_id: int
) -> dict | None:
    """Return one AnalysisSeries with resolved labels, or None if not found."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            as_.[Stream_ID],
            as_.[Name],
            as_.[Parameter_ID],
            p.[Parameter] AS [ParameterName],
            as_.[SamplingPoint_ID],
            COALESCE(sp.[SamplingPoint], 'Point ' + CAST(sp.[SamplingPoint_ID] AS NVARCHAR)) AS [SamplingPointLabel],
            as_.[Unit_ID],
            u.[Unit],
            as_.[ValueKind_ID],
            as_.[Campaign_ID]
        FROM [dbo].[AnalysisSeries] as_
        JOIN [dbo].[Parameter] p ON as_.[Parameter_ID] = p.[Parameter_ID]
        JOIN [dbo].[SamplingPoint] sp ON as_.[SamplingPoint_ID] = sp.[SamplingPoint_ID]
        JOIN [dbo].[Unit] u ON as_.[Unit_ID] = u.[Unit_ID]
        WHERE as_.[Stream_ID] = ?
        """,
        analysis_series_id,
    )
    r = cursor.fetchone()
    if r is None:
        return None
    return {
        "analysis_series_id": r[0],
        "name": r[1],
        "parameter_id": r[2],
        "parameter_name": r[3],
        "sampling_point_id": r[4],
        "sampling_point_label": r[5],
        "unit_id": r[6],
        "unit_name": r[7],
        "value_kind_id": r[8],
        "campaign_id": r[9],
    }


def create_analysis_series(
    conn: pyodbc.Connection,
    *,
    parameter_id: int,
    sampling_point_id: int,
    unit_id: int,
    value_kind_id: int = 1,
    name: str,
    campaign_id: int | None = None,
) -> int:
    """Insert an AnalysisSeries row. Returns Stream_ID.

    AnalysisSeries is the Lab subtype of Stream: a Stream row (StreamKind=Lab) is
    inserted to mint the Stream_ID, then the AnalysisSeries row is created with
    that Stream_ID as its PK. Raises ValueError if a series with the same identity
    constraint (Parameter_ID, SamplingPoint_ID, ValueKind_ID) already exists.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [Stream_ID]
        FROM [dbo].[AnalysisSeries]
        WHERE [Parameter_ID] = ?
          AND [SamplingPoint_ID] = ?
          AND [ValueKind_ID] = ?
        """,
        parameter_id,
        sampling_point_id,
        value_kind_id,
    )
    row = cursor.fetchone()
    if row is not None:
        raise ValueError(
            f"AnalysisSeries already exists (ID={row[0]}) for "
            f"Parameter={parameter_id}, SamplingPoint={sampling_point_id}, "
            f"ValueKind={value_kind_id}"
        )
    stream_id = _insert_stream(cursor, _STREAM_KIND_LAB)
    cursor.execute(
        """
        INSERT INTO [dbo].[AnalysisSeries]
            ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID],
             [ValueKind_ID], [Unit_ID], [Campaign_ID])
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        stream_id,
        name,
        parameter_id,
        sampling_point_id,
        value_kind_id,
        unit_id,
        campaign_id,
    )
    conn.commit()
    return stream_id


def list_lab_panels(conn: pyodbc.Connection) -> list[dict]:
    """Return templates with series count."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            t.[LabPanel_ID],
            t.[Name],
            t.[Description],
            t.[CreatedByPerson_ID],
            t.[DefaultSampleCollectionKind_ID],
            t.[DefaultSampleEquipment_ID],
            (SELECT COUNT(*) FROM [dbo].[LabPanelSeries] ts
             WHERE ts.[LabPanel_ID] = t.[LabPanel_ID]) AS [SeriesCount]
        FROM [dbo].[LabPanel] t
        ORDER BY t.[Name]
        """
    )
    return [
        {
            "lab_panel_id": r[0],
            "name": r[1],
            "description": r[2],
            "created_by_person_id": r[3],
            "default_sample_collection_kind_id": r[4],
            "default_sample_equipment_id": r[5],
            "series_count": r[6],
        }
        for r in cursor.fetchall()
    ]


def get_template_series(
    conn: pyodbc.Connection, template_id: int
) -> list[dict]:
    """Return series list for a template (joined with lookup names)."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            as_.[Stream_ID],
            as_.[Name],
            as_.[Parameter_ID],
            p.[Parameter] AS [ParameterName],
            as_.[SamplingPoint_ID],
            COALESCE(sp.[SamplingPoint], 'Point ' + CAST(sp.[SamplingPoint_ID] AS NVARCHAR)) AS [SamplingPointLabel],
            as_.[Unit_ID],
            u.[Unit],
            as_.[ValueKind_ID]
        FROM [dbo].[LabPanelSeries] ts
        JOIN [dbo].[AnalysisSeries] as_ ON ts.[AnalysisSeries_ID] = as_.[Stream_ID]
        JOIN [dbo].[Parameter] p ON as_.[Parameter_ID] = p.[Parameter_ID]
        JOIN [dbo].[SamplingPoint] sp ON as_.[SamplingPoint_ID] = sp.[SamplingPoint_ID]
        JOIN [dbo].[Unit] u ON as_.[Unit_ID] = u.[Unit_ID]
        WHERE ts.[LabPanel_ID] = ?
        ORDER BY as_.[Name]
        """,
        template_id,
    )
    return [
        {
            "analysis_series_id": r[0],
            "name": r[1],
            "parameter_id": r[2],
            "parameter_name": r[3],
            "sampling_point_id": r[4],
            "sampling_point_label": r[5],
            "unit_id": r[6],
            "unit_name": r[7],
            "value_kind_id": r[8],
        }
        for r in cursor.fetchall()
    ]


def create_lab_panel(
    conn: pyodbc.Connection,
    *,
    name: str,
    description: str | None = None,
    created_by_person_id: int | None = None,
    default_sample_collection_kind_id: int | None = None,
    default_sample_equipment_id: int | None = None,
    series_ids: list[int],
) -> int:
    """Insert a template and its series rows in a transaction. Returns Template_ID."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[LabPanel]
            ([Name], [Description], [CreatedByPerson_ID],
             [DefaultSampleCollectionKind_ID], [DefaultSampleEquipment_ID])
        OUTPUT INSERTED.[LabPanel_ID]
        VALUES (?, ?, ?, ?, ?)
        """,
        name,
        description,
        created_by_person_id,
        default_sample_collection_kind_id,
        default_sample_equipment_id,
    )
    template_id: int = cursor.fetchone()[0]
    for sid in series_ids:
        cursor.execute(
            """
            INSERT INTO [dbo].[LabPanelSeries]
                ([LabPanel_ID], [AnalysisSeries_ID])
            VALUES (?, ?)
            """,
            template_id,
            sid,
        )
    conn.commit()
    return template_id


def add_series_to_template(
    conn: pyodbc.Connection, template_id: int, analysis_series_id: int
) -> None:
    """Add an AnalysisSeries to a template. No-op if already present."""
    cursor = conn.cursor()
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM [dbo].[LabPanelSeries]
            WHERE [LabPanel_ID] = ? AND [AnalysisSeries_ID] = ?
        )
        INSERT INTO [dbo].[LabPanelSeries]
            ([LabPanel_ID], [AnalysisSeries_ID])
        VALUES (?, ?)
        """,
        template_id,
        analysis_series_id,
        template_id,
        analysis_series_id,
    )
    conn.commit()


def remove_series_from_template(
    conn: pyodbc.Connection, template_id: int, analysis_series_id: int
) -> None:
    """Remove an AnalysisSeries from a template."""
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM [dbo].[LabPanelSeries]
        WHERE [LabPanel_ID] = ? AND [AnalysisSeries_ID] = ?
        """,
        template_id,
        analysis_series_id,
    )
    conn.commit()


def patch_lab_panel(
    conn: pyodbc.Connection,
    lab_panel_id: int,
    data: dict,
) -> dict | None:
    """Partial update of a LabPanel. If series_ids is present, replaces the full series list."""
    panels = list_lab_panels(conn)
    if not any(p["lab_panel_id"] == lab_panel_id for p in panels):
        return None

    cursor = conn.cursor()

    fields = []
    values = []
    if "name" in data:
        fields.append("[Name]=?")
        values.append(data["name"])
    if "description" in data:
        fields.append("[Description]=?")
        values.append(data["description"])
    if "default_sample_collection_kind_id" in data:
        fields.append("[DefaultSampleCollectionKind_ID]=?")
        values.append(data["default_sample_collection_kind_id"])
    if "default_sample_equipment_id" in data:
        fields.append("[DefaultSampleEquipment_ID]=?")
        values.append(data["default_sample_equipment_id"])

    if fields:
        values.append(lab_panel_id)
        cursor.execute(
            f"UPDATE [dbo].[LabPanel] SET {', '.join(fields)} WHERE [LabPanel_ID]=?",
            *values,
        )

    if "series_ids" in data:
        cursor.execute(
            "DELETE FROM [dbo].[LabPanelSeries] WHERE [LabPanel_ID]=?",
            lab_panel_id,
        )
        for series_id in data["series_ids"]:
            cursor.execute(
                "INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (?, ?)",
                lab_panel_id,
                series_id,
            )

    conn.commit()
    updated = list_lab_panels(conn)
    return next((p for p in updated if p["lab_panel_id"] == lab_panel_id), None)


def delete_lab_panel(conn: pyodbc.Connection, lab_panel_id: int) -> None:
    """Delete a LabPanel and all its LabPanelSeries rows in a transaction."""
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM [dbo].[LabPanelSeries] WHERE [LabPanel_ID] = ?",
        lab_panel_id,
    )
    cursor.execute(
        "DELETE FROM [dbo].[LabPanel] WHERE [LabPanel_ID] = ?",
        lab_panel_id,
    )
    conn.commit()
