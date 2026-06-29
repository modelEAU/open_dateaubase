"""Campaign membership is junction-authoritative (consistency audit F10, D2).

delete_campaign_deployment must remove membership via the junction tables and
must not couple the CampaignSamplingLocation cleanup to ELH open/closed state.
Runs without a DB: we inspect the SQL the repo issues.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.v1.repositories import campaign_repository as cr


def _conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def _sqls(cursor):
    return [c.args[0] for c in cursor.execute.call_args_list]


def test_delete_removes_junctions_and_sp_link_decoupled_from_open_elh():
    conn, cursor = _conn()
    cr.delete_campaign_deployment(
        conn, campaign_id=5, equipment_id=7, sampling_point_id=3
    )
    sqls = _sqls(cursor)

    # 1. membership junction removed
    assert any("DELETE FROM [dbo].[CampaignEquipment]" in s for s in sqls)
    # 2. active physical placement removed; closed rows (no ValidTo IS NULL) untouched
    assert any(
        "DELETE FROM [dbo].[EquipmentLocationHistory]" in s and "[ValidTo] IS NULL" in s
        for s in sqls
    )
    # 3. SP-link removal is junction-driven and NOT gated on open-ELH state (the F10 fix)
    sp_sql = next(s for s in sqls if "DELETE FROM [dbo].[CampaignSamplingLocation]" in s)
    assert "CampaignEquipment" in sp_sql, "SP-link check must be junction-authoritative"
    assert "ValidTo" not in sp_sql, "SP-link check must not depend on ELH open/closed state"

    conn.commit.assert_called_once()


def test_campaign_equipment_deleted_before_sp_link_check():
    """CE must be removed before the SP-link NOT EXISTS so the equipment being
    deleted is excluded from 'does another member still use this SP?'."""
    conn, cursor = _conn()
    cr.delete_campaign_deployment(conn, 5, 7, 3)
    sqls = _sqls(cursor)
    ce_idx = next(i for i, s in enumerate(sqls) if "DELETE FROM [dbo].[CampaignEquipment]" in s)
    sp_idx = next(i for i, s in enumerate(sqls) if "CampaignSamplingLocation" in s)
    assert ce_idx < sp_idx


def test_delete_without_sampling_point_skips_sp_link():
    conn, cursor = _conn()
    cr.delete_campaign_deployment(conn, 5, 7, sampling_point_id=None)
    sqls = _sqls(cursor)
    assert not any("CampaignSamplingLocation" in s for s in sqls)
    conn.commit.assert_called_once()
