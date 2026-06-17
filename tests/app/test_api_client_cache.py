"""Tests for reference-data lookup caching in app.api_client.

The list_*_lookup helpers are wrapped in st.cache_data so pages don't re-fetch
reference data on every rerun. These tests pin that behavior: repeated reads
hit the API once, and clear_lookup_caches() forces a refetch.
"""

from __future__ import annotations

from unittest.mock import patch

import app.api_client as api

from tests.app.test_api_client import _FakeClient, _mock_response


def _counting_get_client():
    """Return a (_get_client replacement, counter) pair recording invocations."""
    calls = {"n": 0}

    def _factory():
        calls["n"] += 1
        return _FakeClient(_mock_response(200, [{"site_id": 1, "name": "WWTP"}]))

    return _factory, calls


def test_lookup_is_cached_within_ttl():
    api.clear_lookup_caches()
    factory, calls = _counting_get_client()
    with patch("app.api_client._get_client", side_effect=factory):
        first = api.list_sites_lookup()
        second = api.list_sites_lookup()
    assert first == second
    assert calls["n"] == 1  # second read served from cache, no API call


def test_clear_lookup_caches_forces_refetch():
    api.clear_lookup_caches()
    factory, calls = _counting_get_client()
    with patch("app.api_client._get_client", side_effect=factory):
        api.list_sites_lookup()
        api.clear_lookup_caches()
        api.list_sites_lookup()
    assert calls["n"] == 2  # cache cleared between reads -> two API calls
