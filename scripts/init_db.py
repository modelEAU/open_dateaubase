from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import pyodbc

ROOT = Path("/workspace")
INIT_FILE = ROOT / "sql" / "init.sql"

DB_HOST = "db"
DB_PORT = 1433
DB_NAME = "master"
DB_USER = "SA"
DB_PASSWORD = "StrongPwd123!"
DB_DRIVER = "ODBC Driver 18 for SQL Server"


def get_connection(database: str = DB_NAME) -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_HOST},{DB_PORT};"
        f"DATABASE={database};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, autocommit=True)


def wait_for_db(max_attempts: int = 60, delay: int = 2) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with get_connection():
                print(f"Database ready after {attempt} attempt(s).")
                return
        except Exception as e:
            print(f"Waiting for DB... ({attempt}/{max_attempts}) -> {e}")
            time.sleep(delay)

    raise RuntimeError("Database did not become ready in time.")


def expand_includes(file_path: Path) -> str:
    lines: list[str] = []
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped.lower().startswith(":r "):
            include_path = stripped[3:].strip()
            include_file = (ROOT / include_path.lstrip("/")).resolve()
            if not include_file.exists():
                raise FileNotFoundError(f"Included SQL file not found: {include_file}")
            lines.append(expand_includes(include_file))
        else:
            lines.append(raw_line)
    return "\n".join(lines)


def split_batches(sql_text: str) -> list[str]:
    parts = re.split(r"(?im)^\s*GO\s*;?\s*$", sql_text)
    return [part.strip() for part in parts if part.strip()]


def execute_batches(sql_text: str) -> None:
    with get_connection("master") as conn:
        cursor = conn.cursor()
        batches = split_batches(sql_text)

        for i, batch in enumerate(batches, start=1):
            print(f"Executing batch {i}/{len(batches)}...")
            cursor.execute(batch)

        cursor.close()


def main() -> int:
    try:
        print("Waiting for SQL Server...")
        wait_for_db()

        print(f"Loading SQL from {INIT_FILE}")
        sql_text = expand_includes(INIT_FILE)

        print("Executing init.sql with expanded includes...")
        execute_batches(sql_text)

        print("Database initialization completed successfully.")
        return 0
    except Exception as e:
        print(f"Database initialization failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())