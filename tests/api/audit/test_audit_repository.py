"""Unit tests for AuditRepository."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from api.v1.repositories.audit_repository import AuditRepository


def _make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return AuditRepository(conn), conn, cursor


class TestLog:
    def test_inserts_row(self):
        repo, conn, cursor = _make_repo()
        repo.log(action="LOGIN", resource_type="UserAccount", user_id=1, resource_id="1")
        cursor.execute.assert_called_once()
        sql = cursor.execute.call_args[0][0]
        assert "INSERT INTO" in sql
        conn.commit.assert_called_once()

    def test_serialises_details_as_json(self):
        repo, conn, cursor = _make_repo()
        repo.log(
            action="CREATE",
            resource_type="Site",
            user_id=2,
            resource_id="42",
            details={"name": "Site A"},
        )
        args = cursor.execute.call_args[0][1:]
        details_arg = args[4]
        assert '"name"' in details_arg
        assert '"Site A"' in details_arg

    def test_db_error_is_silenced(self):
        repo, conn, cursor = _make_repo()
        cursor.execute.side_effect = Exception("DB error")
        repo.log(action="LOGIN", resource_type="UserAccount")  # must not raise


class TestListLogs:
    def _make_row(self, action="LOGIN"):
        return (
            1,                       # AuditLog_ID
            10,                      # UserAccount_ID
            "Alice",                 # FullName
            "alice@example.com",     # Email
            action,                  # Action
            "UserAccount",           # ResourceType
            "10",                    # ResourceID
            None,                    # Details
            datetime(2024, 1, 1, tzinfo=timezone.utc),  # Timestamp
        )

    def test_returns_list_of_dicts(self):
        repo, conn, cursor = _make_repo()
        cursor.fetchall.return_value = [self._make_row()]
        result = repo.list_logs()
        assert len(result) == 1
        assert result[0]["action"] == "LOGIN"
        assert result[0]["full_name"] == "Alice"

    def test_applies_user_id_filter(self):
        repo, conn, cursor = _make_repo()
        cursor.fetchall.return_value = []
        repo.list_logs(user_id=5)
        sql = cursor.execute.call_args[0][0]
        assert "[UserAccount_ID] = ?" in sql

    def test_applies_action_filter(self):
        repo, conn, cursor = _make_repo()
        cursor.fetchall.return_value = []
        repo.list_logs(action="CREATE")
        sql = cursor.execute.call_args[0][0]
        assert "[Action] = ?" in sql

    def test_parses_details_json(self):
        repo, conn, cursor = _make_repo()
        row = list(self._make_row())
        row[7] = '{"key": "value"}'
        cursor.fetchall.return_value = [tuple(row)]
        result = repo.list_logs()
        assert result[0]["details"] == {"key": "value"}

    def test_null_details_stays_none(self):
        repo, conn, cursor = _make_repo()
        cursor.fetchall.return_value = [self._make_row()]
        result = repo.list_logs()
        assert result[0]["details"] is None
