# Self-Configuring Ingestion

## Overview

A **Channel** is the invariant descriptor for a measurement stream: it captures
*what equipment is measuring what parameter*, at what processing degree, and in what unit.
Context that changes over time (physical location, campaign) is stored separately in
`EquipmentInstallation` and `CampaignEquipment` and derived at query time — it is never
baked into the Channel row itself.

Because the Channel identity is the combination
`(Equipment_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree)` — and that combination
is enforced by a `UNIQUE` constraint — ingestion can use a simple find-or-create pattern:

```
Ingestion script
     │  "I am Equipment 7, measuring Parameter 3 (TSS),
     │   Sensor provenance, Raw processing"
     ▼
  find or create Channel row via UNIQUE key
     │  Channel_ID = 42 (created on first write; reused on all subsequent writes)
     ▼
  dbo.Value  (scalar) / dbo.ValueVector / dbo.ValueMatrix / …
```

There is no routing table to pre-configure and no `RouteNotFound` errors. The same
`Channel_ID` is reused for every timestamp from that stream, regardless of where the
sensor is physically installed.

---

## The UNIQUE Constraint

```sql
-- On dbo.Channel
CONSTRAINT [UQ_Channel_SensorStream]
UNIQUE ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree])
-- Filtered: WHERE Equipment_ID IS NOT NULL
```

This constraint guarantees at most one Channel row per sensor stream. The find-or-create
logic simply does:

```sql
-- Find or create: if no row exists yet, insert; then select the Channel_ID
IF NOT EXISTS (
    SELECT 1 FROM [dbo].[Channel]
    WHERE [Equipment_ID]      = @Equipment_ID
      AND [Parameter_ID]      = @Parameter_ID
      AND [DataProvenance_ID] = @DataProvenance_ID
      AND [ProcessingDegree]  = @ProcessingDegree
)
INSERT INTO [dbo].[Channel]
    ([Equipment_ID], [Parameter_ID], [Unit_ID], [DataProvenance_ID],
     [ProcessingDegree], [ValueType_ID])
VALUES (@Equipment_ID, @Parameter_ID, @Unit_ID, @DataProvenance_ID,
        @ProcessingDegree, @ValueType_ID);

SELECT [Channel_ID] FROM [dbo].[Channel]
WHERE [Equipment_ID]      = @Equipment_ID
  AND [Parameter_ID]      = @Parameter_ID
  AND [DataProvenance_ID] = @DataProvenance_ID
  AND [ProcessingDegree]  = @ProcessingDegree;
```

This is implemented in `api/v1/repositories/ingestion_repository.py` as
`find_or_create_sensor_metadata()`.

---

## API: Ingesting Sensor Data

### POST /api/v1/ingest/sensor

```json
{
  "equipment_id": 7,
  "parameter_id": 3,
  "unit_id": 2,
  "data_provenance_id": 1,
  "processing_degree": "Raw",
  "timestamps": ["2025-09-10T10:00:00Z", "2025-09-10T10:15:00Z"],
  "values": [185.0, 192.3]
}
```

Response includes `channel_id` (the Channel row that was found or created).

### POST /api/v1/ingest/processed

For derived/processed time series (output of a processing step). Supply
`source_channel_id` and a new `processing_degree`. The endpoint clones the identity
fields from the source Channel and creates a new Channel row for the processed output.

### POST /api/v1/ingest/lab

Lab data does not use the Channel model. See [Lab Data](lab_data.md).

---

## Equipment Moves

When a sensor moves from location A to location B, **the Channel row does not change**.
The Channel captures the equipment-parameter relationship, which is invariant.
What changes is the `EquipmentInstallation` record:

1. Close the old `EquipmentInstallation` row by setting `RemovedDate = D`.
2. Insert a new `EquipmentInstallation` row with `InstalledDate = D` and the new
   `Sampling_point_ID`.

Data written after the move is queried via the same `Channel_ID`. At query time, location
is derived by joining `EquipmentInstallation` on the timestamp. See
[Equipment Move Checklist](../operations/equipment_move_checklist.md) for the step-by-step.

---

## Deriving Context at Query Time

Because location and campaign are not stored on Channel, they are derived from join tables:

```sql
-- Where was Channel 42 at timestamp T?
SELECT
    sp.[Sampling_point],
    sp.[Sampling_location],
    ei.[InstalledDate],
    ei.[RemovedDate]
FROM [dbo].[Channel] c
JOIN [dbo].[EquipmentInstallation] ei
    ON  ei.[Equipment_ID] = c.[Equipment_ID]
    AND ei.[InstalledDate] <= @T
    AND (ei.[RemovedDate] IS NULL OR ei.[RemovedDate] > @T)
JOIN [dbo].[SamplingPoints] sp ON sp.[Sampling_point_ID] = ei.[Sampling_point_ID]
WHERE c.[Channel_ID] = 42;

-- Which campaign was active for Channel 42 at timestamp T?
SELECT
    camp.[Campaign_ID],
    camp.[Name] AS CampaignName
FROM [dbo].[Channel] c
JOIN [dbo].[CampaignEquipment] ce
    ON ce.[Equipment_ID] = c.[Equipment_ID]
JOIN [dbo].[Campaign] camp
    ON  camp.[Campaign_ID] = ce.[Campaign_ID]
    AND camp.[StartDate] <= @T
    AND (camp.[EndDate] IS NULL OR camp.[EndDate] > @T)
WHERE c.[Channel_ID] = 42;
```

---

## ProcessingDegree Vocabulary

| Value | Meaning |
|---|---|
| `Raw` | Data as received from the instrument (default) |
| `Cleaned` | Outliers or artefacts removed |
| `Calibrated` | Calibration applied |
| `Validated` | Human-reviewed and accepted |
| `Filtered` | Smoothed or frequency-filtered |
| `Predicted` | Computed/predicted by a model |

---

## Relationship to Other Tables

```
Equipment ──┐
            ├──► Channel  ──► Value / ValueVector / ValueMatrix / ValueImage
Parameter ──┤
DataProv  ──┘

EquipmentInstallation  (where was Equipment physically at time T?)
CampaignEquipment      (which campaign was Equipment part of at time T?)
```
