# Sensor Status Architecture

## Overview

Status is stored as a time series in `dbo.Value` using **state-change encoding** — only
transitions are recorded, not heartbeats.

1. **Status is tracked via SignalPort sub-signals.** A status channel is a `Channel` whose
   `SignalPort` has `SignalPortType = Status` and a non-null `ParentPort_ID` pointing to the
   measured value port.
2. **Status values go in `dbo.Observation` + `dbo.Value`** — no separate value table.
3. **A lookup table (`SensorStatusCode`)** defines the meaning of each code.
4. **State-change encoding**: only write a row when status changes.

---

## Schema

### SignalPort sub-signal relationship

A status channel is identified by navigating the SignalPort hierarchy:

```text
SignalPort (value port):  SignalPort_ID=10, SignalPortType=Value,  ParentPort_ID=NULL
SignalPort (status port): SignalPort_ID=11, SignalPortType=Status, ParentPort_ID=10

Channel (measurement): Channel_ID=42, SignalPort_ID=10, Parameter_ID=3
Channel (status):      Channel_ID=43, SignalPort_ID=11, Parameter_ID=<status param>
```

`Channel 43` carries status codes for `Channel 42`. Observations written against
`Channel_ID=43` are status transitions for the measurement on Channel 42.

To find the status channel for a given measurement channel:

```sql
SELECT sc.[Channel_ID]
FROM   [dbo].[Channel]        sc
JOIN   [dbo].[SignalPort]     sp  ON sp.[SignalPort_ID]      = sc.[SignalPort_ID]
JOIN   [dbo].[SignalPortType] spt ON spt.[SignalPortType_ID] = sp.[SignalPortType_ID]
WHERE  sp.[ParentPort_ID] = (
           SELECT c2.[SignalPort_ID] FROM [dbo].[Channel] c2 WHERE c2.[Channel_ID] = @MeasurementChannelID
       )
  AND  spt.[Name] = N'Status';
```

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

### Step 1: Create the status SignalPort and Channel

```sql
-- Create a Status sub-signal port under the measurement port (SignalPort_ID=10)
INSERT INTO [dbo].[SignalPort]
    ([DataAcquisitionSystem_ID], [Tag], [SignalPortType_ID], [ParentPort_ID], [IsActive])
VALUES (@das_id, @status_tag, 2, 10, 1);  -- SignalPortType_ID=2 = Status

SET @status_port_id = SCOPE_IDENTITY();

-- Create the status Channel
INSERT INTO [dbo].[Channel]
    ([SignalPort_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (@status_port_id, @status_param_id, @provenance_id, 1, 1);

SET @status_channel_id = SCOPE_IDENTITY();
```

### Step 2: Insert status transitions via Observation + Value

```sql
-- Initial status: Operational
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
VALUES (@status_channel_id, '2025-01-01T00:00:00', 'Scalar');
INSERT INTO [dbo].[Value] ([Observation_ID], [Value]) VALUES (SCOPE_IDENTITY(), 1);

-- Later, sensor goes fouled:
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
VALUES (@status_channel_id, '2025-02-15T09:00:00', 'Scalar');
INSERT INTO [dbo].[Value] ([Observation_ID], [Value]) VALUES (SCOPE_IDENTITY(), 10);
```

---

## Views

### dbo.vw_ChannelStatus

Joins per-channel status records with their measurement channels via the SignalPort
sub-signal relationship.

```sql
SELECT * FROM [dbo].[vw_ChannelStatus]
WHERE EquipmentID = 5;
```

Columns: `StatusChannelID`, `MeasurementChannelID`, `EquipmentID`, `EquipmentName`,
`MeasurementParameter`, `Timestamp`, `StatusCodeID`.

### dbo.vw_DeviceStatus

Finds status channels by resolving the currently-active `SignalPortEquipmentHistory`
row for the equipment, then filtering for `SignalPortType=Status` ports.

```sql
SELECT * FROM [dbo].[vw_DeviceStatus]
WHERE EquipmentID = 5;
```

Columns: `StatusChannelID`, `EquipmentID`, `EquipmentName`, `Timestamp`, `StatusCodeID`.

---

## Query Patterns

### Current status for a channel

```sql
SELECT TOP 1
    sc.[StatusCodeID], sc.[StatusName], sc.[IsOperational], sc.[Severity],
    o.[Timestamp] AS StatusSince
FROM [dbo].[Observation]   o
JOIN [dbo].[Value]         v  ON v.[Observation_ID] = o.[Observation_ID]
JOIN [dbo].[SensorStatusCode] sc ON sc.[StatusCodeID] = CAST(v.[Value] AS INT)
WHERE o.[Channel_ID] = (
    SELECT sc2.[Channel_ID]
    FROM   [dbo].[Channel] sc2
    JOIN   [dbo].[SignalPort] sp ON sp.[SignalPort_ID] = sc2.[SignalPort_ID]
    JOIN   [dbo].[SignalPortType] spt ON spt.[SignalPortType_ID] = sp.[SignalPortType_ID]
    WHERE  sp.[ParentPort_ID] = (SELECT c2.[SignalPort_ID] FROM [dbo].[Channel] c2 WHERE c2.[Channel_ID] = @MeasurementChannelID)
      AND  spt.[Name] = N'Status'
)
ORDER BY o.[Timestamp] DESC;
```

### Status at a point in time

```sql
SELECT TOP 1
    sc.[StatusCodeID], sc.[StatusName], sc.[IsOperational], sc.[Severity],
    o.[Timestamp] AS StatusSince
FROM [dbo].[Observation]   o
JOIN [dbo].[Value]         v  ON v.[Observation_ID] = o.[Observation_ID]
JOIN [dbo].[SensorStatusCode] sc ON sc.[StatusCodeID] = CAST(v.[Value] AS INT)
WHERE o.[Channel_ID] = (  /* same sub-query as above */ ... )
  AND o.[Timestamp] <= @QueryTimestamp
ORDER BY o.[Timestamp] DESC;
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

---

## State-Change Encoding

Only write a row when the status actually changes. No heartbeats needed. The status at
any point in time is the value from the most recent `dbo.Observation`/`dbo.Value` row
with `Timestamp <= query_time` for that status Channel.

---

## Integration with Annotations

Status and annotations are complementary:

- **Status** = machine-reported state (what the sensor reports about itself)
- **Annotations** = human-authored commentary (what operators observed)

---

## Adding New Status Codes

```sql
INSERT INTO [dbo].[SensorStatusCode]
    ([StatusCodeID], [StatusName], [Description], [IsOperational], [Severity])
VALUES (11, 'Deicing', 'Sensor covered in ice', 0, 2);
```

No schema migration needed — status codes are seed data in a lookup table.
