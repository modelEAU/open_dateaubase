# Database Views

Virtual tables defined by SQL queries.


<span id="vw_ChannelStatus"></span>

## vw_ChannelStatus

Per-channel sensor status view. A status channel is a Channel whose SignalPort has SignalPortType=Status and a non-null ParentPort_ID pointing to the measured value port. Navigates via SignalPort sub-signal relationship — replaces the StatusChannel_ID column from v2.x.



**View Definition:**

```sql
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    valueC.[Channel_ID]         AS MeasurementChannelID,
    e.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    p.[Parameter]               AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]               o        ON o.[Observation_ID]      = v.[Observation_ID]
JOIN [dbo].[Channel]                   statusC  ON statusC.[Channel_ID]    = o.[Channel_ID]
JOIN [dbo].[SignalPort]                statusP  ON statusP.[SignalPort_ID] = statusC.[SignalPort_ID]
JOIN [dbo].[SignalPortType]            spt      ON spt.[SignalPortType_ID] = statusP.[SignalPortType_ID]
JOIN [dbo].[SignalPort]                valueP   ON valueP.[SignalPort_ID]  = statusP.[ParentPort_ID]
JOIN [dbo].[Channel]                   valueC   ON valueC.[SignalPort_ID]  = valueP.[SignalPort_ID]
JOIN [dbo].[Parameter]                 p        ON p.[Parameter_ID]        = valueC.[Parameter_ID]
LEFT JOIN [dbo].[SignalPortEquipmentHistory] peh  ON peh.[SignalPort_ID]     = valueP.[SignalPort_ID]
                                                  AND peh.[EndTime]          IS NULL
LEFT JOIN [dbo].[Equipment]            e        ON e.[Equipment_ID]        = peh.[Equipment_ID]
WHERE spt.[Name] = N'Status'
  AND statusP.[ParentPort_ID] IS NOT NULL

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| StatusChannelID | INT | `StatusChannelID` | Channel_ID of the status time series |
| MeasurementChannelID | INT | `MeasurementChannelID` | Channel_ID of the measurement channel this status describes |
| EquipmentID | INT | `EquipmentID` | Equipment ID of the currently-linked sensor (NULL if no active history row) |
| EquipmentName | NVARCHAR(200) | `EquipmentName` | Identifier of the currently-linked equipment |
| MeasurementParameter | NVARCHAR(100) | `MeasurementParameter` | Name of the measured parameter (TSS, pH, etc.) |
| Timestamp | DATETIME2(7) | `Timestamp` | Timestamp of the status observation |
| StatusCodeID | INT | `StatusCodeID` | Raw integer status code stored in the status Channel's Value rows |

<span id="vw_DeviceStatus"></span>

## vw_DeviceStatus

Device-level status view. Finds status channels by following the currently-active SignalPortEquipmentHistory row for each equipment, then filtering for ports with SignalPortType=Status. Replaces the EquipmentStatusChannel junction table from v2.x.



**View Definition:**

```sql
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    e.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]               o        ON o.[Observation_ID]      = v.[Observation_ID]
JOIN [dbo].[Channel]                   statusC  ON statusC.[Channel_ID]    = o.[Channel_ID]
JOIN [dbo].[SignalPort]                statusP  ON statusP.[SignalPort_ID] = statusC.[SignalPort_ID]
JOIN [dbo].[SignalPortType]            spt      ON spt.[SignalPortType_ID] = statusP.[SignalPortType_ID]
JOIN [dbo].[SignalPortEquipmentHistory]  peh      ON peh.[SignalPort_ID]     = statusP.[SignalPort_ID]
                                                 AND peh.[EndTime]          IS NULL
JOIN [dbo].[Equipment]                 e        ON e.[Equipment_ID]        = peh.[Equipment_ID]
WHERE spt.[Name] = N'Status'

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| StatusChannelID | INT | `StatusChannelID` | Channel_ID of the status time series |
| EquipmentID | INT | `EquipmentID` | Equipment ID this status describes |
| EquipmentName | NVARCHAR(200) | `EquipmentName` | Identifier of the equipment |
| Timestamp | DATETIME2(7) | `Timestamp` | Timestamp of the status observation |
| StatusCodeID | INT | `StatusCodeID` | Raw integer status code stored in the status Channel's Value rows |