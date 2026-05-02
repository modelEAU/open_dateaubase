"""Expandable form section component."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import streamlit as st


@contextmanager
def form_section(label: str, *, form_key: str, expanded: bool = False) -> Generator[None, None, None]:
    """Wrap form fields in a collapsible expander.

    Usage::

        with form_section("Add record", form_key="add_form"):
            name = st.text_input("Name")
            submitted = st.form_submit_button("Save")
        if submitted:
            ...
    """
    with st.expander(label, expanded=expanded):
        with st.form(form_key):
            yield


def confirm_dialog(message: str, *, key: str) -> bool:
    """Render a confirmation prompt and return True once confirmed.

    The confirmation state is stored in ``st.session_state`` under *key* so
    callers can check it on re-runs.
    """
    if st.session_state.get(key):
        return True

    st.warning(message)
    if st.button("Confirm", key=f"{key}_btn"):
        st.session_state[key] = True
        st.rerun()

    return False
