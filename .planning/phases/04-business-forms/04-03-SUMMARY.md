---
phase: 04-business-forms
plan: 03
subsystem: api+ui
tags: [fastapi, streamlit, campaigns, equipment-installation, deployment]

requires:
  - phase: 04-business-forms
    provides: Lookup endpoints (sampling_points, equipment)

provides:
  - Campaign deployment management (CampaignEquipment + CampaignSamplingLocation + EquipmentInstallation)

affects: [sensor-ingest-context]

tech-stack:
  added: []
  patterns:
    - "Sub-resource pattern: /campaigns/{id}/deployments endpoints"
    - "Atomic multi-table transaction for deployment creation/deletion"
    - "Streamlit @st.dialog decorator for complex form dialogs"
    - "Equipment filtering to prevent duplicate deployments"

key-files:
  created: []
  modified:
    - api/v1/repositories/campaign_repository.py
    - api/v1/endpoints/campaigns.py
    - api/v1/schemas/campaigns.py
    - app/pages/3_Campaigns.py
    - app/api_client.py

key-decisions:
  - "Deployment = equipment + sampling point pairing, creates 3 table rows atomically"
  - "EquipmentInstallation.InstalledDate derived from Campaign.CampaignStartDateTime"
  - "Prevention of duplicate equipment deployment within same campaign"
  - "UI filters out already-deployed equipment in Add Deployment dialog"

requirements-completed: []

# Metrics
duration: N/A (previously implemented)
completed: 2026-03-05
---

# Phase 04 Plan 03: Campaign Deployments Summary

**Campaign deployment management with atomic EquipmentInstallation creation and Streamlit UI panel**

## Performance

- **Duration:** Previously implemented (committed now)
- **Started:** 2026-03-05
- **Completed:** 2026-03-05
- **Tasks:** 3 (2 auto + 1 checkpoint)
- **Files modified:** 5

## Accomplishments

- Repository functions for listing, creating, and deleting campaign deployments
- REST API endpoints: GET/POST/DELETE /campaigns/{id}/deployments
- Pydantic schemas for deployment request/response validation
- Streamlit @st.dialog for Add Deployment with equipment filtering
- Deployments panel in 3_Campaigns.py with table display and remove functionality
- Error handling for campaigns without start dates

## Task Commits

Each task was committed atomically:

1. **Task 1: Campaign deployment API endpoints** - `25286f6` (feat)
2. **Task 2: Enhance 3_Campaigns.py with deployment panel** - `25286f6` (feat)

**Plan metadata:** [to be committed] (docs: complete plan)

## Files Created/Modified

- `api/v1/repositories/campaign_repository.py` - Added list_campaign_deployments, create_campaign_deployment, delete_campaign_deployment
- `api/v1/endpoints/campaigns.py` - Added deployment sub-resource endpoints
- `api/v1/schemas/campaigns.py` - Added DeploymentOut, DeploymentCreateIn, DeploymentCreateOut, DeploymentDeleteIn schemas
- `app/pages/3_Campaigns.py` - Added deployments panel with add/remove functionality
- `app/api_client.py` - Added deployment client functions (previously committed)

## Decisions Made

1. **Deployment creates 3 table rows atomically**: When adding a deployment, the system creates entries in CampaignEquipment, CampaignSamplingLocation, and EquipmentInstallation as a single transaction. This ensures referential integrity.

2. **InstalledDate derived from campaign start**: EquipmentInstallation.InstalledDate is automatically set to Campaign.CampaignStartDateTime, ensuring temporal consistency between the campaign and its equipment installations.

3. **Prevent duplicate equipment deployment**: The system checks if equipment is already deployed in a campaign before allowing a new deployment, preventing data inconsistencies.

4. **UI filters deployed equipment**: The Add Deployment dialog filters out equipment that is already deployed in the selected campaign, improving UX and preventing errors.

## Deviations from Plan

None - plan executed as specified. The implementation was completed in a previous session and committed now.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Deployment management is complete
- Ready for sensor data ingest that references campaigns and installations
- Existing campaign CRUD functionality remains intact

---
*Phase: 04-business-forms*
*Completed: 2026-03-05*
