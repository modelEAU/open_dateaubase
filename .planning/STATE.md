# Project State

## Current Position

- **Active milestone**: Milestone 1 — Frontend Web App (v1.0)
- **Active phase**: Phase 02 — CRUD Pages: Reference Data
- **Plan**: 3 of 4 complete in current phase
- **Status**: At checkpoint - awaiting human verification of form-based CRUD
- **Last activity**: 2026-03-05 — Completed gap closure plan (8 tasks, form-based CRUD redesign)

Progress: █████░░░░░ 60% (6/10 plans)

## Accumulated Decisions

- **API communication**: Streamlit app calls FastAPI over HTTP (not direct DB imports). Clean separation, testable, future-proof.
- **Auth approach**: Session-state stub for now (`st.session_state["user"]`). Login page always succeeds. Real auth wired in later.
- **Primary UI framework**: Streamlit multipage app (`app/pages/` directory structure)
- **Package management**: uv with optional extras — run `uv sync --extra api --extra app --extra dev` together to avoid extras pruning each other
- **Test strategy**: API client layer tested with pytest + httpx mocking; UI verified via human checkpoint at end of each page plan
- **Deployment target**: Docker Compose (`docker-compose up`) — one command for DB + API + App
- **MSSQL insert ID**: Use `SELECT @@IDENTITY` after INSERT (pyodbc; OUTPUT clause not usable with cursor.fetchone() in same execute)
- **UI Pattern - REFERENCE DATA**: Form-based CRUD (not inline editing) — table for display + dialog forms for create/edit

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

- **Last session**: 2026-03-05T17:55:02Z
- **Stopped at**: Checkpoint for 02-04-GAP-CLOSURE.md - human verification of form-based CRUD
- **Resume file**: None (gap closure complete, awaiting verification)
- **Next action**: Human verification of form-based CRUD pages

## Brief Alignment

Backend (FastAPI + MSSQL) is complete at v2.1.0. Frontend does not exist. Building a Streamlit multipage app that calls the existing API. Target users are non-IT graduate students.

**Current Challenge**: Human verification of form-based CRUD redesign required before proceeding to Phase 03.
