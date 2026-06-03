# Design: Lab Observation Model Restructuring

## Context

`LabValue.LabResult` is a `FLOAT64`, making lab measurements scalar-only. Real lab work
produces vectors (PSVD), matrices, and images. The Observation/payload infrastructure
already supports all four value kinds but is locked behind `Observation.Channel_ID NOT NULL`
(requires a signal interface — wrong concept for lab data).

Additionally, repeated lab measurements of the same type need to form queryable time series,
requiring a stable stream identity per parameter.

---

## Data model design

LabAnalysis sits at the intersection of two orthogonal grouping axes:

```
LabExperiment                   AnalysisSeries
(session: who/when/samples)     (identity: what is measured, over time)
         \                          /
          \                        /
           ──── LabAnalysis ────
                (one sample,
                one observation)
                     |
                Observation
                     |
          Value / ValueVector / ValueMatrix / ValueImage
```

| Entity | Purpose | Analogy |
|---|---|---|
| AnalysisSeries | Stable stream identity (Parameter, SamplingPoint, ValueKind, Unit, axes) | Channel |
| LabExperiment | Session grouping — one named occasion, can span multiple series | "a lab run" |
| LabAnalysis | One measurement on one sample; FK to both Experiment and Series | event record |
| Observation | Temporal anchor, routes to payload | Observation (shared) |

Example — PSVD settling session 2026-05-11:

- LabExperiment "PSVD-Settling-2026-05-11" groups ALL analyses done that day
  - LabAnalysis 1: series=TSS-Effluent, sample=A  → scalar 12.4 mg/L
  - LabAnalysis 2: series=TSS-Effluent, sample=A1 → scalar 10.1 mg/L
  - LabAnalysis 3: series=TSS-Effluent, sample=A2 → scalar 11.8 mg/L
  - LabAnalysis 4: series=TSS-Effluent, sample=A3 → scalar 10.9 mg/L
  - LabAnalysis 5: series=PSVD-Effluent, sample=A → vector [0.5%, 1.2%, ...]

The TSS time series = all LabAnalyses where `AnalysisSeries_ID = <TSS-Gravimetric-Effluent>`.
The PSVD session = all LabAnalyses where `LabExperiment_ID = <PSVD-Settling-2026-05-11>`.

---

## Schema changes

### New tables

#### AnalysisSeries

Stream identity for lab measurements (analogous to Channel).

Unlike Channel, which intentionally excludes sampling location from its identity
(location is inferred at query time via EquipmentLocationHistory), AnalysisSeries
includes SamplingPoint_ID as explicit identity. Lab samples always have a known origin
and "TSS at Influent" must be a different series from "TSS at Effluent".

| Column | Type | Notes |
|---|---|---|
| AnalysisSeries_ID | INT PK identity | |
| Name | NVARCHAR(200) NOT NULL | e.g. "TSS Gravimetric at Effluent" |
| Parameter_ID | INT NOT NULL FK → Parameter | What is measured |
| SamplingPoint_ID | INT NOT NULL FK → SamplingPoint | Where samples originate |
| ValueKind_ID | INT NOT NULL DEFAULT 1 FK → ValueKind | |
| Unit_ID | INT nullable FK → Unit | |
| ProcessingKind_ID | INT NOT NULL DEFAULT 1 FK → ProcessingKind | |
| Campaign_ID | INT nullable FK → Campaign | |
| Description | NVARCHAR(MAX) nullable | |
| CreatedByPerson_ID | INT nullable FK → Person | |

#### AnalysisSeriesAxis

Axis definitions for Vector/Matrix series (analogous to ChannelAxis).

| Column | Type | Notes |
|---|---|---|
| AnalysisSeries_ID | INT PK FK → AnalysisSeries | |
| AxisRole | INT PK | 0=row/primary, 1=col/secondary |
| ValueBinningAxis_ID | INT FK → ValueBinningAxis | |

#### LabExperiment

Session container — groups heterogeneous analyses done together in one lab occasion.

| Column | Type | Notes |
|---|---|---|
| LabExperiment_ID | INT PK identity | |
| Name | NVARCHAR(200) nullable | e.g. "PSVD-Settling-2026-05-11" |
| Campaign_ID | INT nullable FK → Campaign | |
| ExperimentDateTime | DATETIME2(7) nullable | When the session took place |
| Description | NVARCHAR(MAX) nullable | |
| CreatedByPerson_ID | INT nullable FK → Person | |

---

### Modified tables

#### LabAnalysis — add two required FKs + Replicate + QualityCode_ID

New columns:

| Column | Type | Notes |
|---|---|---|
| LabExperiment_ID | INT NOT NULL FK → LabExperiment | Which session |
| AnalysisSeries_ID | INT NOT NULL FK → AnalysisSeries | Which measurement stream |
| Replicate | INT NOT NULL DEFAULT 1 | Moved from LabValue |
| QualityCode_ID | INT nullable FK → QualityCode | Moved from LabValue |

Existing columns remain: LabAnalysis_ID, Sample_ID, Laboratory_ID, AnalystPerson_ID,
Procedure_ID, AnalysisDateTime, Campaign_ID, Notes (Notes replaces LabValue.Comment).

LabAnalysis does NOT carry Parameter_ID / ValueKind_ID / Unit_ID — those live on AnalysisSeries.

#### Observation — decouple from Channel

Changes:

- `Channel_ID` nullable: true (was NOT NULL)
- ADD `LabAnalysis_ID` INT nullable FK → LabAnalysis
- ADD CHECK: exactly one of (Channel_ID, LabAnalysis_ID) IS NOT NULL
- Update unique constraints:
  - Sensor: `UQ_Obs_Channel (Channel_ID, Timestamp, ValueKind_ID)` WHERE Channel_ID IS NOT NULL
  - Lab: `UQ_Obs_Lab (LabAnalysis_ID)` WHERE LabAnalysis_ID IS NOT NULL (1 obs per analysis)

---

### Dropped tables

#### LabValue — REMOVED

Replaced by `Observation` (via LabAnalysis_ID) + existing payload tables.

Field migration:

- `Parameter_ID` → `AnalysisSeries.Parameter_ID`
- `Replicate` → `LabAnalysis.Replicate`
- `QualityCode_ID` → `LabAnalysis.QualityCode_ID`
- `Comment` → `LabAnalysis.Notes`
- `LabResult` (FLOAT64 scalar) → `Value.Value` (or ValueVector / ValueMatrix / ValueImage)

---

## Example queries

```sql
-- TSS time series (across all sessions):
SELECT le.ExperimentDateTime, la.AnalysisDateTime, s.Sample_ID, v.Value
FROM LabAnalysis la
JOIN LabExperiment le       ON la.LabExperiment_ID = le.LabExperiment_ID
JOIN Sample s               ON la.Sample_ID = s.Sample_ID
JOIN Observation o          ON o.LabAnalysis_ID = la.LabAnalysis_ID
JOIN Value v                ON v.Observation_ID = o.Observation_ID
WHERE la.AnalysisSeries_ID = 2   -- "TSS-Gravimetric-Effluent"
ORDER BY la.AnalysisDateTime;

-- Everything measured in one PSVD session (cross-parameter):
SELECT as_.Name AS series, la.Sample_ID, la.AnalysisDateTime
FROM LabAnalysis la
JOIN AnalysisSeries as_     ON la.AnalysisSeries_ID = as_.AnalysisSeries_ID
WHERE la.LabExperiment_ID = 7;   -- "PSVD-Settling-2026-05-11"

-- Confirm old sensor data still works (no change to sensor path):
SELECT c.Channel_ID, o.Timestamp, v.Value
FROM Channel c
JOIN Observation o ON o.Channel_ID = c.Channel_ID
JOIN Value v       ON v.Observation_ID = o.Observation_ID
WHERE c.Channel_ID = 42;
```

---

## Files to create / modify

### YAML schema dictionary

Create:

- `schema_dictionary/tables/AnalysisSeries.yaml`
- `schema_dictionary/tables/AnalysisSeriesAxis.yaml`
- `schema_dictionary/tables/LabExperiment.yaml`

Modify:

- `schema_dictionary/tables/LabAnalysis.yaml` — add LabExperiment_ID, AnalysisSeries_ID (both NOT NULL), Replicate, QualityCode_ID
- `schema_dictionary/tables/Observation.yaml` — Channel_ID nullable, add LabAnalysis_ID, update constraints
- `schema_dictionary/tables/LabValue.yaml` — mark as removed

### Python models

`src/open_dateaubase/data_model/table_models.py`:

- `ObservationBase`: `channelID` → `Optional[int]`, add `labanalysisID: Optional[int]`
- `LabAnalysisBase`: add `labexperimentID: int`, `analysisseriesID: int`, `replicate: int`, `qualitycodeID: Optional[int]`
- Remove `LabValueBase` / `LabValue`
- Add `AnalysisSeriesBase` / `AnalysisSeries`
- Add `AnalysisSeriesAxisBase` / `AnalysisSeriesAxis`
- Add `LabExperimentBase` / `LabExperiment`

### SQL DDL (regenerated from YAML)

- `sql_generation_scripts/v4.1.0_create_mssql.sql`
- `sql_generation_scripts/v4.1.0_seed_mssql.sql` (check if seed changes needed)

### API / Repository (follow-on scope)

- `api/v1/endpoints/ingest.py`: update `POST /ingest/lab` request shape
- `api/v1/repositories/ingestion_repository.py`: update lab ingestion logic

### Tests

Search `LabValue`, `lab_value`, `LabResult` and update.

---

## Verification

1. `uv run pytest` green before changes
2. After YAML edits, regenerate DDL
3. Spin up test DB; insert an AnalysisSeries + LabExperiment + LabAnalyses; confirm
   scalar and vector observations route to correct payload tables
4. Confirm sensor Observations still work (Channel_ID IS NOT NULL path unaffected)
5. Run the time-series query above; verify ordering and completeness
6. `uv run mkdocs build` — ERD diagrams update
