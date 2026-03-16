# Inserting Data: Step-by-Step Walkthroughs

This page explains how to add measurement data to open_datEAUbase for each value type
the schema supports. It is written for practitioners who already understand the domain
but are new to the schema.

---

## The central idea: Channel as a stream descriptor

Every sensor measurement series is described by **one row in `dbo.Channel`**.
That row is not a measurement — it identifies the invariant *stream*: which equipment
is measuring which parameter, with what processing degree and in what unit.

The `ValueType_ID` column on the Channel row determines which storage table holds the
actual values:

| ValueType_ID | Name | Storage table | When to use |
| --- | --- | --- | --- |
| 1 | Scalar | `dbo.Value` | One number per timestamp (pH, TSS, temperature, …) |
| 2 | Vector | `dbo.ValueVector` | A 1-D distribution over a physical axis (spectrum, PSD, …) |
| 3 | Matrix | `dbo.ValueMatrix` | A 2-D joint distribution over two physical axes (size × velocity, …) |
| 4 | Image | `dbo.ValueImage` | A camera or microscope frame stored as a file reference |

A Channel row is created **automatically on first ingest** via the self-configuring
find-or-create pattern — no manual setup required. See
[Self-Configuring Ingestion](../architecture/ingestion_routing.md) for details.

Lab measurements (discrete sample results) do **not** use the Channel model.
See [Lab Data](../architecture/lab_data.md).

---

## Prerequisites (all types)

Before inserting any values, the following lookup rows must exist. Most are set up once
per deployment and reused across many series.

| Table | What it holds | Example |
| --- | --- | --- |
| `dbo.Watershed` | Drainage area | "Rivière Saint-Charles" |
| `dbo.Site` | Physical installation site | "WWTP Est Inlet" |
| `dbo.SamplingPoints` | Specific measurement location at a site | "WWTP-IN-01" |
| `dbo.Parameter` | The quantity being measured | "TSS", "Absorbance" |
| `dbo.Unit` | Measurement unit | "mg/L", "nm", "m/s" |
| `dbo.EquipmentModel` | Instrument make/model | "ISCO 6712 autosampler" |
| `dbo.Equipment` | Specific instrument serial number | "ISCO-001" |
| `dbo.Person` | Person responsible for data | "M. Tremblay" |
| `dbo.DataProvenance` | How data was produced | Sensor (1), Lab (2), Manual (3) |

These are populated with plain `INSERT` statements and are independent of value type.
The `EquipmentInstallation` table is also populated to record where the equipment is
physically deployed (see [Sensor Lifecycle](../architecture/sensor_lifecycle.md)).

---

## Walk-through 1 — Scalar data from a sensor (via API)

**Scenario:** A TSS probe at WWTP-IN-01 reports one mg/L reading every 15 minutes.

### Using the API (recommended)

```bash
POST /api/v1/ingest/sensor
```

```json
{
  "equipment_id": 1,
  "parameter_id": 1,
  "unit_id": 1,
  "data_provenance_id": 1,
  "processing_degree": "Raw",
  "timestamps": [
    "2025-09-10T10:00:00Z",
    "2025-09-10T10:15:00Z",
    "2025-09-10T10:30:00Z"
  ],
  "values": [185.0, 192.3, 178.9]
}
```

Response includes the `channel_id` that was found or created.

On first call for this `(equipment_id, parameter_id, data_provenance_id,
processing_degree)` combination, a new `Channel` row is created automatically. All
subsequent calls for the same stream reuse that `Channel_ID`.

### Directly via SQL (v2.2.0 - Observation Hub Pattern)

```sql
-- Step 1: find or create the Channel row
IF NOT EXISTS (
    SELECT 1 FROM [dbo].[Channel]
    WHERE [Equipment_ID] = 1 AND [Parameter_ID] = 1
      AND [DataProvenance_ID] = 1 AND [ProcessingDegree_ID] = 1
)
INSERT INTO [dbo].[Channel]
    ([Equipment_ID], [Parameter_ID], [DataProvenance_ID],
     [ProcessingDegree_ID], [ValueType_ID])
VALUES (1, 1, 1, 1, 1);  -- ValueType_ID = 1 = Scalar

DECLARE @channel_id INT;
SELECT @channel_id = [Channel_ID] FROM [dbo].[Channel]
WHERE [Equipment_ID] = 1 AND [Parameter_ID] = 1
  AND [DataProvenance_ID] = 1 AND [ProcessingDegree_ID] = 1;

-- Step 2: insert observations and values
-- Each measurement requires an Observation row first, then a Value row
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
VALUES (@channel_id, '2025-09-10T10:00:00.0000000', 'Scalar');
INSERT INTO [dbo].[Value] ([Observation_ID], [Value])
VALUES (SCOPE_IDENTITY(), 185.0);

INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
VALUES (@channel_id, '2025-09-10T10:15:00.0000000', 'Scalar');
INSERT INTO [dbo].[Value] ([Observation_ID], [Value])
VALUES (SCOPE_IDENTITY(), 192.3);

INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
VALUES (@channel_id, '2025-09-10T10:30:00.0000000', 'Scalar');
INSERT INTO [dbo].[Value] ([Observation_ID], [Value])
VALUES (SCOPE_IDENTITY(), 178.9);
```

### Retrieve the data

```sql
SELECT v.[Value], o.[Timestamp]
FROM   [dbo].[Value] v
JOIN   [dbo].[Observation] o ON v.[Observation_ID] = o.[Observation_ID]
WHERE  o.[Channel_ID] = @channel_id
ORDER BY o.[Timestamp];
```

---

## Walk-through 2 — Spectrum data from a UV-Vis spectrometer

**Scenario:** A S::CAN spectro::lyser at WWTP-IN-01 measures UV-Vis absorbance
across wavelengths 200–750 nm, sampled into 7 wavelength bands.
It produces one full spectrum every 15 minutes.

The key difference from Scalar: you have **an ordered set of values per timestamp**,
each associated with a specific wavelength band. The schema stores this using:

- `ValueBinningAxis` — defines the physical axis (name and unit)
- `ValueBin` — defines each band: a `[LowerBound, UpperBound)` half-open interval
- `ChannelAxis` — links the Channel series to its axis (1 row for Vector)
- `ValueVector` — stores the actual values (one row per bin per timestamp)

### Step 1: Create the binning axis

```sql
-- The "nm" unit (Unit_ID = 6) must already exist in dbo.Unit.
INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID])
VALUES ('UV-Vis 200-750nm', 'S::CAN spectro::lyser wavelength axis', 7, 6);
-- Returns ValueBinningAxis_ID = 1
```

### Step 2: Define the bins

```sql
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES
    (1, 0,  200,  300),
    (1, 1,  300,  350),
    (1, 2,  350,  400),
    (1, 3,  400,  450),
    (1, 4,  450,  500),
    (1, 5,  500,  600),
    (1, 6,  600,  750);
```

The center wavelength of any bin is computed on read: `(LowerBound + UpperBound) / 2.0`.

### Step 3: Find or create the Channel row

```sql
-- ValueType_ID = 2 = Vector
IF NOT EXISTS (
    SELECT 1 FROM [dbo].[Channel]
    WHERE [Equipment_ID] = 2 AND [Parameter_ID] = 5
      AND [DataProvenance_ID] = 1 AND [ProcessingDegree] = 'Raw'
)
INSERT INTO [dbo].[Channel]
    ([Equipment_ID], [Parameter_ID], [Unit_ID], [DataProvenance_ID],
     [ProcessingDegree], [ValueType_ID])
VALUES (2, 5, 7, 1, 'Raw', 2);

DECLARE @channel_id INT;
SELECT @channel_id = [Channel_ID] FROM [dbo].[Channel]
WHERE [Equipment_ID] = 2 AND [Parameter_ID] = 5
  AND [DataProvenance_ID] = 1 AND [ProcessingDegree] = 'Raw';
```

### Step 4: Link the axis to the Channel

`ChannelAxis` is the junction between a Channel series and its physical axis.
`AxisRole = 0` means "the single axis" for a Vector.

```sql
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID], [AxisRole], [ValueBinningAxis_ID])
VALUES (@channel_id, 0, 1);
```

### Step 5: Insert the spectral measurements (v2.2.0)

```sql
-- First, create the Observation for this timestamp
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
VALUES (@channel_id, '2025-09-10T10:00:00.0000000', 'Vector');
DECLARE @obs_id BIGINT = SCOPE_IDENTITY();

-- Then insert the vector values using the Observation_ID
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value])
VALUES
    (@obs_id, 1, 0.142),
    (@obs_id, 2, 0.287),
    (@obs_id, 3, 0.531),
    (@obs_id, 4, 0.612),
    (@obs_id, 5, 0.489),
    (@obs_id, 6, 0.334),
    (@obs_id, 7, 0.201);
```

### Retrieve a spectrum

```sql
SELECT
    vb.[BinIndex],
    (vb.[LowerBound] + vb.[UpperBound]) / 2.0  AS wavelength_nm,
    vv.[Value]                                  AS absorbance
FROM   [dbo].[ValueVector] vv
JOIN   [dbo].[Observation] o  ON vv.[Observation_ID] = o.[Observation_ID]
JOIN   [dbo].[ValueBin]    vb ON vv.[ValueBin_ID]    = vb.[ValueBin_ID]
WHERE  o.[Channel_ID] = @channel_id
  AND  o.[Timestamp]  = '2025-09-10T10:00:00.0000000'
ORDER BY vb.[BinIndex];
```

---

## Walk-through 3 — Image data from a camera or microscope

**Scenario:** A camera captures JPEG images at the start of each rain event. Images are
stored in object storage; the database stores frame metadata and a pointer to the file.

### Step 1: Find or create the Channel row

```sql
-- ValueType_ID = 4 = Image
IF NOT EXISTS (
    SELECT 1 FROM [dbo].[Channel]
    WHERE [Equipment_ID] = 3 AND [Parameter_ID] = 9
      AND [DataProvenance_ID] = 1 AND [ProcessingDegree] = 'Raw'
)
INSERT INTO [dbo].[Channel]
    ([Equipment_ID], [Parameter_ID], [Unit_ID], [DataProvenance_ID],
     [ProcessingDegree], [ValueType_ID])
VALUES (3, 9, NULL, 1, 'Raw', 4);

DECLARE @channel_id INT;
SELECT @channel_id = [Channel_ID] FROM [dbo].[Channel]
WHERE [Equipment_ID] = 3 AND [Parameter_ID] = 9
  AND [DataProvenance_ID] = 1 AND [ProcessingDegree] = 'Raw';
```

No `ChannelAxis` row is needed — images do not use a binning axis.

### Step 2: Insert the image record (v2.2.0)

```sql
-- First, create the Observation for this image
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
VALUES (@channel_id, '2025-09-10T14:32:00.0000000', 'Image');

-- Then insert the image metadata using the Observation_ID
INSERT INTO [dbo].[ValueImage]
    ([Observation_ID], [ImageWidth], [ImageHeight], [ImageFormat],
     [StorageBackend], [StoragePath])
VALUES
    (SCOPE_IDENTITY(),
     1920, 1080, 'JPEG',
     'azure_blob',
     'https://storage.example.com/cso-images/20250910T143200.jpg');
```

---

## Walk-through 4 — 2-D Matrix (particle size × settling velocity)

**Scenario:** A LISST-Portable|Xr measures a joint particle size × settling velocity
distribution. Each measurement is a 2-D grid: 4 size classes × 2 velocity classes.

### Steps 1–2: Create both binning axes and their bins

```sql
-- Size axis (µm)
INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID])
VALUES ('Particle size', 'LISST-Xr size classes (µm)', 4, 7);
-- Returns ValueBinningAxis_ID = 2

-- Velocity axis (m/s)
INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID])
VALUES ('Settling velocity', 'LISST-Xr velocity classes (m/s)', 2, 8);
-- Returns ValueBinningAxis_ID = 3

-- Size bins
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (2, 0,   1,  10), (2, 1,  10,  50), (2, 2,  50, 200), (2, 3, 200, 500);

-- Velocity bins
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (3, 0, 0.00, 0.01), (3, 1, 0.01, 0.10);
```

### Step 3: Find or create the Channel row (ValueType_ID = 3 = Matrix)

```sql
IF NOT EXISTS (
    SELECT 1 FROM [dbo].[Channel]
    WHERE [Equipment_ID] = 4 AND [Parameter_ID] = 6
      AND [DataProvenance_ID] = 1 AND [ProcessingDegree] = 'Raw'
)
INSERT INTO [dbo].[Channel]
    ([Equipment_ID], [Parameter_ID], [Unit_ID], [DataProvenance_ID],
     [ProcessingDegree], [ValueType_ID])
VALUES (4, 6, 5, 1, 'Raw', 3);

DECLARE @channel_id INT;
SELECT @channel_id = [Channel_ID] FROM [dbo].[Channel]
WHERE [Equipment_ID] = 4 AND [Parameter_ID] = 6
  AND [DataProvenance_ID] = 1 AND [ProcessingDegree] = 'Raw';
```

### Step 4: Link both axes

```sql
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID], [AxisRole], [ValueBinningAxis_ID])
VALUES
    (@channel_id, 0, 2),   -- row axis    = size
    (@channel_id, 1, 3);   -- column axis = velocity
```

### Step 5: Insert the matrix cells (v2.2.0)

```sql
-- First, create the Observation for this matrix
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
VALUES (@channel_id, '2025-09-10T10:00:00.0000000', 'Matrix');
DECLARE @obs_id BIGINT = SCOPE_IDENTITY();

-- Then insert the matrix cells using the Observation_ID
INSERT INTO [dbo].[ValueMatrix]
    ([Observation_ID], [RowValueBin_ID], [ColValueBin_ID], [Value])
SELECT
    @obs_id,
    rb.[ValueBin_ID],
    cb.[ValueBin_ID],
    src.[Value]
FROM (VALUES
    (0, 0,  8.4), (0, 1,  3.1),
    (1, 0, 22.7), (1, 1, 11.5),
    (2, 0, 31.6), (2, 1, 18.3),
    (3, 0,  5.3), (3, 1,  2.9)
) AS src(size_idx, vel_idx, [Value])
JOIN [dbo].[ValueBin] rb ON rb.[ValueBinningAxis_ID] = 2 AND rb.[BinIndex] = src.size_idx
JOIN [dbo].[ValueBin] cb ON cb.[ValueBinningAxis_ID] = 3 AND cb.[BinIndex] = src.vel_idx;
```

---

## Summary

| Value type | ChannelAxis rows | Storage table | Rows per timestamp |
| --- | --- | --- | --- |
| Scalar | 0 | `dbo.Value` | 1 |
| Vector | 1 (`AxisRole = 0`) | `dbo.ValueVector` | n_bins |
| Matrix | 2 (`AxisRole = 0` and `1`) | `dbo.ValueMatrix` | n_row_bins × n_col_bins |
| Image | 0 | `dbo.ValueImage` | 1 (one frame) |

`Channel.ValueType_ID` is the single discriminator that drives which table to query.

To list all Vector channels:

```sql
SELECT c.[Channel_ID], p.[Parameter]
FROM   [dbo].[Channel]    c
JOIN   [dbo].[ValueType]  vt ON c.[ValueType_ID] = vt.[ValueType_ID]
JOIN   [dbo].[Parameter]  p  ON c.[Parameter_ID] = p.[Parameter_ID]
WHERE  vt.[ValueType_Name] = 'Vector';
```
