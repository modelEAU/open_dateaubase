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


def forward_lineage(conn: pyodbc.Connection, metadata_id: int) -> list[dict]:
    return get_lineage_forward(metadata_id, conn)


def backward_lineage(conn: pyodbc.Connection, metadata_id: int) -> list[dict]:
    return get_lineage_backward(metadata_id, conn)


def full_lineage_tree(conn: pyodbc.Connection, metadata_id: int) -> dict:
    return get_full_lineage_tree(metadata_id, conn)


def persist_processing(
    conn: pyodbc.Connection,
    *,
    source_metadata_ids: list[int],
    method_name: str,
    method_version: str | None,
    processing_type: str,
    parameters: dict,
    executed_at: datetime | None,
    executed_by_person_id: int | None,
    output_metadata_id: int,
) -> int:
    """Insert ProcessingStep + DataLineage rows.

    Returns the ProcessingStep_ID.
    Raises HTTPException(500) on unexpected DB error.
    """
    effective_executed_at = executed_at or datetime.now(tz=timezone.utc)
    try:
        return record_processing(
            source_metadata_ids=source_metadata_ids,
            method_name=method_name,
            method_version=method_version,
            processing_type=processing_type,
            parameters=parameters,
            executed_at=effective_executed_at,
            executed_by_person_id=executed_by_person_id,
            output_metadata_id=output_metadata_id,
            conn=conn,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record processing lineage: {exc}",
        ) from exc
