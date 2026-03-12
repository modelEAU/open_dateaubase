"""App entrypoint and router.

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

    col_status, col_nav = st.columns(2)

    with col_status:
        st.markdown("### API Status")
        try:
            health = get_health()
            st.metric("API version", health.get("version", "—"))
            st.metric("Database", health.get("db_status", health.get("status", "—")))
            schema = health.get("schema_version") or health.get("db_schema_version")
            if schema:
                st.metric("Schema version", schema)
        except APIError as e:
            if e.status_code == 503 and "Cannot reach API" not in e.message:
                st.error(f"API is running but the database is unavailable: {e.message}")
            else:
                st.error(
                    f"Cannot reach API at {settings.API_BASE_URL}. "
                    "Make sure the API server is running."
                )

    with col_nav:
        st.markdown("### Quick navigation")
        st.markdown(
            """
Use the sidebar to navigate between sections:

- **Sites**
- **Equipment**
- **Campaigns**
- **Channels**
- **Annotations**
- **Units**
- **Equipment Models**
- **Parameters**
- **Binning Axes**
- **Sensor Ingest**
- **Lab Ingest**
- **Explore**
            """
        )

    st.caption("Use the sidebar to navigate between sections.")


if not is_authenticated():
    pg = st.navigation(
        [
            st.Page(login_page, title="Login", icon="🔐", default=True),
        ],
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

    pg = st.navigation(
        [
            st.Page(dashboard_page, title="Home",  default=True),
            st.Page("pages/1_Sites.py", title="Sites"),
            st.Page("pages/2_Equipment.py", title="Equipment"),
            st.Page("pages/3_Campaigns.py", title="Campaigns"),
            st.Page("pages/4_Channels.py", title="Channels"),
            st.Page("pages/5_Annotations.py", title="Annotations"),
            st.Page("pages/5_Units.py", title="Units"),
            st.Page("pages/6_Equipment_Models.py", title="Equipment Models"),
            st.Page("pages/7_Parameters.py", title="Parameters"),
            st.Page("pages/8_Binning_Axes.py", title="Binning Axes"),
            st.Page("pages/9_Sensor_Ingest.py", title="Sensor Ingest"),
            st.Page("pages/10_Lab_Ingest.py", title="Lab Ingest"),
            st.Page("pages/11_Explore.py", title="Explore"),
        ],
        position="sidebar",
    )

pg.run()