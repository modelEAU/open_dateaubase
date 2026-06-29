"""AppTest coverage for the campaign wizard page (Batch 6 multi-site UX + the
deployment-step rerun bug).

The page does `from app.api_client import …`, and AppTest.from_file re-execs the
script per run, so the lookups are patched on `app.api_client.*`.
"""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

PAGE = "app/pages/campaign_wizard_page.py"
AC = "app.api_client"

_SITES = [{"site_id": 1, "name": "Site A"}, {"site_id": 2, "name": "Site B"}]
_KINDS = [{"campaign_kind_id": 1, "name": "Experiment"}]
_PERSONS = [{"person_id": 1, "id": 1, "label": "Alice Smith"}]
_EQUIP = [{"equipment_id": 5, "identifier": "EQ5"}]
_SLS = {
    1: [{"id": 10, "name": "Inlet"}, {"id": 11, "name": "Outlet"}],
    2: [{"id": 20, "name": "Lab tap"}],
}


def _patches(stack: ExitStack) -> None:
    stack.enter_context(patch(f"{AC}.list_sites_lookup", return_value=_SITES))
    stack.enter_context(patch(f"{AC}.list_campaign_kinds", return_value=_KINDS))
    stack.enter_context(patch(f"{AC}.list_persons_lookup", return_value=_PERSONS))
    stack.enter_context(patch(f"{AC}.list_equipment_lookup", return_value=_EQUIP))
    stack.enter_context(
        patch(f"{AC}.list_site_sampling_locations", side_effect=lambda sid: _SLS.get(sid, []))
    )


def test_add_another_site_renders_a_second_block():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(PAGE)
        at.session_state["cmp_wiz_step"] = 1
        at.run()
        assert len(at.selectbox) == 1  # one site picker
        at.button(key="cmp_wiz_s1_add_site").click().run()
        assert len(at.selectbox) == 2  # second site block added


def test_equipment_selection_keeps_sampling_locations():
    """The reported bug: selecting an equipment reran the page and blanked the
    sampling-location list ('No sampling locations selected')."""
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(PAGE)
        at.session_state["cmp_wiz_step"] = 2
        at.session_state["_cmp_wiz_snap_1"] = {
            "cmp_wiz_s1_block_ids": [0],
            "cmp_wiz_s1_site_0": "Site A",
            "cmp_wiz_s1_sls_0": ["Inlet", "Outlet"],
        }
        at.run()
        eq_selects = [s for s in at.selectbox if "Equipment at" in s.label]
        assert len(eq_selects) == 2

        # Select an equipment → triggers the rerun that used to blank the step.
        eq_selects[0].select("EQ5").run()

        eq_after = [s for s in at.selectbox if "Equipment at" in s.label]
        assert len(eq_after) == 2
        assert not any("No sampling locations selected" in i.value for i in at.info)


def test_multi_site_deployment_lists_both_sites():
    """Two site blocks → equipment dropdowns for SLs from both sites."""
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(PAGE)
        at.session_state["cmp_wiz_step"] = 2
        at.session_state["_cmp_wiz_snap_1"] = {
            "cmp_wiz_s1_block_ids": [0, 1],
            "cmp_wiz_s1_site_0": "Site A",
            "cmp_wiz_s1_sls_0": ["Inlet"],
            "cmp_wiz_s1_site_1": "Site B",
            "cmp_wiz_s1_sls_1": ["Lab tap"],
        }
        at.run()
        labels = [s.label for s in at.selectbox if "Equipment at" in s.label]
        assert any("Site A" in lab for lab in labels)
        assert any("Site B" in lab for lab in labels)
