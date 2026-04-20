"""Home — Streamlit multipage entry point.

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
from app.auth import get_current_user, logout, require_auth
from app.config import settings

st.set_page_config(page_title=settings.APP_TITLE, page_icon="💧", layout="wide")

require_auth()


def _home() -> None:
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
- **Sensor / Lab Ingest** — upload and register measurements
- **Explore** — browse and plot time series
- **Campaigns** — sampling campaign wizard
- **Administration** — manage sites, equipment, channels, and lookup tables
            """
        )


_pages = Path(__file__).parent / "pages"

pg = st.navigation(
    {
        "": [
            st.Page(_home, title="Home", icon="🏠"),
        ],
        "Operations": [
            st.Page(str(_pages / "sensor_ingest.py"), title="Sensor Ingest", icon="📡"),
            st.Page(str(_pages / "lab_ingest.py"), title="Lab Ingest", icon="🧪"),
            st.Page(str(_pages / "explore.py"), title="Explore", icon="📊"),
        ],
        "Campaigns": [
            st.Page(str(_pages / "campaigns.py"), title="Campaigns", icon="🗂️"),
        ],
        "Entities": [
            st.Page(str(_pages / "projects.py"), title="Projects"),
            st.Page(str(_pages / "watersheds.py"), title="Watersheds"),
            st.Page(str(_pages / "sites.py"), title="Sites"),
            st.Page(str(_pages / "process_units.py"), title="Process Units"),
            st.Page(str(_pages / "equipment.py"), title="Equipment"),
            st.Page(str(_pages / "equipment_models.py"), title="Equipment Models"),
            st.Page(str(_pages / "data_acquisition_systems.py"), title="Data Acquisition Systems"),
            st.Page(str(_pages / "signal_ports.py"), title="Signal Ports"),
            st.Page(str(_pages / "control_loops.py"), title="Control Loops"),
            st.Page(str(_pages / "channels.py"), title="Channels"),
            st.Page(str(_pages / "parameters.py"), title="Parameters"),
            st.Page(str(_pages / "binning_axes.py"), title="Binning Axes"),
            st.Page(str(_pages / "annotations.py"), title="Annotations"),
            st.Page(str(_pages / "laboratories.py"), title="Laboratories"),
            st.Page(str(_pages / "persons.py"), title="Persons"),
            st.Page(str(_pages / "procedures.py"), title="Procedures"),
        ],
        "Vocabulary": [
            st.Page(str(_pages / "site_types.py"), title="Site Types"),
            st.Page(str(_pages / "campaign_types.py"), title="Campaign Types"),
            st.Page(str(_pages / "process_unit_types.py"), title="Process Unit Types"),
            st.Page(str(_pages / "signal_port_types.py"), title="Signal Port Types"),
            st.Page(str(_pages / "equipment_event_types.py"), title="Equipment Event Types"),
            st.Page(str(_pages / "annotation_types.py"), title="Annotation Types"),
            st.Page(str(_pages / "sample_types.py"), title="Sample Types"),
            st.Page(str(_pages / "sample_methods.py"), title="Sample Methods"),
            st.Page(str(_pages / "quality_codes.py"), title="Quality Codes"),
            st.Page(str(_pages / "units.py"), title="Units"),
            st.Page(str(_pages / "bin_modes.py"), title="Bin Modes"),
            st.Page(str(_pages / "processing_degrees.py"), title="Processing Degrees"),
            st.Page(str(_pages / "purposes.py"), title="Purposes"),
        ],
        "Workflows": [
            st.Page(str(_pages / "equipment_move.py"), title="Equipment Move"),
        ],
    }
)

# Persistent sidebar content — added after st.navigation() per Streamlit ≥1.41 requirement
with st.sidebar:
    user = get_current_user()
    if user:
        st.write(f"Logged in as: **{user['name']}**")
    if st.button("Sign out"):
        logout()

pg.run()
