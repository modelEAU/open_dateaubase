# Lab Data (v2.0.0+)

**Schema version introduced:** 2.0.0
**Phase:** B

---

## Background

Discrete laboratory measurements are fundamentally different from continuous sensor streams:

- A lab measurement is tied to a **physical sample** (a bottle of water collected at a point in time).
- Multiple analytes may be measured on the same sample in a single analytical run.
- Lab data has its own provenance metadata: which laboratory, which analyst, which procedure, which replicate.

The **Channel** model describes an invariant *stream* identified by equipment + parameter. This abstraction does not fit lab data — there is no continuous equipment stream for a grab sample. For this reason, lab data lives in dedicated tables (`LabAnalysis` + `LabValue`) rather than in `Channel` + `Value`.

---

## Tables

### LabAnalysis

One row per analytical run on a discrete physical sample.

| Column | Type | Notes |
| --- | --- | --- |
| `LabAnalysis_ID` | INT IDENTITY | Surrogate PK |
| `Sample_ID` | INT FK→Sample | The physical sample analysed (required) |
| `Laboratory_ID` | INT FK→Laboratory | Where analysis was performed (nullable) |
| `AnalystPerson_ID` | INT FK→Person | Who performed the analysis (nullable) |
| `Procedure_ID` | INT FK→Procedures | SOP used (nullable) |
| `AnalyzedAt` | DATETIME2(7) | UTC datetime of analysis (default: now) |
| `Campaign_ID` | INT FK→Campaign | Campaign this analysis belongs to (nullable) |
| `Notes` | NVARCHAR(500) | Free-text notes |

### LabValue

One row per measured value (one analyte + replicate) within a `LabAnalysis`.

| Column | Type | Notes |
| --- | --- | --- |
| `LabValue_ID` | INT IDENTITY | Surrogate PK |
| `LabAnalysis_ID` | INT FK→LabAnalysis | Parent analysis run (required) |
| `Parameter_ID` | INT FK→Parameter | Analyte measured (required) |
| `Unit_ID` | INT FK→Unit | Measurement unit (required) |
| `Value` | FLOAT | Numerical result |
| `Replicate` | INT | Replicate index (1 = primary, 2+ = duplicates) |
| `QualityCode` | INT | Optional quality flag |
| `Comment_ID` | INT FK→Comments | Optional free-text comment |

### Supporting Tables (shared with sensor model)

| Table | Purpose |
| --- | --- |
| `Sample` | Discrete physical sample with collection metadata |
| `Laboratory` | Lab name and optional site link |
| `CampaignEquipment` | Equipment deployed during a campaign |
| `CampaignSamplingLocation` | Locations monitored during a campaign |

---

## How to Record a Lab Measurement

### Step 1: Create or reuse the Sample row

```sql
INSERT INTO [dbo].[Sample]
    ([Sampling_point_ID], [SampledByPerson_ID], [Campaign_ID],
     [SampleDateTimeStart], [SampleType], [Description])
VALUES
    (@sp_id, @marie_id, @campaign_id,
     '2025-03-15T08:00:00', 'Grab', 'Morning inlet grab sample');

SET @sample_id = SCOPE_IDENTITY();
```

### Step 2: Create a LabAnalysis row

```sql
INSERT INTO [dbo].[LabAnalysis]
    ([Sample_ID], [Laboratory_ID], [AnalystPerson_ID], [Procedure_ID],
     [Campaign_ID], [Notes])
VALUES
    (@sample_id, @lab_id, @marie_id, @sop_id,
     @campaign_id, NULL);

SET @lab_analysis_id = SCOPE_IDENTITY();
```

### Step 3: Insert LabValue rows (one per analyte per replicate)

```sql
INSERT INTO [dbo].[LabValue]
    ([LabAnalysis_ID], [Parameter_ID], [Unit_ID], [Value], [Replicate])
VALUES
    (@lab_analysis_id, @tss_param_id, @mgl_unit_id, 24.5, 1),   -- TSS replicate 1
    (@lab_analysis_id, @tss_param_id, @mgl_unit_id, 24.8, 2),   -- TSS replicate 2
    (@lab_analysis_id, @cod_param_id, @mgl_unit_id, 312.0, 1);  -- COD replicate 1
```

---

## API: Ingesting Lab Data

### POST /api/v1/ingest/lab

```json
{
  "sample_id": 5,
  "laboratory_id": 1,
  "analyst_person_id": 3,
  "procedure_id": null,
  "campaign_id": 2,
  "notes": null,
  "values": [
    {"parameter_id": 1, "unit_id": 2, "value": 24.5, "replicate": 1},
    {"parameter_id": 1, "unit_id": 2, "value": 24.8, "replicate": 2},
    {"parameter_id": 4, "unit_id": 2, "value": 312.0, "replicate": 1}
  ]
}
```

Response:

```json
{
  "lab_analysis_id": 42,
  "lab_value_ids": [101, 102, 103]
}
```

---

## Filtering Recipes

### All lab results for a sample

```sql
SELECT lv.[Parameter_ID], p.[Parameter], lv.[Value], lv.[Unit_ID], lv.[Replicate]
FROM   [dbo].[LabValue]    lv
JOIN   [dbo].[LabAnalysis] la ON la.[LabAnalysis_ID] = lv.[LabAnalysis_ID]
JOIN   [dbo].[Parameter]   p  ON p.[Parameter_ID]    = lv.[Parameter_ID]
WHERE  la.[Sample_ID] = @sample_id
ORDER BY p.[Parameter], lv.[Replicate];
```

### All lab analyses for a campaign

```sql
SELECT la.[LabAnalysis_ID], la.[AnalyzedAt], s.[SampleDateTimeStart],
       sp.[Sampling_point]
FROM   [dbo].[LabAnalysis]   la
JOIN   [dbo].[Sample]        s  ON s.[Sample_ID]          = la.[Sample_ID]
JOIN   [dbo].[SamplingPoints] sp ON sp.[Sampling_point_ID] = s.[Sampling_point_ID]
WHERE  la.[Campaign_ID] = @campaign_id
ORDER BY la.[AnalyzedAt];
```

### TSS lab values at a location (for comparison with sensor)

```sql
SELECT la.[AnalyzedAt], lv.[Value], lv.[Replicate]
FROM   [dbo].[LabValue]      lv
JOIN   [dbo].[LabAnalysis]   la ON la.[LabAnalysis_ID] = lv.[LabAnalysis_ID]
JOIN   [dbo].[Sample]        s  ON s.[Sample_ID]       = la.[Sample_ID]
WHERE  lv.[Parameter_ID]        = @tss_param_id
  AND  s.[Sampling_point_ID]    = @sp_id
ORDER BY la.[AnalyzedAt];
```

---

## Campaign Junction Tables

Three junction tables define which resources a campaign uses — all introduced in v1.3.0,
unchanged since:

| Table | Links | Purpose |
| --- | --- | --- |
| `CampaignSamplingLocation` | Campaign ↔ SamplingPoints | Locations monitored in campaign |
| `CampaignEquipment` | Campaign ↔ Equipment | Equipment deployed in campaign |
| `CampaignParameter` | Campaign ↔ Parameter | Parameters measured in campaign |

### Locations used in a campaign

```sql
SELECT sp.[Sampling_location]
FROM   [dbo].[CampaignSamplingLocation] csl
JOIN   [dbo].[SamplingPoints]           sp  ON csl.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE  csl.[Campaign_ID] = @campaign_id;
```

### Campaigns that share any sampling location

```sql
SELECT DISTINCT c.[Name]
FROM   [dbo].[CampaignSamplingLocation] csl1
JOIN   [dbo].[CampaignSamplingLocation] csl2 ON csl1.[Sampling_point_ID] = csl2.[Sampling_point_ID]
JOIN   [dbo].[Campaign] c ON csl2.[Campaign_ID] = c.[Campaign_ID]
WHERE  csl1.[Campaign_ID] = @campaign_a_id
  AND  csl2.[Campaign_ID] != @campaign_a_id;
```
