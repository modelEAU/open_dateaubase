# Plan: Lab Observation Model Restructuring

## Context

`LabValue.LabResult` is a FLOAT64, blocking vector/matrix/image lab measurements. The Observation/payload infrastructure already supports all four value kinds but requires `Channel_ID NOT NULL`, which is wrong for lab data. Additionally, repeated lab measurements of the same parameter need a stable stream identity for time-series querying. This plan restructures the lab data model around two new concepts: `AnalysisSeries` (stream identity) and `LabExperiment` (session grouping), replaces `LabValue` with the shared `Observation` + payload tables, and updates the ingest API accordingly.

---

## Decisions

| # | Decision |
|---|---|
| 1 | 1 LabAnalysis = 1 parameter measurement on 1 sample. LabExperiment is the session grouping. |
| 2 | `UQ_LabAnalysis (LabExperiment_ID, AnalysisSeries_ID, Sample_ID, Replicate)` — prevents duplicate measurements |
| 3 | `Observation.Timestamp` stays NOT NULL, set to `LabAnalysis.AnalysisDateTime` at insert |
| 4 | XOR CHECK on Observation: exactly one of `(Channel_ID, LabAnalysis_ID)` IS NOT NULL |
| 5 | `Campaign_ID` removed from both `AnalysisSeries` and `LabAnalysis`; campaign lives on `LabExperiment` only |
| 6 | `UQ_AnalysisSeries (Parameter_ID, SamplingPoint_ID, ValueKind_ID, ProcessingKind_ID)` — `Unit_ID` excluded from constraint but made NOT NULL |
| 7 | `LabExperiment.ExperimentDateTime` NOT NULL; `LabExperiment.Name` NOT NULL |
| 8 | `ProcessingKind_ID` stays on `AnalysisSeries` (supports raw vs. corrected lab series) |
| 9 | `Laboratory_ID` and `Procedure_ID` stay on `LabAnalysis` (per-measurement, not per-session) |
| 10 | `CreatedByPerson_ID` removed from `AnalysisSeries` |
| 11 | `LabValue.yaml` deleted outright (pre-release, no tombstone needed) |
| 12 | `AnalysisSeriesAxis` mirrors `ChannelAxis` exactly (separate tables, same structure) |
| 13 | Extend `render.py` to support a `filter:` field on index specs (renders `WHERE` clause for both MSSQL and PostgreSQL) |
| 14 | API ingest: bulk session endpoint with find-or-create `AnalysisSeries` |

---

## Data model

```
LabExperiment                   AnalysisSeries
(session: who/when/campaign)    (identity: parameter × location × kind × processing)
         \                          /
          \                        /
           ──── LabAnalysis ────
                (one sample,
                one measurement)
                     |
                Observation
                     |
          Value / ValueVector / ValueMatrix / ValueImage
```

---

## Wave 1: Schema layer

### 1.1 Extend DDL renderer for filtered indexes

**File:** `tools/schema_migrate/render.py:241-256` (`_render_create_index`)

Add support for an optional `filter:` key on index entries. When present, append `WHERE <filter>` to the generated `CREATE INDEX` statement. Syntax is identical for MSSQL and PostgreSQL.

### 1.2 Create new YAML files

**`schema_dictionary/tables/AnalysisSeries.yaml`**

| Column | Type | Nullable | Notes |
|---|---|---|---|
| AnalysisSeries_ID | INT PK identity | NO | |
| Name | NVARCHAR(200) | NO | e.g. "TSS Gravimetric at Effluent" |
| Parameter_ID | INT FK → Parameter | NO | |
| SamplingPoint_ID | INT FK → SamplingPoint | NO | |
| ValueKind_ID | INT FK → ValueKind DEFAULT 1 | NO | |
| Unit_ID | INT FK → Unit | NO | Fixed unit for all measurements in this series |
| ProcessingKind_ID | INT FK → ProcessingKind DEFAULT 1 | NO | |
| Description | NVARCHAR(MAX) | YES | |

Unique constraint: `UQ_AnalysisSeries (Parameter_ID, SamplingPoint_ID, ValueKind_ID, ProcessingKind_ID)`

**`schema_dictionary/tables/AnalysisSeriesAxis.yaml`**

Mirror of `ChannelAxis.yaml` with `AnalysisSeries_ID` instead of `Channel_ID`.

| Column | Type | Notes |
|---|---|---|
| AnalysisSeries_ID | INT PK FK → AnalysisSeries | |
| AxisRole | INT PK | 0=row/primary, 1=col/secondary |
| ValueBinningAxis_ID | INT FK → ValueBinningAxis | |

CHECK: `AxisRole IN (0, 1)`

**`schema_dictionary/tables/LabExperiment.yaml`**

| Column | Type | Nullable | Notes |
|---|---|---|---|
| LabExperiment_ID | INT PK identity | NO | |
| Name | NVARCHAR(200) | NO | |
| Campaign_ID | INT FK → Campaign | YES | |
| ExperimentDateTime | DATETIME2(7) | NO | |
| Description | NVARCHAR(MAX) | YES | |
| CreatedByPerson_ID | INT FK → Person | YES | |

### 1.3 Modify existing YAML files

**`schema_dictionary/tables/LabAnalysis.yaml`**

Add:
- `LabExperiment_ID INT NOT NULL FK → LabExperiment`
- `AnalysisSeries_ID INT NOT NULL FK → AnalysisSeries`
- `Replicate INT NOT NULL DEFAULT 1`
- `QualityCode_ID INT nullable FK → QualityCode`

Remove: `Campaign_ID`

Add unique constraint: `UQ_LabAnalysis (LabExperiment_ID, AnalysisSeries_ID, Sample_ID, Replicate)`

**`schema_dictionary/tables/Observation.yaml`**

- `Channel_ID`: change to `nullable: true`
- Add: `LabAnalysis_ID INT nullable FK → LabAnalysis`
- Replace existing unique constraint with two filtered constraints:
  - `UQ_Obs_Channel (Channel_ID, Timestamp, ValueKind_ID)` with `filter: "Channel_ID IS NOT NULL"`
  - `UQ_Obs_Lab (LabAnalysis_ID)` with `filter: "LabAnalysis_ID IS NOT NULL"`
- Add CHECK: `CK_Observation_Source: (Channel_ID IS NOT NULL AND LabAnalysis_ID IS NULL) OR (Channel_ID IS NULL AND LabAnalysis_ID IS NOT NULL)`

**`schema_dictionary/tables/LabValue.yaml`** — delete this file.

### 1.4 Regenerate DDL

Run the schema generation script and verify `sql_generation_scripts/v4.1.0_create_mssql.sql` contains:
- New tables: `AnalysisSeries`, `AnalysisSeriesAxis`, `LabExperiment`
- Modified `LabAnalysis` with new FKs, unique constraint, no `Campaign_ID`
- Modified `Observation` with nullable `Channel_ID`, `LabAnalysis_ID`, XOR CHECK, filtered unique constraints
- No `LabValue` table

---

## Wave 2: Python models

**File:** `src/open_dateaubase/data_model/table_models.py`

**`ObservationBase`** — make `channelID` Optional, add `labanalysisID`:
```python
channelID: Optional[int] = Field(None, alias="Channel_ID")
labanalysisID: Optional[int] = Field(None, alias="LabAnalysis_ID")
```

**`LabAnalysisBase`** — add new required fields, remove `campaignID`:
```python
labexperimentID: int = Field(..., alias="LabExperiment_ID")
analysisseriesID: int = Field(..., alias="AnalysisSeries_ID")
replicate: int = Field(1, alias="Replicate")
qualitycodeID: Optional[int] = Field(None, alias="QualityCode_ID")
# remove: campaignID
```

**Remove** `LabValueBase` and `LabValue` classes.

**Add** three new model pairs following the existing frozen `ConfigDict(from_attributes=True, populate_by_name=True)` pattern:
- `AnalysisSeriesBase` / `AnalysisSeries`
- `AnalysisSeriesAxisBase` / `AnalysisSeriesAxis`
- `LabExperimentBase` / `LabExperiment`

---

## Wave 3: API layer

### 3.1 `api/v1/schemas/ingestion.py`

Replace `LabValueItem` and `LabIngestRequest` with:

```python
class LabMeasurementItem(BaseModel):
    # Series identity — used to find or create AnalysisSeries
    parameter_id: int
    sampling_point_id: int
    unit_id: int
    value_kind_id: int = 1
    processing_kind_id: int = 1
    series_name: str

    # Measurement
    sample_id: int
    value: float | list | None
    laboratory_id: int | None = None
    analyst_person_id: int | None = None
    procedure_id: int | None = None
    analysis_datetime: datetime | None = None  # defaults to SYSUTCDATETIME() if omitted
    replicate: int = 1
    quality_code_id: int | None = None
    notes: str | None = None

class LabIngestRequest(BaseModel):
    name: str
    experiment_datetime: datetime
    campaign_id: int | None = None
    description: str | None = None
    created_by_person_id: int | None = None
    measurements: list[LabMeasurementItem]

    @validator("measurements")
    def measurements_not_empty(cls, v): ...

class LabIngestResponse(BaseModel):
    lab_experiment_id: int
    rows_written: int
```

### 3.2 `api/v1/repositories/ingestion_repository.py`

Add:

**`find_or_create_analysis_series(conn, parameter_id, sampling_point_id, value_kind_id, processing_kind_id, unit_id, name) → int`**
- SELECT by `(Parameter_ID, SamplingPoint_ID, ValueKind_ID, ProcessingKind_ID)`
- INSERT if not found (with `Unit_ID`, `Name`)
- Return `AnalysisSeries_ID`

**`insert_lab_experiment(conn, name, experiment_datetime, campaign_id, description, created_by_person_id) → int`**
- INSERT into `LabExperiment`, return `LabExperiment_ID`

**`insert_lab_analysis(conn, ...)` — updated signature:**
`(lab_experiment_id, analysis_series_id, sample_id, laboratory_id, analyst_person_id, procedure_id, analysis_datetime, replicate, quality_code_id, notes) → int`

**`insert_lab_observation(conn, lab_analysis_id, timestamp, value_kind_id, value) → int`**
- INSERT into `Observation` (`LabAnalysis_ID`, `Timestamp`, `ValueKind_ID`, `Channel_ID=NULL`)
- Route payload to `Value` / `ValueVector` / `ValueMatrix` based on `value_kind_id`

Remove `insert_lab_value()`.

### 3.3 `api/v1/endpoints/ingest.py` — `POST /ingest/lab`

New flow:
1. `insert_lab_experiment()` → `lab_experiment_id`
2. For each item in `request.measurements`:
   a. `find_or_create_analysis_series()` → `series_id`
   b. `insert_lab_analysis()` → `lab_analysis_id`
   c. `insert_lab_observation()` → `observation_id`
3. Return `LabIngestResponse(lab_experiment_id=..., rows_written=len(measurements))`

---

## Wave 4: Tests

- `tests/api/contract/test_schema_contracts.py`: update `LabIngestRequest` validation test to new shape
- Search `tests/` for `LabValue`, `lab_value`, `LabResult`, `LabIngestRequest` and update all references
- Add integration test: insert `AnalysisSeries` + `LabExperiment` + `LabAnalysis` + `Observation`; confirm scalar routes to `Value`; confirm sensor `Observation` (Channel_ID path) still works

---

## Verification

```bash
uv run pytest                        # green baseline before any changes
# after Wave 1: regenerate DDL, inspect for XOR CHECK + filtered UQs
uv run pytest
# after Wave 2: model tests green
uv run pytest
# after Waves 3-4: all tests green
uv run pytest
uv run mkdocs build                  # ERD diagrams update
```

Manual smoke test (test DB):
1. Insert `AnalysisSeries` + `LabExperiment` + scalar `LabAnalysis` → confirm routes to `Value`
2. Insert vector `LabAnalysis` → confirm routes to `ValueVector`
3. Confirm old sensor `Observation` (Channel_ID path) unaffected
4. Run TSS time-series query from original design doc; verify ordering
