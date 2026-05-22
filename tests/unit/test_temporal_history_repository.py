"""Unit tests for api.v1.repositories.temporal_history_repository.

These tests run without a database — they patch pyodbc.Connection with
MagicMock and assert against the SQL strings and call sequence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from api.v1.repositories import temporal_history_repository


class TestOpenLocationForCampaign:
    """BUG-5 regression: campaign deployments must create EquipmentLocationHistory."""

    def _conn(self, closed_row_id: int | None, new_row_id: int = 7):
        """Build a mock connection whose cursor returns closed_row_id from the
        UPDATE OUTPUT and new_row_id from the INSERT OUTPUT."""
        conn = MagicMock()
        cursor = MagicMock()
        # The UPDATE/INSERT both go through fetchone(); side_effect drives them in order.
        fetchone_returns: list[tuple[int] | None] = [
            (closed_row_id,) if closed_row_id is not None else None,
            (new_row_id,),
        ]
        cursor.fetchone.side_effect = fetchone_returns
        conn.cursor.return_value = cursor
        return conn, cursor

    def test_closes_active_row_and_opens_new_with_campaign_id(self):
        conn, cursor = self._conn(closed_row_id=3, new_row_id=7)
        start = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)

        new_id, closed_id = temporal_history_repository.open_location_for_campaign(
            conn,
            equipment_id=42,
            sampling_point_id=8,
            start_time=start,
            campaign_id=99,
            notes="deployment for pilot",
        )

        assert new_id == 7
        assert closed_id == 3

        # Two cursor.execute calls: close UPDATE, then open INSERT.
        assert cursor.execute.call_count == 2
        update_sql = cursor.execute.call_args_list[0][0][0]
        insert_sql = cursor.execute.call_args_list[1][0][0]

        assert "UPDATE" in update_sql and "EquipmentLocationHistory" in update_sql
        assert "ValidTo" in update_sql

        assert "INSERT INTO" in insert_sql
        assert "EquipmentLocationHistory" in insert_sql
        # Critical: the INSERT must include Campaign_ID — this is the column
        # the previous broken implementation omitted (BUG-5).
        assert "Campaign_ID" in insert_sql

        # Caller owns the transaction — function must NOT commit.
        conn.commit.assert_not_called()

    def test_no_active_row_to_close(self):
        conn, _ = self._conn(closed_row_id=None, new_row_id=11)
        start = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)

        new_id, closed_id = temporal_history_repository.open_location_for_campaign(
            conn,
            equipment_id=42,
            sampling_point_id=8,
            start_time=start,
            campaign_id=99,
        )

        assert new_id == 11
        assert closed_id is None
        conn.commit.assert_not_called()

    def test_insert_args_carry_campaign_id_and_start_time(self):
        conn, cursor = self._conn(closed_row_id=None, new_row_id=11)
        start = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)

        temporal_history_repository.open_location_for_campaign(
            conn,
            equipment_id=42,
            sampling_point_id=8,
            start_time=start,
            campaign_id=99,
            notes=None,
        )

        # Second call is the INSERT; args after the SQL string are the bound parameters.
        insert_args = cursor.execute.call_args_list[1][0][1:]
        assert 42 in insert_args  # equipment_id
        assert 8 in insert_args   # sampling_point_id
        assert start in insert_args  # start_time
        assert 99 in insert_args  # campaign_id
