# Equipment Move Checklist

Use this checklist when physically relocating a sensor from one sampling
location to another.  The goal is to ensure data flows to the correct
`MetaData` entry before, during, and after the move.

---

## Before the Move

- [ ] **Identify the sensor** — `Equipment_ID` in `dbo.Equipment`.
- [ ] **Identify the current location** — confirm the latest open row in
      `dbo.EquipmentInstallation` for this `Equipment_ID`.
- [ ] **Choose a move timestamp** — decide the exact datetime `D` when the
      sensor will be considered "at the new location". Use UTC.
- [ ] **Identify or create the target MetaData entry** — confirm a
      `dbo.MetaData` row exists for (Equipment, Parameter, new location).
      If not, create it now and note the `Metadata_ID`.
- [ ] **Identify the active route** — run:

```sql
SELECT *
FROM   [dbo].[IngestionRoute]
WHERE  [Equipment_ID]     = <id>
  AND  [DataProvenance_ID]= 1          -- Sensor
  AND  [ProcessingDegree] = 'Raw'
  AND  [ValidTo]          IS NULL;
```

---

## During the Move (at timestamp D)

### Step 1 — Close the old IngestionRoute

```sql
UPDATE [dbo].[IngestionRoute]
SET    [ValidTo] = '<D>',
       [Notes]   = COALESCE([Notes], '') + ' | Closed: sensor moved to <new location> at <D>'
WHERE  [IngestionRoute_ID] = <id of active route>;
```

### Step 2 — Open a new IngestionRoute

```sql
INSERT INTO [dbo].[IngestionRoute]
    ([Equipment_ID], [Parameter_ID], [DataProvenance_ID],
     [ProcessingDegree], [ValidFrom], [ValidTo], [Metadata_ID], [Notes])
VALUES
    (<Equipment_ID>,
     <Parameter_ID>,
     1,           -- DataProvenance: Sensor
     'Raw',
     '<D>',
     NULL,        -- still active
     <new Metadata_ID>,
     'Sensor moved from <old location> to <new location> at <D>');
```

### Step 3 — Record the physical installation

```sql
-- Close the old installation
UPDATE [dbo].[EquipmentInstallation]
SET    [RemovedDate] = '<D>',
       [Notes]       = COALESCE([Notes], '') + ' | Removed for relocation'
WHERE  [Equipment_ID]       = <Equipment_ID>
  AND  [RemovedDate]        IS NULL;

-- Create the new installation
INSERT INTO [dbo].[EquipmentInstallation]
    ([Equipment_ID], [Sampling_point_ID], [InstalledDate], [Campaign_ID], [Notes])
VALUES
    (<Equipment_ID>,
     <new Sampling_point_ID>,
     '<D>',
     <Campaign_ID or NULL>,
     'Relocated from <old location>');
```

---

## After the Move

### Step 4 — Verify route resolution

Run the resolution query for a timestamp **before D** (should return
the old `Metadata_ID`):

```sql
SELECT [Metadata_ID]
FROM   [dbo].[IngestionRoute]
WHERE  [Equipment_ID]      = <id>
  AND  [Parameter_ID]      = <id>
  AND  [DataProvenance_ID] = 1
  AND  [ProcessingDegree]  = 'Raw'
  AND  [ValidFrom]        <= '<D - 1 hour>'
  AND  ([ValidTo] IS NULL OR [ValidTo] > '<D - 1 hour>');
-- Expected: old Metadata_ID
```

Run the same query for a timestamp **after D** (should return the new
`Metadata_ID`):

```sql
SELECT [Metadata_ID]
FROM   [dbo].[IngestionRoute]
WHERE  [Equipment_ID]      = <id>
  AND  [Parameter_ID]      = <id>
  AND  [DataProvenance_ID] = 1
  AND  [ProcessingDegree]  = 'Raw'
  AND  [ValidFrom]        <= '<D + 1 hour>'
  AND  ([ValidTo] IS NULL OR [ValidTo] > '<D + 1 hour>');
-- Expected: new Metadata_ID
```

### Step 5 — Confirm no overlapping active routes

```sql
SELECT COUNT(*) AS active_routes
FROM   [dbo].[IngestionRoute]
WHERE  [Equipment_ID]      = <id>
  AND  [Parameter_ID]      = <id>
  AND  [DataProvenance_ID] = 1
  AND  [ProcessingDegree]  = 'Raw'
  AND  [ValidFrom]        <= GETUTCDATE()
  AND  ([ValidTo] IS NULL OR [ValidTo] > GETUTCDATE());
-- Expected: exactly 1
```

### Step 6 — (Optional) Update any related annotations

If annotations (`dbo.Annotation`, Phase 2d+) reference the old
`Metadata_ID` and should be carried forward, update them or create
new annotations on the new `Metadata_ID`.

---

## Quick Reference

| Action | Table | Key columns |
|---|---|---|
| Close old route | `IngestionRoute` | Set `ValidTo = D` |
| Open new route | `IngestionRoute` | Set `ValidFrom = D`, `ValidTo = NULL` |
| Record removal | `EquipmentInstallation` | Set `RemovedDate = D` |
| Record deployment | `EquipmentInstallation` | New row, `InstalledDate = D` |

---

## See Also

- [Ingestion Routing](../architecture/ingestion_routing.md) — how
  route resolution works and how to troubleshoot.
- [Sensor Lifecycle](../architecture/sensor_lifecycle.md) — full
  equipment event and installation history model.
