# Roadmap — open_datEAUbase Frontend

## Milestone 1: Frontend Web App (v1.0)

Goal: A fully functional Streamlit app that lets graduate students manage and import water quality data without knowing the database schema.

---

### Phase 01: App Foundation
Research: No | Dependencies: None

Set up the `app/` directory, API client, configuration, and auth stub. This is the skeleton everything else attaches to.

Deliverables:
- `app/` directory with Streamlit multipage structure
- `app/api_client.py` — typed functions for all API routes (httpx-based)
- `app/config.py` — settings loaded from env (API URL, etc.)
- `app/auth.py` — session-state auth stub (always-logged-in placeholder)
- `app/Home.py` — Streamlit entry point with navigation
- pytest tests for `api_client.py`

---

### Phase 02: CRUD Pages — Reference Data
Research: No | Dependencies: Phase 01

Simple CRUD pages for entities with few foreign keys.

Deliverables:
- Sites page (list, create, edit, delete)
- Equipment page (list, create, edit, delete)
- Campaigns page (list, create, edit, delete)
- Reusable CRUD table component

---

### Phase 03: CRUD Pages — Core Entities
Research: No | Dependencies: Phase 02

CRUD pages for entities with multiple FK dropdowns (populated from API).

Deliverables:
- Channels page (list with filter, create with FK dropdowns for Equipment/Parameter/ProcessingDegree)
- Annotations page (list, create, edit, delete)

---

### Phase 04: Business Forms — Data Ingestion
Research: No | Dependencies: Phase 01

User-facing forms for importing data. No schema knowledge required from the user.

Deliverables:
- Sensor ingest form: select equipment + parameter from dropdowns, paste/upload CSV of timestamped values
- Lab ingest form: select sample + laboratory + procedure, enter results per parameter

---

### Phase 05: Timeseries Viewer
Research: No | Dependencies: Phase 01

Interactive channel explorer with date range filtering and Plotly charts.

Deliverables:
- Channel selector with search
- Date range picker
- Plotly line chart rendered in Streamlit
- Download button for raw data (CSV)

---

### Phase 06: Deployment Setup
Research: No | Dependencies: Phase 01–05

Make the full stack runnable with `docker-compose up`.

Deliverables:
- `Dockerfile.app` for the Streamlit app
- Updated `docker-compose.yml` with `app` service
- `.env.example` covering all required vars
- README section on local dev + production deployment

---

## Future (Post v1.0)

- **Auth layer**: Replace stub with real authentication (JWT, institutional SSO)
- **Marimo pages**: Interactive exploratory analysis notebooks for power users
- **Plotly Dash dashboards**: Real-time monitoring dashboards
- **Sensor status management UI**: View and update equipment status streams
- **Lineage viewer**: Visual graph of data processing lineage
