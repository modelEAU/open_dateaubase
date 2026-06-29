"""snapshot_get must survive Streamlit dropping a prior step's widget keys.

Regression for the campaign wizard's Equipment Deployments step: selecting an
equipment triggers a rerun on which the step-1 site/sampling-location widgets
are not rendered, so Streamlit drops their live session_state keys. Reading them
directly blanked the step ("No sampling locations selected"); reading from the
persistent snapshot fixes it.
"""

from __future__ import annotations

from app.components import wizard_helpers as wh


def test_snapshot_get_falls_back_when_live_key_dropped(monkeypatch):
    monkeypatch.setattr(wh.st, "session_state", {})
    # Step 1 saved its selections into the snapshot; the live widget keys were
    # then dropped by Streamlit on a later-step rerun.
    wh.st.session_state["_cmp_wiz_snap_1"] = {
        "cmp_wiz_s1_site": "Site A",
        "cmp_wiz_s1_sl_selected": ["Inlet", "Outlet"],
    }

    assert wh.snapshot_get("cmp_wiz", 1, "cmp_wiz_s1_site") == "Site A"
    assert wh.snapshot_get("cmp_wiz", 1, "cmp_wiz_s1_sl_selected") == ["Inlet", "Outlet"]


def test_live_state_wins_over_snapshot(monkeypatch):
    monkeypatch.setattr(wh.st, "session_state", {})
    wh.st.session_state["_cmp_wiz_snap_1"] = {"cmp_wiz_s1_site": "Site A"}
    wh.st.session_state["cmp_wiz_s1_site"] = "Site B"  # freshly changed, still rendered
    assert wh.snapshot_get("cmp_wiz", 1, "cmp_wiz_s1_site") == "Site B"


def test_default_when_neither_present(monkeypatch):
    monkeypatch.setattr(wh.st, "session_state", {})
    assert wh.snapshot_get("cmp_wiz", 1, "missing", default=[]) == []
