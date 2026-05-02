"""Audit log API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.database import get_db
from ..endpoints.auth import get_current_user
from ..repositories.audit_repository import AuditRepository
from ..schemas.audit import AuditLogEntry, AuditLogPage

router = APIRouter()


def get_audit_repo(conn=Depends(get_db)) -> AuditRepository:
    return AuditRepository(conn)


@router.get("/logs", response_model=AuditLogPage)
def list_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action (CREATE, UPDATE, DELETE, LOGIN, SIGNUP)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    from_dt: Optional[datetime] = Query(None, description="Start of time range (ISO 8601)"),
    to_dt: Optional[datetime] = Query(None, description="End of time range (ISO 8601)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _current_user=Depends(get_current_user),
    audit_repo: AuditRepository = Depends(get_audit_repo),
):
    """Return a paginated list of audit log entries. Requires authentication."""
    filters = dict(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    items = audit_repo.list_logs(limit=limit, offset=offset, **filters)
    total = audit_repo.count_logs(**filters)
    return AuditLogPage(total=total, limit=limit, offset=offset, items=items)
