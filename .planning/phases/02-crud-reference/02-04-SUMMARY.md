---
phase: 02-crud-reference
plan: 04-gap-closure
subsystem: ui

tags: [streamlit, crud, forms, patch, lookup]

requires:
  - phase: 02-crud-reference
    provides: API endpoints for sites, equipment, campaigns
    
provides:
  - PATCH endpoints for partial updates
  - Lookup endpoints for FK dropdowns
  - crud_form component for form field rendering
  - form_dialog component for modal dialogs
  - Form-based CRUD pages for Sites, Equipment, Campaigns

affects:
  - 02-crud-reference

tech-stack:
  added: []
  patterns:
    - "Form-based CRUD: Table display + dialog forms for create/edit"
    - "PATCH for partial updates, POST for creates"
    - "Lookup endpoints for FK dropdown data"

key-files:
  created:
    - app/components/crud_form.py
    - app/components/form_dialog.py
  modified:
    - api/v1/schemas/metadata.py
    - api/v1/schemas/equipment.py
    - api/v1/schemas/campaigns.py
    - api/v1/repositories/site_repository.py
    - api/v1/repositories/equipment_repository.py
    - api/v1/repositories/campaign_repository.py
    - api/v1/endpoints/sites.py
    - api/v1/endpoints/equipment.py
    - api/v1/endpoints/campaigns.py
    - app/api_client.py
    - app/pages/1_Sites.py
    - app/pages/2_Equipment.py
    - app/pages/3_Campaigns.py

key-decisions:
  - "Adopted form-based CRUD pattern based on user feedback - better UX than inline editing"
  - "PATCH endpoints support partial updates for form submissions"
  - "Lookup endpoints provide lightweight id+name pairs for dropdowns"
  - "Required fields marked with (*) in form labels"
  - "Validate button shows validation errors before submit"

requirements-completed: []

duration: 29min
completed: 2026-03-05
---

# Phase 02 Plan 04 (Gap Closure): Form-Based CRUD Summary

**Form-based CRUD pattern with dialog forms, FK dropdowns, and PATCH partial updates for all reference data pages**

## Performance

- **Duration:** 29 min
- **Started:** 2026-03-05T17:25:58Z
- **Completed:** 2026-03-05T17:55:02Z
- **Tasks:** 8
- **Files modified:** 15

## Accomplishments

1. **API Enhancements**
   - Added PATCH endpoints for Sites, Equipment, Campaigns (/api/v1/{entity}/{id})
   - Added lookup endpoints: /sites/lookup/list, /campaigns/types, /equipment/models/lookup
   - Created Patch schemas (SitePatch, EquipmentPatch, CampaignPatch) with all optional fields
   - Added repository methods for partial updates with dynamic SQL

2. **UI Components**
   - Created `crud_form.py` with `render_form_field()` supporting text, number, select, date, textarea
   - Created `form_dialog.py` with `create_form_dialog()` and `edit_form_dialog()` using st.dialog
   - Added validation with required field checking and visual feedback (* markers)

3. **Page Rewrites**
   - Rewrote Sites page with table + dialog forms, New/Edit/Delete buttons
   - Rewrote Equipment page with model dropdown showing "Manufacturer - Model Name"
   - Rewrote Campaigns page with site filter, site dropdown, and campaign type dropdown

4. **API Client Updates**
   - Added `patch_site()`, `patch_equipment()`, `patch_campaign()` methods
   - Added `list_sites_lookup()`, `list_equipment_models_lookup()`, `list_campaign_types()` methods

## Task Commits

1. **Task 1-2: PATCH and lookup endpoints** - `4b0af82`
2. **Task 3: crud_form component** - `99d9708`
3. **Task 4: form_dialog component** - `ad0037d`
4. **Task 5: api_client PATCH and lookup** - `963212c`
5. **Task 6: Sites page rewrite** - `820bba1`
6. **Task 7: Equipment page rewrite** - `718f907`
7. **Task 8: Campaigns page rewrite** - `487ef4d`

## Files Created/Modified

- `api/v1/schemas/metadata.py` - Added SitePatch, SiteLookupOut schemas
- `api/v1/schemas/equipment.py` - Added EquipmentPatch, EquipmentModelLookupOut schemas
- `api/v1/schemas/campaigns.py` - Added CampaignPatch, CampaignTypeOut schemas
- `api/v1/repositories/site_repository.py` - Added patch_site(), get_sites_lookup()
- `api/v1/repositories/equipment_repository.py` - Added patch_equipment(), get_models_lookup()
- `api/v1/repositories/campaign_repository.py` - Added patch_campaign(), get_campaign_types()
- `api/v1/endpoints/sites.py` - Added PATCH /{id} and /lookup/list endpoints
- `api/v1/endpoints/equipment.py` - Added PATCH /{id} and /models/lookup endpoints
- `api/v1/endpoints/campaigns.py` - Added PATCH /{id} and /types endpoints
- `app/api_client.py` - Added patch_* and lookup methods
- `app/components/crud_form.py` - New: Form field rendering utilities
- `app/components/form_dialog.py` - New: Modal dialog components
- `app/pages/1_Sites.py` - Rewritten with form-based CRUD
- `app/pages/2_Equipment.py` - Rewritten with form-based CRUD
- `app/pages/3_Campaigns.py` - Rewritten with form-based CRUD

## Decisions Made

- **Form-based CRUD pattern** adopted based on human feedback - better UX for graduate students than inline editing
- **PATCH for updates** - Partial updates via PATCH, creates via POST
- **Lookup endpoints** - Lightweight endpoints for FK dropdown data (< 100ms response)
- **Required field markers** - Red asterisk (*) indicates required fields
- **Validate before Send** - Users can validate forms before submission

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all components integrated smoothly.

## Verification Status

- [x] All PATCH endpoints return 200 with partial updates
- [x] All lookup endpoints return id+name pairs
- [x] `uv run python -c "import app.components.crud_form; import app.components.form_dialog"` passes
- [x] All three pages pass syntax check
- [x] `uv run pytest tests/unit/ -q` passes (47 tests)
- [ ] Human verification checkpoint (awaiting approval)

## Next Phase Readiness

Phase 02 complete after human verification. Ready for Phase 03: CRUD Pages — Core Entities.

---
*Phase: 02-crud-reference*
*Completed: 2026-03-05*
