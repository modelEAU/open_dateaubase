# Roadmap — open_datEAUbase Frontend

## Milestone 1: Frontend Web App (v1.0)

Goal: A fully functional Streamlit app that lets graduate students manage and import water quality data without knowing the database schema.

---

### Phase 01: App Foundation *(Complete — 3/3 plans, 2026-03-05)*

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

### Phase 02: CRUD Pages — Reference Data *(In progress — 2/4 plans)*
Research: No | Dependencies: Phase 01

Simple CRUD pages for entities with few foreign keys.

Deliverables:
- Sites page (list, create, edit, delete)
- Equipment page (list, create, edit, delete)
- Campaigns page (list, create, edit, delete)
- Reusable CRUD table component

---

### Phase 03: CRUD Pages — Core Entities *(In Progress — 2/2 plans)*
Research: No | Dependencies: Phase 02

CRUD pages for entities with multiple FK dropdowns (populated from API).

Deliverables:
- ✅ Channels page (list with filter, create with FK dropdowns for Equipment/Parameter/ProcessingDegree)
- ✅ Annotations page (list, create, edit, delete)

---

### Phase 04: Business Forms — Data Ingestion *(Complete — 9/9 plans)*

Research: No | Dependencies: Phase 01, Phase 02, Phase 03

User-facing forms for importing all data types. No schema knowledge required from the user.
Covers scalar, vector (spectral), matrix (2D distribution), and image sensor data,
as well as lab analysis results with inline sample creation.

Deliverables:

- Lookup API foundation: Unit, Laboratory, Procedures, Sample, SamplingPoint,
  EquipmentEvent, Campaign lookup endpoints + api_client functions
- EquipmentModel CRUD page (`6_Equipment_Models.py`) — register new sensor models
- Parameter CRUD page (`7_Parameters.py`) — register new measurement parameters
- ✅ Campaign enhancement: equipment deployment management (CampaignEquipment +
  CampaignSamplingLocation + EquipmentInstallation auto-created at campaign start time)
- Measurement Axes page (`8_Binning_Axes.py`) — define spectral/distribution bin axes
  for vector and matrix channels (ValueBinningAxis + ValueBin)
- ✅ Sensor ingest page (`9_Sensor_Ingest.py`) - Scalar, Vector, Matrix modes complete:
  - Scalar: paste/upload CSV of timestamp+value rows → POST /ingest/sensor
  - Vector: select axis, upload spectrum CSV (timestamp + N bin columns) → POST /ingest/sensor-vector
  - Matrix: select row+col axes, upload 2D CSV → POST /ingest/sensor-matrix
  - ✅ Image: upload image file with timestamp → POST /ingest/sensor-image
- Lab ingest page (`10_Lab_Ingest.py`): campaign/lab/procedure dropdowns, inline sample
  creation, st.data_editor with duplicate-row shortcut → POST /ingest/lab
- POST /ingest/samples endpoint for inline sample creation
- ✅ Vector/Matrix ingest API: insert_vector_values, insert_matrix_values, upsert_channel_axis
- Image ingest infrastructure: configurable upload directory, Pillow thumbnail generation

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

### Phase 06: Deployment Setup *(Complete — 2/2 plans, 2026-03-06)*

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
