"""Batch 2 detection layer (consistency audit F1 + F13).

These repo helpers feed the DAS-move / reconfigure warnings. They run without a
DB (MagicMock cursor): we pin the SQL shape and the row→dict mapping.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.v1.repositories import temporal_history_repository as thr


def _conn(fetchall=None, fetchone=None):
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall if fetchall is not None else []
    cursor.fetchone.return_value = fetchone  # None unless a row is supplied
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# --- F1: equipment stranded by a DAS move ----------------------------------

def test_das_move_conflicts_query_keys_on_das_and_excludes_target_site():
    conn, cursor = _conn(fetchall=[])
    thr.get_das_move_equipment_conflicts(conn, das_id=3, new_site_id=9)

    sql = cursor.execute.call_args.args[0]
    # walks DAS -> SignalInterface -> active wiring -> active location -> SP.Site
    assert "si.[DataAcquisitionSystem_ID] = ?" in sql
    assert "ewh.[ValidTo] IS NULL" in sql
    assert "elh.[ValidTo] IS NULL" in sql
    assert "sp.[Site_ID] <> ?" in sql
    assert cursor.execute.call_args.args[1:] == (3, 9)


def test_das_move_conflicts_maps_rows():
    conn, _ = _conn(fetchall=[(5, "pH-01", 7, "Influent", 2, "Plant A")])
    rows = thr.get_das_move_equipment_conflicts(conn, das_id=3, new_site_id=9)
    assert rows == [
        {
            "equipment_id": 5,
            "equipment_identifier": "pH-01",
            "sampling_point_id": 7,
            "sampling_point_name": "Influent",
            "current_site_id": 2,
            "current_site_name": "Plant A",
        }
    ]


def test_das_move_no_conflicts_returns_empty():
    conn, _ = _conn(fetchall=[])
    assert thr.get_das_move_equipment_conflicts(conn, 3, 9) == []


# --- F13: equipment's still-active campaign deployment ----------------------

def test_active_campaign_deployment_filters_to_unfinished_campaigns():
    conn, cursor = _conn(fetchone=None)
    thr.get_active_campaign_deployment(conn, equipment_id=5)

    sql = cursor.execute.call_args.args[0]
    assert "elh.[ValidTo] IS NULL" in sql
    # only campaigns still running (no end, or end in the future)
    assert "c.[CampaignEndDateTime] IS NULL" in sql
    assert "c.[CampaignEndDateTime] > SYSUTCDATETIME()" in sql


def test_active_campaign_deployment_maps_row():
    conn, _ = _conn(fetchone=(12, "Pilot 2026", 88, 7, "Influent"))
    got = thr.get_active_campaign_deployment(conn, 5)
    assert got == {
        "campaign_id": 12,
        "campaign_name": "Pilot 2026",
        "equipment_location_history_id": 88,
        "sampling_point_id": 7,
        "sampling_point_name": "Influent",
    }


def test_active_campaign_deployment_none_when_no_open_campaign_row():
    conn, _ = _conn(fetchone=None)
    assert thr.get_active_campaign_deployment(conn, 5) is None
