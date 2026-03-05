# Project State

## Current Position

- **Active milestone**: Milestone 1 — Frontend Web App (v1.0)
- **Active phase**: Phase 03 — Core Entities
- **Plan**: 2 complete in current phase
- **Status**: Completed 03-02 Channels and Annotations CRUD Pages
- **Last activity**: 2026-03-05 — Completed 03-02 (3 tasks, Channels and Annotations UI)

Progress: ██████░░░░ 80% (8/10 plans)

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

- **Last session**: 2026-03-05T18:48:00Z
- **Stopped at**: Completed 03-02-PLAN.md - Channels and Annotations CRUD Pages
- **Resume file**: None
- **Next action**: Continue with Phase 03 Plan 03 or verify work

## Brief Alignment

Backend (FastAPI + MSSQL) is complete at v2.1.0. Frontend Streamlit app under construction. Building a Streamlit multipage app that calls the existing API. Target users are non-IT graduate students.

**Status**: Phase 03 Plans 01-02 complete - Channel write API, lookup endpoints, and CRUD UI pages are ready. Channels and Annotations fully functional in Streamlit frontend.
