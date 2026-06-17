"""Branch coverage for the shared generic CRUD renderer via AppTest.

render_crud_page backs ~20 reference-data pages, but had no AppTest coverage.
Each test drives the harness (which calls render_crud_page with plain callables)
in one configuration and asserts on the rendered output.

Coverage map:
  load OK (list)   — dataframe rendered
  load OK (dict)   — {"items": [...]} unwrapped and rendered
  load empty       — info message, no dataframe
  load APIError    — error surfaced, script stops
  no create_fn     — '➕ New' button hidden
  embedded empty   — caption (not info) shown
"""
from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

HARNESS = str(Path(__file__).parent / "generic_crud_harness.py")


def _run(cfg: dict):
    at = AppTest.from_file(HARNESS)
    at.session_state["_crud_cfg"] = cfg
    at.run()
    return at


def test_list_renders_dataframe():
    at = _run({"list": "ok"})
    assert not at.exception
    assert len(at.dataframe) == 1


def test_dict_response_is_unwrapped():
    at = _run({"list": "dict"})
    assert not at.exception
    assert len(at.dataframe) == 1


def test_empty_shows_info_and_no_dataframe():
    at = _run({"list": "empty"})
    assert not at.exception
    assert len(at.dataframe) == 0
    assert any("No widgets found" in i.value for i in at.info)


def test_api_error_is_surfaced():
    at = _run({"list": "error"})
    assert not at.exception
    assert any("backend down" in e.value for e in at.error)


def test_new_button_hidden_without_create_fn():
    at = _run({"list": "ok", "create": False})
    assert not at.exception
    assert not any("New" in b.label for b in at.button)


def test_new_button_shown_with_create_fn():
    at = _run({"list": "ok", "create": True})
    assert any("New" in b.label for b in at.button)


def test_embedded_empty_uses_caption():
    at = _run({"list": "empty", "embedded": True})
    assert not at.exception
    assert len(at.dataframe) == 0
    assert any("No widgets found" in c.value for c in at.caption)
