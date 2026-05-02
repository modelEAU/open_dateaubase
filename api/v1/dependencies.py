"""Shared FastAPI dependencies.

Import ``audit_repo`` and ``current_user`` from here so future endpoints
don't need to duplicate the dependency wiring.
"""

from __future__ import annotations

from fastapi import Depends

from api.database import get_db
from .endpoints.auth import get_current_user
from .repositories.audit_repository import AuditRepository


def get_audit_repo(conn=Depends(get_db)) -> AuditRepository:
    return AuditRepository(conn)


__all__ = ["get_audit_repo", "get_current_user"]
