#!/usr/bin/env python3
"""Initialize the open_dateaubase schema and seed data.

Applies all migrations and seed files in version order, using
SchemaVersion to skip steps that are already applied.  Safe to run
against a fresh container (schema does not exist yet) or a partially
initialised one.

Usage
-----
    uv run python scripts/init_db.py [--server localhost,14330]

Environment variables (override defaults)
------------------------------------------
    DB_SERVER   e.g. "localhost,14330"  (default: localhost,14330)
    DB_NAME     e.g. "open_dateaubase" (default: open_dateaubase)
    DB_USER     e.g. "SA"              (default: SA)
    DB_PASSWORD e.g. "StrongPwd123!"  (default: StrongPwd123!)
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

_SERVER = os.getenv("DB_SERVER", "localhost,14330")
_DB = os.getenv("DB_NAME", "open_dateaubase")
_USER = os.getenv("DB_USER", "SA")
_PWD = os.getenv("DB_PASSWORD", "StrongPwd123!")

_MASTER_DSN = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={_SERVER};"
    f"DATABASE=master;"
    f"UID={_USER};"
    f"PWD={_PWD};"
    f"TrustServerCertificate=yes;"
)

_APP_DSN = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={_SERVER};"
    f"DATABASE={_DB};"
    f"UID={_USER};"
    f"PWD={_PWD};"
    f"TrustServerCertificate=yes;"
)


def _connect(dsn: str, retries: int = 30, delay: float = 2.0):
    """Connect with retries (SQL Server takes a few seconds to start)."""
    import pyodbc

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            conn = pyodbc.connect(dsn, timeout=5, autocommit=False)
            return conn
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                print(f"  waiting for SQL Server ({attempt}/{retries})…", flush=True)
                time.sleep(delay)
    raise RuntimeError(f"Cannot connect after {retries} attempts") from last_exc


def _run_sql_file(path: Path, conn) -> None:
    """Execute a .sql file against *conn*, splitting on GO."""
    sql = path.read_text(encoding="utf-8")
    batches = re.split(r"^\s*GO\s*$", sql, flags=re.MULTILINE | re.IGNORECASE)
    cursor = conn.cursor()
    for batch in batches:
        batch = batch.strip()
        if batch:
            cursor.execute(batch)
    conn.commit()


# ---------------------------------------------------------------------------
# Ordered list of (schema_version, migration_file, seed_file)
# ---------------------------------------------------------------------------

_STEPS: list[tuple[str, Path | None, Path | None]] = [
    (
        "1.0.0",
        ROOT / "migrations" / "v1.0.0_create_mssql.sql",
        ROOT / "sql" / "seed_v1.0.0.sql",
    ),
    (
        "1.0.1",
        ROOT / "migrations" / "v1.0.0_to_v1.0.1_mssql.sql",
        ROOT / "sql" / "seed_v1.0.1.sql",
    ),
    (
        "1.0.2",
        ROOT / "migrations" / "v1.0.1_to_v1.0.2_mssql.sql",
        ROOT / "sql" / "seed_v1.0.2.sql",
    ),
    (
        "1.1.0",
        ROOT / "migrations" / "v1.0.2_to_v1.1.0_mssql.sql",
        ROOT / "sql" / "seed_v1.1.0.sql",
    ),
]


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        import pyodbc  # noqa: F401
    except ImportError:
        print("ERROR: pyodbc not installed. Run: uv sync --extra db", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # 1. Ensure the database exists (connect to master)
    # ------------------------------------------------------------------
    print(f"Connecting to SQL Server at {_SERVER}…")
    master_conn = _connect(_MASTER_DSN)
    master_conn.autocommit = True
    cursor = master_conn.cursor()
    cursor.execute(
        "IF DB_ID(N'open_dateaubase') IS NULL CREATE DATABASE [open_dateaubase];"
    )
    master_conn.close()
    print(f"Database '{_DB}' is ready.")

    # ------------------------------------------------------------------
    # 2. Connect to open_dateaubase
    # ------------------------------------------------------------------
    conn = _connect(_APP_DSN)

    # ------------------------------------------------------------------
    # 3. Find which versions are already applied
    # ------------------------------------------------------------------
    cursor = conn.cursor()
    applied: set[str] = set()
    try:
        cursor.execute("SELECT [Version] FROM [dbo].[SchemaVersion]")
        applied = {row[0] for row in cursor.fetchall()}
        print(f"Already applied: {sorted(applied)}")
    except Exception:
        # SchemaVersion table doesn't exist yet — that's fine
        print("SchemaVersion table not found; applying from scratch.")
    conn.commit()

    # ------------------------------------------------------------------
    # 4. Apply each step that is not yet recorded
    # ------------------------------------------------------------------
    for version, migration, seed in _STEPS:
        if version in applied:
            print(f"  skip  v{version} (already applied)")
            continue

        print(f"  apply v{version}…")
        if migration and migration.exists():
            _run_sql_file(migration, conn)
        elif migration:
            print(f"    WARNING: migration file not found: {migration}")

        if seed and seed.exists():
            _run_sql_file(seed, conn)
        elif seed:
            print(f"    WARNING: seed file not found: {seed}")

        print(f"  v{version} done.")

    # ------------------------------------------------------------------
    # 5. Report final state
    # ------------------------------------------------------------------
    cursor = conn.cursor()
    cursor.execute("SELECT [Version] FROM [dbo].[SchemaVersion] ORDER BY [AppliedAt]")
    versions = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) FROM [dbo].[MetaData]")
    n_meta = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM [dbo].[Value]")
    n_val = cursor.fetchone()[0]
    conn.close()

    print(f"\nSchema versions applied: {versions}")
    print(f"MetaData rows: {n_meta}  |  Value rows: {n_val}")
    print("Database initialised successfully.")


if __name__ == "__main__":
    main()
