---
phase: 04-business-forms
plan: 02
subsystem: api+ui
tags: [fastapi, streamlit, crud, equipment-model, parameter, unit, form-dialog]

requires:
  - phase: 04-business-forms
    provides: Lookup endpoints (list_units_lookup for Parameters page)
provides:
  - EquipmentModel CRUD (API + UI)
  - Parameter CRUD (API + UI)
  - Unit inline creation (POST /ingest/lookup/units + sub-form UX)
  - "add_new" feature in base form_dialog for all select fields
affects: [04-03, 04-05]

tech-stack:
  added: []
  patterns:
    - "add_new field spec: select fields accept add_new config with title/fields/on_create for inline item creation"
    - "Sub-form pattern: form_dialog transitions to sub-form via session state (_sf_active/_sf_field)"

key-files:
  created:
    - api/v1/endpoints/parameters.py
    - app/pages/6_Equipment_Models.py
    - app/pages/7_Parameters.py
  modified:
    - api/v1/endpoints/equipment.py
    - api/v1/repositories/equipment_repository.py
    - api/v1/repositories/metadata_repository.py
    - api/v1/repositories/lookup_repository.py
    - api/v1/schemas/equipment.py
    - api/v1/schemas/channel.py
    - api/v1/endpoints/ingest.py
    - api/v1/router.py
    - app/api_client.py
    - app/components/form_dialog.py
    - app/pages/7_Parameters.py

key-decisions:
  - "Unit creation via POST /ingest/lookup/units (kept alongside GET lookup — no separate router needed)"
  - "add_new sub-form uses session state (_sf_active/_sf_field) to replace main form content inside the same dialog"
  - "Newly-created options stored in session state per field (_sf_extra_opts_{field}) and cleared on dialog close"

issues-created: []

duration: 19min
completed: 2026-03-05
---

# Phase 04 Plan 02: EquipmentModel and Parameter CRUD Summary

**EquipmentModel/Parameter CRUD API + Streamlit pages, with inline "Add new unit" sub-form in the base form_dialog component**

## Performance

- **Duration:** 19 min
- **Started:** 2026-03-05T21:21:28Z
- **Completed:** 2026-03-05T21:40:15Z
- **Tasks:** 2 (+ 1 checkpoint pending verification)
- **Files modified:** 13

## Accomplishments

- Full CRUD API for EquipmentModel: GET/POST `/equipment/models`, GET/PUT/DELETE `/equipment/models/{id}`
- Full CRUD API for Parameter: GET/POST `/parameters`, GET/PUT/DELETE `/parameters/{id}`
- `6_Equipment_Models.py`: CRUD page following Equipment pattern exactly
- `7_Parameters.py`: CRUD page with unit dropdown
- `POST /ingest/lookup/units`: create new units inline
- Base `form_dialog.py` refactored: select fields with `add_new` config show "➕ Add new..." option that transitions the dialog to a sub-form (← Back / OK), creates the item, injects it as pre-selected in the parent form

## Task Commits

1. **Task 1: EquipmentModel and Parameter CRUD API** - `842651f` (feat)
2. **Task 2: Streamlit CRUD pages** - `166c7a3` (feat)

## Files Created/Modified

- `api/v1/endpoints/parameters.py` — new Parameter CRUD router
- `api/v1/endpoints/equipment.py` — added /models CRUD routes
- `api/v1/repositories/equipment_repository.py` — list/get/insert/update/delete_equipment_model
- `api/v1/repositories/metadata_repository.py` — list/get/insert/update/delete_parameter
- `api/v1/repositories/lookup_repository.py` — insert_unit
- `api/v1/schemas/equipment.py` — EquipmentModelIn/Out
- `api/v1/schemas/channel.py` — ParameterIn/Out
- `api/v1/endpoints/ingest.py` — POST /ingest/lookup/units
- `api/v1/router.py` — registered parameters_router
- `app/api_client.py` — list/create/update/delete for equipment models and parameters; create_unit
- `app/components/form_dialog.py` — full refactor with add_new sub-form support
- `app/pages/6_Equipment_Models.py` — new CRUD page
- `app/pages/7_Parameters.py` — new CRUD page with add_new unit wired

## Decisions Made

- Unit creation kept under `/ingest/lookup/units` (POST alongside existing GET) — no new router needed
- Sub-form uses session state (`_sf_active`, `_sf_field`) to swap main form content with sub-form inside the same `@st.dialog` — clean modal UX without nesting dialogs
- Extra options from sub-form stored per field in session state (`_sf_extra_opts_{name}`) and cleaned up on dialog close/submit

## Deviations from Plan

### Auto-added (user-requested during checkpoint)

**[User request] Inline "Add new" sub-form for select dropdowns**
- **Requested:** During checkpoint verification
- **Scope:** Base form_dialog feature (applies to all forms), wired for `unit_id` in Parameters page
- **Added:** `POST /ingest/lookup/units`, `create_unit()` in api_client, full sub-form UX in form_dialog, `add_new` config in 7_Parameters.py

---

**Total deviations:** 0 auto-fixed, 1 user-requested feature addition

## Issues Encountered

None

## Next Phase Readiness

- EquipmentModel and Parameter CRUD complete
- `add_new` pattern available for any future select field across all forms
- Ready for 04-03 (Campaign enhancement / equipment deployment)

---
*Phase: 04-business-forms*
*Completed: 2026-03-05*
