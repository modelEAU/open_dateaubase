# Database Views

Virtual tables defined by SQL queries.


<span id="vw_ChannelEquipmentAtTime"></span>

## vw_ChannelEquipmentAtTime

Resolves, for every Observation, which physical Equipment was wired to the Channel at the time of the observation. Walks EquipmentWiringHistory by matching SignalInterface_ID (and, when the Channel's port is known, SignalInterfacePort_ID) and bracketing (ValidFrom, ValidTo]. When a Channel has no port recorded and multiple Equipment share the interface at the same time, EquipmentID is NULL and Resolution = 'ambiguous'.



**View Definition:**

```sql
WITH channel_wiring AS (
    SELECT
        o.[Observation_ID] AS ObservationID,
        c.[Channel_ID]     AS ChannelID,
        o.[Timestamp]      AS Timestamp,
        c.[SignalInterface_ID],
        c.[SignalInterfacePort_ID],
        ewh.[Equipment_ID] AS EquipmentID,
        ROW_NUMBER() OVER (
            PARTITION BY o.[Observation_ID]
            ORDER BY
                CASE WHEN ewh.[SignalInterfacePort_ID] IS NOT NULL THEN 0 ELSE 1 END,
                ewh.[ValidFrom] DESC
        ) AS rn,
        COUNT(*) OVER (PARTITION BY o.[Observation_ID]) AS match_count
    FROM [dbo].[Observation] o
    JOIN [dbo].[Channel] c                      ON c.[Channel_ID]           = o.[Channel_ID]
    LEFT JOIN [dbo].[EquipmentWiringHistory] ewh ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
                                                AND (
                                                     ewh.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
                                                     OR (ewh.[SignalInterfacePort_ID] IS NULL AND c.[SignalInterfacePort_ID] IS NULL)
                                                     OR c.[SignalInterfacePort_ID] IS NULL
                                                    )
                                                AND ewh.[ValidFrom] <= o.[Timestamp]
                                                AND (ewh.[ValidTo] IS NULL OR ewh.[ValidTo] > o.[Timestamp])
)
SELECT
    cw.ObservationID,
    cw.ChannelID,
    cw.Timestamp,
    CASE WHEN cw.match_count > 1 AND cw.[SignalInterfacePort_ID] IS NULL THEN NULL ELSE cw.EquipmentID END AS EquipmentID,
    e.[Identifier]     AS EquipmentName,
    CASE
        WHEN cw.EquipmentID IS NULL AND cw.match_count = 0 THEN N'unlinked'
        WHEN cw.match_count > 1 AND cw.[SignalInterfacePort_ID] IS NULL THEN N'ambiguous'
        ELSE N'resolved'
    END AS Resolution
FROM channel_wiring cw
LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = cw.EquipmentID
WHERE cw.rn = 1

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| ObservationID | BIGINT | `ObservationID` | Observation row |
| ChannelID | INT | `ChannelID` | Channel this observation belongs to |
| Timestamp | DATETIME2(7) | `Timestamp` | Observation timestamp used for resolution |
| EquipmentID | INT | `EquipmentID` | Equipment wired at this time (NULL if unresolved / ambiguous) |
| EquipmentName | NVARCHAR(200) | `EquipmentName` | Identifier of the resolved equipment |
| Resolution | NVARCHAR(20) | `Resolution` | 'resolved' | 'unlinked' | 'ambiguous' |

<span id="vw_ChannelLocationAtTime"></span>

## vw_ChannelLocationAtTime

Resolves the SamplingPoint a Channel was sampling at the time of each Observation, by composing vw_ChannelEquipmentAtTime with EquipmentLocationHistory. When equipment cannot be resolved (ambiguous or unlinked wiring), SamplingPointID is NULL.



**View Definition:**

```sql
SELECT
    cea.ObservationID,
    cea.ChannelID,
    cea.Timestamp,
    cea.EquipmentID,
    elh.[SamplingPoint_ID] AS SamplingPointID,
    sp.[SamplingPoint]     AS SamplingPointName
FROM [dbo].[vw_ChannelEquipmentAtTime] cea
LEFT JOIN [dbo].[EquipmentLocationHistory] elh ON elh.[Equipment_ID] = cea.EquipmentID
                                              AND elh.[ValidFrom]   <= cea.Timestamp
                                              AND (elh.[ValidTo] IS NULL OR elh.[ValidTo] > cea.Timestamp)
LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| ObservationID | BIGINT | `ObservationID` | Observation row |
| ChannelID | INT | `ChannelID` | Channel this observation belongs to |
| Timestamp | DATETIME2(7) | `Timestamp` | Observation timestamp used for resolution |
| EquipmentID | INT | `EquipmentID` | Equipment resolved at this time (NULL if unresolved) |
| SamplingPointID | INT | `SamplingPointID` | SamplingPoint where the equipment was installed at this time |
| SamplingPointName | NVARCHAR(200) | `SamplingPointName` | Name of the SamplingPoint |

<span id="vw_ChannelStatus"></span>

## vw_ChannelStatus

Per-channel sensor status view. A status channel is a Channel whose ChannelRole = Status and whose ParentChannel_ID points at the measured value Channel. The equipment behind the value channel is resolved via the new EquipmentWiringHistory table (v4.0.0).



**View Definition:**

```sql
SELECT
    statusC.[Channel_ID]      AS StatusChannelID,
    valueC.[Channel_ID]       AS MeasurementChannelID,
    e.[Equipment_ID]          AS EquipmentID,
    e.[Identifier]            AS EquipmentName,
    p.[Parameter]             AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)    AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]   o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]       statusC ON statusC.[Channel_ID] = o.[Channel_ID]
JOIN [dbo].[ChannelKind]   role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[Channel]       valueC  ON valueC.[Channel_ID]   = statusC.[ParentChannel_ID]
JOIN [dbo].[Parameter]     p       ON p.[Parameter_ID]     = valueC.[Parameter_ID]
LEFT JOIN [dbo].[EquipmentWiringHistory] ewh
       ON ewh.[SignalInterface_ID] = valueC.[SignalInterface_ID]
      AND (
           ewh.[SignalInterfacePort_ID] = valueC.[SignalInterfacePort_ID]
           OR valueC.[SignalInterfacePort_ID] IS NULL
          )
      AND ewh.[ValidTo] IS NULL
LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
WHERE role.[Name] = N'Status'
  AND statusC.[ParentChannel_ID] IS NOT NULL

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| StatusChannelID | INT | `StatusChannelID` | Channel_ID of the status time series |
| MeasurementChannelID | INT | `MeasurementChannelID` | Channel_ID of the measurement channel this status describes |
| EquipmentID | INT | `EquipmentID` | Equipment ID currently wired to the measurement channel (NULL if unresolved) |
| EquipmentName | NVARCHAR(200) | `EquipmentName` | Identifier of the currently-linked equipment |
| MeasurementParameter | NVARCHAR(100) | `MeasurementParameter` | Name of the measured parameter (TSS, pH, etc.) |
| Timestamp | DATETIME2(7) | `Timestamp` | Timestamp of the status observation |
| StatusCodeID | INT | `StatusCodeID` | Raw integer status code stored in the status Channel's Value rows |

<span id="vw_DeviceStatus"></span>

## vw_DeviceStatus

Device-level status view. Finds status channels through the v4.0.0 SignalInterface + EquipmentWiringHistory chain: a status Channel (ChannelRole = Status) inherits its equipment from the parent value Channel's current wiring. Replaces the port-centric v3.0.0 join.



**View Definition:**

```sql
SELECT
    statusC.[Channel_ID]       AS StatusChannelID,
    e.[Equipment_ID]           AS EquipmentID,
    e.[Identifier]             AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)     AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]  o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]      statusC ON statusC.[Channel_ID] = o.[Channel_ID]
JOIN [dbo].[ChannelKind]  role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[Channel]      valueC  ON valueC.[Channel_ID]   = statusC.[ParentChannel_ID]
JOIN [dbo].[EquipmentWiringHistory] ewh
       ON ewh.[SignalInterface_ID] = valueC.[SignalInterface_ID]
      AND (
           ewh.[SignalInterfacePort_ID] = valueC.[SignalInterfacePort_ID]
           OR valueC.[SignalInterfacePort_ID] IS NULL
          )
      AND ewh.[ValidTo] IS NULL
JOIN [dbo].[Equipment]    e       ON e.[Equipment_ID]     = ewh.[Equipment_ID]
WHERE role.[Name] = N'Status'

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| StatusChannelID | INT | `StatusChannelID` | Channel_ID of the status time series |
| EquipmentID | INT | `EquipmentID` | Equipment ID this status describes |
| EquipmentName | NVARCHAR(200) | `EquipmentName` | Identifier of the equipment |
| Timestamp | DATETIME2(7) | `Timestamp` | Timestamp of the status observation |
| StatusCodeID | INT | `StatusCodeID` | Raw integer status code stored in the status Channel's Value rows |