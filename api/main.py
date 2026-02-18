"""FastAPI application entry point for the open_datEAUbase API."""

from __future__ import annotations

from fastapi import FastAPI

from .config import settings
from .v1.router import router as v1_router

app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/", tags=["root"])
def root():
    """API root — links to documentation and health check."""
    return {
        "message": f"{settings.api_title} is running.",
        "docs": "/docs",
        "health": "/api/v1/health",
        "schema_version": settings.schema_version,
    }
