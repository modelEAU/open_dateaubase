#!/usr/bin/env python3
"""Initialize the open_dateaubase schema and seed data.

Applies the v1.0.0 baseline and the consolidated v1.0.0→v2.1.0 migration,
then seeds test data.  Safe to re-run: skips steps already recorded in
SchemaVersion.

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
# Migration steps — (label, migration_file, seed_file | None)
# SchemaVersion is created by the v2.1.0 migration, so we check for it
# after applying that step.
# ---------------------------------------------------------------------------

_BASELINE = ROOT / "migrations" / "v1.0.0_create_mssql.sql"
_MIGRATION = ROOT / "migrations" / "v1.0.0_to_v2.1.0_mssql.sql"
_SEED = ROOT / "sql" / "seed_v2.1.0.sql"

TARGET_VERSION = "2.1.0"


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
        f"IF DB_ID(N'{_DB}') IS NULL CREATE DATABASE [{_DB}];"
    )
    master_conn.close()
    print(f"Database '{_DB}' is ready.")

    # ------------------------------------------------------------------
    # 2. Connect to the application database
    # ------------------------------------------------------------------
    conn = _connect(_APP_DSN)
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # 3. Check current schema version
    # ------------------------------------------------------------------
    applied: set[str] = set()
    try:
        cursor.execute("SELECT [Version] FROM [dbo].[SchemaVersion]")
        applied = {row[0] for row in cursor.fetchall()}
        print(f"Already applied: {sorted(applied)}")
    except Exception:
        print("SchemaVersion table not found; applying from scratch.")
    conn.commit()

    if TARGET_VERSION in applied:
        print(f"Schema is already at v{TARGET_VERSION}. Nothing to do.")
    else:
        # ------------------------------------------------------------------
        # 4a. Apply v1.0.0 baseline if SchemaVersion not yet present
        #     (means we're starting from an empty DB)
        # ------------------------------------------------------------------
        if not applied:
            print(f"  apply baseline v1.0.0…")
            if _BASELINE.exists():
                _run_sql_file(_BASELINE, conn)
                print(f"  baseline done.")
            else:
                print(f"  ERROR: baseline file not found: {_BASELINE}", file=sys.stderr)
                sys.exit(1)

        # ------------------------------------------------------------------
        # 4b. Apply the consolidated v1.0.0 → v2.1.0 migration
        # ------------------------------------------------------------------
        print(f"  apply migration v1.0.0 → v{TARGET_VERSION}…")
        if _MIGRATION.exists():
            _run_sql_file(_MIGRATION, conn)
            print(f"  migration done.")
        else:
            print(f"  ERROR: migration file not found: {_MIGRATION}", file=sys.stderr)
            sys.exit(1)

        # ------------------------------------------------------------------
        # 4c. Apply seed data
        # ------------------------------------------------------------------
        print(f"  apply seed data…")
        if _SEED.exists():
            _run_sql_file(_SEED, conn)
            print(f"  seed done.")
        else:
            print(f"  WARNING: seed file not found: {_SEED}")

    # ------------------------------------------------------------------
    # 5. Report final state
    # ------------------------------------------------------------------
    cursor = conn.cursor()
    cursor.execute("SELECT [Version], [AppliedDateTime], [Description] FROM [dbo].[SchemaVersion] ORDER BY [AppliedDateTime]")
    versions = [(r[0], r[1], r[2]) for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) FROM [dbo].[Channel]")
    n_channel = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM [dbo].[Value]")
    n_val = cursor.fetchone()[0]

    conn.close()

    print(f"\nSchema versions applied:")
    for v, applied_at, desc in versions:
        print(f"  {v}  ({applied_at})  {desc}")
    print(f"\nChannel rows: {n_channel}  |  Value rows: {n_val}")
    print("Database initialised successfully.")


if __name__ == "__main__":
    main()
