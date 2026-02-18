# Lab Data Support (v1.3.0)

This document describes the Laboratory and Sample concepts introduced in schema version 1.3.0 (Phase 2b).

---

## Background

Sensor-based continuous monitoring and discrete laboratory measurements need to coexist in the same database. Before v1.3.0, there was no structured way to record:

- Which laboratory performed an analysis
- Which physical sample was analysed
- Who performed the analysis
- What equipment was used to collect the sample

Phase 2b adds this context without changing how sensor data works.

---

## New Tables

### Laboratory

Represents a physical (or virtual) laboratory where samples are analysed.

| Column | Type | Notes |
|--------|------|-------|
| Laboratory_ID | INT PK | Auto-generated |
| Name | NVARCHAR(200) | Required |
| Site_ID | INT FK→Site | NULL for external labs |
| Description | NVARCHAR(500) | Optional |

### Sample

A discrete physical sample collected at a location.

| Column | Type | Notes |
|--------|------|-------|
| Sample_ID | INT PK | Auto-generated |
| Sampling_point_ID | INT FK→SamplingPoints | Required |
| SampledByPerson_ID | INT FK→Person | Who collected it |
| Campaign_ID | INT FK→Campaign | Which campaign |
| SampleDateTimeStart | DATETIME2(7) | Required (UTC) |
| SampleDateTimeEnd | DATETIME2(7) | NULL for grab samples |
| SampleType | NVARCHAR(50) | Grab, Composite24h, Composite8h, Passive, Other |
| SampleEquipment_ID | INT FK→Equipment | Auto-sampler, if used |
| Description | NVARCHAR(500) | Optional notes |

### Campaign Junction Tables

Three junction tables define which resources a campaign uses:

| Table | Links | Purpose |
|-------|-------|---------|
| CampaignSamplingLocation | Campaign ↔ SamplingPoints | Locations monitored in campaign |
| CampaignEquipment | Campaign ↔ Equipment | Equipment deployed in campaign |
| CampaignParameter | Campaign ↔ Parameter | Parameters measured in campaign |

---

## MetaData Lab Context Columns (new in v1.3.0)

Three new nullable columns on `MetaData` for lab measurements:

| Column | FK target | When populated |
|--------|-----------|----------------|
| Sample_ID | Sample | Lab data only (DataProvenance_ID=2) |
| Laboratory_ID | Laboratory | Lab data only |
| AnalystPerson_ID | Person | Lab data only |

Sensor data rows leave these NULL. All existing rows are unaffected.

---

## How to Record a Lab Measurement

**Step 1:** Insert a `Sample` row for the physical sample:

```sql
INSERT INTO dbo.Sample (Sampling_point_ID, SampledByPerson_ID, Campaign_ID,
                        SampleDateTimeStart, SampleType, Description)
VALUES (1, @marie_id, @campaign_id, '2025-03-15T08:00:00', 'Grab', 'Morning TSS sample');
```

**Step 2:** Insert a `MetaData` row linking all context:

```sql
INSERT INTO dbo.MetaData (Sampling_point_ID, Parameter_ID, Unit_ID, ValueType_ID,
                          DataProvenance_ID, Campaign_ID,
                          Sample_ID, Laboratory_ID, AnalystPerson_ID)
VALUES (@sp_id, @tss_param_id, @mgl_unit_id, 1,
        2,            -- DataProvenance = Laboratory
        @campaign_id,
        @sample_id, @lab_id, @marie_id);
```

**Step 3:** Insert the value:

```sql
INSERT INTO dbo.Value (Metadata_ID, Timestamp, Value)
VALUES (@lab_md_id, '2025-03-15T10:30:00', 24.5);
```

---

## Filtering Recipes

### All TSS data at a location (both lab and sensor)

```sql
SELECT m.Metadata_ID, dp.DataProvenance_Name, v.Value, v.Timestamp
FROM dbo.MetaData m
JOIN dbo.DataProvenance dp ON m.DataProvenance_ID = dp.DataProvenance_ID
JOIN dbo.Value v ON m.Metadata_ID = v.Metadata_ID
WHERE m.Sampling_point_ID = @sp_id
  AND m.Parameter_ID = @tss_id
ORDER BY v.Timestamp;
```

### Only lab results

```sql
WHERE m.DataProvenance_ID = 2  -- Laboratory
```

### Campaign composability: what locations does Campaign A use?

```sql
SELECT sp.Sampling_location
FROM dbo.CampaignSamplingLocation csl
JOIN dbo.SamplingPoints sp ON csl.Sampling_point_ID = sp.Sampling_point_ID
WHERE csl.Campaign_ID = @campaign_a_id;
```

### What campaigns overlap with Campaign A (share any sampling location)?

```sql
SELECT DISTINCT c.Name
FROM dbo.CampaignSamplingLocation csl1
JOIN dbo.CampaignSamplingLocation csl2 ON csl1.Sampling_point_ID = csl2.Sampling_point_ID
JOIN dbo.Campaign c ON csl2.Campaign_ID = c.Campaign_ID
WHERE csl1.Campaign_ID = @campaign_a_id
  AND csl2.Campaign_ID != @campaign_a_id;
```
