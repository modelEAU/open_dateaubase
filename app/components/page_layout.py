"""Common page layout: enforces auth and renders the sidebar user block."""

from __future__ import annotations

import streamlit as st

from app.auth import get_current_user, logout, require_auth


def render_sidebar() -> None:
    """Render the user info, refresh-data, and sign-out controls in the sidebar."""
    with st.sidebar:
        user = get_current_user()
        if user:
            st.write(f"**{user['full_name']}**")
            st.caption(user["email"])
        st.divider()
        # Reference-data lookups are cached process-wide with a short TTL
        # (see app/api_client.py). This forces an immediate refetch so newly
        # added equipment/sites/parameters/etc. show up in dropdowns at once.
        if st.button("Refresh data", key="_sidebar_refresh", help="Reload dropdown / reference data now"):
            st.cache_data.clear()
            st.rerun()
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
