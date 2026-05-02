"""Pydantic schemas for audit log."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AuditLogEntry(BaseModel):
    audit_log_id: int
    user_id: Optional[int]
    full_name: Optional[str]
    email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[Any]
    timestamp: datetime


class AuditLogPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuditLogEntry]
