"""App entrypoint.

Run with: uv run streamlit run app/Home.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from app.api_client import APIError, get_health
from app.auth import get_current_user, is_authenticated, logout, require_auth
from app.config import settings

st.set_page_config(page_title=settings.APP_TITLE, page_icon="💧", layout="wide")


def login_page() -> None:
    require_auth(show_login=True)


def dashboard_page() -> None:
    st.header("open_datEAUbase")
    st.subheader("Water quality data management")

    st.markdown("### API Status")
    try:
        health = get_health()
        col1, col2, col3 = st.columns(3)
        col1.metric("API version", health.get("api_version", "—"))
        col2.metric("Database", health.get("db", "—"))
        col3.metric("Schema version", health.get("schema_version", "—"))
    except APIError as e:
        if e.status_code == 503 and "Cannot reach API" not in e.message:
            st.error(f"API is running but the database is unavailable: {e.message}")
        else:
            st.error(
                f"Cannot reach API at {settings.API_BASE_URL}. "
                "Make sure the API server is running."
            )


if not is_authenticated():
    pg = st.navigation(
        [st.Page(login_page, title="Login", icon="🔐", default=True)],
        position="hidden",
    )
else:
    with st.sidebar:
        user = get_current_user()
        if user:
            st.write(f"Logged in as: **{user['full_name']}**")
            st.caption(user["email"])
        st.divider()
        if st.button("Sign out"):
            logout()

    _pages_dir = Path(__file__).parent / "pages"

    pg = st.navigation(
        [
            st.Page(dashboard_page, title="Home", icon="🏠", default=True),
            st.Page(_pages_dir / "Audit_Log.py", title="Audit Log", icon="📋"),
        ],
        position="sidebar",
    )

pg.run()
