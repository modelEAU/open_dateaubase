"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.config import settings
from api.database import get_db

router = APIRouter()


@router.get("/health")
def health(conn=Depends(get_db)):
    """Returns API and database health status."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 [Version] FROM [dbo].[SchemaVersion] ORDER BY [AppliedAt] DESC"
        )
        row = cursor.fetchone()
        schema_version = row[0] if row else "unknown"
        return {
            "status": "ok",
            "db": "connected",
            "schema_version": schema_version,
            "api_version": settings.api_version,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": f"error: {exc}", "api_version": settings.api_version},
        )
