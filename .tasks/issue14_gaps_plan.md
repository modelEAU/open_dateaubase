# Plan: Issue 14 Gaps — Missing Admin Pages + Campaign Wizard Image Upload

## Goal
Close the two remaining gaps from Issue 14:
1. Add admin pages for tables that lack them
2. Add sampling location image upload to the campaign wizard

---

## Gap Analysis

### Tables actually missing admin pages

Of the 48 tables with no admin page, most are junction tables, system tables, or complex data
tables that shouldn't have standalone admin pages. The ones that warrant pages:

**Vocabulary/lookup tables (users must manage these to configure the system):**
| Table | Used By | Priority |
|---|---|---|
| `CampaignType` | Campaign creation | High |
| `ProcessUnitType` | Process unit creation | High |
| `SignalPortType` | Signal port management | High |
| `EquipmentEventType` | Equipment event logging | Medium |
| `BinMode` | Value binning configuration | Medium |
| `Purpose` | General tagging | Low |
| `ProcessingDegree` | Data processing pipeline | Low |

**Domain entity tables (primary objects worth listing/editing):**
| Table | Notes | Priority |
|---|---|---|
| `Project` | Top-level grouping above Campaign | High |
| `Watershed` | Geographic reference for Sites | Medium |
| `Procedures` | Lab/measurement protocols | Low |

**Tables excluded (no standalone admin page needed):**
- Junction tables: CampaignEquipment, CampaignSamplingLocation, ControlLoopPort*, ProjectHas*, etc.
- System tables: SchemaVersion, MetaData, DataProvenance, ProcessingLineage
- Data tables: Value, ValueBin, Sample, LabAnalysis, Observation, Dataset, etc.
- History tables: SignalPortEquipmentHistory, SignalPortLocationHistory (managed with parent)
- EquipmentEvent, EquipmentInstallation: managed inline with Equipment page (not standalone)
- EquipmentStatusChannel: DROPPED in v3.0.0
- SamplingPoints: managed within Sites page already
- HydrologicalCharacteristics, UrbanCharacteristics: managed within Watershed/Site page

---

## Fix 1: Missing Admin Pages

### Approach
Each admin page follows the same Streamlit pattern as the existing vocabulary pages
(e.g., `app/pages/site_types.py`). Each page needs:
- API endpoint(s): GET list, POST create, PATCH update, DELETE
- Repository function(s)
- Schema (In/Out Pydantic models)
- App page file + sidebar nav registration

### Pages to build (in priority order)

#### Tier 1 — High priority (needed to use existing features properly)
1. **CampaignType** (`/app/pages/campaign_types.py`)
   - Simple vocab: id, name, description
   - API: `GET /campaign-types`, `POST`, `PATCH /{id}`, `DELETE /{id}`

2. **ProcessUnitType** (`/app/pages/process_unit_types.py`)
   - Simple vocab: id, name, description
   - API: `GET /process-unit-types`, `POST`, `PATCH /{id}`, `DELETE /{id}`

3. **SignalPortType** (`/app/pages/signal_port_types.py`)
   - Simple vocab: id, name, description
   - API: `GET /signal-port-types`, `POST`, `PATCH /{id}`, `DELETE /{id}`

#### Tier 2 — Medium priority
4. **EquipmentEventType** (`/app/pages/equipment_event_types.py`)
   - Simple vocab: id, name, description

5. **BinMode** (`/app/pages/bin_modes.py`)
   - Simple vocab: id, name, description

6. **Project** (`/app/pages/projects.py`)
   - Richer entity: id, name, description, start_date, end_date, contact_id (optional)
   - API: `GET /projects`, `POST`, `PATCH /{id}`, `DELETE /{id}`

7. **Watershed** (`/app/pages/watersheds.py`)
   - Entity: id, name, description, area_km2 (nullable)

#### Tier 3 — Low priority (implement if time allows)
8. **Purpose** (`/app/pages/purposes.py`)
9. **ProcessingDegree** (`/app/pages/processing_degrees.py`)
10. **Procedures** (`/app/pages/procedures.py`)

---

## Fix 2: Campaign Wizard — Sampling Location Image Upload

### Current state
- API endpoints: EXIST (`POST/GET/DELETE /sites/{site_id}/sampling-locations/{sp_id}/picture`)
- App API client functions: EXIST (`upload_sampling_point_picture`, etc.)
- Campaign wizard Step 2: captures name, description, lat, lng, process_unit_id — NO image

### Approach
The API requires a `sp_id` before uploading, so image upload must happen AFTER creation.
This is a two-step flow: create SP → upload image. Both happen within the wizard step.

**UI change in `app/components/campaign_wizard.py` Step 2:**
- Add `st.file_uploader("Photo (optional)", type=["jpg","jpeg","png"])` per sampling location form
- Store the uploaded bytes in session state alongside the other form fields
- After `create_sampling_location()` returns `sp_id`, if bytes are present, call `upload_sampling_point_picture(site_id, sp_id, bytes, filename)`
- Surface a non-blocking error if upload fails (SP was created OK, just warn about photo)

**Session state key:** `f"sl_{idx}_photo"` (parallel to existing `f"sl_{idx}_name"` pattern)

**No new API work needed** — endpoints and client already exist.

---

---

## Fix 3: Nav Reorganization

### Problem
Current "Administration" section has 20 items in a flat list. Adding 10+ more will make it
unnavigable. The current list mixes primary entities, vocabulary tables, and workflow pages.

### Proposed section structure (Streamlit `st.navigation` groups)

```
""          → Home
Operations  → Sensor Ingest, Lab Ingest, Explore
Campaigns   → Campaigns
Entities    → Project, Watershed, Sites, Process Units, Equipment, Equipment Models,
               Data Acquisition Systems, Signal Ports, Control Loops, Channels,
               Parameters, Binning Axes, Annotations, Laboratories, Persons
Vocabulary  → Site Types, Campaign Types, Process Unit Types, Signal Port Types,
               Equipment Event Types, Annotation Types, Sample Types, Sample Methods,
               Quality Codes, Units, Bin Modes, Purpose, Processing Degree, Procedures
Workflows   → Equipment Move
```

**Rationale:**
- **Entities** = domain objects with their own lifecycle and richer structure
- **Vocabulary** = pure lookup/reference tables (name + description, referenced by entities)
- **Workflows** = multi-step operational pages (Equipment Move wizard)
- Operations/Campaigns stay as-is since they're already cleanly separated

**Moves from current "Administration":**
- Units → Vocabulary (simple reference data)
- Equipment Move → Workflows
- Everything else → Entities
- New vocab pages land directly in Vocabulary
- New entity pages (Project, Watershed) land directly in Entities

---

## Phases

- [x] Phase 1: Confirm scope with user
- [x] Phase 2: Implement all new vocab admin pages
  - Tier 1: CampaignType, ProcessUnitType, SignalPortType
  - Tier 2: EquipmentEventType, BinMode
  - Tier 3: Purpose, ProcessingDegree, Procedures
  - Note: BinMode, SignalPortType, ProcessingDegree are read-only (fixed seeded values, no IDENTITY)
- [x] Phase 3: Implement new entity admin pages
  - Tier 2: Project, Watershed
- [x] Phase 4: Nav reorganization — restructure `Home.py` into Entities / Vocabulary / Workflows
- [x] Phase 5: Campaign wizard image upload (UI-only, no API work)
- [x] Phase 6: Verify — 47 unit tests pass, API imports cleanly, all routes present

## Status
**COMPLETE** — all phases done. 47/47 unit tests passing.
