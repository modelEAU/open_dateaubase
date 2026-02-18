"""Database connection management for the open_datEAUbase API.

All endpoints call get_connection() to obtain a raw pyodbc connection.
Callers are responsible for closing the connection (use try/finally or
FastAPI dependency injection via get_db()).
"""

from __future__ import annotations

import pyodbc
from fastapi import HTTPException

from .config import settings


def get_connection() -> pyodbc.Connection:
    """Return a new pyodbc connection to SQL Server.

    Raises:
        HTTPException(503): If the connection cannot be established.
    """
    if not all([settings.db_host, settings.db_name, settings.db_user, settings.db_password]):
        missing = [
            k
            for k, v in {
                "DB_HOST": settings.db_host,
                "DB_NAME": settings.db_name,
                "DB_USER": settings.db_user,
                "DB_PASSWORD": settings.db_password,
            }.items()
            if not v
        ]
        raise HTTPException(
            status_code=503,
            detail=f"Database not configured. Missing env vars: {', '.join(missing)}",
        )

    conn_str = (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=10;"
    )
    try:
        return pyodbc.connect(conn_str)
    except pyodbc.Error as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to database: {exc}",
        ) from exc


def get_db():
    """FastAPI dependency that yields a connection and closes it after the request."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
