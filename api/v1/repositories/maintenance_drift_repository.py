"""Data access for maintenance-drift derived Channel creation (PRD-2.5 S1).

Creates a ProcessingStep (method='maintenance_drift') with MethodParameters JSON,
then mints a derived Channel linked to that step. Does NOT read or write dbo.Value.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pyodbc

from api.v1.errors import EntityNotFoundError
from . import value_repository

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


# ---------------------------------------------------------------------------
# Read-back (PRD-4 S4): drift since last cleaning for a maintenance Event
# ---------------------------------------------------------------------------

# How far to look on each side of the event window for a source reading. The
# "before" reading is the last sample before the maintenance; the "after" the
# first after it. ponytail: fixed 7-day margin; widen if plants clean rarely.
_READBACK_MARGIN = timedelta(days=7)


def derive_before_after(
    rows: list[dict], window_start: datetime, window_end: datetime | None
) -> dict:
    """Split source-stream *rows* around a maintenance window into before/after.

    ``before`` = the last reading strictly before ``window_start``; ``after`` =
    the first reading strictly after ``window_end`` (or ``window_start`` when
    the event is instantaneous). ``percent_diff`` = 100·(after−before)/before,
    or None when either side or a non-zero baseline is missing.
    """
    before = None
    after = None
    for r in rows:
        ts = r["timestamp"]
        val = r["value"]
        if ts < window_start:
            if before is None or ts > before["timestamp"]:
                before = {"timestamp": ts, "value": val}
        elif window_end is not None and ts <= window_end:
            continue  # inside the spanning maintenance window → neither side
        else:
            # At/after an instantaneous event, or strictly after a span's end.
            if after is None or ts < after["timestamp"]:
                after = {"timestamp": ts, "value": val}

    percent_diff = None
    if (
        before is not None and after is not None
        and before["value"] not in (None, 0)
        and after["value"] is not None
    ):
        percent_diff = (after["value"] - before["value"]) / before["value"] * 100.0
    return {"before": before, "after": after, "percent_diff": percent_diff}


def _find_drift_for_event(conn: pyodbc.Connection, event_id: int) -> dict | None:
    """Find the drift Channel + source channel linked to *event_id*, or None.

    The link lives in the maintenance_drift ProcessingStep's MethodParameters
    JSON (``event_ids`` + ``source_channel_id``); the derived Channel points
    back to the step via ``ProducedByStep_ID``.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ps.[ProcessingStep_ID], ps.[MethodParameters], c.[Stream_ID]
        FROM [dbo].[ProcessingStep] ps
        JOIN [dbo].[Channel] c ON c.[ProducedByStep_ID] = ps.[ProcessingStep_ID]
        WHERE ps.[MethodName] = 'maintenance_drift'
        ORDER BY ps.[ProcessingStep_ID] DESC
        """
    )
    for step_id, method_params, drift_channel_id in cursor.fetchall():
        try:
            params = json.loads(method_params) if method_params else {}
        except (ValueError, TypeError):
            continue
        if event_id in (params.get("event_ids") or []):
            return {
                "step_id": int(step_id),
                "drift_channel_id": int(drift_channel_id),
                "source_channel_id": params.get("source_channel_id"),
            }
    return None


def get_drift_readback(conn: pyodbc.Connection, event_id: int) -> dict:
    """Assemble the drift read-back for a maintenance Event.

    Raises :class:`EntityNotFoundError` if the event does not exist or has no
    maintenance-drift Channel linked to it.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [EventDateTimeStart], [EventDateTimeEnd] FROM [dbo].[Event] WHERE [Event_ID]=?",
        event_id,
    )
    row = cursor.fetchone()
    if row is None:
        raise EntityNotFoundError(f"Event {event_id} not found.")
    window_start, window_end = row[0], row[1]

    link = _find_drift_for_event(conn, event_id)
    if link is None:
        raise EntityNotFoundError(f"No maintenance-drift Channel linked to Event {event_id}.")

    # Read the source stream in a bounded window around the event and derive.
    from_dt = window_start - _READBACK_MARGIN
    to_dt = (window_end or window_start) + _READBACK_MARGIN
    source_rows = value_repository.get_scalar_values(
        conn, link["source_channel_id"], from_dt, to_dt
    )
    derived = derive_before_after(source_rows, window_start, window_end)

    return {
        "event_id": event_id,
        "drift_channel_id": link["drift_channel_id"],
        "source_channel_id": link["source_channel_id"],
        "window_start": window_start,
        "window_end": window_end,
        **derived,
    }
