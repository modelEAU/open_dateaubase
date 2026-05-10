# Pre-release Bug Fix Plan

## Context

Pre-release branch (`issue-24-signal-interface`), targeting a 2.0 tag merged back to main.
**No migration scripts are needed.** The workflow for every change is:
1. Fix YAML → this regenerates the DDL (`sql_generation_scripts/v*.sql`)
2. Update API schemas, endpoints, repositories to match
3. Update UI forms and pages to match
4. Update any importer config/scripts to match
5. Run `uv run pytest` — unit tests (schema CI) + integration tests against the fresh DDL

Migration scripts only exist between **releases**. Everything here lands in the 2.0 initial DDL.

---

## Triage: Prioritized Waves

### Wave 1 — Pure code fixes (no YAML change, immediate value)

**1a. CampaignEquipment: remove `Role` and `notes` from API/UI**

The DB table has only `Campaign_ID`, `Equipment_ID` — the YAML already does not have a `Role`
column but the API stack and UI still pass/render both fields.

- `api/v1/schemas/campaigns.py` — remove `role` and `notes` from `DeploymentCreateIn`
- `api/v1/endpoints/campaigns.py` — stop passing `role`/`notes` to repository
- `api/v1/repositories/campaign_repository.py` — remove both params from the function signature
- `app/components/campaign_wizard.py` — remove the Role text input and Notes text area from the equipment deployment step
- YAML: `schema_dictionary/tables/CampaignEquipment.yaml` — confirm no `Role` column present; if it is, remove it

**1b. CampaignSamplingLocation: same treatment**

Same stack, different table context. Remove `role` and `notes` everywhere they appear for
sampling-location deployments. YAML: `schema_dictionary/tables/CampaignSamplingLocation.yaml`.

---

### Wave 2 — YAML column renames (regenerate DDL, update API + UI)

**2a. `SignalInterface.Make` → `Manufacturer`**
- `schema_dictionary/tables/SignalInterface.yaml`: rename column from `Make` to `Manufacturer`
- Update any API schema field (`make`) and UI label

**2b. `Person.Function` → `AssignedFunctions`**
- `schema_dictionary/tables/Person.yaml`: rename column (description already touched)
- Update API schema and UI

**2c. `ProcessingStep.Parameters` → `MethodParameters`**
- `schema_dictionary/tables/ProcessingStep.yaml`: rename column
- Update API schema and any processing-related UI

**2d. `SamplingPoint`: drop `SamplingLocation` field**
- The `SamplingLocation` column inside `SamplingPoint` is redundant with the table concept
- `schema_dictionary/tables/SamplingPoint.yaml`: remove the column entry
- Update API schema and any UI that exposed this field

---

### Wave 3 — Controlled vocabulary fixes

**3a. ProcessingKind: replace seed values**

Current (wrong): Raw, Cleaned, Calibrated, Validated, Filtered, Predicted, Other

Correct set: Raw, Free of outliers, Free of drift, Free of faults, Smoothed, Interpolated,
Predicted, Derived

- `schema_dictionary/tables/ProcessingKind.yaml`: replace `seed_data` entirely
- Regenerate seed SQL
- Note: this feeds directly into Wave 5 (ProcessingType FK on ProcessingStep)

**3b. `ProcedureType` (free text) → `ProcedureKind_ID` (FK)**

- Create `schema_dictionary/tables/ProcedureKind.yaml` with seed values:
  - Maintenance and Cleaning Protocol
  - Calibration Protocol
  - Validation Protocol
  - Laboratory Method Protocol
  - Software Manual
- `schema_dictionary/tables/Procedures.yaml`: remove `ProcedureType` text column, add `ProcedureKind_ID` FK
- Update API schema (`ProcedureType: str` → `ProcedureKind_ID: int`) and UI (free text → dropdown)

**3c. EquipmentEventKind: remove "Validation" entry**
- `schema_dictionary/tables/EquipmentEventKind.yaml`: delete the Validation seed row
- Regenerate seed SQL

**3d. Parameter: remove `manuel_units` from seed data**
- `schema_dictionary/tables/Parameter.yaml`: remove any `manuel_units` entries from seed rows
- YAML only, no column — this is a seed data correctness fix

---

### Wave 4 — Table removals: `SignalInterfaceKind` and `SignalInterfacePortKind`

Both tables are "too obtuse" and should be removed entirely from the schema.

**4a. Remove `SignalInterfaceKind`**
- Delete `schema_dictionary/tables/SignalInterfaceKind.yaml`
- `schema_dictionary/tables/SignalInterface.yaml`: remove `SignalInterfaceKind_ID` FK column
- Regenerate DDL
- Update API and UI (remove kind dropdowns for signal interfaces)

**4b. Remove `SignalInterfacePortKind`**
- Delete `schema_dictionary/tables/SignalInterfacePortKind.yaml`
- `schema_dictionary/tables/SignalInterfacePort.yaml`: remove `SignalInterfacePortKind_ID` FK column
- Regenerate DDL
- Update API and UI

---

### Wave 5 — Channel identity restructure

**Current unique constraint on Channel:**
`(SignalInterface_ID, TagName, Parameter_ID, DataProvenanceKind_ID, ProcessingKind_ID)`

**Problem:** `ProcessingKind_ID` in the identity causes channels with identical wiring/tag but
different processing levels to collide. Two students validating the same signal in different
years would conflict.

**Fix:**
- Remove `ProcessingKind_ID` from the Channel unique constraint; keep it as an informational
  denormalized field only
- The authoritative processing level is tracked via `ProcessingLineage` (Output role)
- `ProcessingStep.ProcessingType` (currently free text) becomes `ProcessingKind_ID` FK to
  `ProcessingKind` table (aligns with metEAUdata `ProcessingType` enum)

Steps:
1. `schema_dictionary/tables/Channel.yaml`: update the `unique_constraints` entry to drop `ProcessingKind_ID`
2. `schema_dictionary/tables/ProcessingStep.yaml`: rename `ProcessingType` column to `ProcessingKind_ID`, add FK to `ProcessingKind`
3. Regenerate DDL
4. Update API schemas and repositories for Channel and ProcessingStep

---

### Wave 6 — New fields: Watershed enhancements

**6a. `ParentWatershed_ID` (self-referential FK)**
- `schema_dictionary/tables/Watershed.yaml`: add nullable `ParentWatershed_ID INT FK → Watershed`
- Regenerate DDL

**6b. `GeometryGeoJSON` field + map UI**
- `schema_dictionary/tables/Watershed.yaml`: add `GeometryGeoJSON NVARCHAR(MAX) NULL`
  - Store GeoJSON as text (NVARCHAR MAX); validation in the app layer, not DB layer
- Regenerate DDL
- API: add `geometry_geojson: str | None` to Watershed schemas; on write, validate that the
  GeoJSON contains only Polygon or MultiPolygon geometry types (reject Points, LineStrings, etc.)
- UI additions required on **every page that creates or browses Watersheds** (including any wizard steps):
  - Leaflet/Folium map widget showing the watershed boundary (OpenStreetMap tiles)
  - GeoJSON file upload button; on upload parse the GeoJSON and display it on the map
  - Validator that rejects GeoJSON files containing non-polygon geometry types with a clear error message
  - If GeometryGeoJSON is set, render it on the map; otherwise show an empty map centered on the site's coordinates

---

### Wave 7 — EquipmentEvent restructure

**7a. Split `PerformedByPerson_ID` / add `RecordedByPerson_ID`**
- `schema_dictionary/tables/EquipmentEvent.yaml`: keep `PerformedByPerson_ID`, add nullable `RecordedByPerson_ID INT FK → Person`
- Update API schema and UI form

**7b. Remove `Campaign_ID`**
- Campaigns already register equipment. Recording CampaignID on an event causes ambiguity when
  campaigns overlap and share equipment.
- `schema_dictionary/tables/EquipmentEvent.yaml`: remove `Campaign_ID` column
- Update API schema and UI

**7c. Distinguish instantaneous vs. ongoing events**
- `EventDateTimeEnd NULL` currently means either "ongoing" or "instantaneous" — ambiguous
- Add `IsInstantaneous BIT NOT NULL DEFAULT 0`
  - `IsInstantaneous=0, EndDateTime=NULL` → ongoing
  - `IsInstantaneous=1, EndDateTime=NULL` → instantaneous (point-in-time event)
  - `IsInstantaneous=0, EndDateTime=<value>` → completed over interval
- `schema_dictionary/tables/EquipmentEvent.yaml`: add the column
- Update API schema (add field) and UI (radio/checkbox to select event type)

---

### Wave 8 — Controlled vocabulary for remaining free-text fields

**8a. `Observation.DataType` → FK to `ValueKind`**
- Currently `DataType NVARCHAR(10)` (values: Scalar, Vector, Matrix, Image)
- `ValueKind` already has exactly these values
- `schema_dictionary/tables/Observation.yaml`:
  - Remove `DataType` text column
  - Add `ValueKind_ID INT NOT NULL FK → ValueKind`
  - Update unique constraint: replace `DataType` with `ValueKind_ID`
- Regenerate DDL; update API (text → int FK) and importers

**8b. `DataAcquisitionSystem.SystemType` → `DataAcquisitionSystemKind_ID`**
- Create `schema_dictionary/tables/DataAcquisitionSystemKind.yaml` with relevant seed values
  (e.g., SCADA, PLC, Datalogger, IoT Gateway, Manual entry, Other)
- `schema_dictionary/tables/DataAcquisitionSystem.yaml`: remove `SystemType` text, add FK column
- Update API and UI

**8c. `ControlLoop.ControllerType` → `ControllerKind_ID`**
- Create `schema_dictionary/tables/ControllerKind.yaml`
  (e.g., PID, Feedforward, MPC, On-Off, Manual, Other)
- `schema_dictionary/tables/ControlLoop.yaml`: remove `ControllerType` text, add FK column
- Update API and UI

---

### Wave 9 — Renames

**9a. `UrbanCharacteristics` → `LandUse`**
- Rename `schema_dictionary/tables/UrbanCharacteristics.yaml` → `LandUse.yaml`
- Update `table.name` field inside the file
- Update any FK references in other YAML files
- Update API routes (`/urban-characteristics` → `/land-use`) and UI labels

---

## Design Stubs

### DS-1: `QualityCode` — no rename needed (CLOSED)

QualityCode is already used in both `LabValue` and regular `Value` tables. The description has
been broadened to "quality flags for measurements". The table name is correct as-is.
No action required.

---

### DS-2: `Equipment.Owner` → `OwningOrganization_ID`

- Create `schema_dictionary/tables/Organization.yaml` with at minimum: `Organization_ID`, `Name`, `Country`, `Description`
- `schema_dictionary/tables/Equipment.yaml`: replace `Owner` (text) with `OwningOrganization_ID INT NULL FK → Organization`
- `schema_dictionary/tables/Person.yaml`: replace `Company` (text) with `OrganizationAffiliation_ID INT NULL FK → Organization`
- `schema_dictionary/tables/Laboratory.yaml` (if exists): same treatment for Company
- Update API and UI throughout

---

### DS-3: `ValueMatrix` → `ValueMatrix2D` (Option A chosen)

The split-table-per-dimensionality arrangement is the right approach and will be kept.

- Rename `ValueMatrix` table to `ValueMatrix2D` in YAML and regenerated DDL
- Add `ValueMatrix3D` for 3-axis data (e.g., image RGB decomposed as X, Y, channel)
- Limitation note: document that N > 3 axes are not currently supported
- Update all FK references from `ValueMatrix` → `ValueMatrix2D`
- Update API and UI to use the new names

---

### DS-4: metEAUdata integration mapping

Based on the example at `/Users/jeandavidt/Developer/modelEAU/data_filters/demos/test dataset.zip`:

**Conceptual mapping (metEAUdata → open_dateaubase):**

| metEAUdata concept | open_dateaubase table(s) |
|--------------------|--------------------------|
| Dataset | `Dataset` |
| Signal (e.g., COD#1) | `Channel` (one row per signal, `DataProvenanceKind` captures source) |
| TimeSeries (e.g., COD#1_RAW#1) | `Channel` row (processed variant) + `Observation`/`Value` rows |
| ProcessingStep.type | `ProcessingKind` (FK on `ProcessingStep.ProcessingKind_ID` — see Wave 5) |
| ProcessingStep.input_series_names | `ProcessingLineage` rows with `RoleInProcessingStep = 'Input'` |
| Output TimeSeries | `ProcessingLineage` row with `RoleInProcessingStep = 'Output'` |
| ProcessingStep.parameters | `ProcessingStep.MethodParameters` (JSON blob — see Wave 2c) |
| Signal.provenance.equipment | `Equipment` → `EquipmentWiringHistory` → `Channel` |
| Signal.provenance.location | `SamplingPoint` |
| Dataset.signals (multi-signal) | `DatasetChannel` junction rows |

**ProcessingType values from example** (map to ProcessingKind seed data in Wave 3a):
- `dimensionality_reduction` → "Derived"
- `transformation` → "Smoothed" or "Predicted" depending on context
- `filtering` → "Free of outliers" / "Free of faults"

**Missing fields identified in current schema** (require YAML additions):

1. `ProcessingStep`: no `FunctionAuthor`, `FunctionReference`, `SourceCode` fields — the example
   embeds full source code in the metadata. Decide: store in `Description` (free text) or add
   structured columns. Recommendation: add `FunctionAuthor VARCHAR(200)` and `FunctionReference
   VARCHAR(500)` to `ProcessingStep.yaml`; skip `SourceCode` (too large, use the reference URL instead).

2. `ProcessingStep`: no `RequiresCalibration BIT` flag — add to YAML

3. `ProcessingStep`: no `CalibrationStartTime` / `CalibrationEndTime` — the example PCA step
   records a `calibration_interval`. Add two nullable timestamp columns.

4. `DatasetChannel`: no time-boundary columns — the example shows time-bounded signal slices
   feeding into a Dataset. Add `StartTime DATETIME NULL` and `EndTime DATETIME NULL` to
   `DatasetChannel.yaml` to express which time slice of a channel is included.

**Action:** Write a worked example script (`examples/meteaudata_import_example.py`) that loads
the test dataset zip and inserts it into the DB using the open_dateaubase API, exercising the
full ProcessingLineage chain (5 raw signals → PCA → PC1/PC2/PC3 → Q/T2 statistics).

---

### DS-5: Equipment events visualization UI

New Streamlit page (e.g., `app/pages/equipment_timeline.py`):
- Select a campaign / site / sampling location → list its equipment
- Select one or more equipment items → render a time-axis chart of their raw-data channels
- Overlay equipment events as annotations on the time axis (like markers in the data explorer)
- Click a time-range on the chart to create a new EquipmentEvent for that period

---

### DS-6: `SetPoint` and `MPC Trajectory` as ChannelKind

- `schema_dictionary/tables/ChannelKind.yaml`: add seed rows:
  - SetPoint — a target value fed to a controller
  - MPC Trajectory — a vector channel; the bin axis is the time horizon
- Regenerate seed SQL

---

### DS-7: `ChannelPortHistory.GatingNote` — keep, clarify description

The field is intentional: it documents which multiplexer slot or round-robin position a channel
occupied during a measurement period (e.g., "TresCON round-robin slot 2").
- Action: improve the description in `ChannelPortHistory.yaml` to make the multiplexer use-case explicit

---

## Execution Order

```text
Wave 1 (code-only, no DDL needed)
  ↓
Wave 2 + Wave 3a/b/c/d  (YAML changes, regenerate DDL)
  ↓
Wave 4  (remove Kind tables — after vocab is stable)
  ↓
Wave 5  (Channel identity — after ProcessingKind seed is final)
  ↓
Wave 6 + Wave 7 + Wave 8 + Wave 9  (independent, can run in parallel)
  ↓
Design Stubs DS-2, DS-3, DS-4, DS-5, DS-6, DS-7  (after core schema is stable)
```

---

## Verification

After each wave:
1. `uv run pytest tests/unit/` — schema CI must pass (YAML validation, model checks)
2. Rebuild DDL: confirm `sql_generation_scripts/` regenerates cleanly
3. `uv run pytest tests/integration/` — integration tests against a fresh DB from the new DDL
4. For UI changes: start the Streamlit app (`streamlit run app/Home.py`) and exercise the affected forms
