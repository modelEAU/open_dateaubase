"""The Parameter → Unit cascade.

A unit is not free-form: ParameterHasUnit says which units a parameter may be
measured in (pH has no mg/L). Every place that builds a parameter+unit pair must
narrow the unit choices to the picked parameter, so this is the one implementation.

Fallback is deliberate: a parameter with no configured units offers all of them
with a note, because blocking ingest on missing reference data is worse than a
slightly-wrong unit that an admin can constrain later.
"""

from __future__ import annotations

import streamlit as st

from app.api_client import APIError, list_parameter_units_lookup
from app.components.kind_select import select_or_none

_NO_UNITS_NOTE = "No units configured for this parameter — showing all."


def units_for_parameter(
    parameter_id: int | None, all_units: list[dict]
) -> tuple[list[dict], str | None]:
    """Units valid for ``parameter_id``, else ``all_units`` with a note.

    Reads through api_client's cached lookup, so linking a unit on the
    Parameter Units page is visible here without a restart.
    """
    if parameter_id is None:
        return all_units, None
    try:
        allowed = list_parameter_units_lookup(parameter_id)
    except APIError:
        allowed = []
    if not allowed:
        return all_units, _NO_UNITS_NOTE
    return allowed, None


def unit_select(
    label: str,
    *,
    parameter_id: int | None,
    all_units: list[dict],
    key: str,
    help: str | None = None,
) -> int | None:
    """Render a Unit selectbox narrowed to ``parameter_id``. Returns unit_id.

    A selection that the new parameter doesn't allow is dropped — otherwise
    Streamlit raises on a session value that isn't in ``options``, and the user
    submits a unit the parameter never permitted.
    """
    units, note = units_for_parameter(parameter_id, all_units)
    id_by_name = {u["unit"]: u["unit_id"] for u in units}
    name = select_or_none(label, list(id_by_name), key=key, help=help)
    if note:
        st.caption(note)
    return id_by_name.get(name or "")
