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
        c.[Stream_ID]      AS ChannelID,
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
    JOIN [dbo].[vw_ChannelResolved] c           ON c.[Stream_ID]            = o.[Channel_ID]
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

Resolves the SamplingPoint a Channel was sampling at the time of each Observation, by composing vw_ChannelEquipmentAtTime with EquipmentLocationHistory. SamplingPointID is NULL whenever the chain is broken; the Resolution (equipment leg) and LocationResolution (location leg) discriminators say *why*, so NULL-because-broken is distinguishable from NULL-because-genuinely-absent (consistency audit F6).



**View Definition:**

```sql
SELECT
    cea.ObservationID,
    cea.ChannelID,
    cea.Timestamp,
    cea.EquipmentID,
    cea.Resolution,
    elh.[SamplingPoint_ID] AS SamplingPointID,
    sp.[SamplingPoint]     AS SamplingPointName,
    CASE
        WHEN cea.EquipmentID IS NULL              THEN N'no-equipment'
        WHEN elh.[SamplingPoint_ID] IS NOT NULL   THEN N'resolved'
        ELSE N'no-location'
    END AS LocationResolution
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
| Resolution | NVARCHAR(20) | `Resolution` | Equipment leg, passed through from vw_ChannelEquipmentAtTime: 'resolved' | 'unlinked' | 'ambiguous' |
| SamplingPointID | INT | `SamplingPointID` | SamplingPoint where the equipment was installed at this time |
| SamplingPointName | NVARCHAR(200) | `SamplingPointName` | Name of the SamplingPoint |
| LocationResolution | NVARCHAR(20) | `LocationResolution` | Location leg: 'resolved' (active ELH row) | 'no-location' (equipment resolved but no covering ELH row) | 'no-equipment' (equipment leg broken upstream, see Resolution) |

<span id="vw_ChannelResolved"></span>

## vw_ChannelResolved

Channel with its current SignalInterfacePort resolved from the active ChannelPortHistory row (ValidTo IS NULL). Replaces the former denormalised Channel.SignalInterfacePort_ID column: there is exactly one source of truth (ChannelPortHistory) so the port can never drift. Every read that needs the current port selects FROM this view instead of FROM the Channel base table; the equipment-resolution join predicates are otherwise unchanged. The filtered unique index UQ_ChannelPortHistory_ActiveRow guarantees at most one active row per channel, so this view returns exactly one row per Channel.



**View Definition:**

```sql
SELECT
    c.[Stream_ID],
    c.[SignalInterface_ID],
    c.[TagName],
    cph.[SignalInterfacePort_ID],
    c.[ParentChannel_ID],
    c.[ChannelKind_ID],
    c.[Parameter_ID],
    c.[DataProvenanceKind_ID],
    c.[ProducedByStep_ID],
    c.[ValueKind_ID],
    c.[Unit_ID]
FROM [dbo].[Channel] c
LEFT JOIN [dbo].[ChannelPortHistory] cph
    ON cph.[Channel_ID] = c.[Stream_ID]
    AND cph.[ValidTo] IS NULL

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| Stream_ID | INT | `Stream_ID` | Channel primary key (shared with Stream) |
| SignalInterface_ID | INT | `SignalInterface_ID` | Publishing SignalInterface (NULL for derived channels) |
| TagName | NVARCHAR(200) | `TagName` | Published tag string |
| SignalInterfacePort_ID | INT | `SignalInterfacePort_ID` | Current port from the active ChannelPortHistory row (NULL if untraced) |
| ParentChannel_ID | INT | `ParentChannel_ID` | Parent value channel for sub-signals (Status/Alarm/Uncertainty) |
| ChannelKind_ID | INT | `ChannelKind_ID` | 1=Value, 2=Status, 3=Alarm, 4=Uncertainty |
| Parameter_ID | INT | `Parameter_ID` | Measured analyte or parameter |
| DataProvenanceKind_ID | INT | `DataProvenanceKind_ID` | How the data was produced |
| ProducedByStep_ID | INT | `ProducedByStep_ID` | ProcessingStep that produced a derived channel (NULL for raw) |
| ValueKind_ID | INT | `ValueKind_ID` | Shape of stored values (1=Scalar, ...) |
| Unit_ID | INT | `Unit_ID` | Unit of measurement |

<span id="vw_ChannelStatus"></span>

## vw_ChannelStatus

Per-channel sensor status view. A status channel is a Channel whose ChannelRole = Status and whose ParentChannel_ID points at the measured value Channel. The equipment behind the value channel is resolved via the new EquipmentWiringHistory table (v4.0.0).



**View Definition:**

```sql
SELECT
    statusC.[Stream_ID]       AS StatusChannelID,
    valueC.[Stream_ID]        AS MeasurementChannelID,
    e.[Equipment_ID]          AS EquipmentID,
    e.[Identifier]            AS EquipmentName,
    p.[Parameter]             AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)    AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]   o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]       statusC ON statusC.[Stream_ID]  = o.[Channel_ID]
JOIN [dbo].[ChannelKind]   role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[vw_ChannelResolved] valueC ON valueC.[Stream_ID] = statusC.[ParentChannel_ID]
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
| StatusChannelID | INT | `StatusChannelID` | Stream_ID of the status time series (Channel PK is now Stream_ID) |
| MeasurementChannelID | INT | `MeasurementChannelID` | Stream_ID of the measurement channel this status describes |
| EquipmentID | INT | `EquipmentID` | Equipment ID currently wired to the measurement channel (NULL if unresolved) |
| EquipmentName | NVARCHAR(200) | `EquipmentName` | Identifier of the currently-linked equipment |
| MeasurementParameter | NVARCHAR(100) | `MeasurementParameter` | Name of the measured parameter (TSS, pH, etc.) |
| Timestamp | DATETIME2(7) | `Timestamp` | Timestamp of the status observation |
| StatusCodeID | INT | `StatusCodeID` | Raw integer status code stored in the status Channel's Value rows |

<span id="vw_DeploymentCoherence"></span>

## vw_DeploymentCoherence

Surfaces deployment drift (consistency audit F1): equipment whose active location sits at a Site different from the Site where its connected Data Acquisition System is currently deployed. A DAS is deployed to a Site (DASLocationHistory); equipment is wired to that DAS's SignalInterfaces (EquipmentWiringHistory) and physically placed at a SamplingPoint (EquipmentLocationHistory), and every SamplingPoint belongs to a Site. When a DAS is moved to a new Site, the equipment it feeds does not move with it automatically — this view lists each such stranded equipment so the drift can be corrected (relocate the equipment, or move the DAS back). Only active rows (ValidTo IS NULL) on both histories are considered; a row appears here only while the mismatch is live.



**View Definition:**

```sql
SELECT
    dlh.[DataAcquisitionSystem_ID]      AS DAS_ID,
    das.[Name]                          AS DASName,
    dlh.[Site_ID]                       AS DASSite_ID,
    dsite.[Name]                        AS DASSiteName,
    e.[Equipment_ID]                    AS Equipment_ID,
    e.[Identifier]                      AS EquipmentName,
    sp.[Site_ID]                        AS EquipmentSite_ID,
    esite.[Name]                        AS EquipmentSiteName,
    sp.[SamplingPoint_ID]               AS SamplingPoint_ID,
    sp.[SamplingPoint]                  AS SamplingPointName
FROM [dbo].[DASLocationHistory] dlh
JOIN [dbo].[DataAcquisitionSystem] das ON das.[DataAcquisitionSystem_ID] = dlh.[DataAcquisitionSystem_ID]
JOIN [dbo].[SignalInterface] si        ON si.[DataAcquisitionSystem_ID] = dlh.[DataAcquisitionSystem_ID]
JOIN [dbo].[EquipmentWiringHistory] ewh ON ewh.[SignalInterface_ID] = si.[SignalInterface_ID]
                                       AND ewh.[ValidTo] IS NULL
JOIN [dbo].[Equipment] e               ON e.[Equipment_ID] = ewh.[Equipment_ID]
JOIN [dbo].[EquipmentLocationHistory] elh ON elh.[Equipment_ID] = e.[Equipment_ID]
                                       AND elh.[ValidTo] IS NULL
JOIN [dbo].[SamplingPoint] sp          ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
LEFT JOIN [dbo].[Site] dsite           ON dsite.[Site_ID] = dlh.[Site_ID]
LEFT JOIN [dbo].[Site] esite           ON esite.[Site_ID] = sp.[Site_ID]
WHERE dlh.[ValidTo] IS NULL
  AND sp.[Site_ID] <> dlh.[Site_ID]

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| DAS_ID | INT | `DAS_ID` | The deployed Data Acquisition System |
| DASName | NVARCHAR(200) | `DASName` | DAS name |
| DASSite_ID | INT | `DASSite_ID` | Site the DAS is currently deployed to |
| DASSiteName | NVARCHAR(200) | `DASSiteName` | Name of the DAS's Site |
| Equipment_ID | INT | `Equipment_ID` | Equipment wired to the DAS but located elsewhere |
| EquipmentName | NVARCHAR(200) | `EquipmentName` | Equipment identifier |
| EquipmentSite_ID | INT | `EquipmentSite_ID` | Site of the equipment's current SamplingPoint (the drift) |
| EquipmentSiteName | NVARCHAR(200) | `EquipmentSiteName` | Name of the equipment's current Site |
| SamplingPoint_ID | INT | `SamplingPoint_ID` | Equipment's current SamplingPoint |
| SamplingPointName | NVARCHAR(200) | `SamplingPointName` | Name of the equipment's current SamplingPoint |

<span id="vw_DeviceStatus"></span>

## vw_DeviceStatus

Device-level status view. Finds status channels through the v4.0.0 SignalInterface + EquipmentWiringHistory chain: a status Channel (ChannelRole = Status) inherits its equipment from the parent value Channel's current wiring. Replaces the port-centric v3.0.0 join.



**View Definition:**

```sql
SELECT
    statusC.[Stream_ID]        AS StatusChannelID,
    e.[Equipment_ID]           AS EquipmentID,
    e.[Identifier]             AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)     AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]  o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]      statusC ON statusC.[Stream_ID]  = o.[Channel_ID]
JOIN [dbo].[ChannelKind]  role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[vw_ChannelResolved] valueC ON valueC.[Stream_ID] = statusC.[ParentChannel_ID]
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
| StatusChannelID | INT | `StatusChannelID` | Stream_ID of the status time series (Channel PK is now Stream_ID) |
| EquipmentID | INT | `EquipmentID` | Equipment ID this status describes |
| EquipmentName | NVARCHAR(200) | `EquipmentName` | Identifier of the equipment |
| Timestamp | DATETIME2(7) | `Timestamp` | Timestamp of the status observation |
| StatusCodeID | INT | `StatusCodeID` | Raw integer status code stored in the status Channel's Value rows |

<span id="vw_InactiveParentReferences"></span>

## vw_InactiveParentReferences

Health view (consistency audit F11): live references to soft-deleted parents. The model leans on IsActive soft-deletes for SignalInterface and SignalInterfacePort, but setting IsActive=0 does nothing to the active EquipmentWiringHistory rows still pointing at that interface/port — they keep resolving as if active. This view lists each active wiring row (ValidTo IS NULL) whose referenced SignalInterface or SignalInterfacePort is inactive, so the app can warn before deactivating a parent that still has live children (and operators can reconcile existing orphans). One row per dangling reference; ReferenceType says which leg is stale.



**View Definition:**

```sql
SELECT
    N'active-wiring->interface' AS ReferenceType,
    ewh.[EquipmentWiringHistory_ID] AS WiringHistoryID,
    ewh.[Equipment_ID]              AS EquipmentID,
    si.[SignalInterface_ID]         AS ParentID,
    si.[Name]                       AS ParentLabel
FROM [dbo].[EquipmentWiringHistory] ewh
JOIN [dbo].[SignalInterface] si ON si.[SignalInterface_ID] = ewh.[SignalInterface_ID]
WHERE ewh.[ValidTo] IS NULL
  AND si.[IsActive] = 0
UNION ALL
SELECT
    N'active-wiring->port'  AS ReferenceType,
    ewh.[EquipmentWiringHistory_ID] AS WiringHistoryID,
    ewh.[Equipment_ID]              AS EquipmentID,
    sip.[SignalInterfacePort_ID]    AS ParentID,
    sip.[PortIdentifier]            AS ParentLabel
FROM [dbo].[EquipmentWiringHistory] ewh
JOIN [dbo].[SignalInterfacePort] sip ON sip.[SignalInterfacePort_ID] = ewh.[SignalInterfacePort_ID]
WHERE ewh.[ValidTo] IS NULL
  AND sip.[IsActive] = 0

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| ReferenceType | NVARCHAR(40) | `ReferenceType` | 'active-wiring->interface' | 'active-wiring->port' |
| WiringHistoryID | INT | `WiringHistoryID` | The active EquipmentWiringHistory row holding the stale reference |
| EquipmentID | INT | `EquipmentID` | Equipment wired by that row |
| ParentID | INT | `ParentID` | SignalInterface_ID or SignalInterfacePort_ID that is inactive |
| ParentLabel | NVARCHAR(200) | `ParentLabel` | Inactive parent's name (interface) or port identifier |

<span id="vw_UnclassifiedEquipment"></span>

## vw_UnclassifiedEquipment

Health view: equipment that cannot be classified, either because it has no EquipmentModel or because its model has no EquipmentKind. Pickers that scope themselves to a kind — the laboratory forms only offer Samplers — silently drop these rows, so "my sampler isn't in the dropdown" is diagnosed here. The Reason column separates the two defects, since they are fixed in different places: attach a model to the equipment, or set the kind on the model. Inactive equipment is included, because the equipment lookup does not filter on IsActive either — any row it can return is a row that can go missing from a picker. Models with no equipment at all are out of scope: they cannot break a picker, and the EquipmentModel form already exposes the kind.



**View Definition:**

```sql
SELECT
    e.[Equipment_ID]       AS EquipmentID,
    e.[Identifier]         AS Identifier,
    e.[IsActive]           AS IsActive,
    e.[EquipmentModel_ID]  AS EquipmentModelID,
    m.[EquipmentModel]     AS EquipmentModelName,
    CASE WHEN e.[EquipmentModel_ID] IS NULL
         THEN N'no model' ELSE N'model has no kind' END AS Reason
FROM [dbo].[Equipment] e
LEFT JOIN [dbo].[EquipmentModel] m ON m.[EquipmentModel_ID] = e.[EquipmentModel_ID]
WHERE e.[EquipmentModel_ID] IS NULL OR m.[EquipmentKind_ID] IS NULL

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| EquipmentID | INT | `EquipmentID` | Equipment that no picker can classify |
| Identifier | NVARCHAR(100) | `Identifier` | The equipment's identifier |
| IsActive | BIT | `IsActive` | Whether the equipment is active |
| EquipmentModelID | INT | `EquipmentModelID` | The equipment's model, NULL when none is attached |
| EquipmentModelName | NVARCHAR(100) | `EquipmentModelName` | Name of the equipment's model, NULL when none is attached |
| Reason | NVARCHAR(20) | `Reason` | Which defect applies: 'no model' or 'model has no kind' |

<span id="vw_UnlinkedChannels"></span>

## vw_UnlinkedChannels

Health view (consistency audit F5): raw/ingested channels that carry Observations but have no active EquipmentWiringHistory on their SignalInterface, so every observation resolves as 'unlinked' (see vw_ChannelEquipmentAtTime) with no equipment and no SamplingPoint. These are channels that were ingested but never linked to physical equipment — "N channels need wiring". Only raw channels are considered: derived/ processed channels have SignalInterface_ID NULL by design and are deliberately unwired, not forgotten, so they are excluded. A channel drops off this list the moment an active wiring row exists for its interface.



**View Definition:**

```sql
SELECT
    c.[Stream_ID]          AS ChannelID,
    c.[TagName]            AS TagName,
    c.[SignalInterface_ID] AS SignalInterfaceID,
    si.[Name]              AS SignalInterfaceName,
    COUNT(o.[Observation_ID]) AS ObservationCount,
    MIN(o.[Timestamp])     AS FirstObservation,
    MAX(o.[Timestamp])     AS LastObservation
FROM [dbo].[Channel] c
JOIN [dbo].[Observation] o ON o.[Channel_ID] = c.[Stream_ID]
LEFT JOIN [dbo].[SignalInterface] si ON si.[SignalInterface_ID] = c.[SignalInterface_ID]
WHERE c.[SignalInterface_ID] IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM [dbo].[EquipmentWiringHistory] ewh
      WHERE ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
        AND ewh.[ValidTo] IS NULL
  )
GROUP BY c.[Stream_ID], c.[TagName], c.[SignalInterface_ID], si.[Name]

```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| ChannelID | INT | `ChannelID` | Channel (Stream_ID) lacking active wiring |
| TagName | NVARCHAR(200) | `TagName` | Channel tag name |
| SignalInterfaceID | INT | `SignalInterfaceID` | The channel's SignalInterface (has no active wiring row) |
| SignalInterfaceName | NVARCHAR(200) | `SignalInterfaceName` | Name of the SignalInterface |
| ObservationCount | INT | `ObservationCount` | How many observations are stranded on this unlinked channel |
| FirstObservation | DATETIME2(7) | `FirstObservation` | Earliest stranded observation timestamp |
| LastObservation | DATETIME2(7) | `LastObservation` | Latest stranded observation timestamp |