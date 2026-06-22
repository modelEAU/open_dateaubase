"""FastAPI application entry point for the open_datEAUbase API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import settings
from .logging_config import configure_logging
from .observability import RequestTimingMiddleware
from .v1.errors import EntityNotFoundError
from .v1.router import router as v1_router

configure_logging()

# Create upload directories on startup
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.upload_base_dir, "sampling_points").mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Emit one structured JSON timing line per request (consumed by Vector ->
# OpenObserve performance dashboard).
app.add_middleware(RequestTimingMiddleware)

app.include_router(v1_router, prefix="/api/v1")


@app.exception_handler(EntityNotFoundError)
def _entity_not_found_handler(_: Request, exc: EntityNotFoundError) -> JSONResponse:
    """Map repository-layer not-found errors to HTTP 404."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/", tags=["root"])
def root():
    """API root — links to documentation and health check."""
    return {
        "message": f"{settings.api_title} is running.",
        "docs": "/docs",
        "health": "/api/v1/health",
        "schema_version": settings.schema_version,
    }
