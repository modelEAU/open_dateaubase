"""Campaigns are multi-site (consistency audit F2/F9, Batch 6).

Campaign.Site_ID is dropped: a campaign's sites are derived from its
sampling-location membership (CampaignSamplingLocation -> SamplingPoint.Site).
These run without a DB — we pin the SQL the repo issues and the derived shape.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.v1.repositories import campaign_repository as cr


def _conn(fetchall=None, fetchone=None):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall if fetchall is not None else []
    cursor.fetchone.return_value = fetchone
    conn.cursor.return_value = cursor
    return conn, cursor


def _sqls(cursor):
    return [c.args[0] for c in cursor.execute.call_args_list]


def test_campaign_sites_derived_from_membership():
    conn, cursor = _conn(fetchall=[(4, "Site A"), (9, "Site B")])
    sites = cr._campaign_sites(conn, 5)

    sql = _sqls(cursor)[0]
    assert "DISTINCT" in sql
    assert "[CampaignSamplingLocation]" in sql
    assert "[SamplingPoint]" in sql and "[Site]" in sql
    assert sites == [
        {"site_id": 4, "site_name": "Site A"},
        {"site_id": 9, "site_name": "Site B"},
    ]


def test_list_filter_by_site_is_membership_not_column():
    conn, cursor = _conn(fetchall=[])
    cr.list_campaigns(conn, site_id=3)
    sql = _sqls(cursor)[0]
    # F2/F9 fix: filter is junction membership, not the dropped Campaign.Site_ID.
    assert "EXISTS" in sql and "[CampaignSamplingLocation]" in sql
    assert "c.[Site_ID]" not in sql


def test_insert_and_update_no_longer_write_site_id():
    # fetchone serves @@IDENTITY ([0]) and the get_campaign_by_id row (9 cols).
    conn, cursor = _conn(fetchone=(1, 2, "kind", "name", None, None, None, None, "person"))
    cr.insert_campaign(conn, {"name": "C", "campaign_kind_id": 2, "site_id": 7})
    cr.update_campaign(conn, 1, {"name": "C", "campaign_kind_id": 2, "site_id": 7})
    writes = [s for s in _sqls(cursor) if "INTO [dbo].[Campaign]" in s or "UPDATE [dbo].[Campaign]" in s]
    assert writes, "expected an INSERT and an UPDATE against Campaign"
    for sql in writes:
        assert "[Site_ID]" not in sql
