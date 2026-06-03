# Development Plan: Lab Ingest UI Redesign

## Scope

Full rewrite of `lab_ingest.py` from flat single-page form to accordion layout with:
1. Experiment context (templates, series management)
2. Sample creation (with collection kind, equipment, person dropdowns)
3. Per-series measurement value entry
4. Template system for reusable experiment recipes

---

## Data Model: Templates

Zero changes to existing core tables. Two new lookup tables:

### LabExperimentTemplate

| Column | Type | Notes |
|---|---|---|
| LabExperimentTemplate_ID | INT PK identity | |
| Name | NVARCHAR(200) NOT NULL | e.g. "PSVD Weekly Panel" |
| Description | NVARCHAR(MAX) nullable | |
| CreatedByPerson_ID | INT nullable FK → Person | |
| CreatedAt | DATETIME2 NOT NULL DEFAULT GETUTCDATE() | |

### LabExperimentTemplateSeries

| Column | Type | Notes |
|---|---|---|
| LabExperimentTemplate_ID | INT PK FK → LabExperimentTemplate | |
| AnalysisSeries_ID | INT PK FK → AnalysisSeries | |

Copy-on-use: "Create from template" reads template's series, copies into session state,
user can modify before submit. Published experiment is fully independent — no live FK.

---

## FILE CHANGES

### Phase A: Foundation — YAML + Python models + naming fix

**A1. New YAML files**
- `schema_dictionary/tables/LabExperimentTemplate.yaml`
- `schema_dictionary/tables/LabExperimentTemplateSeries.yaml`

**A2. New Python models** (`src/open_dateaubase/data_model/table_models.py`)
- `LabExperimentTemplateBase` / `LabExperimentTemplateCreate` / `LabExperimentTemplate`
- `LabExperimentTemplateSeriesBase` / `LabExperimentTemplateSeries`

**A3. Fix SampleBase alias** — no column change, no migration

The existing column `SampleCollectionKind_ID` is correctly defined in Sample.yaml.
But `SampleBase.samplemethodID` uses alias `SampleMethod_ID` — rename to
`samplecollectionkindID` with alias `SampleCollectionKind_ID` to match the actual
schema. The description already says "Method of sample collection" which is correct
conceptually — just the name was wrong.

No schema changes. No new columns. This is a Python-only rename.

---

### Phase B: API layer — repository + endpoints

**B1. New repository functions** (`api/v1/repositories/ingestion_repository.py`)

```python
def list_lab_experiments_lookup(conn) -> list[dict]:
    """Recent LabExperiments: {lab_experiment_id, name, experiment_datetime, series_count}"""

def get_lab_experiment_series(conn, lab_experiment_id: int) -> list[dict]:
    """Distinct AnalysisSeries used in a LabExperiment"""

def list_analysis_series_lookup(conn) -> list[dict]:
    """All AnalysisSeries for dropdown: {analysis_series_id, name, parameter_name, ...}"""

def create_analysis_series(conn, *, parameter_id, sampling_point_id, unit_id,
                           value_kind_id=1, processing_kind_id=1, name) -> int:
    """Insert and return AnalysisSeries_ID. Raise on duplicate."""

def list_lab_experiment_templates(conn) -> list[dict]:
    """Templates with series count."""

def get_template_series(conn, template_id: int) -> list[dict]:
    """Series list for a template."""

def create_lab_experiment_template(conn, *, name, description, created_by_person_id,
                                    series_ids: list[int]) -> int:
    """Insert template + its series rows in transaction."""

def add_series_to_template(conn, template_id: int, analysis_series_id: int) -> None:
def remove_series_from_template(conn, template_id: int, analysis_series_id: int) -> None:
```

**B2. Update insert_sample** — add `sample_collection_kind_id`, `sample_equipment_id` to INSERT.
Both are nullable FKs already present in the Sample table schema. Just not wired through the
repo or API yet.

**B3. New API endpoint file** (`api/v1/endpoints/lab.py` — clean separation from sensor ingest)

```
GET    /ingest/lab/experiments/lookup
GET    /ingest/lab/experiments/{id}/series
GET    /ingest/lab/analysis-series/lookup
POST   /ingest/lab/analysis-series
GET    /ingest/lab/templates
GET    /ingest/lab/templates/{id}
POST   /ingest/lab/templates
POST   /ingest/lab/templates/{id}/series
DELETE /ingest/lab/templates/{id}/series/{series_id}
```

Pydantic schemas for request/response go in `api/v1/schemas/ingestion.py`.

**B4. Update SampleCreateRequest** (`api/v1/schemas/ingestion.py`):

```python
class SampleCreateRequest(BaseModel):
    sampling_point_id: int
    sampled_by_person_id: int | None = None
    campaign_id: int | None = None
    sample_datetime_start: datetime
    sample_datetime_end: datetime | None = None
    sample_collection_kind_id: int | None = None    # NEW — how collected
    sample_equipment_id: int | None = None           # NEW — equipment used
    description: str | None = None
```

---

### Phase C: Frontend components

**C1. Embeddable generic_crud** (`app/components/generic_crud.py`)

Add `embedded: bool = False` parameter:
- `embedded=False` (default) — current full-page behavior, unchanged
- `embedded=True` — compact rendering inside existing container, returns `True` if data was modified
- Reused for: AnalysisSeries inline management, Template series management

**C2. New API client functions** (`app/api_client.py`)

```python
def list_lab_experiments_lookup() -> list[dict]
def get_lab_experiment_series(experiment_id: int) -> list[dict]
def list_analysis_series_lookup() -> list[dict]
def create_analysis_series(data: dict) -> dict
def list_lab_experiment_templates() -> list[dict]
def get_lab_experiment_template(template_id: int) -> dict
def create_lab_experiment_template(data: dict) -> dict
def add_series_to_template(template_id: int, analysis_series_id: int) -> None
def remove_series_from_template(template_id: int, analysis_series_id: int) -> None
def list_sample_collection_kinds_lookup() -> list[dict]
def list_equipment_lookup() -> list[dict]
```

---

### Phase D: lab_ingest.py — full rewrite

Replace the flat form with an accordion layout using `st.expander`. No wizard navigation.
Three sections, all visible simultaneously.

```
┌───────────────────────────────────────────────────────────┐
│ Lab Analysis Ingest                                        │
│                                                           │
│ ┌─── ▼ Step 1: Experiment ──────────────────────────────┐ │
│ │                                                        │ │
│ │  Mode:  [New ●]  [From template ○]  [Continue existing ○] │ │
│ │                                                        │ │
│ │  Name*: [TSS-Settling-2026-06-02        ]              │ │
│ │  Campaign: [PSVD Study ▼]                              │ │
│ │  Date/time: [2026-06-02] [08:30]                       │ │
│ │  Created by: [Jane Smith ▼]         ← person dropdown │ │
│ │                                                        │ │
│ │  ── Assigned AnalysisSeries ──                         │ │
│ │  │ Series Name          │ Parameter │ Unit │ Kind     │ │
│ │  │ TSS Gravimetric@Eff  │ TSS       │ mg/L │ Scalar   │ │
│ │  │ PSVD@Eff             │ PSVD      │ µm   │ Vector   │ │
│ │  │ [+ Add series] [Remove]                             │ │
│ │                                                        │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                           │
│ ┌─── ▼ Step 2: Sample ──────────────────────────────────┐ │
│ │  Mode:  [Create new ●]  [Use existing ○]              │ │
│ │                                                        │ │
│ │  Sampling point:  [Effluent ▼]                         │ │
│ │  Collection kind: [Grab sample ▼]    ← NEW dropdown   │ │
│ │  Equipment:       [Auto sampler #2 ▼] ← NEW dropdown  │ │
│ │  Sampled by:      [Jane Smith ▼]     ← fixed dropdown │ │
│ │  Campaign:        [PSVD Study ▼]                       │ │
│ │  Start:  [2026-06-02] [08:30]                          │ │
│ │  End:    [2026-06-02] [08:35]                          │ │
│ │  Description: [                                       ] │ │
│ │  [Create Sample]                                        │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                           │
│ ┌─── ▼ Step 3: Measurement Values ──────────────────────┐ │
│ │  TSS Scalar │ PSVD Vector │ [+ Add series]            │ │
│ │  ┌─ TSS Gravimetric at Effluent (mg/L, RAW) ───────┐ │ │
│ │  │                                                   │ │ │
│ │  │ Value * │ Replicate │ Quality │ Notes            │ │ │
│ │  │ 12.4    │     1     │         │                  │ │ │
│ │  │ 10.1    │     2     │         │                  │ │ │
│ │  │         │           │         │                  │ │ │
│ │  └──────────────────────────────────────────────────┘ │ │
│ │  [Duplicate last row]                                   │ │
│ │                                                        │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                           │
│   [Submit Experiment]                                      │
└───────────────────────────────────────────────────────────┘
```

**Session state:**

```python
if "lab_session" not in st.session_state:
    st.session_state.lab_session = {
        # Step 1
        "mode": "new",                    # "new" | "template" | "existing"
        "template_id": None,
        "experiment_id": None,
        "name": "",
        "campaign_id": None,
        "datetime": datetime.now(),
        "description": "",
        "created_by_person_id": None,
        "series": [],                     # list of AnalysisSeries dicts

        # Step 2
        "sample_mode": "new",
        "sample_id": None,
        "sample_sp_id": None,
        "sample_collection_kind_id": None,
        "sample_equipment_id": None,
        "sample_sampled_by_id": None,
        "sample_campaign_id": None,
        "sample_start": datetime.now(),
        "sample_end": None,
        "sample_description": "",

        # Step 3
        "measurements": {},               # {series_index: [{value, replicate, qc, notes}]}
    }
```

**Accordion:**

```python
with st.expander("1. Experiment", expanded=True):
    _render_experiment_step()
with st.expander("2. Sample", expanded=st.session_state.lab_session.get("series")):
    _render_sample_step()
with st.expander("3. Measurement Values", expanded=st.session_state.lab_session.get("sample_id")):
    _render_measurement_step()
```

The `expanded` logic naturally guides the user: experiment always open, sample opens once
series are defined, values open once a sample exists.

**Step 1 (`_render_experiment_step`):**
- Mode radio → switches form fields
- "From template" → selectbox → fills series list
- "Continue existing" → selectbox → fills series list from experiment history
- "New" → text inputs for name/campaign/date/person
- Series table below: editable rows; each series is a mini-form with name+param+sp+unit+kind+processing
- "Add series" → modal or inline row with dropdowns from `list_analysis_series_lookup()`
- All inputs write to `st.session_state.lab_session`

**Step 2 (`_render_sample_step`):**
- Mode radio: create new or use existing
- Create new: sampling point (dropdown), collection kind (NEW dropdown), equipment (NEW dropdown),
  sampled by (FIXED dropdown), campaign, dates, description
- "Create Sample" button → POST with new fields → `sample_id` stored in session
- Use existing: selectbox from `list_samples_lookup()`

**Step 3 (`_render_measurement_step`):**
- Tabs, one per series in session
- Each tab: header with series identity (fixed), then dynamic `st.data_editor`
- Columns depend on ValueKind: NumberColumn for scalar, TextColumn "CSV" for vector/matrix, file upload for image
- "Duplicate last row" per tab
- Measures[series_index] stored in session

**Submit:**
1. Validate required fields
2. Build `LabIngestRequest` from session state
3. POST → success message with experiment ID
4. Session kept intact — user can create another sample for same experiment
5. "Clear form" button resets all session state

---

### Phase E: Tests

**E1. Python model tests:**
- `LabExperimentTemplateBase` / `LabExperimentTemplateSeriesBase` serialization
- `SampleCreateRequest` with new optional fields

**E2. API integration tests:**
- Lookup endpoints return expected shapes
- Template CRUD (create, get series, add/remove series)
- Sample creation with `sample_collection_kind_id` + `sample_equipment_id`
- Full submit flow with template-seeded series

**E3. Manual smoke test:**
1. Create template with 2 series
2. Create experiment from template → series pre-populate
3. Add/remove series before submit
4. Create sample with collection kind + equipment
5. Enter values per series tab
6. Submit → verify LabAnalysis + Observation rows created
7. Continue same experiment → create another sample → submit
8. Verify data integrity: no duplicate series, correct FK chain

---

## Implementation Order

```
Phase A: YAML + Python models + alias fix        → uv run pytest green
Phase B: API repository + endpoints + schema     → Python tests pass
Phase C: Frontend components + api_client         → client functions return correct data
Phase D: lab_ingest.py rewrite                   → manual E2E flow works
Phase E: Tests                                   → automated + manual tests pass
```

**Within Phase D (safe incremental build):**
1. Scaffold accordion + session state structure
2. Build Step 3 measurement tabs (works with hardcoded session data)
3. Build Step 2 sample creation (collection kind, equipment, person dropdowns)
4. Build Step 1 experiment + template + series management
5. Wire submit and session persistence
6. Remove old code paths

---

## Data model change summary

| Table | Action |
|---|---|
| LabExperimentTemplate | **NEW** — lookup table, no FKs to core data |
| LabExperimentTemplateSeries | **NEW** — junction table, no FKs to core data |
| Sample | **No change** — `SampleCollectionKind_ID` already exists |
| SampleCollectionKind | **No change** — already exists, seeded with Grab/Composite/Passive |
| Equipment | **No change** — FK from Sample already exists |
| `SampleBase.samplemethodID` | **Fix alias** — rename to `samplecollectionkindID` (Python-only, no migration) |
