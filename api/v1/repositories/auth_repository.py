"""Repository for authentication queries."""

from __future__ import annotations

from typing import Optional

import pyodbc


class AuthRepository:
    """Repository for authentication-related database access."""

    def __init__(self, conn: pyodbc.Connection):
        self.conn = conn

    def get_user_by_email(self, email: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                [UserAccount_ID],
                [Email],
                [FullName],
                [PasswordHash],
                [IsActive],
                [IsVerified],
                [CreatedAt],
                [UpdatedAt]
            FROM dbo.[UserAccount]
            WHERE [Email] = ?
            """,
            email,
        )
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        return {
            "user_id": row[0],
            "email": row[1],
            "full_name": row[2],
            "password_hash": row[3],
            "is_active": bool(row[4]),
            "is_verified": bool(row[5]),
            "created_at": row[6],
            "updated_at": row[7],
        }

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                [UserAccount_ID],
                [Email],
                [FullName],
                [PasswordHash],
                [IsActive],
                [IsVerified],
                [CreatedAt],
                [UpdatedAt]
            FROM dbo.[UserAccount]
            WHERE [UserAccount_ID] = ?
            """,
            user_id,
        )
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        return {
            "user_id": row[0],
            "email": row[1],
            "full_name": row[2],
            "password_hash": row[3],
            "is_active": bool(row[4]),
            "is_verified": bool(row[5]),
            "created_at": row[6],
            "updated_at": row[7],
        }

    def create_user(self, email: str, full_name: str, password_hash: str) -> dict:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO dbo.[UserAccount] (
                [Email],
                [FullName],
                [PasswordHash],
                [IsActive],
                [IsVerified]
            )
            OUTPUT
                INSERTED.[UserAccount_ID],
                INSERTED.[Email],
                INSERTED.[FullName],
                INSERTED.[IsActive],
                INSERTED.[IsVerified],
                INSERTED.[CreatedAt],
                INSERTED.[UpdatedAt]
            VALUES (?, ?, ?, 1, 1)
            """,
            email,
            full_name,
            password_hash,
        )
        row = cursor.fetchone()
        self.conn.commit()
        cursor.close()

        return {
            "user_id": row[0],
            "email": row[1],
            "full_name": row[2],
            "is_active": bool(row[3]),
            "is_verified": bool(row[4]),
            "created_at": row[5],
            "updated_at": row[6],
        }