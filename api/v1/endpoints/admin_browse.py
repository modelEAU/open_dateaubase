"""Read-only generic table browser for database introspection.

Distinct from the curated CRUD endpoints: this exposes raw table *contents* so a
data steward can inspect what is actually stored, including columns the edit
forms deliberately hide. Read-only and whitelisted against the DB catalog;
sensitive tables (credentials) are never exposed.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.database import get_db

router = APIRouter()

# Tables never exposed by the browser (credentials / secrets).
_BLACKLIST = {"UserAccount"}
_DEFAULT_LIMIT = 200
_MAX_LIMIT = 1000


class TableInfo(BaseModel):
    name: str


class TableData(BaseModel):
    table: str
    columns: list[str]
    rows: list[dict]
    row_count: int
    truncated: bool


def _browsable_tables(conn) -> list[str]:
    """Base tables in dbo, minus the blacklist — the injection-safe whitelist."""
    cur = conn.cursor()
    cur.execute(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES"
        " WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = 'dbo'"
        " ORDER BY TABLE_NAME"
    )
    return [r[0] for r in cur.fetchall() if r[0] not in _BLACKLIST]


def _cell(value):
    """Coerce a DB value into something JSON-serializable for display."""
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    return value


@router.get("", response_model=list[TableInfo])
def list_browsable_tables(conn=Depends(get_db)):
    return [TableInfo(name=n) for n in _browsable_tables(conn)]


@router.get("/{table}", response_model=TableData)
def read_table(
    table: str,
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    conn=Depends(get_db),
):
    # Validate against the catalog whitelist before interpolating the name.
    if table not in _browsable_tables(conn):
        raise HTTPException(status_code=404, detail=f"Table '{table}' is not browsable.")
    cur = conn.cursor()
    cur.execute(f"SELECT TOP (?) * FROM [dbo].[{table}]", limit)
    columns = [d[0] for d in cur.description]
    rows = [{c: _cell(v) for c, v in zip(columns, row)} for row in cur.fetchall()]
    return TableData(
        table=table,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=len(rows) >= limit,
    )
