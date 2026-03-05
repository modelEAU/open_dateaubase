---
phase: 02-crud-reference
plan: 01
subsystem: api
tags: [fastapi, pyodbc, pydantic, sites, crud]

requires:
  - phase: 01-app-foundation
    provides: API structure, parameterized query patterns, HTTPException conventions

provides:
  - POST /sites (201) — create site
  - PUT /sites/{site_id} (200) — update site
  - DELETE /sites/{site_id} (204) — delete site
  - SiteIn Pydantic schema
  - insert_site, update_site, delete_site repository functions

affects: [02-02-crud-reference, 02-03-crud-reference, 02-04-crud-reference]

tech-stack:
  added: []
  patterns: ["@@IDENTITY for last insert ID (pyodbc/MSSQL)", "conn.commit() after each write"]

key-files:
  created: []
  modified:
    - api/v1/schemas/metadata.py
    - api/v1/repositories/site_repository.py
    - api/v1/endpoints/sites.py

key-decisions:
  - "Use SELECT @@IDENTITY (not SCOPE_IDENTITY) — pyodbc does not support OUTPUT clause row return directly"

patterns-established:
  - "Write repo pattern: execute INSERT, SELECT @@IDENTITY, commit, return get_by_id()"
  - "Write endpoint pattern: call repo fn, raise 404 if None/False, return result"

issues-created: []

duration: 1min
completed: 2026-03-05
---

# Phase 02 Plan 01: API Write Routes — Sites Summary

**POST/PUT/DELETE for Sites added to FastAPI using pyodbc parameterized queries and @@IDENTITY for insert ID retrieval**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-05T15:14:04Z
- **Completed:** 2026-03-05T15:15:27Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `SiteIn` Pydantic model (all optional except `name`) added to schemas
- `insert_site`, `update_site`, `delete_site` in `site_repository.py` — fully parameterized, `conn.commit()` after each write
- `POST /sites` (201), `PUT /sites/{site_id}` (200), `DELETE /sites/{site_id}` (204) in endpoints
- 47 existing unit tests still pass, app imports cleanly

## Task Commits

1. **Task 1: SiteIn schema + repository write functions** — `af5a62c` (feat)
2. **Task 2: POST/PUT/DELETE site endpoints** — `e7cfb86` (feat)

## Files Created/Modified

- `api/v1/schemas/metadata.py` — added `SiteIn` model after `SiteOut`
- `api/v1/repositories/site_repository.py` — added `insert_site`, `update_site`, `delete_site`
- `api/v1/endpoints/sites.py` — added three write endpoints; imported `SiteIn`

## Decisions Made

- `SELECT @@IDENTITY` used to retrieve the new Site_ID after INSERT. MSSQL's `OUTPUT` clause cannot be used directly with pyodbc cursor.fetchone() in the same execute call, and `SCOPE_IDENTITY()` requires a separate SELECT — `@@IDENTITY` is safe here since we hold the connection.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Sites write API is complete; Streamlit CRUD page can now call POST/PUT/DELETE.
- Ready for `02-02-PLAN.md` (Equipment + Campaigns write routes).

---
*Phase: 02-crud-reference*
*Completed: 2026-03-05*
