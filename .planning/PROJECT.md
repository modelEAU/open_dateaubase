# open_datEAUbase — Project Overview

## What We're Building

A web-based frontend for the open_datEAUbase water quality database, used by masters and PhD students to manage, browse, and import environmental monitoring data. The database backend (MSSQL) and REST API (FastAPI) already exist.

## Users

Graduate students and researchers — not IT professionals. Clarity and simplicity are the highest priorities. Users understand water quality concepts but not database schemas.

## Architecture

```
[Browser] → [Streamlit App] → [FastAPI API (HTTP)] → [MSSQL Database]
```

- **Streamlit** as the primary UI framework (multipage app)
- **FastAPI** (existing) as the data layer — app calls it over HTTP
- **MSSQL / Azure SQL Edge** as the database (existing)
- **Docker Compose** for local dev and deployment

## Core Goals

1. CRUD pages for all major database entities (Channels, Sites, Equipment, Campaigns, Annotations)
2. Business operation forms (sensor ingest, lab ingest) with dropdowns populated from the API
3. Timeseries viewer with date range selection and charting
4. Auth-ready: login page stub so real authentication can be plugged in later
5. Well-tested: API client layer tested with pytest; UI forms tested via Playwright or manual checkpoints
6. Easy deployment: single `docker-compose up` command starts DB + API + App

## What Already Exists

- `api/` — FastAPI app with repositories, services, endpoints
- `docker-compose.yml` — MSSQL dev database
- `tests/` — pytest test suite (unit, contract, integration)
- `pyproject.toml` — uv-managed Python 3.12 project

## Tech Constraints

- Python 3.12+, `uv` package manager
- Sync (no async/await) consistent with existing API style
- Streamlit primary UI; Marimo and Plotly Dash are candidates for specific pages (deferred)
- No external auth provider yet — stub only

## Key Principle

If a grad student has to read a docstring to understand a button, the UI has failed.
