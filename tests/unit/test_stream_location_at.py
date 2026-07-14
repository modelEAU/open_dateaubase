"""Unit tests for GET /streams/{id}/location-at and its repository query.

The gap this closes: equipment had a location-at endpoint, streams (tags) did
not — there was no way to ask "where is this stream coming from?".

No database — pyodbc.Connection is a MagicMock and we assert on the SQL and
the mapped result. The SQL itself was additionally exercised against the live
schema; the shape assertions here guard the parts that silently rot (the
point-in-time predicates and the ancestor walk).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from api.v1.repositories import temporal_history_repository

AT = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)


def _conn(*fetchone_rows):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = list(fetchone_rows)
    conn.cursor.return_value = cursor
    return conn, cursor


def _channel_row(
    *,
    equipment_id: int | None = 42,
    identifier: str | None = "SC1000-A",
    history_id: int | None = 5,
    sampling_point_id: int | None = 8,
    resolved_stream_id: int = 101,
):
    """One row of the channel-chain SELECT, in column order."""
    return (
        equipment_id,
        identifier,
        history_id,
        sampling_point_id,
        "Inlet",
        2,
        "Pilot Plant",
        AT,
        None,
        resolved_stream_id,
    )


class TestGetStreamLocationAt:
    def test_analysis_series_resolves_via_direct_fk(self):
        conn, cursor = _conn((8, "Effluent", 2, "Pilot Plant"))

        row = temporal_history_repository.get_stream_location_at(conn, 100, AT)

        assert row is not None
        assert row["source"] == "analysis_series"
        assert row["sampling_point_id"] == 8
        assert row["site_name"] == "Pilot Plant"
        # Lab series short-circuits: the channel chain is never queried.
        assert cursor.execute.call_count == 1
        assert "AnalysisSeries" in cursor.execute.call_args_list[0][0][0]

    def test_channel_resolves_through_port_wiring_then_location(self):
        conn, cursor = _conn(None, _channel_row())

        row = temporal_history_repository.get_stream_location_at(conn, 101, AT)

        assert row is not None
        assert row["source"] == "wiring"
        assert row["sampling_point_id"] == 8
        assert row["equipment_id"] == 42
        assert row["equipment_identifier"] == "SC1000-A"
        assert row["history_id"] == 5
        # Resolved on the channel itself, so nothing was inherited.
        assert row["inherited_from_stream_id"] is None

        sql = cursor.execute.call_args_list[1][0][0]
        # All three hops are temporal and must be point-in-time filtered.
        # vw_ChannelResolved is NOT usable here: it pins the port to the
        # currently-open ChannelPortHistory row, which is wrong for past times.
        assert "vw_ChannelResolved" not in sql
        assert "ChannelPortHistory" in sql
        assert "EquipmentWiringHistory" in sql
        assert "EquipmentLocationHistory" in sql
        assert sql.count("ValidFrom] <= ?") == 3

        # stream_id anchors the recursive CTE first, then at_time twice per hop.
        params = cursor.execute.call_args_list[1][0][1:]
        assert params == (101, AT, AT, AT, AT, AT, AT)

    def test_derived_channel_inherits_location_from_ancestor(self):
        # '::smoothed' has no wiring of its own; the walk up ParentChannel_ID
        # lands on raw channel 18, whose equipment is at the sampling point.
        conn, cursor = _conn(None, _channel_row(resolved_stream_id=18))

        row = temporal_history_repository.get_stream_location_at(conn, 22, AT)

        assert row is not None
        assert row["source"] == "wiring"
        assert row["sampling_point_id"] == 8
        assert row["inherited_from_stream_id"] == 18

        sql = cursor.execute.call_args_list[1][0][0]
        assert "WITH ancestry" in sql
        assert "ParentChannel_ID" in sql
        # Nearest ancestor that actually has a location wins.
        assert "CASE WHEN elh.[SamplingPoint_ID] IS NULL THEN 1 ELSE 0 END" in sql

    def test_unwired_channel_returns_row_with_no_source(self):
        # Channel exists but no wiring/location anywhere up the chain:
        # LEFT JOINs give the depth-0 row with NULLs.
        conn, _ = _conn(
            None,
            _channel_row(
                equipment_id=None,
                identifier=None,
                history_id=None,
                sampling_point_id=None,
            ),
        )

        row = temporal_history_repository.get_stream_location_at(conn, 102, AT)

        assert row is not None
        assert row["source"] is None
        assert row["sampling_point_id"] is None
        # Nothing resolved, so nothing to attribute to an ancestor.
        assert row["inherited_from_stream_id"] is None

    def test_unknown_stream_returns_none(self):
        conn, _ = _conn(None, None)

        assert temporal_history_repository.get_stream_location_at(conn, 999, AT) is None


def test_route_is_registered():
    from api.v1.router import router

    paths = {r.path for r in router.routes}  # type: ignore[attr-defined]
    assert "/streams/{stream_id}/location-at" in paths
