# Lab Ingest UI Redesign

## Current Problems

### 1. No session-level identity
The current page treats each submission as a one-shot flat list of rows. There is:
- No way to **select an existing LabExperiment** and see what was previously recorded
- No way to **browse ongoing experiments** to add more samples to them
- Data recovery on error is impossible — the whole form clears

### 2. No AnalysisSeries pre-population
Each row in the data editor repeats parameter, sampling_point, unit, series_name — against the user's mental model where "I'm measuring TSS at Effluent today, I should pick that series once and just enter values."
- AnalysisSeries already bundles (Parameter × SamplingPoint × Unit × ValueKind × ProcessingKind)
- The current page ignores this and asks for each field per-row

### 3. Missing sample fields
`SampleCreateRequest` and `SampleBase` support `sample_method_id`, `sample_equipment_id`, and `sampled_by_person_id`, but:
- **Method** (`SampleMethod_ID`) is absent from the UI
- **Sampled by** (`SampledByPerson_ID`) is a raw number input instead of a person dropdown
- **Equipment** (`SampleEquipment_ID`) is absent from the UI

### 4. Person IDs as raw number inputs
Both `CreatedByPerson_ID` and `SampledByPerson_ID` are `st.number_input` — users must know/create a numeric ID. The `list_persons_lookup()` endpoint already provides `{person_id, label}` for dropdowns.

### 5. No multi-sample workflow
A LabExperiment (session) often has multiple samples, each getting measurements. Current flow locks to one sample per submission and re-creates the experiment header each time.

---

## Proposed Workflow

```
 ┌──────────────────────────────┐
 │ Step 1: Experiment Context   │
 │  - Select existing experiment│
 │    OR create new one         │
 │  - If existing: series auto- │
 │    populate from its history │
 │  - If new: pick/create       │
 │    AnalysisSeries(es)        │
 └──────────┬───────────────────┘
            │
 ┌──────────▼───────────────────┐
 │ Step 2: Sample               │
 │  - Select existing sample OR │
 │    create new one            │
 │  - Sampling point (dropdown) │
 │  - Method (dropdown)         │
 │  - Equipment (dropdown)      │
 │  - Sampled by (dropdown)     │
 │  - Start/end date+time       │
 │  - Description               │
 └──────────┬───────────────────┘
            │
 ┌──────────▼───────────────────┐
 │ Step 3: Measurement Values   │
 │  - One tab per AnalysisSeries│
 │    selected in Step 1        │
 │  - Series identity pre-filled│
 │    (param, unit, processing) │
 │  - Just enter values +       │
 │    replicate / quality /     │
 │    notes for each sample-row │
 │  - Or add more series        │
 └──────────┬───────────────────┘
            │
 ┌──────────▼───────────────────┐
 │ Step 4: Review & Submit      │
 │  - Summary of experiment +   │
 │    sample + N measurements   │
 │  - Submit → creates          │
 │    LabAnalysis rows +        │
 │    Observations              │
 └──────────────────────────────┘
```

### Design decisions

| Decision | Rationale |
|---|---|
| Wizard (multi-step) over one long page | Keeps each step focused. Current page already has 4 sections that feel sequential. |
| Experiment-first, not series-first | The user organises their work by experiment session. Series are secondary ("what am I measuring in this session"). |
| Existing-experiment → auto-populate series | If a user ran "PSVD Settling" yesterday, today's experiment should start from the same series list. |
| Sample creation as a dedicated step | Separates sample concerns (collection details) from measurement concerns (values). |
| Series changes tracked in session | If the user realises they need more series mid-way, they can add them without starting over. |
| Keep Scalar/Vector/Matrix/Image tabs | Value-kind grouping is correct — different input UIs per kind. But tabs should be per-series, not per-kind. |

---

## Detailed Design

### Step 1 — Experiment Context

**Mode: "New experiment" | "Continue existing"**

**New experiment:**
| Field | Widget | Source |
|---|---|---|
| Name* | text_input | — |
| Campaign | selectbox | `list_campaigns_lookup()` |
| Date/time* | date_input + time_input | — |
| Description | text_area | — |
| Created by* | selectbox | `list_persons_lookup()` |

**Continue existing:**
- `selectbox` listing recent LabExperiments (name + date) via `GET /ingest/lab/experiments/lookup`
- On selection, load the LabExperiment's existing AnalysisSeries into the session

**Series assignment (both modes):**
Once experiment context is set, show a **Series Manager**:
- List of currently assigned AnalysisSeries (Name, Parameter, Unit, ProcessingKind)
- "Add series" button → selectbox picking from `GET /ingest/lab/analysis-series/lookup` (or create new inline)
- "Remove series" button on each
- Each series is a row: [Name, Parameter, SamplingPoint, Unit, ValueKind, ProcessingKind] — read-only for existing, editable for new

If no series are assigned yet, prompt: *"Add at least one AnalysisSeries to continue."*

**Required new API endpoints:**
- `GET /ingest/lab/experiments/lookup` → list of `{lab_experiment_id, name, experiment_datetime, series_count}` recent experiments
- `GET /ingest/lab/experiments/{id}/series` → list of `{AnalysisSeries}` FK'd to that experiment
- `GET /ingest/lab/analysis-series/lookup` → list of all `{analysis_series_id, name, parameter_name, sampling_point_label, unit, processing_kind_name}`
- `POST /ingest/lab/analysis-series` → create one (fields: name, parameter_id, sampling_point_id, unit_id, value_kind_id, processing_kind_id)

### Step 2 — Sample

**Mode: "Use existing sample" | "Create new sample"**

Same basic structure as current Section B, but with fixes:

| Field | Change | Widget |
|---|---|---|
| Sampling point* | Unchanged | selectbox |
| Sample method | **NEW** — select from list | selectbox via `list_sample_collection_kinds()` or dedicated `GET /sample-methods/lookup` |
| Sample equipment | **NEW** — select from list | selectbox via `list_equipment(...)` or dedicated |
| Sampled by | **FIX** — was number input | selectbox via `list_persons_lookup()` |
| Campaign | Unchanged | selectbox |
| Start date/time* | Unchanged | date_input + time_input |
| End date/time | Unchanged | date_input + time_input |
| Description | Unchanged | text_area |

**Required new API endpoints / changes:**
- `SampleCreateRequest.sample_method_id` — add field (nullable, INT FK → SampleMethod)
- `SampleCreateRequest.sample_equipment_id` — add field (nullable, INT FK → SampleEquipment)
- `GET /sample-methods/lookup` or reuse existing `list_sample_collection_kinds()`

### Step 3 — Measurement Values

Render **one tab per AnalysisSeries** selected in Step 1 (not per value-kind).

Within each tab, the user enters values for that series. The series identity is fixed (parameter, unit, sampling point, processing kind). The user just provides:

| Field | Notes |
|---|---|
| Value* | float / comma-separated / semicolon-separated / image upload — depends on ValueKind |
| Replicate | int, default 1 |
| Quality code | optional int |
| Notes | optional text |

If there are multiple series with the same ValueKind (e.g., two scalar series), they each get their own tab — avoids confusion about which row belongs to which series.

**"Add another measurement for this series"** — dynamic rows within each tab.

### Step 4 — Review & Submit

Summary card:
- Experiment: name, date, campaign, created by
- Sample: ID, location, method, equipment, collected by
- Series: N series × M measurements each
- Submit button → `POST /ingest/lab` with existing API shape

---

## UI Sketch

```
┌─────────────────────────────────────────────────────┐
│  Lab Analysis Ingest                                 │
│  Step 1 · Step 2 · Step 3 · Step 4                  │
├─────────────────────────────────────────────────────┤
│ ● Experiment Context                                 │
│                                                      │
│  Mode: [Continue existing ●]  [New experiment  ]     │
│                                                      │
│  Experiment: [PSVD-Settling-2026-06-02 ▼]            │
│                                                      │
│  ┌─ Series for this experiment ──────────────────┐   │
│  │ ☑ TSS Gravimetric at Effluent  (scalar)      │   │
│  │ ☑ PSVD at Effluent            (vector)        │   │
│  │ ☐ COD at Influent             (scalar)        │   │
│  │ [+ Add series]                                 │   │
│  └───────────────────────────────────────────────┘   │
│                                                      │
│             [Back]              [Next: Sample →]     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Step 2: Sample                                     │
│                                                      │
│  Mode: [Create new sample ●]  [Use existing    ]     │
│                                                      │
│  Sampling point: [Effluent ▼]                        │
│  Method:         [Grab sample ▼]                     │
│  Equipment:      [— none — ▼]                        │
│  Sampled by:     [Jane Smith ▼]                      │
│  Campaign:       [PSVD-Settling-Study ▼]             │
│  Start:  [2026-06-02]  [08:30]                       │
│  End:    [2026-06-02]  [08:35]                       │
│  Description: [                                        ] │
│                                                      │
│             [← Back]          [Next: Values →]        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Step 3: Measurement Values                         │
│                                                      │
│  TSS Gravimetric @ Effl.  │ PSVD @ Effl. │ +Series  │
│  ┌──────────────────────────────────────────────┐    │
│  │ Series: TSS Gravimetric at Effluent          │    │
│  │ Parameter: TSS   Unit: mg/L   Processing: RAW│    │
│  │                                              │    │
│  │  Value * │ Replicate │ Quality │ Notes       │    │
│  │ ─────────┼───────────┼─────────┼─────────────│    │
│  │   12.4   │     1     │         │             │    │
│  │   10.1   │     2     │         │             │    │
│  │          │           │         │             │    │ ← dynamic rows
│  └──────────────────────────────────────────────┘    │
│                                                      │
│             [← Back]      [Review & Submit →]        │
└─────────────────────────────────────────────────────┘
```

---

## File Changes Summary

### New files
- `app/pages/lab_ingest.py` — full rewrite (was already the existing page, now wizard)

### Modified files
- `app/api_client.py` — add: `list_lab_experiments_lookup()`, `get_lab_experiment_series()`, `list_analysis_series_lookup()`, `create_analysis_series()`, `list_sample_methods_lookup()`, `list_sample_equipment_lookup()`
- `app/pages/lab_ingest.py` — rewrite with wizard, pre-population, sample method/equipment, person dropdowns

### API layer (existing plan already covers these)
- Edge endpoint changes to support sample method/equipment are additive

---

## Migration Strategy

1. Build Step 3 (Measurement Values with per-series tabs) first — reusable block
2. Rebuild Step 2 (Sample) with method, equipment, person dropdown fixes
3. Build Step 1 (Experiment Context) with series manager
4. Wire up Step 4 (Review & Submit)
5. Add navigation (Next/Back) between steps
6. Add required API lookup endpoints
7. Deploy and test end-to-end