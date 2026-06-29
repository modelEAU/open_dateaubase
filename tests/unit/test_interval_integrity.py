"""Interval integrity guard (consistency audit F7).

The *History swap helpers reject a backdated ValidFrom that would overlap or
invert existing rows. These run without a DB (MagicMock cursor): we pin the
guard's SQL shape and that a conflict short-circuits before any write.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from api.v1.repositories import temporal_history_repository as thr

NOW = datetime(2026, 6, 29)


def test_guard_rejects_timestamp_inside_existing_interval():
    cursor = MagicMock()
    # an existing closed interval straddling NOW
    cursor.fetchone.return_value = (datetime(2025, 1, 1), datetime(2027, 1, 1))
    with pytest.raises(ValueError, match="overlap or invert"):
        thr._assert_valid_from_ok(
            cursor, "EquipmentWiringHistory", "Equipment_ID", 1, NOW
        )


def test_guard_allows_when_no_conflict():
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    thr._assert_valid_from_ok(
        cursor, "EquipmentLocationHistory", "Equipment_ID", 1, NOW
    )  # must not raise


def test_guard_sql_shape_and_params():
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    thr._assert_valid_from_ok(
        cursor, "DASLocationHistory", "DataAcquisitionSystem_ID", 7, NOW
    )
    sql = cursor.execute.call_args.args[0]
    assert "[DataAcquisitionSystem_ID] = ?" in sql
    assert "[ValidTo] IS NULL AND [ValidFrom] >= ?" in sql
    assert "[ValidFrom] <= ? AND ? < [ValidTo]" in sql
    assert cursor.execute.call_args.args[1:] == (7, NOW, NOW, NOW)


def test_relocate_rejects_backdated_overlap_before_any_write():
    """F8 passes (different SP) → F7 guard finds a conflict → no close/insert/commit."""
    with patch.object(
        thr, "get_active_location_for_equipment", return_value={"sampling_point_id": 99}
    ):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (datetime(2025, 1, 1), datetime(2027, 1, 1))
        conn.cursor.return_value = cursor

        with pytest.raises(ValueError, match="overlap or invert"):
            thr.relocate_equipment(
                conn,
                equipment_id=1,
                new_sampling_point_id=5,
                start_time=NOW,
                campaign_id=2,
            )

        # guard ran exactly one SELECT; no UPDATE/INSERT, no commit
        assert cursor.execute.call_count == 1
        conn.commit.assert_not_called()
