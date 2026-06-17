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
from app.auth import _show_auth_page as _login
from app.config import settings

st.set_page_config(page_title=settings.APP_TITLE, page_icon="💧", layout="wide")


def _home() -> None:
    st.header("open_datEAUbase")
    st.subheader("modelEAU's open-source water quality data management system")

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
            st.Page(str(_pages / "sensor_ingest.py"), title="Insert Sensor Data", icon="📡"),
            st.Page(str(_pages / "lab_ingest.py"), title="Insert Lab Data", icon="🧪"),
            st.Page(str(_pages / "lab_panels.py"), title="Lab Panels", icon="🗂️"),
            st.Page(str(_pages / "explore.py"), title="Visualize Data", icon="📊"),
            st.Page(str(_pages / "equipment_move.py"), title="Move a sensor", icon="➡️"),
        ],
        "Workflows": [
            st.Page(str(_pages / "site_wizard.py"), title="1. New Site Wizard", icon="🏭"),
            st.Page(str(_pages / "field_system_wizard.py"), title="2. New Field System Wizard", icon="📡"),
            st.Page(str(_pages / "campaign_wizard_page.py"), title="3. New Campaign Wizard", icon="👩‍🔬"),
        ],
        "Entities": [
            st.Page(str(_pages / "campaigns.py"), title="Campaigns", icon="🚀"),
            st.Page(str(_pages / "watersheds.py"), title="Watersheds", icon="🌊"),
            st.Page(str(_pages / "sites.py"), title="Sites", icon="📍"),
            st.Page(str(_pages / "process_units.py"), title="Process Units", icon="🟦"),
            st.Page(str(_pages / "equipment.py"), title="Equipment", icon="🟧"),
            st.Page(str(_pages / "equipment_models.py"), title="Equipment Models", icon="™️"),
            st.Page(
                str(_pages / "data_acquisition_systems.py"),
                title="Data Acquisition Systems",
                icon="📡"
            ),
            st.Page(str(_pages / "control_loops.py"), title="Control Loops", icon="🔄"),
            st.Page(str(_pages / "channels.py"), title="Channels", icon="📺"),
            st.Page(str(_pages / "parameters.py"), title="Parameters", icon="⚗️"),
            st.Page(str(_pages / "binning_axes.py"), title="Binning Axes", icon="🗃️"),
            st.Page(str(_pages / "annotations.py"), title="Annotations", icon="🏷️"),
            st.Page(str(_pages / "laboratories.py"), title="Laboratories", icon="🔬"),
            st.Page(str(_pages / "persons.py"), title="Persons", icon="👤"),
            st.Page(str(_pages / "procedures.py"), title="Procedures", icon="📋"),
        ],
        "Associations": [
            st.Page(
                str(_pages / "equipment_model_associations.py"),
                title="Equipment - Equipment Model Associations",
                icon="🔗",
            ),
            st.Page(
                str(_pages / "parameter_units.py"),
                title="Parameter - Unit Associaitons",
                icon="📐",
            ),
        ],
        "Signal Sources": [
            st.Page(
                str(_pages / "signal_interfaces.py"),
                title="Signal Interfaces",
                icon="🔌",
            ),

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
            st.Page(str(_pages / "operation_kinds.py"), title="Operation Kinds"),
        ],
    }
)

# Persistent sidebar content — added after st.navigation() per Streamlit ≥1.41 requirement
with st.sidebar:
    user = get_current_user()
    if user:
        st.write(f"Logged in as: **{user['full_name']}**")
    if st.button("Sign out"):
        logout()

pg.run()
