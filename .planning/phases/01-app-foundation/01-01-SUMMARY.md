---
phase: 01-app-foundation
plan: 01
subsystem: frontend-foundation
tags: [streamlit, httpx, plotly, pydantic, python-dotenv]

requires: []
provides:
  - app/ directory with Streamlit multipage skeleton
  - app/config.py Settings dataclass with env-backed defaults
  - app/api_client.py typed HTTP client wrapping all FastAPI routes
  - pyproject.toml [app] optional extras (streamlit, httpx, plotly)
affects: [01-02, 01-03, 02, 03, 04, 05, 06]

tech-stack:
  added: [streamlit>=1.40, httpx>=0.28, plotly>=5.24]
  patterns:
    - Settings dataclass singleton loaded from env with .env.local fallback
    - APIError exception class for non-2xx and connection failures
    - One typed function per API route using httpx.Client context manager

key-files:
  created:
    - app/__init__.py
    - app/config.py
    - app/api_client.py
    - app/components/__init__.py
    - app/pages/.gitkeep
  modified:
    - pyproject.toml

key-decisions:
  - "Used plain dataclass for Settings instead of pydantic-settings (zero new deps, same behaviour)"
  - "All API functions open a fresh httpx.Client context per call (simple, no connection pool state to manage)"
  - "app extras kept isolated from main deps so CI/API tests run without browser stack"

patterns-established:
  - "APIError pattern: raise APIError(status_code, message) on any non-2xx or ConnectError"
  - "Filter params always via httpx params= dict, never f-string interpolation into URLs"

issues-created: []

duration: 2min
completed: 2026-03-05
---

# Phase 01 Plan 01: Project Structure + API Client — Summary

**`app/` multipage skeleton + typed httpx API client covering all 20 FastAPI routes, with env-backed Settings dataclass and isolated optional extras**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-05T14:41:18Z
- **Completed:** 2026-03-05T14:43:10Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created `app/` directory structure (multipage Streamlit layout: `pages/`, `components/`)
- Added `[app]` optional extras to pyproject.toml (`streamlit>=1.40`, `httpx>=0.28`, `plotly>=5.24`)
- Implemented `app/config.py` with a `Settings` dataclass singleton reading `API_BASE_URL`, `APP_TITLE`, `APP_VERSION` from env with sensible defaults
- Implemented `app/api_client.py` with `APIError` exception class and one typed function per API route (health, sites, equipment, campaigns, channels, timeseries, annotations, ingestion)

## Task Commits

1. **Task 1: Create app/ skeleton and update pyproject.toml** — `8c86218` (feat)
2. **Task 2: Write app/api_client.py** — `21be8a4` (feat)

## Files Created/Modified

- `app/__init__.py` — empty package init
- `app/config.py` — Settings dataclass with env defaults, .env.local loading
- `app/components/__init__.py` — empty package init (components added in later plans)
- `app/pages/.gitkeep` — tracks pages/ directory (pages added in later plans)
- `app/api_client.py` — APIError class + 20 typed functions wrapping all API routes
- `pyproject.toml` — added `[app]` optional-dependencies group

## Decisions Made

- Used a plain `dataclass` for `Settings` instead of `pydantic-settings` to avoid a new dependency — identical behaviour for this use case.
- Each API function opens its own `httpx.Client` context manager rather than a shared client. Simple, avoids any connection-pool state issues across Streamlit reruns.
- `httpx` placed in `[app]` extras only (not `[dev]`), keeping the core test suite free of the browser stack.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

`tests/api/contract/` imports `pyodbc` at module level; those tests error-out when running with only `--extra app` installed (pre-existing issue, not introduced here). Unit tests at `tests/unit/` pass cleanly with 47/47.

## Next Phase Readiness

- `app/api_client.py` and `app/config.py` are in place and importable
- Ready for **01-02-PLAN.md** (API client TDD tests)

---
*Phase: 01-app-foundation*
*Completed: 2026-03-05*
