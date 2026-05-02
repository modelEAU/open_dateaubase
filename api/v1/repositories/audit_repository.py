"""Repository for audit log queries."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import pyodbc


class AuditRepository:
    def __init__(self, conn: pyodbc.Connection):
        self.conn = conn

    def log(
        self,
        action: str,
        resource_type: str,
        *,
        user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Insert one audit log entry. Silently ignores DB errors so that a
        logging failure never breaks the main operation."""
        details_json = json.dumps(details, default=str) if details else None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO dbo.[AuditLog]
                    ([UserAccount_ID], [Action], [ResourceType], [ResourceID], [Details])
                VALUES (?, ?, ?, ?, ?)
                """,
                user_id,
                action,
                resource_type,
                resource_id,
                details_json,
            )
            self.conn.commit()
            cursor.close()
        except Exception:
            pass

    def list_logs(
        self,
        *,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        filters: list[str] = []
        params: list[Any] = []

        if user_id is not None:
            filters.append("[UserAccount_ID] = ?")
            params.append(user_id)
        if action:
            filters.append("[Action] = ?")
            params.append(action)
        if resource_type:
            filters.append("[ResourceType] = ?")
            params.append(resource_type)
        if from_dt:
            filters.append("[Timestamp] >= ?")
            params.append(from_dt)
        if to_dt:
            filters.append("[Timestamp] <= ?")
            params.append(to_dt)

        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        params += [limit, offset]

        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT
                al.[AuditLog_ID],
                al.[UserAccount_ID],
                ua.[FullName],
                ua.[Email],
                al.[Action],
                al.[ResourceType],
                al.[ResourceID],
                al.[Details],
                al.[Timestamp]
            FROM dbo.[AuditLog] al
            LEFT JOIN dbo.[UserAccount] ua
                ON ua.[UserAccount_ID] = al.[UserAccount_ID]
            {where}
            ORDER BY al.[Timestamp] DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """,
            *params,
        )
        rows = cursor.fetchall()
        cursor.close()

        return [
            {
                "audit_log_id": r[0],
                "user_id": r[1],
                "full_name": r[2],
                "email": r[3],
                "action": r[4],
                "resource_type": r[5],
                "resource_id": r[6],
                "details": json.loads(r[7]) if r[7] else None,
                "timestamp": r[8],
            }
            for r in rows
        ]

    def count_logs(
        self,
        *,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> int:
        filters: list[str] = []
        params: list[Any] = []

        if user_id is not None:
            filters.append("[UserAccount_ID] = ?")
            params.append(user_id)
        if action:
            filters.append("[Action] = ?")
            params.append(action)
        if resource_type:
            filters.append("[ResourceType] = ?")
            params.append(resource_type)
        if from_dt:
            filters.append("[Timestamp] >= ?")
            params.append(from_dt)
        if to_dt:
            filters.append("[Timestamp] <= ?")
            params.append(to_dt)

        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM dbo.[AuditLog] {where}", *params)
        count = cursor.fetchone()[0]
        cursor.close()
        return count
