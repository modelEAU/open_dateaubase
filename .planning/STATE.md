# Project State

## Current Position

- **Active milestone**: Milestone 1 — Frontend Web App (v1.0)
- **Active phase**: Phase 02 — CRUD Pages: Reference Data
- **Plan**: 2 of 4 complete in current phase
- **Status**: At checkpoint - awaiting form-based CRUD redesign
- **Last activity**: 2026-03-05 — Completed Tasks 1-2 of 02-04-PLAN.md (Equipment and Campaigns pages with inline editor)

Progress: █████░░░░░ 50% (5/10 plans)

## Checkpoint Feedback (02-04 Task 3)

**Status**: Human verification completed on inline data editor pattern.

**Feedback Summary**:
The inline data editor (st.data_editor) works well for READ and DELETE operations, but CREATE and UPDATE require form-based interfaces for better UX:

1. **New Row Button**: Opens a form dialog for creating new items
2. **Edit Button**: Select a row, click edit, form pre-populates with that row's data
3. **Form Fields**:
   - Show all fields from the row
   - Required fields marked with red star (*)
   - Foreign key fields show names/descriptions (not raw IDs)
   - Dropdowns/populated from related tables for FKs
4. **Validation Button**: Shows validation errors clearly
5. **Send Button**: Submits the form
6. **HTTP Methods**: POST for create, PATCH for update

**Decision**: Adopt form-based CRUD pattern for all reference data pages (Sites, Equipment, Campaigns). This requires:
- New API lookup endpoints for FK dropdowns
- PATCH endpoints for partial updates
- New form components (crud_form.py, form_dialog.py)
- Redesign of all three CRUD pages

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

- **Checkpoint Decision Required**: Form-based CRUD redesign is significant scope change mid-phase. Gap closure plan created at `.planning/phases/02-crud-reference/02-04-gap-PLAN.md`.
- API has no authentication — Streamlit app will also be open. Acceptable for now (internal/trusted use).
- `author_person_id` in annotation forms must be manually entered by user (no auth context yet).
- Dynamic SQL f-strings in some repos are a SQL injection risk — do not expose filter fields as raw user input in the UI; always use pre-validated options from API dropdowns.

## Session Continuity

- **Last session**: 2026-03-05T15:30:00Z
- **Stopped at**: Checkpoint for 02-04-PLAN.md - human verification of inline CRUD, feedback received
- **Resume file**: .planning/phases/02-crud-reference/02-04-gap-PLAN.md
- **Next action**: Review and approve gap closure plan for form-based CRUD redesign

## Brief Alignment

Backend (FastAPI + MSSQL) is complete at v2.1.0. Frontend does not exist. Building a Streamlit multipage app that calls the existing API. Target users are non-IT graduate students.

**Current Challenge**: Inline editing pattern requires redesign to form-based CRUD based on user feedback. This affects all three reference data pages (Sites, Equipment, Campaigns).
