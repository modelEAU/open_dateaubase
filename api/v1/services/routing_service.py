"""Service for IngestionRoute resolution.

Wraps ingestion_repository with HTTP-friendly error translation.
"""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import HTTPException

from ..repositories.ingestion_repository import (
    RouteAmbiguous,
    RouteNotFound,
    resolve_ingestion_route,
)


def resolve_route(
    conn: pyodbc.Connection,
    equipment_id: int,
    parameter_id: int,
    data_provenance_id: int,
    processing_degree: str,
    timestamp: datetime,
) -> int:
    """Resolve IngestionRoute to a Metadata_ID.

    Raises HTTPException(400) if no route or ambiguous routes found.
    """
    try:
        return resolve_ingestion_route(
            conn,
            equipment_id,
            parameter_id,
            data_provenance_id,
            processing_degree,
            timestamp,
        )
    except RouteNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RouteAmbiguous as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
