# Campaigns and Provenance

## Background: Why Campaigns?

A **Campaign** is a time-bounded measurement context. It answers: *"What were we trying
to do when this data was collected?"*

The `Campaign` table is the sole organisational grouping for measurements and samples.

---

## Campaign Types

Controlled vocabulary (`CampaignType` table):

| ID | Name | When to use |
| --- | --- | --- |
| 1 | Experiment | Planned scientific study with specific hypotheses |
| 2 | Operations | Routine monitoring or plant operation |
| 3 | Commissioning | Initial setup and validation of new equipment |

---

## What is DataProvenance?

`DataProvenance` answers: *"How was this measurement produced?"*

| ID | Name | When to use |
| --- | --- | --- |
| 1 | Sensor | Continuous or semi-continuous instrument measurement |
| 2 | Laboratory | Discrete sample analysed in a laboratory |
| 3 | Manual Entry | Value entered by hand (e.g., operator log) |
| 4 | Model Output | Computed/predicted value from a simulation |
| 5 | External Source | Data ingested from an external database or agency |

`Channel.DataProvenance_ID` distinguishes the source type of each measurement stream.

---

## Campaign and Channel

Campaigns are no longer stored on the Channel row. The Channel table captures only the
invariant identity of a measurement stream
`(Equipment, Parameter, Unit, DataProvenance, ProcessingDegree)`.

Campaign membership is derived at query time via `CampaignEquipment`:

```sql
-- Which channels (streams) were active during Campaign X?
SELECT c.[Channel_ID], c.[Parameter_ID], p.[Parameter], c.[ProcessingDegree]
FROM   [dbo].[Channel]          c
JOIN   [dbo].[CampaignEquipment] ce ON ce.[Equipment_ID] = c.[Equipment_ID]
JOIN   [dbo].[Parameter]         p  ON p.[Parameter_ID]  = c.[Parameter_ID]
WHERE  ce.[Campaign_ID] = @CampaignID;
```

```sql
-- What campaigns was Equipment 7 part of?
SELECT camp.[Name], camp.[StartDate], camp.[EndDate]
FROM   [dbo].[CampaignEquipment] ce
JOIN   [dbo].[Campaign]          camp ON camp.[Campaign_ID] = ce.[Campaign_ID]
WHERE  ce.[Equipment_ID] = 7;
```

---

## How to Add a New Campaign

```sql
INSERT INTO [dbo].[Campaign]
    ([CampaignType_ID], [Site_ID], [Name], [Description], [StartDate], [EndDate])
VALUES
    (1, @SiteID, 'Nutrient Removal Experiment', 'Testing enhanced BNR', '2025-09-01', NULL);
```

To associate equipment with the campaign:

```sql
INSERT INTO [dbo].[CampaignEquipment] ([Campaign_ID], [Equipment_ID], [Role])
VALUES (@campaign_id, @sensor_equipment_id, 'Primary sensor');
```

---

## Filtering Recipes

### All sensor data for a channel at a given site

```sql
SELECT v.[Value], v.[Timestamp]
FROM   [dbo].[Value]    v
JOIN   [dbo].[Channel]  c ON c.[Channel_ID]  = v.[Channel_ID]
WHERE  c.[DataProvenance_ID] = 1       -- Sensor
  AND  c.[Channel_ID] = @ChannelID
ORDER BY v.[Timestamp];
```

### Channels active during a campaign at a specific site

```sql
SELECT c.[Channel_ID], p.[Parameter], c.[ProcessingDegree]
FROM   [dbo].[Channel]           c
JOIN   [dbo].[CampaignEquipment] ce   ON ce.[Equipment_ID]  = c.[Equipment_ID]
JOIN   [dbo].[Campaign]          camp ON camp.[Campaign_ID]  = ce.[Campaign_ID]
JOIN   [dbo].[Parameter]         p    ON p.[Parameter_ID]    = c.[Parameter_ID]
WHERE  camp.[Site_ID] = @SiteID
  AND  camp.[Campaign_ID] = @CampaignID;
```

### All lab analyses for a campaign

```sql
SELECT la.[LabAnalysis_ID], la.[AnalyzedAt], s.[SampleDateTimeStart]
FROM   [dbo].[LabAnalysis] la
JOIN   [dbo].[Sample]      s ON s.[Sample_ID] = la.[Sample_ID]
WHERE  la.[Campaign_ID] = @CampaignID
ORDER BY la.[AnalyzedAt];
```
