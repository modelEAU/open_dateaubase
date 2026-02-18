# Processing Lineage (Phase 3, v1.6.0)

This document explains how open_dateaubase records **data transformation history** — the chain of processing steps that transform raw sensor or lab measurements into cleaned, validated, or aggregated time series.

---

## Why lineage?

Every `MetaData` row represents a *fixed-context* time series: same location, equipment, parameter, and processing level.  When a processing algorithm (outlier removal, interpolation, aggregation, …) is applied to a raw series, the result is stored under a **new** `MetaData` row — not an update of the original.

The lineage tables record the relationship between those `MetaData` rows and the steps that transformed them, so users can always trace:

- **Forward**: "What was this raw series processed into?"
- **Backward**: "Where did this cleaned series come from?"
- **Full chain**: "Show the entire provenance from first measurement to final product."

---

## New tables (v1.6.0)

### `dbo.ProcessingStep`

One row per transformation applied.

| Column | Type | Notes |
|---|---|---|
| `ProcessingStep_ID` | `INT IDENTITY` | PK |
| `Name` | `NVARCHAR(200)` | Human-readable label |
| `Description` | `NVARCHAR(2000)` | Free text |
| `MethodName` | `NVARCHAR(200)` | Machine-readable (e.g. `'outlier_removal'`) |
| `MethodVersion` | `NVARCHAR(100)` | Library version (e.g. `'meteaudata 0.5.1'`) |
| `ProcessingType` | `NVARCHAR(100)` | String from metEAUdata's `ProcessingType` enum |
| `Parameters` | `NVARCHAR(MAX)` | JSON blob of method parameters |
| `ExecutedAt` | `DATETIME2(7)` | UTC timestamp of execution |
| `ExecutedByPerson_ID` | `INT` | FK → `Person`; NULL for automated runs |

`ProcessingType` is stored as a plain string (e.g. `'Smoothing'`, `'Filtering'`, `'GapFilling'`) mirroring metEAUdata's `ProcessingType` enum.  **No lookup table is needed** — the enum in the Python library is the source of truth.  Adding a new processing type requires no schema migration, just a new enum value in metEAUdata.

### `dbo.DataLineage`

One row per (step, metadata, role) triple.

| Column | Type | Notes |
|---|---|---|
| `DataLineage_ID` | `INT IDENTITY` | PK |
| `ProcessingStep_ID` | `INT` | FK → `ProcessingStep` |
| `Metadata_ID` | `INT` | FK → `MetaData` |
| `Role` | `NVARCHAR(10)` | `'Input'` or `'Output'` — CHECK constraint |

### `dbo.MetaData.ProcessingDegree` (new column)

Denormalized shortcut for fast filtering.  Allowed values: `Raw`, `Cleaned`, `Validated`, `Interpolated`, `Aggregated`.

- Set **once** at row creation; never updated.
- Ground truth is the `DataLineage` graph.
- All rows existing before v1.6.0 are backfilled to `'Raw'`.

---

## Example: outlier removal on a TSS series

```sql
-- Step 1: raw TSS series already exists
-- MetaData row for raw TSS → Metadata_ID = 10

-- Step 2: run outlier removal in Python (via open_dateaubase.meteaudata_bridge):
-- record_processing(
--     source_metadata_ids=[10],
--     method_name='outlier_removal',
--     method_version='meteaudata 0.5.1',
--     processing_type='Filtering',
--     parameters={'window': 5, 'threshold': 3.0},
--     executed_at='2025-06-01T10:00:00',
--     output_metadata_id=11,   -- newly created MetaData row for cleaned TSS
--     conn=conn,
-- )

-- What was inserted:
SELECT * FROM dbo.ProcessingStep WHERE ProcessingStep_ID = (SELECT MAX(ProcessingStep_ID) FROM dbo.ProcessingStep);
SELECT * FROM dbo.DataLineage   WHERE ProcessingStep_ID = (SELECT MAX(ProcessingStep_ID) FROM dbo.ProcessingStep);
-- Role='Input'  → Metadata_ID=10 (raw)
-- Role='Output' → Metadata_ID=11 (cleaned)
```

---

## Example queries

### "What was this raw series processed into?"

```python
from open_dateaubase.lineage import get_lineage_forward

results = get_lineage_forward(metadata_id=10, conn=conn)
for r in results:
    print(r["processing_step"]["MethodName"], "→", r["output_metadata_ids"])
# outlier_removal → [11]
```

### "Where did this cleaned series come from?"

```python
from open_dateaubase.lineage import get_lineage_backward

results = get_lineage_backward(metadata_id=11, conn=conn)
for r in results:
    print(r["processing_step"]["MethodName"], "consumed", r["input_metadata_ids"])
# outlier_removal consumed [10]
```

### "Show the full chain from raw to final"

```python
from open_dateaubase.lineage import get_full_lineage_tree

tree = get_full_lineage_tree(metadata_id=11, conn=conn)
# tree['parents'] → ancestors (recursive CTE goes up to the raw root)
# tree['children'] → descendants (steps applied downstream)
```

### "Show all processing levels of a time series"

```python
from open_dateaubase.lineage import get_all_processing_degrees
from datetime import datetime

versions = get_all_processing_degrees(
    sampling_point_id=5,
    parameter_id=3,
    from_dt=datetime(2025, 1, 1),
    to_dt=datetime(2025, 12, 31),
    conn=conn,
)
for v in versions:
    print(v["processing_degree"], "→ Metadata_ID", v["metadata_id"],
          "(", v["value_count"], "values)")
# Raw        → Metadata_ID 10 (8640 values)
# Cleaned    → Metadata_ID 11 (8600 values)
# Validated  → Metadata_ID 12 (8600 values)
```

---

## How metEAUdata writes lineage automatically

When using the `OpenDateaubaseAdapter`, lineage is recorded automatically after processing:

```python
import pyodbc
from meteaudata.storage.adapters.open_dateaubase_adapter import OpenDateaubaseAdapter

conn = pyodbc.connect("DRIVER=...;SERVER=...;DATABASE=open_dateaubase;...")
adapter = OpenDateaubaseAdapter(conn)

# Load provenance from DB — no manual metadata_id strings needed
prov = adapter.get_provenance(metadata_id=10)

# Process the signal (metEAUdata records steps internally)
signal = ...  # your Signal with processing_steps history

# Write lineage back to DB in one call
adapter.write_lineage(
    signal=signal,
    source_metadata_ids=[10],     # raw inputs
    output_metadata_id=11,        # cleaned output (must already exist in MetaData)
)
```

Internally `write_lineage` calls `open_dateaubase.meteaudata_bridge.record_processing` for each `ProcessingStep` in `signal.processing_steps`.

The manual approach still works:

```python
from meteaudata.types import DataProvenance
prov = DataProvenance(metadata_id="10", parameter="TSS", location="Primary Effluent")
```

Both approaches coexist.

---

## ProcessingDegree value set

| Value | Meaning |
|---|---|
| `Raw` | Unprocessed data as received from the sensor or lab |
| `Cleaned` | Outliers removed or obvious errors corrected |
| `Validated` | Range and consistency checks passed |
| `Interpolated` | Gaps filled by interpolation |
| `Aggregated` | Resampled to a coarser time resolution |

---

## Adding a new ProcessingType

Because `ProcessingType` is stored as a plain string, no schema migration is needed:

1. Add the new value to metEAUdata's `ProcessingType` enum.
2. Use the new enum value in your processing code.
3. The new string appears automatically in `dbo.ProcessingStep.ProcessingType`.

No migration file, no value-set table update, no DBA intervention.

---

## Immutability of MetaData rows

`MetaData.ProcessingDegree` is written **once** at row creation and is never updated.  A `MetaData` row represents a fixed-context time series; if the processing degree changes, a new `MetaData` row is created and the lineage graph records the relationship.  This design ensures that `MetaData` rows are immutable audit records.
