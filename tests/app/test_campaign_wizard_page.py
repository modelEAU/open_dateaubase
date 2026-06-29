"""Campaign wizard page: multi-site sampling-location selection (Batch 6 UX).

`_selected_sls` unions the locations picked across every site block. SL names
may collide between sites, so resolution must be per block (by that block's
site) — a campaign spanning two sites resolves both even when an SL name repeats.
"""

from __future__ import annotations

import streamlit as st

from app.pages import campaign_wizard_page as cwp

_SLS = {
    1: [{"id": 10, "name": "Inlet"}, {"id": 11, "name": "Outlet"}],  # Site A
    2: [{"id": 20, "name": "Inlet"}],  # Site B — same SL name as A
}

_LOOKUPS = {"sites": [{"name": "Site A", "site_id": 1}, {"name": "Site B", "site_id": 2}]}


def _setup(monkeypatch, snap):
    monkeypatch.setattr(st, "session_state", {"_cmp_wiz_snap_1": snap})
    monkeypatch.setattr(cwp, "list_site_sampling_locations", lambda sid: _SLS.get(sid, []))


def test_union_across_sites_resolves_both_despite_name_collision(monkeypatch):
    _setup(
        monkeypatch,
        {
            "cmp_wiz_s1_block_ids": [0, 1],
            "cmp_wiz_s1_site_0": "Site A",
            "cmp_wiz_s1_sls_0": ["Inlet"],
            "cmp_wiz_s1_site_1": "Site B",
            "cmp_wiz_s1_sls_1": ["Inlet"],
        },
    )
    out = cwp._selected_sls(_LOOKUPS)
    assert [(sl["id"], sl["site_name"]) for sl in out] == [
        (10, "Site A"),
        (20, "Site B"),
    ]


def test_empty_blocks_yield_no_locations(monkeypatch):
    _setup(monkeypatch, {"cmp_wiz_s1_block_ids": [0], "cmp_wiz_s1_site_0": "Site A"})
    assert cwp._selected_sls(_LOOKUPS) == []
