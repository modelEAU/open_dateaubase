"""Site setup wizard coverage via AppTest (previously untested).

The page runs main() itself, so AppTest executes it directly with the four
lookup calls mocked. Covers that step 0 renders and that its required-field
validation fires.

Coverage map:
  step 0 — renders (site name input present)
  step 0 — site name required; new-watershed name required
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).parent.parent.parent / "app" / "pages" / "site_wizard.py")
# AppTest runs the page as a fresh script, so its `from app.api_client import ...`
# binds at run time — patch the source module, which the import then picks up.
MOD = "app.api_client"

_LOOKUP_SPECS = [
    (f"{MOD}.list_site_kinds", [{"id": 1, "name": "WWTP"}]),
    (f"{MOD}.list_process_unit_types", [{"process_unit_kind_id": 1, "name": "Aeration"}]),
    (f"{MOD}.list_process_units_lookup", []),
    (f"{MOD}.list_watersheds", [{"watershed_id": 1, "name": "Watershed A"}]),
]


@contextmanager
def _patches():
    with ExitStack() as stack:
        for target, ret in _LOOKUP_SPECS:
            stack.enter_context(patch(target, return_value=ret))
        yield


def test_step0_renders_site_name_input():
    at = AppTest.from_file(PAGE)
    with _patches():
        at.run()
    assert not at.exception
    assert any("Site name" in ti.label for ti in at.text_input)


def test_step0_site_name_required():
    at = AppTest.from_file(PAGE)
    with _patches():
        at.run()
        at.button(key="site_wiz_next_0").click().run()
    assert any("Site name is required" in e.value for e in at.error)


def test_step0_new_watershed_name_required():
    # Choose "Create new" watershed but leave site + watershed names blank.
    at = AppTest.from_file(PAGE)
    with _patches():
        at.session_state["site_wiz_ws_mode"] = "Create new"
        at.run()
        at.button(key="site_wiz_next_0").click().run()
    msgs = [e.value for e in at.error]
    assert any("Watershed name is required" in m for m in msgs)
