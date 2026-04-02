# Database Views

Virtual tables defined by SQL queries.


<span id="vw_ChannelStatus"></span>

## vw_ChannelStatus

Per-channel sensor status view. Navigates the SignalPort sub-signal relationship to find
status channels (SignalPortType=Status, ParentPort_ID pointing to the value port).

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

| Column | SQL Type | Description |
|--------|----------|-------------|
| StatusChannelID | INT | Channel_ID of the status time series |
| MeasurementChannelID | INT | Channel_ID of the measurement channel this status describes |
| EquipmentID | INT | Equipment ID of the currently-linked sensor (NULL if no active history row) |
| EquipmentName | NVARCHAR(200) | Identifier of the currently-linked equipment |
| MeasurementParameter | NVARCHAR(100) | Name of the measured parameter (TSS, pH, etc.) |
| Timestamp | DATETIME2(7) | Timestamp of the status observation |
| StatusCodeID | INT | Raw integer status code stored in the status Channel |

<span id="vw_DeviceStatus"></span>

## vw_DeviceStatus

Device-level status view. Finds status channels by resolving the currently-active
`SignalPortEquipmentHistory` row for each equipment, then filtering for `SignalPortType=Status` ports.

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

| Column | SQL Type | Description |
|--------|----------|-------------|
| StatusChannelID | INT | Channel_ID of the status time series |
| EquipmentID | INT | Equipment ID this status describes |
| EquipmentName | NVARCHAR(200) | Identifier of the equipment |
| Timestamp | DATETIME2(7) | Timestamp of the status observation |
| StatusCodeID | INT | Raw integer status code stored in the status Channel |
