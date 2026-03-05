---
phase: 04-business-forms
plan: 01
subsystem: api
tags: [fastapi, lookup, repository, pyodbc]

requires: []
provides:
  - GET /ingest/lookup/units → [{unit_id, unit}]
  - GET /ingest/lookup/laboratories → [{laboratory_id, name}]
  - GET /ingest/lookup/procedures → [{procedure_id, procedure_name}]
  - GET /ingest/lookup/samples → [{sample_id, label, sample_date}]
  - GET /ingest/lookup/sampling-points → [{sampling_point_id, label}]
  - GET /ingest/lookup/equipment-events → [{equipment_event_id, label}]
  - GET /campaigns/lookup → [{campaign_id, name}]
  - 7 api_client.py lookup functions
affects: [04-02, 04-03, 04-04, 04-05, 04-06, 04-07, 04-08, 04-09]

tech-stack:
  added: []
  patterns:
    - "Lookup endpoints placed under entity-specific /lookup/* paths (ingest.py, campaigns.py)"
    - "Lookup repository pattern: dedicated lookup_repository.py with typed pyodbc functions"

key-files:
  created:
    - api/v1/repositories/lookup_repository.py
  modified:
    - api/v1/endpoints/ingest.py
    - api/v1/endpoints/campaigns.py
    - app/api_client.py

key-decisions:
  - "Lookup routes added directly to ingest.py and campaigns.py (no separate router) to keep routing simple"
  - "lookup_repository.py centralizes all reference-data queries for reuse across future plans"

patterns-established:
  - "Lookup repo pattern: conn-first pyodbc functions returning list[dict] with snake_case keys"

issues-created: []

duration: 2min
completed: 2026-03-05
---

# Phase 04 Plan 01: Lookup API Foundation Summary

**7 lookup endpoints (Unit, Laboratory, Procedures, Sample, SamplingPoint, EquipmentEvent, Campaign) + matching api_client functions unblocking all ingest form plans**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-05T21:16:52Z
- **Completed:** 2026-03-05T21:18:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `lookup_repository.py` with 6 parameterized pyodbc query functions
- Added 6 GET lookup routes to `/ingest/lookup/*` and 1 to `/campaigns/lookup`
- Added 7 matching `list_*_lookup()` functions to `app/api_client.py`
- All 89 contract tests + 136 total non-legacy tests still pass

## Task Commits

1. **Task 1: Create lookup_repository.py and add lookup routes** - `29d4cf9` (feat)
2. **Task 2: Add api_client.py lookup functions** - `35ab6d5` (feat)

**Plan metadata:** (this commit) (docs: complete plan)

## Files Created/Modified

- `api/v1/repositories/lookup_repository.py` - 6 lookup query functions (units, labs, procedures, samples, sampling points, equipment events)
- `api/v1/endpoints/ingest.py` - Added 6 GET /ingest/lookup/* routes
- `api/v1/endpoints/campaigns.py` - Added GET /campaigns/lookup route
- `app/api_client.py` - Added 7 lookup client functions grouped under "# Lookup helpers"

## Decisions Made

- Lookup routes added inline to existing endpoint files (no new router) — keeps routing flat and avoids over-engineering for simple GET endpoints.
- `lookup_repository.py` created as a dedicated module so all reference-data queries are co-located and importable by future endpoints (e.g., inline sample creation in 04-06).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- All 7 lookup endpoints are available and tested
- api_client.py has matching functions ready for Streamlit page imports
- Ready for 04-02 (EquipmentModel CRUD page) and subsequent ingest form plans

---
*Phase: 04-business-forms*
*Completed: 2026-03-05*
