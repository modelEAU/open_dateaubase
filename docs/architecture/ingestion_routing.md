# Ingestion Routing and Channel Resolution

## Overview

A **Channel** is the invariant descriptor for a single measurement stream. It captures
*which signal port is measuring which parameter*, at what processing degree and data
provenance. Physical context that changes over time — where the sensor is deployed, which
campaign it belongs to — is stored in separate temporal history tables and resolved at
query time by joining on the observation timestamp.

Because the Channel identity is enforced by a `UNIQUE` constraint, ingestion uses a
find-or-create pattern: the same `Channel_ID` is reused for every timestamp from the same
stream, regardless of where the sensor moves or which campaign is active.

---

## The UNIQUE Constraint (v3.0.0)

```sql
-- On dbo.Channel
CONSTRAINT [UQ_Channel_SignalStream]
UNIQUE ([SignalPort_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID])
WHERE [Parameter_ID] IS NOT NULL
```

The four columns together define a stream:

| Column | Meaning |
| --- | --- |
| `SignalPort_ID` | Which physical port on which DAS is producing the signal |
| `Parameter_ID` | What is being measured (TSS, pH, Turbidity, …) |
| `DataProvenance_ID` | Origin of the data (Sensor=1, Laboratory=2, Manual=3, …) |
| `ProcessingDegree_ID` | How processed is the value (Raw=1, Calibrated=2, …) |

This is implemented in `api/v1/repositories/ingestion_repository.py:find_or_create_sensor_metadata()`.

---

## Ingest-Time Resolution Chain

When the importer calls any ingest endpoint, the following lookup chain executes in
order. Steps 1–2 are **hard failures** (HTTP 422, no DB writes). Steps 3–6 are
**auto-creates with logged warnings**.

```
Import config field       Lookup target                        Behaviour if absent
─────────────────         ────────────────────────────────     ──────────────────────────────
parameter_name        →   dbo.Parameter (by name)              HARD FAIL — 422, no write
unit_name             →   dbo.Unit (by name)                    HARD FAIL — 422, no write
das_name              →   dbo.DataAcquisitionSystem (by Name)   auto-create bare row ⚠
tag (tagged mode)     →   dbo.SignalPort (by DAS_ID + Tag)      auto-create bare row ⚠
equipment_name        →   dbo.Equipment (by Identifier)         auto-create bare row ⚠
  (tagless mode)            [new port only] → opens
                            SignalPortEquipmentHistory            auto-create + history row ✓

Then:
(SignalPort_ID, Parameter_ID,
 DataProvenance_ID,
 ProcessingDegree_ID)     →   dbo.Channel                       find-or-create ✓

Channel_ID                →   dbo.Observation                   insert
Observation_ID            →   dbo.Value / ValueVector /
                               ValueMatrix / ValueImage          insert
```

### Tagged vs. tagless behaviour difference

| Auto-created on first import | Tagged mode | Tagless mode |
| --- | --- | --- |
| `DataAcquisitionSystem` | yes (bare) | yes (bare) |
| `SignalPort` | yes (bare) | yes (bare) |
| `SignalPortEquipmentHistory` | **NO** — equipment not known from tag alone | yes — opened at `SYSUTCDATETIME()` |
| `SignalPortLocationHistory` | **NO** | **NO** |
| `Channel` | yes | yes |

Tagged ports have **no equipment provenance** recorded automatically. A tagged port such
as `13230077_10_0x0100_spectro::lyser_INFLUENTV160` identifies the data stream by the
DAS tag name alone; you must manually register the equipment via
`temporal_history_repository.register_equipment_at_port()` or the campaign wizard.

---

## Query-Time Location Resolution

An `Observation` row has no direct FK to `Site`, `SamplingPoint`, or `Campaign`. To
answer "where was this measurement made?", join through the `SignalPort` temporal history
tables at the observation timestamp:

```sql
-- Where was channel 42 measuring at timestamp @T?
SELECT
    sp.[Name]        AS SamplingPoint,
    si.[Name]        AS Site
FROM [dbo].[Observation] o
JOIN [dbo].[Channel]                     c   ON c.[Channel_ID]    = o.[Channel_ID]
JOIN [dbo].[SignalPort]                  port ON port.[SignalPort_ID] = c.[SignalPort_ID]
-- Location history: which SamplingPoint was the port deployed at?
LEFT JOIN [dbo].[SignalPortLocationHistory] lh
    ON  lh.[SignalPort_ID] = port.[SignalPort_ID]
    AND lh.[StartTime]    <= o.[Timestamp]
    AND (lh.[EndTime] IS NULL OR lh.[EndTime] > o.[Timestamp])
LEFT JOIN [dbo].[SamplingPoint]          sp  ON sp.[SamplingPoint_ID] = lh.[SamplingPoint_ID]
LEFT JOIN [dbo].[Site]                   si  ON si.[Site_ID]          = sp.[Site_ID]
WHERE o.[Channel_ID] = 42 AND o.[Timestamp] = @T;
```

To find which campaign was active, join through equipment:

```sql
-- Which campaign owned this measurement?
SELECT camp.[Name] AS Campaign
FROM [dbo].[Observation]              o
JOIN [dbo].[Channel]                  c    ON c.[Channel_ID]     = o.[Channel_ID]
JOIN [dbo].[SignalPort]               port ON port.[SignalPort_ID] = c.[SignalPort_ID]
-- Equipment history: which Equipment was on this port?
JOIN [dbo].[SignalPortEquipmentHistory] peh
    ON  peh.[SignalPort_ID] = port.[SignalPort_ID]
    AND peh.[StartTime]    <= o.[Timestamp]
    AND (peh.[EndTime] IS NULL OR peh.[EndTime] > o.[Timestamp])
-- Campaign membership via equipment
JOIN [dbo].[CampaignEquipment]        ce   ON ce.[Equipment_ID]  = peh.[Equipment_ID]
JOIN [dbo].[Campaign]                 camp ON camp.[Campaign_ID] = ce.[Campaign_ID]
WHERE o.[Channel_ID] = 42 AND o.[Timestamp] = @T;
```

If `SignalPortLocationHistory` has no row covering the timestamp, the location columns
return `NULL` — the observation is **locationless** (an orphan for query purposes).

---

## Pre-Import Checklist

The importer only hard-fails on missing `Parameter` and `Unit` rows. Everything else
silently succeeds with bare, contextless rows. To ensure imported data is queryable with
full context, complete these steps **before** running the importer.

### Step 1 — Vocabulary (hard prerequisites)

These must exist or the importer aborts with HTTP 422:

- **Unit** rows for every `unit_name` used in the config (e.g. `mg/L`, `NTU`, `AU`, `-`)
- **Parameter** rows for every `parameter_name` used in the config

Seeded by `sql/seed_importer_fixtures.sql` for the standard test instruments.

### Step 2 — Equipment (soft prerequisite)

The importer resolves equipment by **Identifier** string match (tagless mode only).
If an `Equipment` row with that identifier exists, it is found. If not, a bare row is
auto-created with only `Identifier` set — no `EquipmentModel_ID`, no serial number,
no owner.

**You must pre-seed Equipment rows** (with a proper `EquipmentModel_ID` FK) before
running the importer if you want meaningful equipment metadata attached to the data.

Seeded by `sql/seed_importer_fixtures.sql` for the standard test instruments.

### Step 3 — DataAcquisitionSystem (soft prerequisite)

The importer resolves DAS by `das_name`. If no matching `DataAcquisitionSystem` row
exists, one is auto-created with only `Name` set — `SystemType` and `Description` will
be `NULL`.

**You must pre-seed DAS rows** (with `SystemType`, `Description`) for import data to
carry meaningful system metadata. This is **not currently done** in the seed files for
importer DAS names (`rodtox_das`, `basestation_das`, `basestation`, `felinoscope_das`,
`pilEAUte_das`).

### Step 4 — Site and SamplingPoint (orphan prevention)

The importer never creates `Site` or `SamplingPoint` rows. Without them, every imported
observation is permanently locationless — `SignalPortLocationHistory` will have no
matching row and location joins return `NULL`.

**Create these before or immediately after first import:**

1. Create the `Site` (via UI or SQL)
2. Create one or more `SamplingPoint` rows at that site
3. After the SignalPorts exist (see Step 5), open a `SignalPortLocationHistory` row:

```sql
INSERT INTO [dbo].[SignalPortLocationHistory]
    ([SignalPort_ID], [SamplingPoint_ID], [StartTime])
VALUES
    (@port_id, @sampling_point_id, @deployment_start_datetime);
```

The campaign wizard is the intended entry point for this step: when you assign equipment
to a campaign at a sampling point, the wizard should open a `SignalPortLocationHistory`
row for each port linked to that equipment.

### Step 5 — SignalPorts (chicken-and-egg)

`SignalPortLocationHistory` requires a `SignalPort_ID` to exist. But SignalPorts are
auto-created on the **first import run**. This creates an ordering problem:

**Option A — run import first, then set location:**

1. Run the importer once. SignalPorts are auto-created.
2. Note the generated `SignalPort_ID` values.
3. Insert `SignalPortLocationHistory` rows with the correct `StartTime` (the actual
   deployment date, not the import date).

**Option B — pre-seed SignalPorts:**

1. Insert `DataAcquisitionSystem` and `SignalPort` rows in the seed SQL.
2. Insert `SignalPortLocationHistory` rows immediately.
3. Run the importer — it will find the existing SignalPorts and reuse them.

Option B is preferable for repeatable test environments (re-running
`docker compose down -v && docker compose up --build` always produces consistent state).
This is the approach taken in the revised seed data.

### Step 6 — Campaign and CampaignEquipment (context)

Without these, imported observations have no scientific/operational context. They are
valid data but not associated with any study or operation.

1. Create a `Campaign` row with the correct `CampaignType_ID`, `Site_ID`, and start date.
2. Insert `CampaignEquipment` rows linking each equipment to the campaign.

The campaign wizard is the correct entry point. Equipment added through the wizard should
automatically create `CampaignEquipment` rows.

---

## Summary Table

| Entity | Hard fail if missing? | Auto-created? | What's missing if auto-created |
| --- | --- | --- | --- |
| `Parameter` | **Yes (422)** | No | Import aborts |
| `Unit` | **Yes (422)** | No | Import aborts |
| `Equipment` | No | **Yes** (bare) | No `EquipmentModel_ID`, owner, serial |
| `DataAcquisitionSystem` | No | **Yes** (bare) | No `SystemType`, `Description` |
| `SignalPort` | No | **Yes** (bare) | No `Description` |
| `SignalPortEquipmentHistory` | No | Tagless only | Tagged channels have no equipment provenance |
| `SignalPortLocationHistory` | No | **Never** | All observations are locationless |
| `Campaign` / `CampaignEquipment` | No | **Never** | No campaign context for any data |

---

## Equipment Moves and Sensor Relocation

When a sensor moves from one sampling point to another, the **Channel row does not
change**. Only the `SignalPortLocationHistory` row is updated:

```
temporal_history_repository.relocate_sensor(
    conn, signal_port_id, new_sampling_point_id, move_time
)
```

This closes the old history row (`EndTime = move_time`) and opens a new one
(`StartTime = move_time`). Observations before the move timestamp resolve to the old
location; observations after resolve to the new one. See
[Sensor Relocation SOP](../operations/sensor-relocation-sop.md) for the full procedure.

---

## ProcessingDegree Vocabulary

| ID | Name | Meaning |
| --- | --- | --- |
| 1 | Raw | Data as received from the instrument |
| 2 | Cleaned | Outliers or artefacts removed |
| 3 | Calibrated | Calibration applied |
| 4 | Validated | Human-reviewed and accepted |
| 5 | Filtered | Smoothed or frequency-filtered |
| 6 | Predicted | Computed/predicted by a model |

---

## Relationship Diagram

```
DataAcquisitionSystem
    │
    └─► SignalPort ──────────────────────────────────────────────┐
              │                                                  │
              ├─► SignalPortEquipmentHistory → Equipment         │
              │       (at timestamp T)          → EquipmentModel │
              │                                 → CampaignEquipment → Campaign
              │                                                  │
              └─► SignalPortLocationHistory → SamplingPoint      │
                      (at timestamp T)       → Site              │
                                             → Watershed         │
                                                                 │
    Channel (SignalPort_ID + Parameter_ID + Provenance + Degree)─┘
        │
        └─► Observation (Timestamp)
                │
                └─► Value / ValueVector / ValueMatrix / ValueImage
```
