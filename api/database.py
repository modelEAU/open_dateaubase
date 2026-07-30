"""Database connection management for the open_datEAUbase API.

Connections are served from a process-wide SQLAlchemy ``QueuePool`` rather than
opened per request. ``pool_pre_ping`` validates a pooled connection before
handing it out (SQL Server idle-closes connections), and ``pool_recycle`` caps
connection age. ``get_db()`` yields a raw DBAPI (pyodbc-compatible) connection,
so repository code that calls ``conn.cursor()`` / ``conn.commit()`` is unchanged.

Closing a yielded connection returns it to the pool instead of tearing down the
TCP/auth session, which is what eliminates the ~400ms cold-connect cost that was
paid on every lookup request.
"""

from __future__ import annotations

import time
import urllib.parse
from contextlib import contextmanager
from typing import Iterator

from fastapi import HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .config import settings

# Process-wide engine, created lazily on first use (see get_engine).
_engine: Engine | None = None


def _build_odbc_str() -> str:
    """Assemble the ODBC connection string from settings.

    Single source of truth for the connection string so network/driver tweaks
    (instance vs port, Encrypt, etc.) live in one place.
    """
    return (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=10;"
    )


def _assert_configured() -> None:
    """Raise HTTPException(503) if required DB env vars are missing."""
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


def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine, creating it on first use."""
    global _engine
    if _engine is None:
        _assert_configured()
        url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(_build_odbc_str())
        _engine = create_engine(
            url,
            pool_pre_ping=True,  # validate a pooled connection before handing it out
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,  # recycle connections older than 30 min
            pool_timeout=30,
        )
    return _engine


def get_connection():
    """Return a pooled raw DBAPI (pyodbc-compatible) connection.

    Raises:
        HTTPException(503): If the DB is unconfigured or unreachable.

    Callers must close the connection (which returns it to the pool).
    """
    _assert_configured()
    try:
        return get_engine().raw_connection()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to database: {exc}",
        ) from exc


class _DeferredCommit:
    """A connection whose ``commit`` the surrounding transaction performs instead."""

    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def commit(self) -> None:
        """Deliberately nothing — ``transaction`` commits once, at the end."""


@contextmanager
def transaction(conn) -> Iterator:
    """Run several repository calls as one all-or-nothing write.

    The repository functions commit as they go, which is right for a single
    write and wrong for a batch: half an import must never survive. Give them
    the connection this yields instead — their commits are held back, and one
    commit lands when the block ends, or everything rolls back.
    """
    try:
        yield _DeferredCommit(conn)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


def get_db(request: Request = None) -> Iterator:
    """FastAPI dependency: yield a pooled connection, then return it to the pool.

    Records the time spent acquiring the connection on ``request.state``
    (``db_connect_ms``) so the request-timing middleware can log it. This is high
    on a genuine cold connect and ~0 when a connection is reused from the pool,
    which is exactly the signal we use to confirm pooling is working.
    """
    start = time.perf_counter()
    conn = get_connection()
    connect_ms = round((time.perf_counter() - start) * 1000, 1)
    if request is not None:
        prior = getattr(request.state, "db_connect_ms", 0.0) or 0.0
        request.state.db_connect_ms = round(prior + connect_ms, 1)
    try:
        yield conn
    finally:
        conn.close()
