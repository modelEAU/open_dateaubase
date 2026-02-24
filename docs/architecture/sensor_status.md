# Sensor Status Architecture (v2.1.0)

**Phase C** replaced the v1.8.0 self-referential `StatusOfMetaDataID` and
`StatusOfEquipmentID` columns with a cleaner structure:

- **Per-channel status**: `Channel.StatusChannel_ID` (nullable FK → Channel) — a
  measurement Channel optionally points to the Channel that carries its status codes.
- **Device-level status**: `EquipmentStatusChannel` table — maps one Equipment row to
  its device-level status Channel.

---

## Overview

Status is stored as a time series in `dbo.Value` using **state-change encoding** — only
transitions are recorded, not heartbeats.

1. **Status is per-channel (per Channel row)**, not per-equipment.
2. **Device-level status is also supported** via `EquipmentStatusChannel`.
3. **Status values go in `dbo.Value`** — no separate value table.
4. **A lookup table (`SensorStatusCode`)** defines the meaning of each code.
5. **State-change encoding**: only write a row when status changes.

---

## Schema

### Channel.StatusChannel_ID

A nullable `Channel_ID` FK on the `Channel` table itself. When non-NULL, this Channel
*is* a status time series describing the measurement Channel identified by
`StatusChannel_ID`.

```text
Channel (measurement): Channel_ID=42, Equipment_ID=7, Parameter_ID=3, StatusChannel_ID=NULL
Channel (status):      Channel_ID=43, Equipment_ID=7, Parameter_ID=<status param>, StatusChannel_ID=42
```

Channel 43 carries status codes for Channel 42. Values written to `dbo.Value` with
`Channel_ID=43` are status transitions for the pH/TSS/etc. measurement on Channel 42.

### EquipmentStatusChannel

Maps an Equipment row to its device-level status Channel (one-to-one).

| Column | Type | Notes |
| --- | --- | --- |
| `Equipment_ID` | INT PK FK→Equipment | Equipment whose device-level status is tracked |
| `StatusChannel_ID` | INT FK→Channel | Channel carrying device-level status codes |

### SensorStatusCode

| StatusCodeID | StatusName | IsOperational | Severity |
| --- | --- | --- | --- |
| 0 | Unknown | false | 1 |
| 1 | Operational | true | 0 |
| 2 | Warning | true | 1 |
| 3 | Fault | false | 2 |
| 4 | Maintenance | false | 1 |
| 5 | Calibrating | false | 1 |
| 6 | Starting Up | false | 1 |
| 7 | Shutting Down | false | 1 |
| 8 | Offline | false | 0 |
| 9 | Degraded | true | 1 |
| 10 | Fouled | true | 2 |

**Severity levels:** 0=normal, 1=warning, 2=fault, 3=critical.

**IsOperational:** When `false`, data collected during this status is considered
untrustworthy. The API supports filtering with `operational_only=true`.

---

## Setting Up a Channel with Per-Channel Status

### Step 1: Create the status Channel

```sql
-- Assumes the measurement Channel already exists (Channel_ID = 42)
INSERT INTO [dbo].[Channel]
    ([Equipment_ID], [Parameter_ID], [Unit_ID], [DataProvenance_ID],
     [ProcessingDegree], [ValueType_ID], [StatusChannel_ID])
SELECT
    [Equipment_ID],
    @status_param_id,   -- Parameter for 'Sensor Status'
    @status_unit_id,    -- Unit for 'Status Code'
    [DataProvenance_ID],
    'Raw',
    1,
    42                  -- points back to the measurement Channel
FROM [dbo].[Channel]
WHERE [Channel_ID] = 42;

SET @status_channel_id = SCOPE_IDENTITY();
```

### Step 2: Insert status transitions into dbo.Value

```sql
-- Initial status: Operational
INSERT INTO [dbo].[Value] ([Channel_ID], [Timestamp], [Value])
VALUES (@status_channel_id, '2025-01-01T00:00:00', 1);  -- 1 = Operational

-- Later, sensor goes fouled:
INSERT INTO [dbo].[Value] ([Channel_ID], [Timestamp], [Value])
VALUES (@status_channel_id, '2025-02-15T09:00:00', 10); -- 10 = Fouled
```

---

## Views

### dbo.vw_ChannelStatus

Joins per-channel status records with their measurement channels.

```sql
SELECT * FROM [dbo].[vw_ChannelStatus]
WHERE EquipmentID = 5;
```

Columns: `StatusChannelID`, `MeasurementChannelID`, `EquipmentID`, `EquipmentName`,
`MeasurementParameter`, `Timestamp`, `StatusCodeID`, `StatusName`, `IsOperational`, `Severity`.

The view selects all Channel rows where `StatusChannel_ID IS NOT NULL`, joining back to
the measurement Channel via `StatusChannel_ID`.

### dbo.vw_DeviceStatus

Joins device-level status records via `EquipmentStatusChannel`.

```sql
SELECT * FROM [dbo].[vw_DeviceStatus]
WHERE EquipmentID = 5;
```

Columns: `StatusChannelID`, `EquipmentID`, `EquipmentName`, `Timestamp`, `StatusCodeID`,
`StatusName`, `IsOperational`, `Severity`.

---

## Query Patterns

### Current status for a channel

```sql
SELECT TOP 1
    sc.[StatusCodeID],
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity],
    v.[Timestamp] AS StatusSince
FROM [dbo].[Channel]               statusC
JOIN [dbo].[Value]                 v  ON v.[Channel_ID]    = statusC.[Channel_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc ON sc.[StatusCodeID] = CAST(v.[Value] AS INT)
WHERE statusC.[StatusChannel_ID] = @MeasurementChannelID
ORDER BY v.[Timestamp] DESC;
```

### Status at a point in time

```sql
SELECT TOP 1
    sc.[StatusCodeID], sc.[StatusName], sc.[IsOperational], sc.[Severity],
    v.[Timestamp] AS StatusSince
FROM [dbo].[Channel]               statusC
JOIN [dbo].[Value]                 v  ON v.[Channel_ID]    = statusC.[Channel_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc ON sc.[StatusCodeID] = CAST(v.[Value] AS INT)
WHERE statusC.[StatusChannel_ID] = @MeasurementChannelID
  AND v.[Timestamp] <= @QueryTimestamp
ORDER BY v.[Timestamp] DESC;
```

### Status band (for UI rendering)

```sql
WITH StatusTransitions AS (
    SELECT TOP 1 v.[Timestamp] AS TransitionTime, CAST(v.[Value] AS INT) AS StatusCodeID
    FROM [dbo].[Channel]   statusC
    JOIN [dbo].[Value]     v ON v.[Channel_ID] = statusC.[Channel_ID]
    WHERE statusC.[StatusChannel_ID] = @MeasurementChannelID
      AND v.[Timestamp] <= @T1
    ORDER BY v.[Timestamp] DESC

    UNION ALL

    SELECT v.[Timestamp], CAST(v.[Value] AS INT)
    FROM [dbo].[Channel]   statusC
    JOIN [dbo].[Value]     v ON v.[Channel_ID] = statusC.[Channel_ID]
    WHERE statusC.[StatusChannel_ID] = @MeasurementChannelID
      AND v.[Timestamp] > @T1 AND v.[Timestamp] <= @T2
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
    CASE WHEN si.IntervalEnd IS NULL THEN @T2
         WHEN si.IntervalEnd > @T2   THEN @T2
         ELSE si.IntervalEnd END                                          AS to_time,
    sc.[StatusCodeID], sc.[StatusName], sc.[IsOperational], sc.[Severity]
FROM StatusIntervals si
LEFT JOIN [dbo].[SensorStatusCode] sc ON sc.[StatusCodeID] = si.StatusCodeID
WHERE si.IntervalEnd IS NULL OR si.IntervalEnd > @T1
ORDER BY si.IntervalStart;
```

---

## API Endpoints

### GET /api/v1/status-codes

List all sensor status codes for UI dropdowns and legends.

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
      "measurement_channel_id": 42,
      "variable": "TSS",
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

Get status transitions over a time range.

**Query parameters:** `from`, `to` (ISO 8601), `channel` (filter to a variable name).

### GET /api/v1/timeseries/{channel_id}/status

Get the status band for a specific measurement channel over a time range.

**Query parameters:** `from`, `to` (ISO 8601).

**Response:**

```json
{
  "channel_id": 42,
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

---

## State-Change Encoding

Only write a row when the status actually changes. No heartbeats needed. The status at
any point in time is the value from the most recent `dbo.Value` row with
`Timestamp <= query_time` for that status Channel.

**Ingestion pipeline pattern:**

1. Track the last known status value.
2. On each data point, check if the status has changed.
3. Only insert a new `dbo.Value` row if different from the last known value.

---

## Integration with Annotations

Status and annotations are complementary:

- **Status** = machine-reported state (what the sensor reports about itself)
- **Annotations** = human-authored commentary (what operators observed)

A `Fault` annotation might be created by a human to explain a machine-reported `Fault`
status, adding context the sensor cannot provide (e.g., "fouling due to biofilm growth").

---

## Adding New Status Codes

```sql
INSERT INTO [dbo].[SensorStatusCode]
    ([StatusCodeID], [StatusName], [Description], [IsOperational], [Severity])
VALUES (11, 'Deicing', 'Sensor covered in ice', 0, 2);
```

No schema migration needed — status codes are seed data in a lookup table.
