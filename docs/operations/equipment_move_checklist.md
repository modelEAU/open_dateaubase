# Equipment Move Checklist

Use this checklist when physically relocating a sensor from one sampling
location to another. The Channel row for the sensor stream does **not** change —
the Channel captures the equipment-parameter relationship, which is invariant
regardless of physical location. Only the `EquipmentInstallation` record needs
to be updated.

---

## Before the Move

- [ ] **Identify the sensor** — `Equipment_ID` in `dbo.Equipment`.
- [ ] **Identify the current installation** — confirm the latest open row in
      `dbo.EquipmentInstallation` for this `Equipment_ID`:

```sql
SELECT *
FROM   [dbo].[EquipmentInstallation]
WHERE  [Equipment_ID] = <id>
  AND  [RemovedDate]  IS NULL;
```

- [ ] **Choose a move timestamp** — decide the exact datetime `D` when the
      sensor will be considered "at the new location". Use UTC.
- [ ] **Identify the new `Sampling_point_ID`** — confirm the destination location
      exists in `dbo.SamplingPoints`. Create it if needed.
- [ ] **Confirm the Channel row** — the existing Channel row for this stream
      remains valid after the move. No new Channel is needed.

```sql
SELECT [Channel_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree]
FROM   [dbo].[Channel]
WHERE  [Equipment_ID] = <id>;
```

---

## During the Move (at timestamp D)

### Step 1 — Close the old installation

```sql
UPDATE [dbo].[EquipmentInstallation]
SET    [RemovedDate] = '<D>',
       [Notes]       = COALESCE([Notes], '') + ' | Removed: relocated to <new location> at <D>'
WHERE  [Equipment_ID] = <Equipment_ID>
  AND  [RemovedDate]  IS NULL;
```

### Step 2 — Record the new installation

```sql
INSERT INTO [dbo].[EquipmentInstallation]
    ([Equipment_ID], [Sampling_point_ID], [InstalledDate], [Campaign_ID], [Notes])
VALUES
    (<Equipment_ID>,
     <new Sampling_point_ID>,
     '<D>',
     <Campaign_ID or NULL>,
     'Relocated from <old location>');
```

### Step 3 — (Optional) Log an equipment event

```sql
INSERT INTO [dbo].[EquipmentEvent]
    ([Equipment_ID], [EquipmentEventType_ID], [EventDateTimeStart],
     [PerformedByPerson_ID], [Campaign_ID], [Notes])
VALUES
    (<Equipment_ID>,
     5,          -- EquipmentEventType = Removal (at old site)
     '<D>',
     <Person_ID or NULL>,
     <Campaign_ID or NULL>,
     'Sensor moved from <old location> to <new location>');
```

---

## After the Move

### Step 4 — Verify location resolution

Run the location query for a timestamp **before D** (should return the old location):

```sql
SELECT ei.[Sampling_point_ID], sp.[Sampling_point], ei.[InstalledDate], ei.[RemovedDate]
FROM   [dbo].[EquipmentInstallation] ei
JOIN   [dbo].[SamplingPoints]        sp ON sp.[Sampling_point_ID] = ei.[Sampling_point_ID]
WHERE  ei.[Equipment_ID]  = <Equipment_ID>
  AND  ei.[InstalledDate] <= '<D - 1 hour>'
  AND  (ei.[RemovedDate]  IS NULL OR ei.[RemovedDate] > '<D - 1 hour>');
-- Expected: old Sampling_point_ID
```

Run the same query for a timestamp **after D** (should return the new location):

```sql
SELECT ei.[Sampling_point_ID], sp.[Sampling_point], ei.[InstalledDate], ei.[RemovedDate]
FROM   [dbo].[EquipmentInstallation] ei
JOIN   [dbo].[SamplingPoints]        sp ON sp.[Sampling_point_ID] = ei.[Sampling_point_ID]
WHERE  ei.[Equipment_ID]  = <Equipment_ID>
  AND  ei.[InstalledDate] <= '<D + 1 hour>'
  AND  (ei.[RemovedDate]  IS NULL OR ei.[RemovedDate] > '<D + 1 hour>');
-- Expected: new Sampling_point_ID
```

### Step 5 — Confirm no overlapping open installations

```sql
SELECT COUNT(*) AS open_installations
FROM   [dbo].[EquipmentInstallation]
WHERE  [Equipment_ID] = <Equipment_ID>
  AND  [RemovedDate]  IS NULL;
-- Expected: exactly 1
```

### Step 6 — (Optional) Update annotations

If annotations (`dbo.Annotation`) reference the old channel and should be extended or
carried forward, create new annotations on the same `Channel_ID` starting from `D`.

---

## Quick Reference

| Action | Table | Key columns |
| --- | --- | --- |
| Close old deployment | `EquipmentInstallation` | Set `RemovedDate = D` |
| Record new deployment | `EquipmentInstallation` | New row, `InstalledDate = D` |
| (Optional) log event | `EquipmentEvent` | `EquipmentEventType_ID = 5` (Removal) |

The `Channel` row is **not touched** during a sensor move.

---

## See Also

- [Self-Configuring Ingestion](../architecture/ingestion_routing.md) — how Channel
  rows work and how data routing is resolved.
- [Sensor Lifecycle](../architecture/sensor_lifecycle.md) — full equipment event and
  installation history model.
