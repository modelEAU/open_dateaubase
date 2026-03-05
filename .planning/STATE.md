# Project State

## Current Position

- **Active milestone**: Milestone 1 — Frontend Web App (v1.0)
- **Active phase**: Phase 04 — Business Forms
- **Plan**: 1 of 9 complete in current phase
- **Status**: In progress
- **Last activity**: 2026-03-05 — Completed 04-01 (2 tasks, Lookup API Foundation)

Progress: █████░░░░░ 53% (10/19 plans)

## Accumulated Decisions

- **API communication**: Streamlit app calls FastAPI over HTTP (not direct DB imports). Clean separation, testable, future-proof.
- **Auth approach**: Session-state stub for now (`st.session_state["user"]`). Login page always succeeds. Real auth wired in later.
- **Primary UI framework**: Streamlit multipage app (`app/pages/` directory structure)
- **Package management**: uv with optional extras — run `uv sync --extra api --extra app --extra dev` together to avoid extras pruning each other
- **Test strategy**: API client layer tested with pytest + httpx mocking; UI verified via human checkpoint at end of each page plan
- **Deployment target**: Docker Compose (`docker-compose up`) — one command for DB + API + App
- **MSSQL insert ID**: Use `SELECT @@IDENTITY` after INSERT (pyodbc; OUTPUT clause not usable with cursor.fetchone() in same execute)
- **UI Pattern - REFERENCE DATA**: Form-based CRUD (not inline editing) — table for display + dialog forms for create/edit
- **Channel schema design**: All ChannelIn fields are optional (nullable) since Channel is a flexible linking table - this allows partial updates without requiring all FK fields
- **Lookup endpoint placement**: Lookup endpoints placed under /channels/lookup/* to maintain consistency with existing /sites/lookup/list pattern
- **Ingest/campaign lookup placement**: Ingest lookup routes added inline to ingest.py (/ingest/lookup/*) and campaigns.py (/campaigns/lookup) — no separate router needed
- **lookup_repository.py**: Centralized module for all reference-data queries; all lookup functions take conn as first param, return list[dict] with snake_case keys
- **Datetime form fields**: Use combined st.date_input + st.time_input with datetime.datetime.combine() for timestamp inputs
- **Channel dropdown labels**: Combine parameter name and equipment identifier for descriptive labels (e.g., "pH (Sensor-A1)")

## Deferred Issues

- Marimo pages for scientific exploration (post v1.0)
- Plotly Dash dashboards (post v1.0)
- Real authentication layer (post v1.0, Phase D of schema work noted as separate concern)
- Sensor status management UI (post v1.0)
- Lineage visualizer (post v1.0)

## Blockers / Concerns

- **Checkpoint**: Human verification required for form-based CRUX redesign
- API has no authentication — Streamlit app will also be open. Acceptable for now (internal/trusted use).
- `author_person_id` in annotation forms must be manually entered by user (no auth context yet).
- Dynamic SQL f-strings in some repos are a SQL injection risk — do not expose filter fields as raw user input in the UI; always use pre-validated options from API dropdowns.

## Session Continuity

- **Last session**: 2026-03-05T21:18:16Z
- **Stopped at**: Completed 04-01-PLAN.md - Lookup API Foundation
- **Resume file**: None
- **Next action**: Continue with 04-02 (EquipmentModel CRUD page)

## Brief Alignment

Backend (FastAPI + MSSQL) is complete at v2.1.0. Frontend Streamlit app under construction. Building a Streamlit multipage app that calls the existing API. Target users are non-IT graduate students.

**Status**: Phase 04 in progress (1/9 plans). Lookup API foundation complete — 7 GET lookup endpoints live for Unit, Laboratory, Procedures, Sample, SamplingPoint, EquipmentEvent, Campaign. All ingest form plans (04-02 through 04-09) can now build dropdowns from API.
