"""Shared fixtures for database integration tests.

Requires a running MSSQL container (docker compose up -d db).
Tests are automatically skipped if the container is not available.
"""

import re
import struct
import uuid
from datetime import datetime, timedelta, timezone

import pytest

try:
    import pyodbc

    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False


def _handle_datetimeoffset(dto_value: bytes) -> datetime:
    """Convert SQL Server DATETIMEOFFSET bytes to a timezone-aware Python datetime.

    pyodbc does not natively support DATETIMEOFFSET (ODBC type -155).
    SQL Server sends it as a 20-byte SQL_SS_TIMESTAMPOFFSET_STRUCT:
      year(2s) month(2s) day(2s) hour(2s) minute(2s) second(2s)
      fraction_ns(4u) tz_hour(2s) tz_minute(2s)
    fraction_ns is in nanoseconds; Python datetime has microsecond precision.
    """
    tup = struct.unpack("<6hI2h", dto_value)
    year, month, day, hour, minute, second = tup[:6]
    microsecond = tup[6] // 1000  # nanoseconds → microseconds
    tz_hour, tz_minute = tup[7], tup[8]
    tz = timezone(timedelta(hours=tz_hour, minutes=tz_minute))
    return datetime(year, month, day, hour, minute, second, microsecond, tz)

# Connection parameters matching docker-compose.yml
MSSQL_HOST = "127.0.0.1"
MSSQL_PORT = 14330
MSSQL_USER = "SA"
MSSQL_PASSWORD = "StrongPwd123!"
MSSQL_DRIVER = "{ODBC Driver 18 for SQL Server}"

# Paths to SQL files (relative to project root)
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
SEED_DIR = PROJECT_ROOT / "sql"

SQL_FILES = {
    "v1.0.0_create": MIGRATIONS_DIR / "v1.0.0_create_mssql.sql",
    "v1.0.0_to_v1.0.1": MIGRATIONS_DIR / "v1.0.0_to_v1.0.1_mssql.sql",
    "v1.0.1_to_v1.0.2": MIGRATIONS_DIR / "v1.0.1_to_v1.0.2_mssql.sql",
    "v1.0.2_to_v1.1.0": MIGRATIONS_DIR / "v1.0.2_to_v1.1.0_mssql.sql",
    "rollback_v1.0.1": MIGRATIONS_DIR / "v1.0.0_to_v1.0.1_mssql_rollback.sql",
    "rollback_v1.0.2": MIGRATIONS_DIR / "v1.0.1_to_v1.0.2_mssql_rollback.sql",
    "rollback_v1.1.0": MIGRATIONS_DIR / "v1.0.2_to_v1.1.0_mssql_rollback.sql",
    "seed_v1.0.0": SEED_DIR / "seed_v1.0.0.sql",
    "seed_v1.0.1": SEED_DIR / "seed_v1.0.1.sql",
    "seed_v1.0.2": SEED_DIR / "seed_v1.0.2.sql",
    "seed_v1.1.0": SEED_DIR / "seed_v1.1.0.sql",
}


def _connect_string(database: str = "master") -> str:
    return (
        f"DRIVER={MSSQL_DRIVER};"
        f"SERVER={MSSQL_HOST},{MSSQL_PORT};"
        f"DATABASE={database};"
        f"UID={MSSQL_USER};"
        f"PWD={MSSQL_PASSWORD};"
        "TrustServerCertificate=yes;"
    )


def run_sql_file(conn: "pyodbc.Connection", filepath: Path) -> None:
    """Execute a SQL file against the given connection.

    Splits on GO batch separators and executes each batch separately,
    which is required for MSSQL scripts that use DDL mixed with DML.
    """
    sql = filepath.read_text(encoding="utf-8")

    # Split on GO as a standalone batch separator (line by itself or with whitespace)
    batches = re.split(r"^\s*GO\s*$", sql, flags=re.MULTILINE | re.IGNORECASE)

    cursor = conn.cursor()
    for batch in batches:
        batch = batch.strip()
        if not batch:
            continue
        # Skip sqlcmd directives (:r, :setvar, etc.)
        if batch.startswith(":"):
            continue
        cursor.execute(batch)
    conn.commit()


def get_table_row_count(conn: "pyodbc.Connection", table: str) -> int:
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM [dbo].[{table}]")
    return cursor.fetchone()[0]


def get_table_names(conn: "pyodbc.Connection") -> set[str]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = 'dbo' AND TABLE_TYPE = 'BASE TABLE'"
    )
    return {row[0] for row in cursor.fetchall()}


def get_column_type(
    conn: "pyodbc.Connection", table: str, column: str
) -> str:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND COLUMN_NAME = ?",
        table,
        column,
    )
    row = cursor.fetchone()
    return row[0] if row else ""


def column_exists(conn: "pyodbc.Connection", table: str, column: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? AND COLUMN_NAME = ?",
        table,
        column,
    )
    return cursor.fetchone() is not None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mssql_engine():
    """Session-scoped fixture that verifies MSSQL connectivity.

    Returns a callable that creates new connections to a given database.
    Skips the entire session if the container is not reachable.
    """
    if not PYODBC_AVAILABLE:
        pytest.skip("pyodbc not installed (install with: uv sync --extra db)")

    try:
        conn = pyodbc.connect(_connect_string("master"), timeout=5, autocommit=True)
        conn.close()
    except (pyodbc.Error, OSError):
        pytest.skip("MSSQL container not running (start with: docker compose up -d db)")

    def connect(database: str = "master") -> "pyodbc.Connection":
        conn = pyodbc.connect(
            _connect_string(database), timeout=10, autocommit=True
        )
        # pyodbc does not natively support DATETIMEOFFSET (ODBC type -155)
        conn.add_output_converter(-155, _handle_datetimeoffset)
        return conn

    return connect


@pytest.fixture()
def fresh_db(mssql_engine):
    """Create a uniquely-named test database, yield it, then drop it."""
    db_name = f"test_{uuid.uuid4().hex[:8]}"

    master_conn = mssql_engine("master")
    master_conn.execute(f"CREATE DATABASE [{db_name}]")

    db_conn = mssql_engine(db_name)
    yield db_conn, db_name

    db_conn.close()
    # Force-close any remaining connections before dropping
    master_conn.execute(
        f"ALTER DATABASE [{db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE"
    )
    master_conn.execute(f"DROP DATABASE [{db_name}]")
    master_conn.close()


def _apply_schema_and_seeds(
    conn: "pyodbc.Connection", steps: list[str]
) -> None:
    """Apply a sequence of SQL file keys from SQL_FILES."""
    for key in steps:
        run_sql_file(conn, SQL_FILES[key])


@pytest.fixture()
def db_at_v100(fresh_db):
    """Database at v1.0.0 with baseline sample data."""
    conn, db_name = fresh_db
    _apply_schema_and_seeds(conn, ["v1.0.0_create", "seed_v1.0.0"])
    yield conn, db_name


@pytest.fixture()
def db_at_v101(fresh_db):
    """Database migrated to v1.0.1 with all sample data."""
    conn, db_name = fresh_db
    _apply_schema_and_seeds(
        conn,
        ["v1.0.0_create", "seed_v1.0.0", "v1.0.0_to_v1.0.1", "seed_v1.0.1"],
    )
    yield conn, db_name


@pytest.fixture()
def db_at_v102(fresh_db):
    """Database migrated to v1.0.2 with all sample data."""
    conn, db_name = fresh_db
    _apply_schema_and_seeds(
        conn,
        [
            "v1.0.0_create",
            "seed_v1.0.0",
            "v1.0.0_to_v1.0.1",
            "seed_v1.0.1",
            "v1.0.1_to_v1.0.2",
            "seed_v1.0.2",
        ],
    )
    yield conn, db_name


@pytest.fixture()
def db_at_v110(fresh_db):
    """Database migrated to v1.1.0 with all sample data."""
    conn, db_name = fresh_db
    _apply_schema_and_seeds(
        conn,
        [
            "v1.0.0_create",
            "seed_v1.0.0",
            "v1.0.0_to_v1.0.1",
            "seed_v1.0.1",
            "v1.0.1_to_v1.0.2",
            "seed_v1.0.2",
            "v1.0.2_to_v1.1.0",
            "seed_v1.1.0",
        ],
    )
    yield conn, db_name
