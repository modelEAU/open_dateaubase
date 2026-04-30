"""v1 API router."""

from __future__ import annotations

from fastapi import APIRouter

from .endpoints.auth import router as auth_router
from .endpoints.health import router as health_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(health_router, tags=["health"])
