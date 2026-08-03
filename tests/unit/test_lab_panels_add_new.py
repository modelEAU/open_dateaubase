"""Regression for #70/#72 through the actual live UI (Lab Panels form), not
just the crud_form unit. Drives create_form_dialog via AppTest.from_function
(the standard @st.dialog test pattern) with a field list shaped like
lab_panels.py's `default_sample_collection_kind_id` overlay."""

from __future__ import annotations

from unittest.mock import patch

from streamlit.testing.v1 import AppTest


def _script() -> None:  # pragma: no cover - executed inside AppTest
    from app.components.form_dialog import create_form_dialog

    fields = [
        {"name": "name", "type": "text", "required": True, "label": "Panel name"},
        {
            "name": "default_sample_collection_kind_id",
            "type": "select",
            "required": False,
            "label": "Default collection kind",
            "options": [{"id": 1, "label": "Grab"}],
            "fk_table": "SampleCollectionKind",
        },
    ]
    create_form_dialog(fields=fields, on_submit=lambda data: True, title="Create New Panel")


def test_add_new_affordance_reaches_the_lab_panels_create_dialog():
    with patch(
        "app.api_client.list_sample_collection_kind_lookup",
        return_value=[{"sample_collection_kind_id": 1, "name": "Grab"}],
    ):
        at = AppTest.from_function(_script, default_timeout=10).run()
    assert not at.exception
    assert any("Add new SampleCollectionKind" in b.label for b in at.button)


def test_creating_a_value_from_the_dialog_does_not_error():
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
        at.text_input(
            key="_offer_add_new::default_sample_collection_kind_id::name"
        ).set_value("Sludge blanket").run()
        create_btn = next(b for b in at.button if b.label == "Create")
        at = create_btn.click().run()

    assert not at.exception
    m_create.assert_called_once_with({"name": "Sludge blanket"})
