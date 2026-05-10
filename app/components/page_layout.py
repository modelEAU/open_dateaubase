"""Common page layout: enforces auth and renders the sidebar user block."""

from __future__ import annotations

import streamlit as st

from app.auth import get_current_user, logout, require_auth


def render_sidebar() -> None:
    """Render the user info and sign-out button in the sidebar."""
    with st.sidebar:
        user = get_current_user()
        if user:
            st.write(f"**{user['full_name']}**")
            st.caption(user["email"])
        st.divider()
        if st.button("Sign out", key="_sidebar_signout"):
            logout()


def authenticated_page(title: str | None = None) -> None:
    """Call at the top of every protected page.

    Redirects to the login screen if the user is not authenticated,
    then renders the sidebar and optional page title.
    """
    require_auth()
    render_sidebar()
    if title:
        st.title(title)
