# Sensor Lifecycle Tracking

## Background

In continuous water quality monitoring, sensors undergo frequent interventions:
calibration, maintenance, firmware updates, temporary removal, and replacement.
Structured tables record these events alongside existing data.

---

## Tables

### EquipmentEventType

Lookup table for classifying lifecycle events.

| ID | Name |
| --- | --- |
| 1 | Calibration |
| 2 | Validation |
| 3 | Maintenance |
| 4 | Installation |
| 5 | Removal |
| 6 | Firmware Update |
| 7 | Failure |
| 8 | Repair |

### EquipmentEvent

A single discrete lifecycle event on a piece of equipment.

| Column | Type | Notes |
| --- | --- | --- |
| `EquipmentEvent_ID` | INT PK | Auto-generated |
| `Equipment_ID` | INT FK→Equipment | Required |
| `EquipmentEventType_ID` | INT FK→EquipmentEventType | Required |
| `EventDateTimeStart` | DATETIME2(7) | Required (UTC) |
| `EventDateTimeEnd` | DATETIME2(7) | NULL for instantaneous events |
| `PerformedByPerson_ID` | INT FK→Person | Optional |
| `Campaign_ID` | INT FK→Campaign | Optional |
| `Notes` | NVARCHAR(1000) | Free-text notes |

An index on `(Equipment_ID, EventDateTimeStart)` supports efficient retrieval of a
sensor's event history.

### EquipmentEventChannel

Junction table linking a lifecycle event to the Channel series it involves.

| Column | Type | Notes |
| --- | --- | --- |
| `EquipmentEvent_ID` | INT FK→EquipmentEvent | PK component 1 |
| `Channel_ID` | INT FK→Channel | PK component 2 |
| `WindowStart` | DATETIME2(7) | Optional: start of relevant sensor window |
| `WindowEnd` | DATETIME2(7) | Optional: end of relevant sensor window |

`WindowStart`/`WindowEnd` narrow sensor readings to the interval when the probe was
immersed in a calibration solution. They are NULL when all values in the series are
relevant.

### EquipmentInstallation

Physical deployment history of equipment at sampling locations.

| Column | Type | Notes |
| --- | --- | --- |
| `Installation_ID` | INT PK | Auto-generated |
| `Equipment_ID` | INT FK→Equipment | Required |
| `Sampling_point_ID` | INT FK→SamplingPoints | Required |
| `InstalledDate` | DATETIME2(7) | Required (UTC) |
| `RemovedDate` | DATETIME2(7) | NULL = currently installed |
| `Campaign_ID` | INT FK→Campaign | Optional |
| `Notes` | NVARCHAR(500) | Optional |

Two indexes support efficient queries: by equipment over time, and by location over time.

---

## SamplingPoints Additions

Three nullable columns added to `SamplingPoints`:

| Column | Type | Purpose |
| --- | --- | --- |
| `ValidFrom` | DATETIME2(7) | When this sampling point record became valid |
| `ValidTo` | DATETIME2(7) | When it became inactive (NULL = currently active) |
| `CreatedByCampaign_ID` | INT FK→Campaign | Which campaign established this location |

All existing rows may have NULL in these columns.

---

## How to Record a Calibration

### Step 1: Create the calibration solution as a Sample

```sql
-- Master standard (prepared in lab)
INSERT INTO [dbo].[Sample]
    ([Sampling_point_ID], [SampleCategory], [SampledByPerson_ID],
     [SampleDateTimeStart], [SampleType], [Description])
VALUES
    (@lab_sp_id, 'Master Standard', @tech_id,
     '2025-03-14T10:00:00', 'Grab', '1000 mg/L TSS master standard');

SET @master_id = SCOPE_IDENTITY();

-- Derived standard: aliquot used for this specific calibration
INSERT INTO [dbo].[Sample]
    ([Sampling_point_ID], [SampleCategory], [ParentSample_ID],
     [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart], [SampleType])
VALUES
    (@cal_sol_sp_id, 'Derived Standard', @master_id,
     @tech_id, @campaign_id, '2025-03-15T08:00:00', 'Grab');

SET @derived_id = SCOPE_IDENTITY();
```

### Step 2: Record a LabAnalysis for the calibration solution

Lab measurements of the calibration solution go through `LabAnalysis` + `LabValue`
rather than the `Channel` table. The `Sample_ID` links the lab result back to the
physical standard.

```sql
INSERT INTO [dbo].[LabAnalysis]
    ([Sample_ID], [Laboratory_ID], [AnalystPerson_ID], [Campaign_ID], [Notes])
VALUES
    (@derived_id, @lab_id, @analyst_id, @campaign_id, 'TSS calibration analysis');

SET @lab_analysis_id = SCOPE_IDENTITY();

INSERT INTO [dbo].[LabValue]
    ([LabAnalysis_ID], [Parameter_ID], [Unit_ID], [Value], [Replicate])
VALUES
    (@lab_analysis_id, @tss_param_id, @mgl_unit_id, 487.3, 1);
```

### Step 3: Record the calibration event

```sql
INSERT INTO [dbo].[EquipmentEvent]
    ([Equipment_ID], [EquipmentEventType_ID], [EventDateTimeStart], [EventDateTimeEnd],
     [PerformedByPerson_ID], [Campaign_ID], [Notes])
VALUES
    (@sensor_equipment_id, 1,   -- EquipmentEventType = Calibration
     '2025-03-15T08:00:00', '2025-03-15T09:00:00',
     @tech_id, @campaign_id, 'TSS calibration at 50 mg/L level');

SET @event_id = SCOPE_IDENTITY();
```

### Step 4: Link event to the sensor Channel

```sql
-- Sensor channel: narrow to the 2-minute immersion window
INSERT INTO [dbo].[EquipmentEventChannel]
    ([EquipmentEvent_ID], [Channel_ID], [WindowStart], [WindowEnd])
VALUES
    (@event_id, @sensor_channel_id, '2025-03-15T08:55:00', '2025-03-15T08:57:00');
```

---

## Cross-Reference Query: Sensor vs Lab for a Calibration Event

```sql
SELECT
    s.[Sample_ID],
    s.[SampleDateTimeStart]                                         AS SolutionPreparedAt,
    AVG(CASE WHEN v.[Timestamp] BETWEEN eec.[WindowStart] AND eec.[WindowEnd]
             THEN v.[Value] END)                                    AS SensorAvg,
    COUNT(CASE WHEN v.[Timestamp] BETWEEN eec.[WindowStart] AND eec.[WindowEnd]
               THEN 1 END)                                          AS SensorN,
    AVG(lv.[Value])                                                 AS LabAvg,
    COUNT(lv.[Value])                                               AS LabN,
    AVG(lv.[Value])
      - AVG(CASE WHEN v.[Timestamp] BETWEEN eec.[WindowStart] AND eec.[WindowEnd]
                 THEN v.[Value] END)                                AS LabMinusSensor
FROM [dbo].[EquipmentEvent]        ee
JOIN [dbo].[EquipmentEventChannel] eec ON eec.[EquipmentEvent_ID] = ee.[EquipmentEvent_ID]
JOIN [dbo].[Channel]               c   ON c.[Channel_ID]          = eec.[Channel_ID]
JOIN [dbo].[Value]                 v   ON v.[Channel_ID]           = c.[Channel_ID]
-- Lab side: via LabAnalysis linked to the calibration Sample
JOIN [dbo].[LabAnalysis]           la  ON la.[Campaign_ID]         = ee.[Campaign_ID]
JOIN [dbo].[Sample]                s   ON s.[Sample_ID]            = la.[Sample_ID]
JOIN [dbo].[LabValue]              lv  ON lv.[LabAnalysis_ID]      = la.[LabAnalysis_ID]
WHERE ee.[EquipmentEvent_ID] = @CalibrationEventID
GROUP BY s.[Sample_ID], s.[SampleDateTimeStart]
ORDER BY s.[SampleDateTimeStart];
```

---

## Equipment Deployment History

### What sensor was at location X on date D?

```sql
SELECT e.[Equipment_ID], em.[Equipment_model], ei.[InstalledDate], ei.[RemovedDate]
FROM   [dbo].[EquipmentInstallation] ei
JOIN   [dbo].[Equipment]             e  ON ei.[Equipment_ID]       = e.[Equipment_ID]
JOIN   [dbo].[EquipmentModel]        em ON e.[model_ID]            = em.[Equipment_model_ID]
WHERE  ei.[Sampling_point_ID] = @location_id
  AND  ei.[InstalledDate]    <= @query_date
  AND  (ei.[RemovedDate] IS NULL OR ei.[RemovedDate] > @query_date);
```

### Full calibration history for a sensor

```sql
SELECT ee.[EventDateTimeStart], ee.[EventDateTimeEnd],
       p.[First_name] + ' ' + p.[Last_name] AS TechnicianName,
       ee.[Notes]
FROM   [dbo].[EquipmentEvent] ee
LEFT JOIN [dbo].[Person]      p ON ee.[PerformedByPerson_ID] = p.[Person_ID]
WHERE  ee.[Equipment_ID]           = @sensor_id
  AND  ee.[EquipmentEventType_ID]  = 1   -- Calibration
ORDER BY ee.[EventDateTimeStart] DESC;
```
