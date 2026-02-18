# Campaigns and Provenance (v1.2.0)

This document describes the Campaign and DataProvenance concepts introduced in schema version 1.2.0 (Phase 2a).

---

## Background: Why Campaigns?

The original schema had a `Project` table that provided a loose grouping for measurements. This was too coarse: a single project might span years and include both routine operations and focused experiments, making it impossible to ask "show me only the data from the nutrient removal experiment in March."

A **Campaign** is a finer-grained, time-bounded context. It answers: *"What were we trying to do when this data was collected?"*

---

## Campaign vs. Project

| Concept | Project | Campaign |
|---------|---------|----------|
| Granularity | Coarse (multi-year) | Fine (weeks to months) |
| Time bounds | None | Optional start/end date |
| Site association | None | Required (one site) |
| Type classification | None | Experiment, Operations, Commissioning |
| Status | Legacy, kept for backward compat | New, preferred for new data |

The `Project` table is **preserved** for backward compatibility. New `Campaign` rows can optionally link back to a `Project` via the nullable `Campaign.Project_ID` FK.

`MetaData.Project_ID` is also preserved. New MetaData rows should populate `Campaign_ID` instead, or in addition.

---

## Campaign Types

Controlled vocabulary (`CampaignType` table):

| ID | Name | When to use |
|----|------|-------------|
| 1 | Experiment | Planned scientific study with specific hypotheses |
| 2 | Operations | Routine monitoring or plant operation |
| 3 | Commissioning | Initial setup and validation of new equipment |

---

## What is DataProvenance?

`DataProvenance` answers: *"How was this measurement produced?"*

| ID | Name | When to use |
|----|------|-------------|
| 1 | Sensor | Continuous or semi-continuous instrument measurement |
| 2 | Laboratory | Discrete sample analysed in a laboratory |
| 3 | Manual Entry | Value entered by hand (e.g., operator log) |
| 4 | Model Output | Computed/predicted value from a simulation |
| 5 | External Source | Data ingested from an external database or agency |

`MetaData.DataProvenance_ID` is **nullable** for legacy rows. A backfill script (`migrations/data/backfill_provenance.sql`) classifies existing rows with an `Equipment_ID` as `Sensor`.

---

## Schema Changes in v1.2.0

### Renamed: Contact → Person

The `Contact` table was renamed to `Person` because it stores people, not just contacts. Changes:

- Table name: `Contact` → `Person`
- PK column: `Contact_ID` → `Person_ID`
- Obsolete columns dropped: `Skype_name`, `Street_number`, `Street_name`, `City`, `Zip_code`, `Country`, `Office_number`
- Column renamed: `Status` → `Role`
- `Role` has a controlled vocabulary: MSc, Postdoc, Intern, PhD, Professor, Research Professional, Technician, Administrator, Guest

**Backward-compatible note:** Foreign key columns in `MetaData` and `ProjectHasContact` kept the name `Contact_ID` but now reference `Person.Person_ID`. No application code that reads `MetaData.Contact_ID` needs to change.

### New tables

- `CampaignType` — lookup with 3 seed rows
- `Campaign` — time-bounded measurement context
- `DataProvenance` — lookup with 5 seed rows

### New MetaData columns

- `MetaData.DataProvenance_ID INT NULL` — FK to `DataProvenance`
- `MetaData.Campaign_ID INT NULL` — FK to `Campaign`

Both are **nullable** to preserve backward compatibility with existing rows.

---

## Migration Path from Project to Campaign

1. Create a `Campaign` row for each logical grouping (e.g., one per `Project` season)
2. Set `Campaign.Project_ID` to the legacy `Project_ID` for traceability
3. Update `MetaData.Campaign_ID` for new rows
4. Optionally backfill `MetaData.Campaign_ID` for historical rows if context is known
5. `MetaData.Project_ID` remains valid and does **not** need to be cleared

---

## Filtering Recipes

### All MetaData for Campaign X

```sql
SELECT m.*
FROM dbo.MetaData m
WHERE m.Campaign_ID = @CampaignID;
```

### All MetaData for Site Y across all campaigns

```sql
SELECT m.*
FROM dbo.MetaData m
JOIN dbo.Campaign c ON m.Campaign_ID = c.Campaign_ID
WHERE c.Site_ID = @SiteID;
```

### Only sensor data (DataProvenance = Sensor)

```sql
SELECT m.*
FROM dbo.MetaData m
WHERE m.DataProvenance_ID = 1;  -- Sensor
```

### Lab vs. sensor for the same parameter and location

```sql
SELECT m.*, dp.DataProvenance_Name
FROM dbo.MetaData m
JOIN dbo.DataProvenance dp ON m.DataProvenance_ID = dp.DataProvenance_ID
WHERE m.Parameter_ID = @ParameterID
  AND m.Sampling_point_ID = @SamplingPointID
ORDER BY dp.DataProvenance_Name;
```

---

## How to Add a New Campaign

1. Insert a `CampaignType` row if the type is genuinely new (rare — only 3 types defined).
2. Insert a `Campaign` row:

```sql
INSERT INTO dbo.Campaign
    (CampaignType_ID, Site_ID, Name, Description, StartDate, EndDate, Project_ID)
VALUES
    (1, @SiteID, 'My Experiment', 'What we are testing', '2025-09-01', NULL, NULL);
```

3. When creating new `MetaData` rows for this campaign, set `Campaign_ID` to the new `Campaign_ID`.
4. If applicable, run `migrations/data/backfill_provenance.sql` to classify existing rows.
