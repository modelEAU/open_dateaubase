---
phase: 06-deployment-setup
plan: 01
subsystem: infrastructure
tags: [docker, uv, python, mssql, odbc, streamlit, fastapi]

requires:
  - phase: 05-timeseries-viewer
    provides: app/Home.py entry point and app/ directory structure confirmed

provides:
  - Dockerfile.api — uv-based FastAPI image with MSSQL ODBC 18
  - Dockerfile.app — uv-based Streamlit image (no ODBC driver)

affects: [06-02-docker-compose]

tech-stack:
  added: []
  patterns: [uv-docker, dockerfile-layer-caching-pyproject-first]

key-files:
  created:
    - Dockerfile.api
    - Dockerfile.app

key-decisions:
  - "python:3.12-slim base (matches requires-python = >=3.12 in pyproject.toml)"
  - "uv sync --extra api / --extra app for isolated dependency sets"
  - "app image has no MSSQL ODBC driver — communicates with API over HTTP only"
  - "Layer caching order: pyproject.toml + uv.lock + src/ before uv sync, then remaining sources"
  - "API_BASE_URL defaulted to http://api:8000/api/v1 in Dockerfile.app for Docker Compose networking"
  - "New Dockerfile.api created instead of modifying legacy Dockerfile (wrong entry point + missing requirements.txt)"

issues-created: []

duration: 2min
completed: 2026-03-06
---

# Phase 6 Plan 1: Dockerfiles Summary

**Production-ready Dockerfile.api (python:3.12-slim + MSSQL ODBC 18 + uv) and Dockerfile.app (python:3.12-slim + uv, no ODBC) — both build and import successfully**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-06T19:14:07Z
- **Completed:** 2026-03-06T19:16:08Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `Dockerfile.api` builds cleanly: installs MSSQL ODBC 18 via Microsoft apt repo, runs `uv sync --extra api`, imports `api.main` successfully at container runtime
- `Dockerfile.app` builds cleanly: no ODBC driver, runs `uv sync --extra app` (streamlit, httpx, plotly only), 118 MB smaller than API image
- Layer caching optimized: pyproject.toml + uv.lock + src/ copied before `uv sync` so dependency layer is cached on code-only changes

## Task Commits

1. **Task 1: Dockerfile.api** — `c81509d` (feat)
2. **Task 2: Dockerfile.app** — `2062ed1` (feat)

## Files Created/Modified

- `Dockerfile.api` — FastAPI service image with MSSQL ODBC 18, uv, python:3.12-slim
- `Dockerfile.app` — Streamlit service image, minimal deps, no ODBC driver

## Decisions Made

- Created `Dockerfile.api` as a new file instead of fixing the legacy `Dockerfile` (which had wrong entry point `api_metadata.main:app` and referenced a non-existent `requirements.txt`)
- Used `python:3.12-slim` to match `requires-python = ">=3.12"` in pyproject.toml (legacy Dockerfile used 3.11)
- Layer cache order: copy `pyproject.toml`, `uv.lock`, `src/` → run `uv sync` → copy remaining sources. This ensures the heavy dependency install layer is cached unless deps change
- `Dockerfile.app` copies only `app/` directory (not the full project), keeping the image lean
- `API_BASE_URL=http://api:8000/api/v1` set as ENV default so the app works in Docker Compose without extra config; overridable at runtime

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Both images verified: `docker images | grep dateaubase` shows both `dateaubase-api:test` and `dateaubase-app:test`
- `api.main` imports cleanly inside the container
- Ready for 06-02-PLAN.md (docker-compose.yml update, .env.example, README deployment section)

---
*Phase: 06-deployment-setup*
*Completed: 2026-03-06*
