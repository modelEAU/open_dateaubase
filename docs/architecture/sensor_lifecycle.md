# Sensor Lifecycle Tracking (v1.4.0)

This document describes the equipment lifecycle concepts introduced in schema version 1.4.0 (Phase 2c).

---

## Background

In continuous water quality monitoring, sensors undergo frequent interventions: calibration, maintenance, firmware updates, temporary removal, and replacement. Before v1.4.0, there was no structured way to record:

- When a calibration or validation was performed and by whom
- Which MetaData series (sensor readings, lab results) were associated with a calibration event
- Which time window of sensor data corresponds to immersion in a calibration solution
- Where a sensor was physically deployed and for how long

Phase 2c adds this context as expand-only additions — no existing data is affected.

---

## New Tables

### EquipmentEventType

Lookup table for classifying lifecycle events.

| ID | Name |
|----|------|
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
|--------|------|-------|
| EquipmentEvent_ID | INT PK | Auto-generated |
| Equipment_ID | INT FK→Equipment | Required |
| EquipmentEventType_ID | INT FK→EquipmentEventType | Required |
| EventDateTimeStart | DATETIME2(7) | Required (UTC) |
| EventDateTimeEnd | DATETIME2(7) | NULL for instantaneous events |
| PerformedByPerson_ID | INT FK→Person | Optional |
| Campaign_ID | INT FK→Campaign | Optional |
| Notes | NVARCHAR(1000) | Free-text notes |

An index on `(Equipment_ID, EventDateTimeStart)` supports efficient retrieval of a sensor's event history.

### EquipmentEventMetaData

Junction table linking a lifecycle event to the MetaData series it involves.

| Column | Type | Notes |
|--------|------|-------|
| EquipmentEvent_ID | INT FK→EquipmentEvent | PK component 1 |
| Metadata_ID | INT FK→MetaData | PK component 2 |
| WindowStart | DATETIME2(7) | Optional: start of relevant sensor window |
| WindowEnd | DATETIME2(7) | Optional: end of relevant sensor window |

`WindowStart`/`WindowEnd` are used to narrow sensor readings to the interval when the probe was immersed in a calibration solution. They are NULL when all values in the series are relevant (e.g., a lab result series).

### EquipmentInstallation

Physical deployment history of equipment at sampling locations.

| Column | Type | Notes |
|--------|------|-------|
| Installation_ID | INT PK | Auto-generated |
| Equipment_ID | INT FK→Equipment | Required |
| Sampling_point_ID | INT FK→SamplingPoints | Required |
| InstalledDate | DATETIME2(7) | Required (UTC) |
| RemovedDate | DATETIME2(7) | NULL = currently installed |
| Campaign_ID | INT FK→Campaign | Optional |
| Notes | NVARCHAR(500) | Optional |

Two indexes support efficient queries: by equipment over time, and by location over time.

---

## SamplingPoints Additions (v1.4.0)

Three nullable columns added to `SamplingPoints`:

| Column | Type | Purpose |
|--------|------|---------|
| ValidFrom | DATETIME2(7) | When this sampling point record became valid |
| ValidTo | DATETIME2(7) | When it became inactive (NULL = currently active) |
| CreatedByCampaign_ID | INT FK→Campaign | Which campaign established this location |

All existing rows have NULL in these columns — fully non-breaking.

---

## How to Record a Calibration

### Step 1: Create the calibration solution as a Sample

A derived standard is a sub-sample of a master standard:

```sql
-- Master standard (prepared in lab, at a lab sampling point)
INSERT INTO dbo.Sample (Sampling_point_ID, SampleCategory, SampledByPerson_ID,
                        SampleDateTimeStart, SampleType, Description)
VALUES (@lab_sp_id, 'Master Standard', @tech_id,
        '2025-03-14T10:00:00', 'Grab', '1000 mg/L TSS master standard');

SET @master_id = SCOPE_IDENTITY();

-- Derived standard: aliquot used for this specific calibration
INSERT INTO dbo.Sample (Sampling_point_ID, SampleCategory, ParentSample_ID,
                        SampledByPerson_ID, Campaign_ID, SampleDateTimeStart, SampleType)
VALUES (@cal_sol_sp_id, 'Derived Standard', @master_id,
        @tech_id, @campaign_id, '2025-03-15T08:00:00', 'Grab');

SET @derived_id = SCOPE_IDENTITY();
```

### Step 2: Create MetaData rows

```sql
-- Sensor readings during immersion (DataProvenance_ID = 1 = Sensor)
INSERT INTO dbo.MetaData (Sampling_point_ID, Parameter_ID, Unit_ID, DataProvenance_ID,
                          Campaign_ID, Sample_ID)
VALUES (@sensor_sp_id, @tss_param_id, @mgl_unit_id, 1, @campaign_id, @derived_id);

SET @sensor_md_id = SCOPE_IDENTITY();

-- Lab analysis of the same solution (DataProvenance_ID = 2 = Laboratory)
INSERT INTO dbo.MetaData (Sampling_point_ID, Parameter_ID, Unit_ID, DataProvenance_ID,
                          Campaign_ID, Sample_ID, Laboratory_ID, AnalystPerson_ID)
VALUES (@cal_sol_sp_id, @tss_param_id, @mgl_unit_id, 2, @campaign_id, @derived_id,
        @lab_id, @analyst_id);

SET @lab_md_id = SCOPE_IDENTITY();
```

### Step 3: Record the calibration event

```sql
INSERT INTO dbo.EquipmentEvent (Equipment_ID, EquipmentEventType_ID,
                                 EventDateTimeStart, EventDateTimeEnd,
                                 PerformedByPerson_ID, Campaign_ID, Notes)
VALUES (@sensor_equipment_id, 1,  -- EquipmentEventType = Calibration
        '2025-03-15T08:00:00', '2025-03-15T09:00:00',
        @tech_id, @campaign_id, 'TSS calibration at 50 mg/L level');

SET @event_id = SCOPE_IDENTITY();
```

### Step 4: Link event to MetaData series

```sql
-- Sensor series: narrow to the 2-minute immersion window
INSERT INTO dbo.EquipmentEventMetaData (EquipmentEvent_ID, Metadata_ID, WindowStart, WindowEnd)
VALUES (@event_id, @sensor_md_id, '2025-03-15T08:55:00', '2025-03-15T08:57:00');

-- Lab series: use all values (no window needed)
INSERT INTO dbo.EquipmentEventMetaData (EquipmentEvent_ID, Metadata_ID)
VALUES (@event_id, @lab_md_id);
```

---

## Cross-Reference Query: Sensor vs Lab for a Calibration Event

This query computes the average sensor reading during the immersion window and the average lab reading, then calculates the bias:

```sql
SELECT
    s.Sample_ID,
    s.SampleDateTimeStart                                           AS SolutionPreparedAt,
    AVG(CASE WHEN m.DataProvenance_ID = 1
              AND v.Timestamp BETWEEN eem.WindowStart AND eem.WindowEnd
             THEN v.Value END)                                       AS SensorAvg,
    COUNT(CASE WHEN m.DataProvenance_ID = 1
               AND v.Timestamp BETWEEN eem.WindowStart AND eem.WindowEnd
              THEN 1 END)                                            AS SensorN,
    AVG(CASE WHEN m.DataProvenance_ID = 2 THEN v.Value END)         AS LabAvg,
    COUNT(CASE WHEN m.DataProvenance_ID = 2 THEN 1 END)             AS LabN,
    AVG(CASE WHEN m.DataProvenance_ID = 2 THEN v.Value END)
      - AVG(CASE WHEN m.DataProvenance_ID = 1
                  AND v.Timestamp BETWEEN eem.WindowStart AND eem.WindowEnd
                 THEN v.Value END)                                   AS LabMinusSensor
FROM dbo.EquipmentEvent ee
JOIN dbo.EquipmentEventMetaData eem ON eem.EquipmentEvent_ID = ee.EquipmentEvent_ID
JOIN dbo.MetaData m                 ON m.Metadata_ID = eem.Metadata_ID
JOIN dbo.Sample s                   ON s.Sample_ID = m.Sample_ID
JOIN dbo.Value v                    ON v.Metadata_ID = m.Metadata_ID
WHERE ee.EquipmentEvent_ID = @CalibrationEventID
GROUP BY s.Sample_ID, s.SampleDateTimeStart
ORDER BY s.SampleDateTimeStart;
```

The key to this design: both the sensor MetaData and the lab MetaData carry `Sample_ID` pointing to the **same** calibration solution sample (`SampleCategory = 'Derived Standard'`). This shared Sample_ID is the join anchor that allows the query to unify sensor and lab data without any additional linking table.

---

## Equipment Deployment History

### What sensor was at location X on date D?

```sql
SELECT e.Equipment_ID, em.Equipment_model, ei.InstalledDate, ei.RemovedDate
FROM dbo.EquipmentInstallation ei
JOIN dbo.Equipment e           ON ei.Equipment_ID = e.Equipment_ID
JOIN dbo.EquipmentModel em     ON e.model_ID = em.Equipment_model_ID
WHERE ei.Sampling_point_ID = @location_id
  AND ei.InstalledDate <= @query_date
  AND (ei.RemovedDate IS NULL OR ei.RemovedDate > @query_date);
```

### Full calibration history for a sensor

```sql
SELECT ee.EventDateTimeStart, ee.EventDateTimeEnd, p.First_name + ' ' + p.Last_name AS TechnicianName,
       ee.Notes
FROM dbo.EquipmentEvent ee
LEFT JOIN dbo.Person p ON ee.PerformedByPerson_ID = p.Person_ID
WHERE ee.Equipment_ID = @sensor_id
  AND ee.EquipmentEventType_ID = 1  -- Calibration
ORDER BY ee.EventDateTimeStart DESC;
```
