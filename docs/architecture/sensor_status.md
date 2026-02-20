# Sensor Status Architecture

## Overview

This document describes the per-channel sensor status tracking feature for open_datEAUbase. Status is stored as a time series in `dbo.Value` using state-change encoding (only transitions are recorded).

## Design Principles

1. **Status is per-channel (per MetaData entry)**, not per-equipment
2. **Device-level status is also supported** (per Equipment)
3. **Status values go in `dbo.Value`** — no new value table
4. **State-change encoding**: only write a row when status changes
5. **A lookup table (`SensorStatusCode`)** defines the meaning of each code
6. **Two self-referential nullable FKs on MetaData**: `StatusOfMetaDataID` and `StatusOfEquipmentID`, with a CHECK that at most one is non-NULL

## The Status Convention

Status is stored as a special type of time series:

1. Create a MetaData entry with:
   - `Variable = 'Sensor Status'` (for channel status) or `'Device Status'` (for device status)
   - `Unit = 'Status Code'`
   - `StatusOfMetaDataID` pointing to the measurement MetaData (for channel status)
   - `StatusOfEquipmentID` pointing to the Equipment (for device status)

2. Insert status transitions into `dbo.Value`:
   - `Value` column contains the `StatusCodeID` (integer 0-10)
   - Only insert when the status actually changes (state-change encoding)

### Example: Setting up a pH channel with status

```sql
-- 1. Create the status MetaData entry
INSERT INTO dbo.MetaData (
    Parameter_ID, Unit_ID, Sampling_point_ID, Equipment_ID,
    StatusOfMetaDataID, ProcessingDegree, ValueType_ID
)
SELECT p.Parameter_ID, u.Unit_ID, md.Sampling_point_ID, md.Equipment_ID,
       md.Metadata_ID, 'Raw', 1
FROM dbo.MetaData md
JOIN dbo.Parameter p ON p.Parameter = 'Sensor Status'
JOIN dbo.Unit u ON u.Unit = 'Status Code'
WHERE md.Metadata_ID = 42;  -- pH measurement MetaData

-- 2. Set the initial status to Operational
INSERT INTO dbo.Value (MetaDataID, tstamp, Value, QualityCode)
VALUES (1001, '2025-01-01', 1, 1);  -- 1 = Operational

-- 3. Later, when sensor goes fouled
INSERT INTO dbo.Value (MetaDataID, tstamp, Value, QualityCode)
VALUES (1001, '2025-02-15', 10, 1);  -- 10 = Fouled
```

## SensorStatusCode Reference

| StatusCodeID | StatusName   | Description                                    | IsOperational | Severity |
|--------------|--------------|------------------------------------------------|---------------|----------|
| 0            | Unknown      | Status not reported or not available           | false         | 1        |
| 1            | Operational  | Sensor channel is functioning normally         | true          | 0        |
| 2            | Warning      | Sensor is operational but a warning exists     | true          | 1        |
| 3            | Fault        | Sensor has faulted, data is unreliable         | false         | 2        |
| 4            | Maintenance  | Sensor is undergoing maintenance               | false         | 1        |
| 5            | Calibrating  | Sensor channel is being calibrated             | false         | 1        |
| 6            | Starting Up  | Sensor is in startup/warmup phase              | false         | 1        |
| 7            | Shutting Down| Sensor is shutting down                        | false         | 1        |
| 8            | Offline      | Sensor is powered off or disconnected          | false         | 0        |
| 9            | Degraded     | Sensor is operational but accuracy reduced     | true          | 1        |
| 10           | Fouled       | Sensor probe is fouled, readings biased        | true          | 2        |

### Severity Levels

- **0 = Normal**: No action needed
- **1 = Warning**: Monitor, may need attention
- **2 = Fault**: Data may be unreliable, investigation needed
- **3 = Critical**: Immediate action required

### IsOperational Flag

When `IsOperational = false`, data collected during this status should be considered untrustworthy. The API supports filtering with `operational_only=true` to exclude such values.

## Query Patterns

### Query 1: Current Status for a Channel

```sql
-- What is the current status of the TSS channel?
SELECT TOP 1
    sc.StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity,
    v.tstamp AS StatusSince
FROM dbo.MetaData statusMD
JOIN dbo.Value v ON v.MetaDataID = statusMD.Metadata_ID
JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(v.Value AS INT)
WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
ORDER BY v.tstamp DESC;
```

### Query 2: Status at a Point in Time

```sql
-- What was the pH status on Feb 16 at noon?
SELECT TOP 1
    sc.StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity,
    v.tstamp AS StatusSince
FROM dbo.MetaData statusMD
JOIN dbo.Value v ON v.MetaDataID = statusMD.Metadata_ID
JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(v.Value AS INT)
WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
  AND v.tstamp <= @Timestamp
ORDER BY v.tstamp DESC;
```

### Query 3: Status Band (for UI Rendering)

```sql
-- Get status intervals for rendering as colored bands
WITH StatusTransitions AS (
    SELECT TOP 1 v.tstamp AS TransitionTime, CAST(v.Value AS INT) AS StatusCodeID
    FROM dbo.MetaData statusMD
    JOIN dbo.Value v ON v.MetaDataID = statusMD.Metadata_ID
    WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID AND v.tstamp <= @T1
    ORDER BY v.tstamp DESC

    UNION ALL

    SELECT v.tstamp AS TransitionTime, CAST(v.Value AS INT) AS StatusCodeID
    FROM dbo.MetaData statusMD
    JOIN dbo.Value v ON v.MetaDataID = statusMD.Metadata_ID
    WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
      AND v.tstamp > @T1 AND v.tstamp <= @T2
),
StatusIntervals AS (
    SELECT
        TransitionTime AS IntervalStart,
        LEAD(TransitionTime) OVER (ORDER BY TransitionTime) AS IntervalEnd,
        StatusCodeID
    FROM StatusTransitions
)
SELECT
    CASE WHEN si.IntervalStart < @T1 THEN @T1 ELSE si.IntervalStart END AS from_time,
    CASE WHEN si.IntervalEnd IS NULL THEN @T2 WHEN si.IntervalEnd > @T2 THEN @T2 ELSE si.IntervalEnd END AS to_time,
    sc.StatusCodeID, sc.StatusName, sc.IsOperational, sc.Severity
FROM StatusIntervals si
JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = si.StatusCodeID
WHERE si.IntervalEnd IS NULL OR si.IntervalEnd > @T1
ORDER BY si.IntervalStart;
```

## API Endpoints

### GET /api/v1/status-codes

List all sensor status codes for UI dropdowns and legends.

**Response:**
```json
{
  "status_codes": [
    {
      "id": 0,
      "name": "Unknown",
      "description": "Status not reported or not available",
      "is_operational": false,
      "severity": 1
    }
  ]
}
```

### GET /api/v1/equipment/{equipment_id}/status

Get the full health picture of a sensor: device-level status plus all per-channel statuses.

**Query parameters:**
- `at`: Point in time to query (ISO 8601). Default: now.

**Response:**
```json
{
  "equipment_id": 5,
  "equipment_name": "SC1000_Controller",
  "queried_at": "2025-02-16T12:00:00Z",
  "device_status": {
    "status_code": 1,
    "status_name": "Operational",
    "is_operational": true,
    "severity": 0,
    "since": "2025-01-01T00:00:00Z"
  },
  "channel_statuses": [
    {
      "measurement_metadata_id": 42,
      "variable": "TSS",
      "location": "Primary Effluent",
      "status_code": 1,
      "status_name": "Operational",
      "is_operational": true,
      "severity": 0,
      "since": "2025-01-01T00:00:00Z"
    }
  ],
  "overall_operational": true,
  "worst_severity": 0
}
```

### GET /api/v1/equipment/{equipment_id}/status/history

Get status transitions over a time range for the whole sensor.

**Query parameters:**
- `from`: Start of range (ISO 8601)
- `to`: End of range (ISO 8601)
- `channel`: Filter to a specific variable name (e.g., "TSS")

### GET /api/v1/timeseries/{metadata_id}/status

Get the status band for a specific measurement channel over a time range.

**Query parameters:**
- `from`: Start of range (ISO 8601)
- `to`: End of range (ISO 8601)

**Response:**
```json
{
  "metadata_id": 43,
  "variable": "pH",
  "equipment_name": "SC1000_Controller",
  "query_range": {
    "from": "2025-02-01T00:00:00Z",
    "to": "2025-02-28T23:59:59Z"
  },
  "status_intervals": [
    {
      "from": "2025-02-01T00:00:00Z",
      "to": "2025-02-15T00:00:00Z",
      "status_code": 1,
      "status_name": "Operational",
      "is_operational": true,
      "severity": 0
    }
  ],
  "has_status_data": true
}
```

### GET /api/v1/timeseries/{metadata_id} (extended)

The existing timeseries endpoint supports two new optional parameters:

- `include_status`: Include status band in response
- `operational_only`: Filter to values where sensor was operational

**Example:**
```
GET /api/v1/timeseries/42?from=2025-02-01&to=2025-02-28&include_status=true&operational_only=true
```

## Integration with Annotations

Status and annotations are complementary:

- **Status** = machine-reported state (what the sensor says about itself)
- **Annotations** = human-authored commentary (what operators observed)

A Fault annotation might be created by a human to explain a machine-reported Fault status. This provides context that the sensor cannot provide (e.g., "sensor was fouled due to biofilm growth").

## State-Change Encoding

The system uses **state-change encoding**, not heartbeats. This means:

1. Only write a row to `dbo.Value` when the status actually changes
2. The status at any point in time is the value from the most recent row <= that timestamp
3. No "still operational" heartbeats are needed

### Implications for Ingestion Scripts

When writing an ingestion pipeline for sensor status:

1. Track the last known status value
2. On each data point, check if the status has changed
3. Only insert into `dbo.Value` if the status is different from the last known value
4. This keeps the `dbo.Value` table small and queryable

## Views

Two convenience views are provided:

### dbo.vw_ChannelStatus

Joins status records with their measurement channels:

```sql
SELECT * FROM dbo.vw_ChannelStatus
WHERE EquipmentID = 5
```

### dbo.vw_DeviceStatus

Joins device-level status records:

```sql
SELECT * FROM dbo.vw_DeviceStatus
WHERE EquipmentID = 5
```

## Adding New Status Codes

To add a new status code, insert a row into `dbo.SensorStatusCode`:

```sql
INSERT INTO dbo.SensorStatusCode (StatusCodeID, StatusName, Description, IsOperational, Severity)
VALUES (11, 'Deicing', 'Sensor covered in ice', false, 2);
```

No migration is needed for adding status codes as they are seed data in a lookup table.

## Future Enhancements

Possible future enhancements (not implemented in this phase):

- **ParentStatusID**: Threading annotations to show relationships between statuses
- **Multi-series annotations**: Junction table for annotations that span multiple MetaData entries
- **Status prediction**: ML-based prediction of when next status change will occur
- **Alert rules**: Configurable alerts when status enters certain states