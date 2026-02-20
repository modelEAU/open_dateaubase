# Database Views

Virtual tables defined by SQL queries.


<span id="vw_ChannelStatus"></span>

## vw_ChannelStatus

Join view for per-channel sensor status queries


**View Definition:**

```sql
SELECT
    statusMD.[Metadata_ID] AS StatusMetaDataID,
    statusMD.[StatusOfMetaDataID] AS MeasurementMetaDataID,
    measMD.[Equipment_ID] AS EquipmentID,
    e.[identifier] AS EquipmentName,
    p.[Parameter] AS MeasurementParameter,
    sp.[Sampling_point] AS LocationName,
    v.[Timestamp],
    CAST(v.[Value] AS INT) AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData] statusMD ON statusMD.[Metadata_ID] = v.[Metadata_ID]
JOIN [dbo].[MetaData] measMD ON measMD.[Metadata_ID] = statusMD.[StatusOfMetaDataID]
JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = measMD.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON sp.[Sampling_point_ID] = measMD.[Sampling_point_ID]
JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = measMD.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc ON sc.[StatusCodeID] = CAST(v.[Value] AS INT)
WHERE statusMD.[StatusOfMetaDataID] IS NOT NULL
```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| StatusMetaDataID | - | `StatusMetaDataID` | MetaDataID of the status time series |
| MeasurementMetaDataID | - | `MeasurementMetaDataID` | MetaDataID of the measurement channel this status describes |
| EquipmentID | - | `EquipmentID` | Equipment ID of the sensor |
| EquipmentName | - | `EquipmentName` | Name of the equipment |
| MeasurementParameter | - | `MeasurementParameter` | Name of the measured parameter (TSS, pH, etc.) |
| LocationName | - | `LocationName` | Name of the sampling location |
| Timestamp | - | `Timestamp` | Timestamp of the status transition |
| StatusCodeID | - | `StatusCodeID` | Status code from SensorStatusCode |
| StatusName | - | `StatusName` | Human-readable status name |
| IsOperational | - | `IsOperational` | Whether data is trustworthy in this status |
| Severity | - | `Severity` | Urgency level (0=normal, 1=warning, 2=fault, 3=critical) |

<span id="vw_DeviceStatus"></span>

## vw_DeviceStatus

Join view for device-level sensor status queries


**View Definition:**

```sql
SELECT
    statusMD.[Metadata_ID] AS StatusMetaDataID,
    statusMD.[StatusOfEquipmentID] AS EquipmentID,
    e.[identifier] AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT) AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData] statusMD ON statusMD.[Metadata_ID] = v.[Metadata_ID]
JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = statusMD.[StatusOfEquipmentID]
LEFT JOIN [dbo].[SensorStatusCode] sc ON sc.[StatusCodeID] = CAST(v.[Value] AS INT)
WHERE statusMD.[StatusOfEquipmentID] IS NOT NULL
```


#### Columns

| Column | SQL Type | Source Field | Description |
|--------|----------|--------------|-------------|
| StatusMetaDataID | - | `StatusMetaDataID` | MetaDataID of the status time series |
| EquipmentID | - | `EquipmentID` | Equipment ID this status describes |
| EquipmentName | - | `EquipmentName` | Name of the equipment |
| Timestamp | - | `Timestamp` | Timestamp of the status transition |
| StatusCodeID | - | `StatusCodeID` | Status code from SensorStatusCode |
| StatusName | - | `StatusName` | Human-readable status name |
| IsOperational | - | `IsOperational` | Whether data is trustworthy in this status |
| Severity | - | `Severity` | Urgency level (0=normal, 1=warning, 2=fault, 3=critical) |