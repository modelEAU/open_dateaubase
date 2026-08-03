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


def test_display_order_sorts_by_primary_key():
    from app.components.generic_crud import display_order

    items = [{"widget_id": 3}, {"widget_id": 1}, {"widget_id": 2}]
    assert [r["widget_id"] for r in display_order(items, "widget_id")] == [1, 2, 3]


def test_selection_index_resolves_against_displayed_order():
    """The table is pk-sorted; a row index must map back through that same order.

    Regression: the renderer indexed the API's (unsorted) list with an index
    taken from the sorted table, so Edit opened a different record.
    """
    from app.components.generic_crud import selected_row

    api_order = [
        {"widget_id": 3, "name": "Charlie"},
        {"widget_id": 1, "name": "Alpha"},
        {"widget_id": 2, "name": "Beta"},
    ]
    # user clicks the first table row -> widget 1, not api_order[0] ("Charlie")
    assert selected_row(api_order, "widget_id", [0])["name"] == "Alpha"
    assert selected_row(api_order, "widget_id", [2])["name"] == "Charlie"


def test_selected_row_handles_no_and_stale_selection():
    from app.components.generic_crud import selected_row

    items = [{"widget_id": 1, "name": "Alpha"}]
    assert selected_row(items, "widget_id", []) is None
    assert selected_row(items, "widget_id", [5]) is None


def test_display_order_tolerates_null_primary_key():
    from app.components.generic_crud import display_order

    items = [{"widget_id": 2}, {"widget_id": None}, {"widget_id": 1}]
    assert [r["widget_id"] for r in display_order(items, "widget_id")] == [1, 2, None]


def test_table_rows_match_display_order():
    at = _run({"list": "ok", "items": [{"widget_id": 9, "name": "Nine"},
                                       {"widget_id": 4, "name": "Four"}]})
    assert not at.exception
    rendered = at.dataframe[0].value
    assert list(rendered["widget_id"]) == [4, 9]


def test_handle_delete_flags_the_mutation_for_embedded_callers():
    """Deletion runs only from the confirm dialog's callback, via _handle_delete."""
    import streamlit as st

    from app.components.generic_crud import _handle_delete

    calls: list[int] = []
    _handle_delete(calls.append, 7, "Widgets", "_crud_deleted_widget_id")
    assert calls == [7]
    assert st.session_state["_crud_deleted_widget_id"] is True


def test_handle_delete_surfaces_api_error_without_flagging():
    from app.api_client import APIError
    from app.components.generic_crud import _handle_delete

    def _boom(pk):
        raise APIError(409, "row is referenced")

    import streamlit as st

    st.session_state.pop("_crud_deleted_widget_id", None)
    _handle_delete(_boom, 7, "Widgets", "_crud_deleted_widget_id")
    assert "_crud_deleted_widget_id" not in st.session_state


def test_read_only_page_shows_caption():
    at = _run({"list": "ok", "create": False, "update": False,
               "delete": False, "caption": "Read-only vocabulary."})
    assert not at.exception
    assert any("Read-only vocabulary." in c.value for c in at.caption)
