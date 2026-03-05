"""Home page — Streamlit multipage entry point.

Run with: uv run streamlit run app/Home.py
"""
from __future__ import annotations

import streamlit as st

from app.api_client import APIError, get_health
from app.auth import get_current_user, logout, require_auth
from app.config import settings

require_auth()

st.set_page_config(page_title=settings.APP_TITLE, page_icon="💧", layout="wide")

# Sidebar
with st.sidebar:
    user = get_current_user()
    if user:
        st.write(f"Logged in as: **{user['name']}**")
    if st.button("Sign out"):
        logout()

# Main content
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
    except APIError:
        st.error(
            f"Cannot reach API at {settings.API_BASE_URL}. "
            "Make sure the API server is running."
        )

with col_nav:
    st.markdown("### Quick navigation")
    st.markdown(
        """
Use the sidebar to navigate between sections:

- **Sites** — monitoring locations where equipment is deployed
- **Equipment** — sensors and instruments collecting measurements
- **Channels** — individual measurement streams (e.g., pH at Site A)
- **Campaigns** — sampling campaigns for lab analyses
- **Timeseries** — view and explore time-stamped measurements
- **Annotations** — notes and flags attached to measurements
        """
    )

st.caption("Use the sidebar to navigate between sections.")
