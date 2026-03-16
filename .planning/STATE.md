---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-16T19:25:49.493Z"
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 27
  completed_plans: 28
  percent: 100
---

# Project State

## Current Position

- **Active milestone**: Milestone 2 — Observation-Centric Schema (v2.2.0)
- **Active phase**: Phase 07 — Observation Migration
- **Plan**: 5 of 7 complete in current phase
- **Status**: In progress
- **Last activity**: 2026-03-16 — Completed 07-05-PLAN.md (API repository updates — Observation-centric insert pattern)

Progress: [██████████] 100%

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
- **add_new select pattern**: Field dicts with `"add_new": {"title", "fields", "on_create"}` trigger a sub-form inside the dialog; newly-created items pre-selected in parent form
- **Unit creation endpoint**: POST /ingest/lookup/units (alongside GET lookup — no new router)
- **Sensor ingest tabs**: Three tabs (Scalar/Vector/Matrix) on 9_Sensor_Ingest.py with isolated session state per tab
- **CSV parsing helpers**: Dedicated parse functions for scalar, vector, and matrix data with header detection and validation
- **Image ingest pattern**: Multipart upload to POST /ingest/sensor-image, file stored on disk, metadata+thumbnail in ValueImage
- **File storage approach**: Store file content on disk, only path and metadata in DB (ValueImage.StoragePath, FileSizeBytes, etc.)
- **Optional dependencies**: Pillow for image metadata extraction is optional; graceful fallback if not installed
- [Phase 04-business-forms]: File storage on disk with metadata in DB, not BLOB storage
- [Phase 04-business-forms]: Pillow made optional with graceful fallback for image metadata
- [Phase 07-observation-migration]: Observation table: BIGINT IDENTITY PK, UNIQUE on (Channel_ID, Timestamp, DataType), transaction stays open through 07-03
- [Phase 07-observation-migration]: Value restructure: drop Value_ID+Channel_ID+Timestamp; Observation_ID becomes sole PK with FK to Observation
- [Phase 07]: Observation.DataType max_length:10 to satisfy schema validator (VARCHAR(10) per DDL plan)
- [Phase 07-observation-migration]: ValueVector/ValueMatrix use SELECT DISTINCT for Observation backfill; ValueImage skips DISTINCT (UQ enforces uniqueness); ValueImage drops constraints in UQ->FK->PK->IDENTITY order
- [Phase 07-observation-migration]: Two-step insert pattern: INSERT Observation (OUTPUT INSERTED.Observation_ID) then INSERT payload table — no Channel_ID or Timestamp in Value/ValueVector/ValueMatrix/ValueImage
- [Phase 07-observation-migration 07-03]: Rollback script uses mssql_rollback.sql naming (CI test constraint); views dropped before Value is touched and recreated after; Value_ID/ValueImage_ID restored as ROW_NUMBER surrogates (SQL Server cannot ADD IDENTITY to existing columns)

## Deferred Issues

- Marimo pages for scientific exploration (post v1.0)
- Plotly Dash dashboards (post v1.0)
- Real authentication layer (post v1.0, Phase D of schema work noted as separate concern)
- Sensor status management UI (post v1.0)
- Lineage visualizer (post v1.0)

## Blockers / Concerns

- **Checkpoint**: Human verification required for Vector/Matrix ingest functionality
- API has no authentication — Streamlit app will also be open. Acceptable for now (internal/trusted use).
- `author_person_id` in annotation forms must be manually entered by user (no auth context yet).
- Dynamic SQL f-strings in some repos are a SQL injection risk — do not expose filter fields as raw user input in the UI; always use pre-validated options from API dropdowns.

## Session Continuity

- **Last session**: 2026-03-16
- **Stopped at**: Completed 07-05-PLAN.md — API ingestion repository updates (Observation-centric inserts)
- **Resume file**: None
- **Next action**: Execute 07-06-PLAN.md (integration + contract test updates)

## Brief Alignment

Backend (FastAPI + MSSQL) is complete at v2.1.0. Frontend Streamlit app complete (phases 01–05). Phase 06 deployment setup complete. Full stack launches with `docker-compose up -d db api app`. Now beginning Phase 07: Observation-Centric Schema migration to v2.2.0.

**Status**: Milestone 1 — Frontend Web App (v1.0) — fully complete. Phase 07 (Observation Migration) in progress — 5 of 7 plans done.
