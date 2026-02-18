# Ingestion Routing

**Schema version introduced:** 1.5.0
**Phase:** 2d

## Overview

The `IngestionRoute` table decouples ingestion scripts from hardcoded
`MetaDataID` values.  Instead of an ingestion script knowing "I write
TSS data to `Metadata_ID = 42`", it identifies itself by what it
_is_—equipment, parameter, provenance, and processing degree—and the
database resolves the target.

```
Ingestion script
     │  "I am Equipment 7, measuring Parameter 3 (TSS),
     │   Sensor provenance, Raw processing"
     ▼
  dbo.IngestionRoute
     │  resolves → Metadata_ID = 42
     ▼
  dbo.Value  (scalar) / dbo.ValueVector / dbo.ValueMatrix / …
```

When a sensor moves or a campaign rolls over, only **one row** in
`IngestionRoute` needs to be updated—no script changes required.

---

## Table: dbo.IngestionRoute

| Column | Type | Nullable | Description |
|---|---|---|---|
| `IngestionRoute_ID` | INT IDENTITY | No | Surrogate PK |
| `Equipment_ID` | INT | **Yes** | Equipment producing the data. NULL for lab/manual provenance. |
| `Parameter_ID` | INT | No | Measured parameter (FK → Parameter) |
| `DataProvenance_ID` | INT | No | How data is produced (FK → DataProvenance) |
| `ProcessingDegree` | NVARCHAR(50) | No | Level of processing. Default `'Raw'`. |
| `ValidFrom` | DATETIME2(7) | No | Inclusive start of route validity |
| `ValidTo` | DATETIME2(7) | **Yes** | Exclusive end. NULL = still active |
| `CreatedAt` | DATETIME2(7) | No | Auto-filled with UTC timestamp |
| `Metadata_ID` | INT | No | Target MetaData entry (FK → MetaData) |
| `Notes` | NVARCHAR(500) | Yes | Free-text description |

### ProcessingDegree controlled vocabulary

| Value | Meaning |
|---|---|
| `Raw` | Data as received from the instrument (default) |
| `Cleaned` | Outliers or artefacts removed |
| `Validated` | Human-reviewed and accepted |
| `Interpolated` | Gaps filled by interpolation |
| `Aggregated` | Time-averaged or otherwise aggregated |

---

## Route Resolution

A route is **active** at timestamp `T` if:

```
ValidFrom <= T  AND  (ValidTo IS NULL  OR  ValidTo > T)
```

At most **one** active route should exist for any
`(Equipment_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree, T)`
combination. The resolution query raises an error if zero or more than
one routes match.

### SQL

```sql
-- Parameters: @Equipment_ID, @Parameter_ID, @DataProvenance_ID,
--             @ProcessingDegree, @Timestamp
SELECT [Metadata_ID]
FROM   [dbo].[IngestionRoute]
WHERE  [Equipment_ID]      = @Equipment_ID
  AND  [Parameter_ID]      = @Parameter_ID
  AND  [DataProvenance_ID] = @DataProvenance_ID
  AND  [ProcessingDegree]  = @ProcessingDegree
  AND  [ValidFrom]        <= @Timestamp
  AND  ([ValidTo] IS NULL OR [ValidTo] > @Timestamp);
```

### Python helper (from `tests/integration/test_phase2d.py`)

```python
def resolve_route(conn, equipment_id, parameter_id, data_provenance_id,
                  processing_degree, timestamp) -> int:
    cursor = conn.cursor()
    cursor.execute(RESOLVE_ROUTE_SQL,
                   equipment_id, parameter_id, data_provenance_id,
                   processing_degree, timestamp, timestamp)
    rows = cursor.fetchall()
    if len(rows) == 0:
        raise LookupError("No active IngestionRoute for …")
    if len(rows) > 1:
        raise ValueError("Ambiguous IngestionRoute: …")
    return rows[0][0]
```

---

## How to Add a New Route

### Scenario: new sensor deployed

1. Create (or confirm) an `Equipment` record for the new sensor.
2. Confirm the `Parameter` record for the measured analyte exists.
3. Insert the route:

```sql
INSERT INTO [dbo].[IngestionRoute]
    ([Equipment_ID], [Parameter_ID], [DataProvenance_ID],
     [ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID], [Notes])
VALUES
    (7,    -- Equipment_ID of new sensor
     3,    -- Parameter_ID (TSS)
     1,    -- DataProvenance_ID (Sensor)
     'Raw',
     '2025-07-01T00:00:00',   -- first data timestamp
     NULL,                     -- still active
     42,   -- Metadata_ID that will store the data
     'TSS sensor installed at Primary Effluent for 2025-H2 ops');
```

---

## How to Handle an Equipment Move

When a sensor moves from location A to location B on date `D`:

1. **Close the old route** by setting `ValidTo = D`:

```sql
UPDATE [dbo].[IngestionRoute]
SET    [ValidTo] = '2025-09-15T00:00:00',
       [Notes]   = 'Sensor moved to Secondary Effluent 2025-09-15'
WHERE  [Equipment_ID]     = 7
  AND  [Parameter_ID]     = 3
  AND  [DataProvenance_ID]= 1
  AND  [ProcessingDegree] = 'Raw'
  AND  [ValidTo]          IS NULL;
```

2. **Create the new MetaData entry** for the new location (if one doesn't
   already exist for Equipment 7 at location B).

3. **Open a new route** starting from `D`:

```sql
INSERT INTO [dbo].[IngestionRoute]
    ([Equipment_ID], [Parameter_ID], [DataProvenance_ID],
     [ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID], [Notes])
VALUES
    (7, 3, 1, 'Raw',
     '2025-09-15T00:00:00', NULL,
     87,   -- Metadata_ID for TSS at Secondary Effluent
     'Sensor moved from Primary to Secondary Effluent');
```

4. Update `EquipmentInstallation` to record the physical move (see
   [Sensor Lifecycle](sensor_lifecycle.md)).

5. Verify: run the resolution query for a timestamp just before and just
   after `D` to confirm the correct `Metadata_ID` is returned.

---

## Campaign Transitions

When a new campaign starts and data should flow to a different
`MetaData` entry (e.g. a campaign-scoped series instead of the
operations series):

1. Close the current route at the campaign start date.
2. Create a new `MetaData` entry linked to the new `Campaign_ID`.
3. Open a new route pointing to the new `MetaData_ID`.
4. When the campaign ends, close the campaign route and (optionally)
   reopen the operations route.

---

## Troubleshooting: "My data isn't being ingested"

1. **Check that a route exists:**

```sql
SELECT *
FROM   [dbo].[IngestionRoute]
WHERE  [Equipment_ID]     = <your equipment id>
  AND  [Parameter_ID]     = <your parameter id>
  AND  [DataProvenance_ID]= <provenance id>
  AND  [ProcessingDegree] = 'Raw'
ORDER BY [ValidFrom] DESC;
```

2. **Check temporal validity:** Is today's timestamp within
   `[ValidFrom, ValidTo)`?

3. **Check for ambiguity:** Does more than one row match the active
   window? If so, set `ValidTo` on all but the intended route.

4. **Check the target MetaData:** Does `Metadata_ID` point to a real
   row in `dbo.MetaData`?

---

## Backfill Script

`migrations/data/backfill_ingestion_routes.sql` creates an
`IngestionRoute` entry for every existing `MetaData` row that has an
`Equipment_ID` and `Parameter_ID`. The script is idempotent—safe to
run multiple times.

```bash
# Apply backfill (adjust connection string as needed)
sqlcmd -S 127.0.0.1,14330 -U SA -P 'StrongPwd123!' \
       -d <database> \
       -i migrations/data/backfill_ingestion_routes.sql
```

---

## Relationship to Other Tables

```
Equipment ──┐
            ├──► IngestionRoute ──► MetaData ──► Value / ValueVector / …
Parameter ──┤
DataProv  ──┘

EquipmentInstallation  (where was Equipment physically? complementary)
Campaign               (which campaign owns this MetaData?)
```
