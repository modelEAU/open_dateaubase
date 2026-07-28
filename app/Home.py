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

from app.api_client import (
    APIError,
    get_health,
    list_analysis_series_lookup,
    list_channels,
    list_das_lookup,
    list_laboratories_lookup,
    list_persons_lookup,
    list_sampling_points_lookup,
    list_signal_interfaces_lookup,
    list_sites_lookup,
)
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

    _onboarding_panel()


def _onboarding_panel() -> None:
    # Session-scoped dismiss
    if st.session_state.get("onboarding_dismissed", False):
        return

    try:
        sps = list_sampling_points_lookup()
        sites = list_sites_lookup()
        persons = list_persons_lookup()
        ch_resp = list_channels(page_size=1)
        channels = ch_resp.get("items", []) if isinstance(ch_resp, dict) else (ch_resp or [])
        analysis_series = list_analysis_series_lookup()
    except Exception:
        return  # API down — don't crash Home

    # Auto-hide once any ingestable Stream exists
    if channels or analysis_series:
        return

    # Fetch sensor/lab counts — failures are non-fatal
    das: list = []
    signal_interfaces: list = []
    laboratories: list = []
    try:
        das = list_das_lookup()
    except Exception:
        pass
    try:
        signal_interfaces = list_signal_interfaces_lookup()
    except Exception:
        pass
    try:
        laboratories = list_laboratories_lookup()
    except Exception:
        pass

    def _step(items: list, done_label: str, todo_label: str, url: str) -> str:
        if items:
            return f"- ✓ {done_label}"
        return f"- ○ [{todo_label}]({url})"

    # Default data-type selection
    if "onboarding_data_type" not in st.session_state:
        st.session_state["onboarding_data_type"] = "Both"

    with st.container(border=True):
        st.markdown("### Get started")

        st.radio(
            "What will you load?",
            ["Lab", "Sensor", "Both"],
            horizontal=True,
            key="onboarding_data_type",
            help="Lab data arrives as results against samples; sensor data arrives as a continuous signal on a channel. This only tailors the setup steps suggested below.",
        )

        data_type: str = st.session_state["onboarding_data_type"]

        foundation = (
            "Complete these foundation steps to start loading data:\n\n"
            + _step(sites, "🏭 Site created", "Create a Site", "sites") + "\n"
            + _step(persons, "👤 Person added", "Add a Person", "persons") + "\n"
            + _step(sps, "📍 Sampling location added", "Add a Sampling Location", "sampling_locations")
        )
        st.markdown(foundation)

        if data_type in ("Sensor", "Both"):
            sensor_steps = (
                "\n**Sensor setup:**\n\n"
                + _step(das, "📡 DAS added", "Add a Data Acquisition System (DAS)", "data_acquisition_systems") + "\n"
                + _step(signal_interfaces, "🔌 Signal Interface added", "Add a Signal Interface", "signal_interfaces") + "\n"
                + _step(channels, "📊 Channel added", "Add a Channel (Field System Wizard)", "field_system_wizard")
            )
            st.markdown(sensor_steps)

        if data_type in ("Lab", "Both"):
            lab_steps = (
                "\n**Lab setup:**\n\n"
                + _step(laboratories, "🧪 Laboratory added", "Add a Laboratory", "laboratories") + "\n"
                + _step(analysis_series, "🔬 Lab Experiment added", "Add a Lab Experiment", "lab_ingest")
            )
            st.markdown(lab_steps)

        st.caption("💡 Campaign creation is optional — you can ingest data without one.")
        st.markdown(
            "_Once an ingestable Stream (Channel or AnalysisSeries) exists, this panel will disappear._"
        )

        if st.button("Dismiss", key="dismiss_onboarding"):
            st.session_state["onboarding_dismissed"] = True
            st.rerun()


_pages = Path(__file__).resolve().parent / "pages"  # resolve so st.Page paths are absolute under AppTest
_user = get_current_user()

_nav = {
        "": [
            st.Page(_home, title="Home", icon="🏠"),
        ],
        "Operations": [
            st.Page(str(_pages / "sensor_ingest.py"), title="Insert Sensor Data", icon="📡"),
            st.Page(str(_pages / "lab_ingest.py"), title="Insert Lab Data", icon="🧪"),
            st.Page(str(_pages / "lab_panels.py"), title="Lab Panels", icon="🗂️"),
            st.Page(str(_pages / "mapper.py"), title="Import Data (Mapper)", icon="📥"),
            st.Page(str(_pages / "explore.py"), title="Visualize Data", icon="📊"),
            st.Page(str(_pages / "equipment_move.py"), title="Move a sensor", icon="➡️"),
            st.Page(str(_pages / "maintenance_control_chart.py"), title="Maintenance Control Chart", icon="📉"),
        ],
        "Reports": [
            st.Page(str(_pages / "campaign_story.py"), title="Campaign Story", icon="📖"),
            st.Page(str(_pages / "equipment_story.py"), title="Equipment Story", icon="🔧"),
            st.Page(str(_pages / "data_health.py"), title="Data Health", icon="🩺"),
            st.Page(str(_pages / "browse_tables.py"), title="Browse Tables", icon="🗄️"),
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
        "Events": [
            st.Page(str(_pages / "events.py"), title="Events", icon="⚡"),
            st.Page(str(_pages / "event_kinds.py"), title="Event Kinds", icon="🏷️"),
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
            st.Page(str(_pages / "sample_material_kinds.py"), title="Sample Materials"),
            st.Page(str(_pages / "sample_collection_kinds.py"), title="Sample Collection Kinds"),
            st.Page(str(_pages / "quality_codes.py"), title="Quality Codes"),
            st.Page(str(_pages / "units.py"), title="Units"),
            st.Page(str(_pages / "bin_kinds.py"), title="Bin Kinds"),
            st.Page(str(_pages / "operation_kinds.py"), title="Operation Kinds"),
        ],
    }

if _user:
    pg = st.navigation(_nav)
else:
    # Same URL paths as the authenticated nav (title/icon-derived), all routed
    # to the login screen, so a browser refresh on any page resolves instead
    # of hitting Streamlit's native "Page not found" fallback.
    pg = st.navigation(
        {
            section: [
                st.Page(_login, title=p.title, icon=p.icon or None, url_path=p.url_path or None)
                for p in pages
            ]
            for section, pages in _nav.items()
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
