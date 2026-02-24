# Database Views

Virtual tables defined by SQL queries.


<span id="vw_ChannelStatus"></span>

## vw_ChannelStatus

Join view for per-channel sensor status queries. Updated in v2.1.0 (Phase C) to use Channel.StatusChannel_ID instead of the legacy StatusOfMetaDataID column.


**View Definition:**

```sql
SELECT
    statusC.[Channel_ID]          AS StatusChannelID,
    statusC.[StatusChannel_ID]    AS MeasurementChannelID,
    measC.[Equipment_ID]          AS EquipmentID,
    e.[identifier]                AS EquipmentName,
    p.[Parameter]                 AS MeasurementParameter,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]               statusC ON statusC.[Channel_ID]      = v.[Channel_ID]
JOIN [dbo].[Channel]               measC   ON measC.[Channel_ID]        = statusC.[StatusChannel_ID]
JOIN [dbo].[Parameter]             p       ON p.[Parameter_ID]          = measC.[Parameter_ID]
JOIN [dbo].[Equipment]             e       ON e.[Equipment_ID]          = measC.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc      ON sc.[StatusCodeID]         = CAST(v.[Value] AS INT)
WHERE statusC.[StatusChannel_ID] IS NOT NULL

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| StatusChannelID | INT | `StatusChannelID` | Channel_ID of the status time series |
| MeasurementChannelID | INT | `MeasurementChannelID` | Channel_ID of the measurement channel this status describes |
| EquipmentID | INT | `EquipmentID` | Equipment ID of the sensor |
| EquipmentName | NVARCHAR(100) | `EquipmentName` | Name/identifier of the equipment |
| MeasurementParameter | NVARCHAR(100) | `MeasurementParameter` | Name of the measured parameter (TSS, pH, etc.) |
| Timestamp | DATETIME2(7) | `Timestamp` | Timestamp of the status transition |
| StatusCodeID | INT | `StatusCodeID` | Status code from SensorStatusCode |
| StatusName | NVARCHAR(100) | `StatusName` | Human-readable status name |
| IsOperational | BIT | `IsOperational` | Whether data is trustworthy in this status |
| Severity | INT | `Severity` | Urgency level (0=normal, 1=warning, 2=fault, 3=critical) |

<span id="vw_DeviceStatus"></span>

## vw_DeviceStatus

Join view for device-level sensor status queries. Updated in v2.1.0 (Phase C) to join via EquipmentStatusChannel instead of the legacy StatusOfEquipmentID column on Channel.


**View Definition:**

```sql
SELECT
    statusC.[Channel_ID]          AS StatusChannelID,
    esc.[Equipment_ID]            AS EquipmentID,
    e.[identifier]                AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]                 statusC ON statusC.[Channel_ID]   = v.[Channel_ID]
JOIN [dbo].[EquipmentStatusChannel]  esc     ON esc.[StatusChannel_ID] = statusC.[Channel_ID]
JOIN [dbo].[Equipment]               e       ON e.[Equipment_ID]       = esc.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode]   sc      ON sc.[StatusCodeID]      = CAST(v.[Value] AS INT)

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| StatusChannelID | INT | `StatusChannelID` | Channel_ID of the status time series |
| EquipmentID | INT | `EquipmentID` | Equipment ID this status describes |
| EquipmentName | NVARCHAR(100) | `EquipmentName` | Name/identifier of the equipment |
| Timestamp | DATETIME2(7) | `Timestamp` | Timestamp of the status transition |
| StatusCodeID | INT | `StatusCodeID` | Status code from SensorStatusCode |
| StatusName | NVARCHAR(100) | `StatusName` | Human-readable status name |
| IsOperational | BIT | `IsOperational` | Whether data is trustworthy in this status |
| Severity | INT | `Severity` | Urgency level (0=normal, 1=warning, 2=fault, 3=critical) |