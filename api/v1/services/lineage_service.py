"""Service wrapping open_dateaubase.lineage and meteaudata_bridge.

Provides HTTP-friendly error handling around the low-level lineage functions.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pyodbc
from fastapi import HTTPException

from open_dateaubase.lineage import (
    get_full_lineage_tree,
    get_lineage_backward,
    get_lineage_forward,
)
from open_dateaubase.meteaudata_bridge import record_processing


def forward_lineage(conn: pyodbc.Connection, channel_id: int) -> list[dict]:
    return get_lineage_forward(channel_id, conn)


def backward_lineage(conn: pyodbc.Connection, channel_id: int) -> list[dict]:
    return get_lineage_backward(channel_id, conn)


def full_lineage_tree(conn: pyodbc.Connection, channel_id: int) -> dict:
    return get_full_lineage_tree(channel_id, conn)


def persist_processing(
    conn: pyodbc.Connection,
    *,
    source_metadata_ids: list[int],
    method_name: str,
    method_version: str | None,
    processing_kind_id: int,
    method_parameters: dict,
    executed_at: datetime | None,
    executed_by_person_id: int | None,
) -> int:
    """Insert ProcessingStep + ProcessingLineage input edges.

    Returns the ProcessingStep_ID.
    The caller is responsible for creating the output Channel with
    ProducedByStep_ID pointing to the returned step_id.
    Raises HTTPException(500) on unexpected DB error.
    """
    effective_executed_at = executed_at or datetime.now(tz=timezone.utc)
    try:
        return record_processing(
            source_metadata_ids=source_metadata_ids,
            method_name=method_name,
            method_version=method_version,
            processing_kind_id=processing_kind_id,
            method_parameters=method_parameters,
            executed_at=effective_executed_at,
            executed_by_person_id=executed_by_person_id,
            conn=conn,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record processing lineage: {exc}",
        ) from exc
