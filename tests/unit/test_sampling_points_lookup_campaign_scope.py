"""Regression: sampling-point lookup must scope to a campaign when asked (#73).

The series picker's sampling-point dropdown used to always list every
sampling point in the database, ignoring the campaign filter the user had
already selected. Add an optional campaign_id filter, joined through the
CampaignSamplingLocation junction.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from api.v1.repositories import lookup_repository


def test_no_campaign_id_queries_all_sampling_points():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value = cursor

    lookup_repository.get_sampling_points_lookup(conn)

    executed = cursor.execute.call_args.args[0]
    assert "CampaignSamplingLocation" not in executed


def test_campaign_id_scopes_via_junction_table():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value = cursor

    lookup_repository.get_sampling_points_lookup(conn, campaign_id=7)

    call = cursor.execute.call_args
    assert "CampaignSamplingLocation" in call.args[0]
    assert "csl.Campaign_ID = ?" in call.args[0]
    assert call.args[1] == 7
