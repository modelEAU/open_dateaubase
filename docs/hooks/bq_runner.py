"""Business query runner for MkDocs documentation generation.

Connects to the open_dateaubase MSSQL instance (if available) and executes
SQL queries, returning results as Markdown tables.

Fails gracefully if the database is not running — the docs build still
succeeds but result cells show a notice instead of live data.
"""

from __future__ import annotations

import struct as _struct


def _datetimeoffset_converter(raw: bytes) -> str:
    """Convert raw DATETIMEOFFSET bytes (ODBC type -155) to an ISO-8601 string.

    SQL Server sends 20 bytes:
      year(2), month(2), day(2), hour(2), minute(2), second(2)  — 6 × uint16 LE
      nanoseconds(4)                                             — uint32 LE
      tz_hour(2), tz_minute(2)                                  — 2 × int16 LE
    """
    year, month, day, hour, minute, second = _struct.unpack_from("<6H", raw, 0)
    ns = _struct.unpack_from("<I", raw, 12)[0]
    tz_hour, tz_min = _struct.unpack_from("<2h", raw, 16)
    sign = "+" if tz_hour >= 0 else "-"
    return (
        f"{year:04d}-{month:02d}-{day:02d}"
        f"T{hour:02d}:{minute:02d}:{second:02d}.{ns:07d}"
        f"{sign}{abs(tz_hour):02d}:{abs(tz_min):02d}"
    )


_CONNECT_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost,14330;"
    "DATABASE=open_dateaubase;"
    "UID=SA;"
    "PWD=StrongPwd123!;"
    "TrustServerCertificate=yes;"
)

_TIMEOUT = 3  # seconds — short so docs build doesn't hang waiting for DB


def _to_markdown_table(columns: list[str], rows: list) -> str:
    """Format query results as a GFM Markdown table string."""
    str_rows = [[str(v) if v is not None else "NULL" for v in row] for row in rows]
    widths = [len(c) for c in columns]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(cells: list[str]) -> str:
        return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"

    divider = "| " + " | ".join("-" * w for w in widths) + " |"
    return "\n".join([fmt(columns), divider] + [fmt(r) for r in str_rows])


def make_runner() -> tuple:
    """Return ``(run_bq, run_ic)`` callables.

    ``run_bq(sql)`` executes *sql* and returns a Markdown table string, or a
    fallback notice if the database is unavailable.

    ``run_ic(sql)`` wraps ``run_bq``: if the query returns 0 rows (expected
    for all integrity checks) it returns a green pass message; otherwise it
    returns the violation rows as a table.

    Both callables are safe to use in ``markdown-exec`` sessions regardless
    of whether ``pyodbc`` is installed or the container is running.
    """
    _NO_PYODBC = (
        "> *Live results unavailable — `pyodbc` not installed.*  \n"
        "> *Run `uv sync --extra db` then restart `mkdocs serve`.*"
    )
    _NO_DB = (
        "> *Live results unavailable — MSSQL container not running.*  \n"
        "> *Start with `docker compose up -d db` then restart `mkdocs serve`.*"
    )

    try:
        import pyodbc
    except ImportError:
        def _run_bq(sql: str) -> str:  # noqa: E306
            return _NO_PYODBC

        def _run_ic(sql: str) -> str:
            return _NO_PYODBC

        return _run_bq, _run_ic

    try:
        _test = pyodbc.connect(_CONNECT_STRING, timeout=_TIMEOUT, autocommit=True)
        _test.add_output_converter(-155, _datetimeoffset_converter)
        _test.close()
    except Exception:
        def _run_bq(sql: str) -> str:  # noqa: E306
            return _NO_DB

        def _run_ic(sql: str) -> str:
            return _NO_DB

        return _run_bq, _run_ic

    def run_bq(sql: str) -> str:
        try:
            conn = pyodbc.connect(_CONNECT_STRING, timeout=_TIMEOUT, autocommit=True)
            conn.add_output_converter(-155, _datetimeoffset_converter)
            cursor = conn.cursor()
            cursor.execute(sql.strip())
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            conn.close()
            if not rows:
                return "_No rows returned._"
            return _to_markdown_table(cols, rows)
        except Exception as exc:
            return f"> ⚠ Query error: `{exc}`"

    def run_ic(sql: str) -> str:
        result = run_bq(sql)
        if result == "_No rows returned._":
            return "✓ **No violations found.**"
        return f"⚠ **Violations detected:**\n\n{result}"

    return run_bq, run_ic
