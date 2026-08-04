"""Retired people leave the pickers without rewriting the records that name them."""

from unittest.mock import patch

from app import api_client
from app.components.crud_form import render_form_field

_LOOKUP = [
    {"person_id": 1, "label": "Ada Lovelace", "is_active": True},
    {"person_id": 2, "label": "Gone Away", "is_active": False},
]


def test_person_lookup_hides_inactive_by_default():
    with patch("app.api_client._request", return_value=_LOOKUP):
        assert [p["person_id"] for p in api_client.list_persons_lookup()] == [1]


def test_person_lookup_can_include_inactive():
    with patch("app.api_client._request", return_value=_LOOKUP):
        got = api_client.list_persons_lookup(active_only=False)
    assert [p["person_id"] for p in got] == [1, 2]


def test_select_keeps_a_value_the_options_no_longer_offer():
    options = [{"id": 1, "label": "Ada Lovelace"}]
    with patch("app.components.crud_form.st") as st:
        st.selectbox.return_value = "#2 (retired)"
        returned = render_form_field("person_id", "select", value=2, options=options)
        labels = st.selectbox.call_args.kwargs["options"]
        index = st.selectbox.call_args.kwargs["index"]
    assert "#2 (retired)" in labels
    assert labels[index] == "#2 (retired)"
    assert returned == 2
