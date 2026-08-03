"""Regression for #70 / #72: a vocabulary-backed select field couldn't create
the value it was missing without leaving the form. `render_form_field` now
takes an optional `fk_table` and offers an inline "+ Add new" affordance
reusing the entity's own CRUD create call (`entity_picker`'s registry)."""

from __future__ import annotations

from unittest.mock import patch

from streamlit.testing.v1 import AppTest


def _script():  # pragma: no cover - executed inside AppTest
    import streamlit as st

    from app.components.crud_form import render_form_field

    result = render_form_field(
        "default_sample_collection_kind_id",
        "select",
        options=[{"id": 1, "label": "Grab"}],
        fk_table="SampleCollectionKind",
    )
    st.session_state["_result"] = result


def test_add_new_button_offered_for_a_name_only_vocabulary():
    with patch(
        "app.api_client.list_sample_collection_kind_lookup",
        return_value=[{"sample_collection_kind_id": 1, "name": "Grab"}],
    ):
        at = AppTest.from_function(_script, default_timeout=10).run()
    assert any("Add new SampleCollectionKind" in b.label for b in at.button)


def test_creating_a_new_value_selects_it_without_leaving_the_form():
    lookup_rows = [{"sample_collection_kind_id": 1, "name": "Grab"}]

    def _create(data: dict) -> dict:
        row = {"sample_collection_kind_id": 2, "name": data["name"]}
        lookup_rows.append(row)
        return row

    with (
        patch(
            "app.api_client.list_sample_collection_kind_lookup",
            side_effect=lambda: list(lookup_rows),
        ),
        patch("app.api_client.create_sample_collection_kind", side_effect=_create) as m_create,
        patch("app.api_client.clear_lookup_caches"),
    ):
        at = AppTest.from_function(_script, default_timeout=10).run()
        toggle = next(b for b in at.button if "Add new SampleCollectionKind" in b.label)
        at = toggle.click().run()
        at.text_input(key="_offer_add_new::default_sample_collection_kind_id::name").set_value(
            "Sludge blanket"
        ).run()
        create_btn = next(b for b in at.button if b.label == "Create")
        at = create_btn.click().run()

    m_create.assert_called_once_with({"name": "Sludge blanket"})
    assert at.session_state["_result"] == 2
