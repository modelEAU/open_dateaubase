"""Unit test for the Explore page-level campaign scoping helper.

_scope_to_campaign restricts the pickable sensor traces + lab series to a single
campaign, so the plot and export can only contain that campaign's streams.
"""
from __future__ import annotations

from app.pages import explore


_TRACES = [
    {"channel_id": 5, "campaign_id": 1, "parameter_name": "TSS"},
    {"channel_id": 6, "campaign_id": 2, "parameter_name": "COD"},
    {"channel_id": 7, "campaign_id": None, "parameter_name": "pH"},  # orphaned
]
_SERIES = [
    {"analysis_series_id": 10, "campaign_id": 1},
    {"analysis_series_id": 11, "campaign_id": 2},
]


def test_none_returns_everything_unchanged():
    dts, sers = explore._scope_to_campaign(_TRACES, _SERIES, None)
    assert dts == _TRACES
    assert sers == _SERIES


def test_filters_both_lists_to_campaign():
    dts, sers = explore._scope_to_campaign(_TRACES, _SERIES, 1)
    assert [d["channel_id"] for d in dts] == [5]
    assert [s["analysis_series_id"] for s in sers] == [10]


def test_campaign_with_no_streams_yields_empty():
    dts, sers = explore._scope_to_campaign(_TRACES, _SERIES, 99)
    assert dts == []
    assert sers == []
