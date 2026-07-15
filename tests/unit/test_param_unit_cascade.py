"""Units offered must be the ones the chosen parameter allows."""

from __future__ import annotations

from unittest.mock import patch

from app.components.labels import NONE_LABEL
from app.components.param_unit import unit_select, units_for_parameter

_ALL_UNITS = [
    {"unit_id": 1, "unit": "mg/L"},
    {"unit_id": 2, "unit": "pH"},
    {"unit_id": 3, "unit": "NTU"},
]
_COD_UNITS = [{"unit_id": 1, "unit": "mg/L"}]


def test_units_narrow_to_parameter():
    with patch("app.components.param_unit.list_parameter_units_lookup", return_value=_COD_UNITS):
        units, note = units_for_parameter(7, _ALL_UNITS)
    assert [u["unit"] for u in units] == ["mg/L"]
    assert note is None


def test_no_parameter_picked_offers_all():
    units, note = units_for_parameter(None, _ALL_UNITS)
    assert units == _ALL_UNITS
    assert note is None


def test_parameter_without_units_falls_back_with_note():
    with patch("app.components.param_unit.list_parameter_units_lookup", return_value=[]):
        units, note = units_for_parameter(7, _ALL_UNITS)
    assert units == _ALL_UNITS
    assert note  # user is told why every unit is on offer


def test_select_drops_unit_the_new_parameter_disallows():
    # User picked NTU, then switched the parameter to COD (mg/L only). NTU must
    # not survive: Streamlit raises on a session value outside `options`, and a
    # silent carry-over submits a unit the parameter never permitted.
    state = {"u": "NTU"}
    with (
        patch("app.components.param_unit.list_parameter_units_lookup", return_value=_COD_UNITS),
        patch("app.components.param_unit.st"),
        patch("app.components.kind_select.st") as st,  # select_or_none renders the widget
    ):
        st.session_state = state
        st.selectbox.side_effect = lambda *a, **kw: NONE_LABEL
        unit_select("Unit", parameter_id=7, all_units=_ALL_UNITS, key="u")
        offered = st.selectbox.call_args.kwargs["options"]
    assert "u" not in state
    assert offered == [NONE_LABEL, "mg/L"]  # house sentinel row, then the allowed unit
