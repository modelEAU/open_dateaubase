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
from app.auth import get_current_user, logout
from app.auth import _show_login_page as _login
from app.config import settings

st.set_page_config(page_title=settings.APP_TITLE, page_icon="💧", layout="wide")


def _home() -> None:
    st.header("open_datEAUbase")
    st.subheader("Water quality data management")

    col_status, col_nav = st.columns(2)

    with col_status:
        st.markdown("### API Status")
        try:
            health = get_health()
            st.metric("API version", health.get("api_version", "—"))
            st.metric("Database", health.get("db", health.get("db_status", "—")))
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
- **Entities** — manage sites, equipment, channels, and signal sources
- **Associations** — equipment model parameters/procedures, parameter units
- **Vocabulary** — lookup tables and controlled vocabularies
            """
        )


_pages = Path(__file__).parent / "pages"
_user = get_current_user()

if not _user:
    pg = st.navigation({"": [st.Page(_login, title="Home", icon="🏠")]})
    pg.run()
    st.stop()

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
            st.Page(str(_pages / "campaign_wizard_page.py"), title="New Campaign", icon="🪄"),
        ],
        "Entities": [
            st.Page(str(_pages / "watersheds.py"), title="Watersheds"),
            st.Page(str(_pages / "sites.py"), title="Sites"),
            st.Page(str(_pages / "process_units.py"), title="Process Units"),
            st.Page(str(_pages / "equipment.py"), title="Equipment"),
            st.Page(str(_pages / "equipment_models.py"), title="Equipment Models"),
            st.Page(
                str(_pages / "data_acquisition_systems.py"),
                title="Data Acquisition Systems",
            ),
            st.Page(str(_pages / "control_loops.py"), title="Control Loops"),
            st.Page(str(_pages / "channels.py"), title="Channels"),
            st.Page(str(_pages / "parameters.py"), title="Parameters"),
            st.Page(str(_pages / "binning_axes.py"), title="Binning Axes"),
            st.Page(str(_pages / "annotations.py"), title="Annotations"),
            st.Page(str(_pages / "laboratories.py"), title="Laboratories"),
            st.Page(str(_pages / "persons.py"), title="Persons"),
            st.Page(str(_pages / "procedures.py"), title="Procedures"),
        ],
        "Associations": [
            st.Page(
                str(_pages / "equipment_model_associations.py"),
                title="Equipment Model Associations",
                icon="🔗",
            ),
            st.Page(
                str(_pages / "parameter_units.py"),
                title="Parameter Units",
                icon="📐",
            ),
        ],
        "Signal Sources": [
            st.Page(
                str(_pages / "signal_interfaces.py"),
                title="Signal Interfaces",
                icon="🔌",
            ),
            st.Page(str(_pages / "signal_interface_kinds.py"), title="Interface Kinds"),
            st.Page(str(_pages / "signal_interface_port_kinds.py"), title="Port Kinds"),
        ],
        "Vocabulary": [
            st.Page(str(_pages / "site_kinds.py"), title="Site Kinds"),
            st.Page(str(_pages / "campaign_kinds.py"), title="Campaign Kinds"),
            st.Page(str(_pages / "process_unit_kinds.py"), title="Process Unit Kinds"),
            st.Page(
                str(_pages / "equipment_event_kinds.py"), title="Equipment Event Kinds"
            ),
            st.Page(str(_pages / "annotation_kinds.py"), title="Annotation Kinds"),
            st.Page(str(_pages / "sample_kinds.py"), title="Sample Kinds"),
            st.Page(str(_pages / "sample_collection_kinds.py"), title="Sample Collection Kinds"),
            st.Page(str(_pages / "quality_codes.py"), title="Quality Codes"),
            st.Page(str(_pages / "units.py"), title="Units"),
            st.Page(str(_pages / "bin_kinds.py"), title="Bin Kinds"),
            st.Page(str(_pages / "processing_kinds.py"), title="Processing Kinds"),
        ],
        "Workflows": [
            st.Page(str(_pages / "equipment_move.py"), title="Equipment Move"),
            st.Page(str(_pages / "site_wizard.py"), title="Site Setup Wizard", icon="🏭"),
            st.Page(str(_pages / "field_system_wizard.py"), title="Field System Wizard", icon="📡"),
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
