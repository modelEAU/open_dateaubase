"""Session-state authentication stub for the Streamlit app.

Real auth: replace the credential check block marked with TODO in _show_login_page().
"""
from __future__ import annotations
import streamlit as st


def require_auth() -> None:
    """Guard: halt page render if user is not logged in."""
    if st.session_state.get("user"):
        return
    _show_login_page()
    st.stop()


def get_current_user() -> dict | None:
    """Return the current user dict {"name": str} or None if not logged in."""
    return st.session_state.get("user")


def logout() -> None:
    """Clear the session and rerun."""
    st.session_state.pop("user", None)
    st.rerun()


def _show_login_page() -> None:
    """Render login form. Called by require_auth() before st.stop()."""
    st.title("open_datEAUbase")
    st.caption("Water quality data management")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        # TODO: Replace this block with real credential check (JWT, LDAP, etc.)
        if username and password:  # stub: any non-empty credentials work
            st.session_state["user"] = {"name": username}
            st.rerun()
        else:
            st.error("Please enter username and password.")
