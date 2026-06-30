"""Data access for maintenance-drift derived Channel creation (PRD-2.5 S1).

Creates a ProcessingStep (method='maintenance_drift') with MethodParameters JSON,
then mints a derived Channel linked to that step. Does NOT read or write dbo.Value.
"""

from __future__ import annotations

import json

import pyodbc

from api.v1.errors import EntityNotFoundError

# OperationKind seed ID 3 = "DriftCorrection" — closest semantic match for a
# maintenance-drift computation step (measures / quantifies sensor drift).
_OPERATION_KIND_DRIFT_CORRECTION = 3

# DataProvenanceKind seed ID 7 = "Derived".
_DERIVED_PROVENANCE_KIND_ID = 7

# StreamKind seed ID 1 = "Sensor" — Channel is the Sensor subtype of Stream.
_STREAM_KIND_SENSOR = 1


def _insert_stream(cursor: pyodbc.Cursor) -> int:
    """Mint a new Stream row and return its Stream_ID."""
    cursor.execute(
        """
        INSERT INTO [dbo].[Stream] ([StreamKind_ID])
        OUTPUT INSERTED.[Stream_ID]
        VALUES (?)
        """,
        _STREAM_KIND_SENSOR,
    )
    return int(cursor.fetchone()[0])


def create_drift_channel(
    conn: pyodbc.Connection,
    *,
    source_channel_id: int,
    event_ids: list[int],
    name: str,
    performed_by_person_id: int | None = None,
) -> dict:
    """Create a maintenance-drift derived Channel linked to a new ProcessingStep.

    Steps:
    1. Validate the source Channel exists and fetch its Parameter_ID / ValueKind_ID / Unit_ID.
    2. INSERT a ProcessingStep with MethodName='maintenance_drift' and MethodParameters
       JSON encoding the source channel and event window IDs.
    3. INSERT a ProcessingLineage edge from the source Channel to the new step.
    4. INSERT a derived Channel row (SignalInterface_ID=NULL, DataProvenanceKind=Derived)
       with ProducedByStep_ID pointing to the new step and ParentChannel_ID = source.
    5. Return the new Channel's identifying fields.

    No dbo.Value rows are read or written.
    """
    cursor = conn.cursor()

    # 1. Fetch source channel
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
        raise EntityNotFoundError(f"Source channel {source_channel_id} not found.")
    _tag_name, parameter_id, value_kind_id, unit_id = row

    method_parameters = json.dumps(
        {
            "source_channel_id": source_channel_id,
            "event_ids": sorted(event_ids),
        }
    )

    # 2. INSERT ProcessingStep
    cursor.execute(
        """
        INSERT INTO [dbo].[ProcessingStep]
            ([MethodName], [MethodVersion], [OperationKind_ID],
             [MethodParameters], [ExecutedAt], [ExecutedByPerson_ID])
        OUTPUT INSERTED.[ProcessingStep_ID]
        VALUES ('maintenance_drift', NULL, ?, ?, GETUTCDATE(), ?)
        """,
        _OPERATION_KIND_DRIFT_CORRECTION,
        method_parameters,
        performed_by_person_id,
    )
    step_id = int(cursor.fetchone()[0])

    # 3. INSERT ProcessingLineage edge (source channel → step)
    cursor.execute(
        """
        INSERT INTO [dbo].[ProcessingLineage] ([ProcessingStep_ID], [Stream_ID])
        VALUES (?, ?)
        """,
        step_id,
        source_channel_id,
    )

    # 4. Mint a new Stream row, then the derived Channel row
    stream_id = _insert_stream(cursor)
    cursor.execute(
        """
        INSERT INTO [dbo].[Channel]
            ([Stream_ID], [SignalInterface_ID], [TagName], [Parameter_ID],
             [DataProvenanceKind_ID], [ProducedByStep_ID], [ValueKind_ID],
             [Unit_ID], [ParentChannel_ID])
        VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?)
        """,
        stream_id,
        name,
        parameter_id,
        _DERIVED_PROVENANCE_KIND_ID,
        step_id,
        value_kind_id or 1,
        unit_id,
        source_channel_id,
    )

    conn.commit()

    return {
        "channel_id": stream_id,
        "name": name,
        "produced_by_step_id": step_id,
    }
