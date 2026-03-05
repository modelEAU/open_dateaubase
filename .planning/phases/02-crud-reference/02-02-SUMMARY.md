---
phase: 02-crud-reference
plan: 02
subsystem: api
tags: [fastapi, pydantic, pyodbc, mssql, crud]

requires:
  - phase: 02-01
    provides: Site write routes pattern (EquipmentIn/CampaignIn mirror SiteIn)

provides:
  - POST/PUT/DELETE /equipment endpoints
  - POST/PUT/DELETE /campaigns endpoints
  - EquipmentIn and CampaignIn Pydantic schemas
  - insert/update/delete functions in equipment_repository and campaign_repository

affects: [02-03, 02-04]

tech-stack:
  added: []
  patterns:
    - "Write pattern: parameterized INSERT + SELECT @@IDENTITY + conn.commit() + re-fetch"
    - "Update returns None only when SELECT returns None post-UPDATE (row missing)"
    - "DELETE returns bool from cursor.rowcount > 0"

key-files:
  created: []
  modified:
    - api/v1/schemas/equipment.py
    - api/v1/repositories/equipment_repository.py
    - api/v1/endpoints/equipment.py
    - api/v1/schemas/campaigns.py
    - api/v1/repositories/campaign_repository.py
    - api/v1/endpoints/campaigns.py

key-decisions:
  - "EquipmentIn: model_id is nullable int (FK to EquipmentModel — user supplies ID)"
  - "CampaignIn: campaign_type_id and site_id are required ints (FK dropdowns in UI)"
  - "PUT returns 404 when get_*_by_id returns None after UPDATE (row not found)"

issues-created: []

duration: 8min
completed: 2026-03-05
---

# Phase 02 Plan 02: API Write Routes — Equipment + Campaigns Summary

**POST/PUT/DELETE endpoints for /equipment and /campaigns with EquipmentIn/CampaignIn schemas and parameterized pyodbc write repositories**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-05T15:17:53Z
- **Completed:** 2026-03-05T15:25:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- EquipmentIn schema with nullable identifier, serial_number, model_id, owner, purchase_date
- CampaignIn schema with required name, campaign_type_id, site_id and optional description, start_date, end_date
- Three write functions per entity: insert (SELECT @@IDENTITY + re-fetch), update (re-fetch or None), delete (rowcount bool)
- POST /equipment (201), PUT /equipment/{id} (200/404), DELETE /equipment/{id} (204/404)
- POST /campaigns (201), PUT /campaigns/{id} (200/404), DELETE /campaigns/{id} (204/404)
- All 47 unit tests + 89 contract tests still pass

## Task Commits

1. **Task 1: EquipmentIn + equipment write routes** — `cffcc74` (feat)
2. **Task 2: CampaignIn + campaign write routes** — `00ac97a` (feat)

## Files Created/Modified

- [api/v1/schemas/equipment.py](api/v1/schemas/equipment.py) — added EquipmentIn
- [api/v1/repositories/equipment_repository.py](api/v1/repositories/equipment_repository.py) — added insert_equipment, update_equipment, delete_equipment
- [api/v1/endpoints/equipment.py](api/v1/endpoints/equipment.py) — added POST/PUT/DELETE routes
- [api/v1/schemas/campaigns.py](api/v1/schemas/campaigns.py) — added CampaignIn
- [api/v1/repositories/campaign_repository.py](api/v1/repositories/campaign_repository.py) — added insert_campaign, update_campaign, delete_campaign
- [api/v1/endpoints/campaigns.py](api/v1/endpoints/campaigns.py) — added POST/PUT/DELETE routes

## Decisions Made

- **EquipmentIn.model_id nullable**: Equipment can exist before a model is catalogued; FK is nullable in DB.
- **CampaignIn.campaign_type_id and site_id required**: Campaigns must belong to a type and site; UI will use dropdowns populated from API.
- **PUT 404 via re-fetch**: After UPDATE, call get_*_by_id; if None → row was not found → 404. Matches Sites pattern from 02-01.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Step

Ready for 02-03-PLAN.md (CRUD component + Sites page)

---
*Phase: 02-crud-reference*
*Completed: 2026-03-05*
