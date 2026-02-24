# Processing Lineage (v1.6.0)

This document explains how open_dateaubase records **data transformation history** — the
chain of processing steps that transform raw sensor measurements into cleaned, validated,
or aggregated time series.

---

## Why lineage?

Every `Channel` row represents a *fixed-identity* measurement stream: same equipment,
parameter, and processing degree. When a processing algorithm (outlier removal,
interpolation, aggregation, …) is applied to a raw series, the result is stored under a
**new** `Channel` row — not an update of the original.

The lineage tables record the relationship between those `Channel` rows and the steps
that transformed them, so users can always trace:

- **Forward**: "What was this raw series processed into?"
- **Backward**: "Where did this cleaned series come from?"
- **Full chain**: "Show the entire provenance from first measurement to final product."

---

## Tables (v1.6.0)

### `dbo.ProcessingStep`

One row per transformation applied.

| Column | Type | Notes |
| --- | --- | --- |
| `ProcessingStep_ID` | `INT IDENTITY` | PK |
| `Name` | `NVARCHAR(200)` | Human-readable label |
| `Description` | `NVARCHAR(2000)` | Free text |
| `MethodName` | `NVARCHAR(200)` | Machine-readable (e.g. `'outlier_removal'`) |
| `MethodVersion` | `NVARCHAR(100)` | Library version (e.g. `'meteaudata 0.5.1'`) |
| `ProcessingType` | `NVARCHAR(100)` | String from metEAUdata's `ProcessingType` enum |
| `Parameters` | `NVARCHAR(MAX)` | JSON blob of method parameters |
| `ExecutedAt` | `DATETIME2(7)` | UTC timestamp of execution |
| `ExecutedByPerson_ID` | `INT` | FK → `Person`; NULL for automated runs |

`ProcessingType` is stored as a plain string (e.g. `'Smoothing'`, `'Filtering'`,
`'GapFilling'`) mirroring metEAUdata's `ProcessingType` enum. **No lookup table is
needed** — the enum in the Python library is the source of truth. Adding a new processing
type requires no schema migration, just a new enum value in metEAUdata.

### `dbo.DataLineage`

One row per (step, channel, role) triple.

| Column | Type | Notes |
| --- | --- | --- |
| `DataLineage_ID` | `INT IDENTITY` | PK |
| `ProcessingStep_ID` | `INT` | FK → `ProcessingStep` |
| `Channel_ID` | `INT` | FK → `Channel` |
| `Role` | `NVARCHAR(10)` | `'Input'` or `'Output'` — CHECK constraint |

### `dbo.Channel.ProcessingDegree`

Denormalized shortcut for fast filtering. Controlled vocabulary: `Raw`, `Cleaned`,
`Calibrated`, `Validated`, `Filtered`, `Predicted`.

- Set **once** at row creation; never updated.
- Ground truth is the `DataLineage` graph.

---

## Example: outlier removal on a TSS series

```sql
-- Raw TSS channel already exists: Channel_ID = 10

-- After processing, a new Channel row is created for the cleaned output: Channel_ID = 11

-- What was inserted into DataLineage:
-- Role='Input'  → Channel_ID=10 (raw)
-- Role='Output' → Channel_ID=11 (cleaned)
SELECT * FROM [dbo].[DataLineage]
WHERE [ProcessingStep_ID] = (SELECT MAX([ProcessingStep_ID]) FROM [dbo].[ProcessingStep]);
```

---

## Python API

### "What was this raw series processed into?"

```python
from open_dateaubase.lineage import get_lineage_forward

results = get_lineage_forward(channel_id=10, conn=conn)
for r in results:
    print(r["processing_step"]["MethodName"], "→", r["output_channel_ids"])
# outlier_removal → [11]
```

### "Where did this cleaned series come from?"

```python
from open_dateaubase.lineage import get_lineage_backward

results = get_lineage_backward(channel_id=11, conn=conn)
for r in results:
    print(r["processing_step"]["MethodName"], "consumed", r["input_channel_ids"])
# outlier_removal consumed [10]
```

### "Show the full chain from raw to final"

```python
from open_dateaubase.lineage import get_full_lineage_tree

tree = get_full_lineage_tree(channel_id=11, conn=conn)
# tree['parents'] → ancestors (recursive CTE goes up to the raw root)
# tree['children'] → descendants (steps applied downstream)
```

### "Show all processing levels of a time series"

```python
from open_dateaubase.lineage import get_all_processing_degrees
from datetime import datetime

versions = get_all_processing_degrees(
    equipment_id=7,
    parameter_id=3,
    from_dt=datetime(2025, 1, 1),
    to_dt=datetime(2025, 12, 31),
    conn=conn,
)
for v in versions:
    print(v["processing_degree"], "→ Channel_ID", v["channel_id"],
          "(", v["value_count"], "values)")
# Raw        → Channel_ID 10 (8640 values)
# Cleaned    → Channel_ID 11 (8600 values)
# Validated  → Channel_ID 12 (8600 values)
```

---

## How metEAUdata writes lineage automatically

```python
import pyodbc
from meteaudata.storage.adapters.open_dateaubase_adapter import OpenDateaubaseAdapter

conn = pyodbc.connect("DRIVER=...;SERVER=...;DATABASE=open_dateaubase;...")
adapter = OpenDateaubaseAdapter(conn)

# Load provenance from DB
prov = adapter.get_provenance(channel_id=10)

# Process the signal (metEAUdata records steps internally)
signal = ...  # your Signal with processing_steps history

# Write lineage back to DB in one call
adapter.write_lineage(
    signal=signal,
    source_channel_ids=[10],   # raw inputs
    output_channel_id=11,      # cleaned output (must already exist in Channel)
)
```

Internally `write_lineage` calls `open_dateaubase.meteaudata_bridge.record_processing`
for each `ProcessingStep` in `signal.processing_steps`.

---

## ProcessingDegree value set

| Value | Meaning |
| --- | --- |
| `Raw` | Unprocessed data as received from the sensor |
| `Cleaned` | Outliers removed or obvious errors corrected |
| `Calibrated` | Calibration applied |
| `Validated` | Range and consistency checks passed |
| `Filtered` | Smoothed or frequency-filtered |
| `Predicted` | Computed/predicted by a model |

---

## Adding a new ProcessingType

Because `ProcessingType` is stored as a plain string, no schema migration is needed:

1. Add the new value to metEAUdata's `ProcessingType` enum.
2. Use the new enum value in your processing code.
3. The new string appears automatically in `dbo.ProcessingStep.ProcessingType`.

---

## Immutability of Channel rows

`Channel.ProcessingDegree` is written **once** at row creation and is never updated. A
`Channel` row represents a fixed-identity stream; if the processing degree changes, a new
`Channel` row is created and the lineage graph records the relationship. This design
ensures that `Channel` rows are immutable audit records.
