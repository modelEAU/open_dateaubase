"""Unit checks for the read-only table browser helpers (no DB needed)."""

from __future__ import annotations

import datetime
from decimal import Decimal

from api.v1.endpoints.admin_browse import _browsable_tables, _cell


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_args, **_kwargs):
        return self

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    def cursor(self):
        return _FakeCursor(self._rows)


def test_browsable_tables_excludes_blacklist():
    conn = _FakeConn([("Equipment",), ("UserAccount",), ("Site",)])
    assert _browsable_tables(conn) == ["Equipment", "Site"]


def test_cell_serializes_non_json_types():
    assert _cell(datetime.date(2026, 6, 26)) == "2026-06-26"
    assert _cell(Decimal("1.5")) == 1.5
    assert _cell(b"abc") == "<3 bytes>"
    assert _cell("plain") == "plain"
    assert _cell(None) is None
