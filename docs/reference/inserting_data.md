# Inserting Data: Step-by-Step Walkthroughs

This page explains how to add measurement data to open_datEAUbase for each value type the schema supports.
It is written for practitioners who already understand the domain but are new to the schema.

---

## The central idea: MetaData as a hub

Every measurement series starts with **one row in `dbo.MetaData`**.
That row is not a measurement — it is a description of the measurement context:
who collected the data, with which instrument, at which location, for what parameter, in what unit, and under what project.

The `ValueType_ID` column on that row is the key decision.
It tells the database which storage table holds the actual values:

| ValueType_ID | Name | Storage table | When to use |
|---|---|---|---|
| 1 | Scalar | `dbo.Value` | One number per timestamp (pH, TSS, temperature, …) |
| 2 | Vector | `dbo.ValueVector` | A 1-D distribution over a physical axis (spectrum, PSD, …) |
| 3 | Matrix | `dbo.ValueMatrix` | A 2-D joint distribution over two physical axes (size × velocity, …) |
| 4 | Image | `dbo.ValueImage` | A camera or microscope frame stored as a file reference |

You create the MetaData row once per campaign setup (or whenever a new instrument/location/parameter combination is needed), then reuse the `Metadata_ID` for every timestamp in that series.

---

## Prerequisites (all types)

Before inserting any values, the following lookup rows must exist.
Most are set up once per project and reused across many series.

| Table | What it holds | Example |
|---|---|---|
| `dbo.Watershed` | Drainage area | "Rivière Saint-Charles" |
| `dbo.Site` | Physical installation site | "WWTP Est Inlet" |
| `dbo.SamplingPoints` | Specific measurement location at a site | "WWTP-IN-01" |
| `dbo.Parameter` | The quantity being measured | "TSS", "Absorbance" |
| `dbo.Unit` | Measurement unit | "mg/L", "nm", "m/s" |
| `dbo.EquipmentModel` | Instrument make/model | "ISCO 6712 autosampler" |
| `dbo.Equipment` | Specific instrument serial number | "ISCO-001" |
| `dbo.Project` | Research or monitoring campaign | "WWTP Inlet Monitoring 2024" |
| `dbo.Contact` | Person responsible for the data | "M. Tremblay" |

These are populated with plain `INSERT` statements and are independent of value type.

---

## Walk-through 1 — Scalar data from a sensor

**Scenario:** A TSS probe at WWTP-IN-01 reports one mg/L reading every 15 minutes.

### Step 1: Create the MetaData row

One MetaData row represents the entire series — the (instrument, parameter, location) combination that produced the data. Create it once; every timestamp reuses the same `Metadata_ID`.

```sql
INSERT INTO [dbo].[MetaData]
    (Project_ID, Contact_ID, Equipment_ID, Parameter_ID, Unit_ID,
     Sampling_point_ID, ValueType_ID)
VALUES
    (1, 1, 1, 1, 1, 1, 1);   -- ValueType_ID = 1 = Scalar
```

`ValueType_ID = 1` means: measurements for this series go in `dbo.Value`.

### Step 2: Insert measurements

Each measurement is a single row — one value and one timestamp.

```sql
INSERT INTO [dbo].[Value] (Metadata_ID, Value, Timestamp)
VALUES
    (7, 185.0, '2025-09-10T10:00:00.0000000'),
    (7, 192.3, '2025-09-10T10:15:00.0000000'),
    (7, 178.9, '2025-09-10T10:30:00.0000000');
```

`Timestamp` is a `DATETIME2(7)` — values are stored in UTC by convention.

### Retrieve the data

```sql
SELECT v.[Value], v.[Timestamp]
FROM   [dbo].[Value] v
WHERE  v.[Metadata_ID] = 7
ORDER BY v.[Timestamp];
```

That is the complete workflow for scalar data.

---

## Walk-through 2 — Spectrum data from a UV-Vis spectrometer

**Scenario:** A S::CAN spectro::lyser at WWTP-IN-01 measures UV-Vis absorbance
across wavelengths 200–750 nm, sampled into 7 wavelength bands.
It produces one full spectrum every 15 minutes.

The key difference from Scalar: you have **an ordered set of values per timestamp**,
each associated with a specific wavelength band.
The schema stores this using three additional tables:

- `ValueBinningAxis` — defines the physical axis (name and unit)
- `ValueBin` — defines each band: a `[LowerBound, UpperBound)` half-open interval in axis units
- `MetaDataAxis` — links the MetaData series to its axis (1 row for Vector)
- `ValueVector` — stores the actual values (one row per bin per timestamp)

### Step 1: Create the binning axis

The axis is the wavelength scale of the spectrometer. It is defined once and can be shared by multiple MetaData series that use the same instrument.

```sql
-- The "nm" unit (Unit_ID = 6) must already exist in dbo.Unit.
INSERT INTO [dbo].[ValueBinningAxis] (Name, Description, NumberOfBins, Unit_ID)
VALUES ('UV-Vis 200-750nm', 'S::CAN spectro::lyser wavelength axis', 7, 6);
-- Returns ValueBinningAxis_ID = 1
```

### Step 2: Define the bins

Each row is one wavelength band. `BinIndex` is zero-based and controls display order.
`LowerBound` is inclusive, `UpperBound` is exclusive (half-open interval).

```sql
INSERT INTO [dbo].[ValueBin] (ValueBinningAxis_ID, BinIndex, LowerBound, UpperBound)
VALUES
    (1, 0,  200,  300),   -- 200–300 nm
    (1, 1,  300,  350),   -- 300–350 nm
    (1, 2,  350,  400),   -- 350–400 nm
    (1, 3,  400,  450),   -- 400–450 nm
    (1, 4,  450,  500),   -- 450–500 nm
    (1, 5,  500,  600),   -- 500–600 nm
    (1, 6,  600,  750);   -- 600–750 nm
```

The center wavelength of any bin is computed on read: `(LowerBound + UpperBound) / 2.0`.
It is never stored redundantly.

### Step 3: Create the MetaData row

```sql
INSERT INTO [dbo].[MetaData]
    (Project_ID, Parameter_ID, Unit_ID, Sampling_point_ID, ValueType_ID)
VALUES
    (1, 5, 7, 1, 2);   -- ValueType_ID = 2 = Vector
-- Returns Metadata_ID = 7
```

Note: `Unit_ID` here is the unit of the **measured quantity** (absorbance, AU or dimensionless).
The axis unit (nm) lives in `ValueBinningAxis`, not in MetaData.

### Step 4: Link the axis to the series

`MetaDataAxis` is the junction between a MetaData series and its physical axis.
`AxisRole = 0` means "the single axis" for a Vector.

```sql
INSERT INTO [dbo].[MetaDataAxis] (Metadata_ID, AxisRole, ValueBinningAxis_ID)
VALUES (7, 0, 1);
```

### Step 5: Insert the spectral measurements

Each timestamp produces as many rows as there are bins (7 in this case).
`ValueBin_ID` references the specific bin in `dbo.ValueBin`.

```sql
INSERT INTO [dbo].[ValueVector] (Metadata_ID, Timestamp, ValueBin_ID, Value, QualityCode)
VALUES
    -- Spectrum at 10:00
    (7, '2025-09-10T10:00:00.0000000', 1, 0.142, NULL),
    (7, '2025-09-10T10:00:00.0000000', 2, 0.287, NULL),
    (7, '2025-09-10T10:00:00.0000000', 3, 0.531, NULL),
    (7, '2025-09-10T10:00:00.0000000', 4, 0.612, NULL),
    (7, '2025-09-10T10:00:00.0000000', 5, 0.489, NULL),
    (7, '2025-09-10T10:00:00.0000000', 6, 0.334, NULL),
    (7, '2025-09-10T10:00:00.0000000', 7, 0.201, NULL);
    -- Repeat for each subsequent 15-minute timestamp ...
```

### Retrieve a spectrum

```sql
SELECT
    vb.[BinIndex],
    (vb.[LowerBound] + vb.[UpperBound]) / 2.0  AS wavelength_nm,
    vv.[Value]                                  AS absorbance,
    vv.[QualityCode]
FROM   [dbo].[ValueVector] vv
JOIN   [dbo].[ValueBin]    vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
WHERE  vv.[Metadata_ID] = 7
  AND  vv.[Timestamp]   = '2025-09-10T10:00:00.0000000'
ORDER BY vb.[BinIndex];
```

---

## Walk-through 3 — Image data from a camera or microscope

**Scenario:** A camera installed at the CSO outfall captures a JPEG image at the start of each rain event. Images are stored in object storage (Azure Blob, S3, or a local file share). The database stores the frame metadata and a pointer to the file; the raw pixel data never enters the database.

### Step 1: Create the MetaData row

```sql
INSERT INTO [dbo].[MetaData]
    (Project_ID, Equipment_ID, Sampling_point_ID, ValueType_ID)
VALUES
    (2, 3, 3, 4);   -- ValueType_ID = 4 = Image
-- Returns Metadata_ID = 8
```

No `MetaDataAxis` row is needed — images do not use a binning axis.

### Step 2: Insert the image record

```sql
INSERT INTO [dbo].[ValueImage]
    (Metadata_ID, Timestamp, ImageWidth, ImageHeight, ImageFormat,
     StorageBackend, StoragePath)
VALUES
    (8, '2025-09-10T14:32:00.0000000',
     1920, 1080, 'JPEG',
     'azure_blob',
     'https://storage.example.com/cso-images/20250910T143200.jpg');
```

`StorageBackend` and `StoragePath` are free-text. Use whatever conventions suit your storage system.

---

## Walk-through 4 — Particle settling velocity distribution (2-D Matrix)

**Scenario:** A LISST-Portable|Xr at WWTP-IN-01 measures a joint particle
size × settling velocity distribution from a grab sample.
Each measurement is a 2-D grid: rows are 4 size classes (µm),
columns are 2 velocity classes (m/s).
The cell value is the volumetric concentration of particles in that (size, velocity) bin.

This requires:

- Two `ValueBinningAxis` rows — one for size, one for velocity
- `ValueBin` rows for each axis
- A MetaData row with `ValueType_ID = 3` (Matrix)
- **Two** `MetaDataAxis` rows (`AxisRole = 0` for size, `AxisRole = 1` for velocity)
- `ValueMatrix` rows: one per grid cell per timestamp

### Step 1: Create both binning axes

```sql
-- Size axis (µm, Unit_ID = 7 in the sample dataset)
INSERT INTO [dbo].[ValueBinningAxis] (Name, Description, NumberOfBins, Unit_ID)
VALUES ('Particle size', 'LISST-Xr size classes (µm)', 4, 7);
-- Returns ValueBinningAxis_ID = 2

-- Settling velocity axis (m/s, Unit_ID = 8 in the sample dataset)
INSERT INTO [dbo].[ValueBinningAxis] (Name, Description, NumberOfBins, Unit_ID)
VALUES ('Settling velocity', 'LISST-Xr velocity classes (m/s)', 2, 8);
-- Returns ValueBinningAxis_ID = 3
```

### Step 2: Define bins for each axis

```sql
-- Size bins (µm)
INSERT INTO [dbo].[ValueBin] (ValueBinningAxis_ID, BinIndex, LowerBound, UpperBound)
VALUES
    (2, 0,   1,  10),   --   1–10 µm
    (2, 1,  10,  50),   --  10–50 µm
    (2, 2,  50, 200),   --  50–200 µm
    (2, 3, 200, 500);   -- 200–500 µm

-- Velocity bins (m/s)
INSERT INTO [dbo].[ValueBin] (ValueBinningAxis_ID, BinIndex, LowerBound, UpperBound)
VALUES
    (3, 0, 0.00, 0.01),  -- 0–0.01 m/s   (slow-settling)
    (3, 1, 0.01, 0.10);  -- 0.01–0.10 m/s (fast-settling)
```

### Step 3: Create the MetaData row

```sql
INSERT INTO [dbo].[MetaData]
    (Project_ID, Contact_ID, Equipment_ID, Parameter_ID, Unit_ID,
     Sampling_point_ID, ValueType_ID)
VALUES
    (1, 1, 2, 6, 5, 1, 3);   -- ValueType_ID = 3 = Matrix
-- Returns Metadata_ID = 10
```

### Step 4: Link both axes

Two rows in `MetaDataAxis` — one per axis.
`AxisRole = 0` is the row axis (size), `AxisRole = 1` is the column axis (velocity).

```sql
INSERT INTO [dbo].[MetaDataAxis] (Metadata_ID, AxisRole, ValueBinningAxis_ID)
VALUES
    (10, 0, 2),   -- row axis    = size
    (10, 1, 3);   -- column axis = velocity
```

### Step 5: Insert the matrix cells

At each timestamp, insert `n_size_bins × n_velocity_bins = 4 × 2 = 8` rows.
The cleanest way is a `SELECT ... FROM (VALUES ...) JOIN` to resolve bin IDs by index:

```sql
INSERT INTO [dbo].[ValueMatrix]
    (Metadata_ID, Timestamp, RowValueBin_ID, ColValueBin_ID, Value, QualityCode)
SELECT
    10,
    '2025-09-10T10:00:00.0000000',
    rb.[ValueBin_ID],
    cb.[ValueBin_ID],
    src.[Value],
    NULL
FROM (VALUES
    -- (size_bin_index, velocity_bin_index, concentration_µL/L)
    (0, 0,  8.4),
    (0, 1,  3.1),
    (1, 0, 22.7),
    (1, 1, 11.5),
    (2, 0, 31.6),
    (2, 1, 18.3),
    (3, 0,  5.3),
    (3, 1,  2.9)
) AS src(size_idx, vel_idx, [Value])
JOIN [dbo].[ValueBin] rb
    ON rb.[ValueBinningAxis_ID] = 2 AND rb.[BinIndex] = src.size_idx
JOIN [dbo].[ValueBin] cb
    ON cb.[ValueBinningAxis_ID] = 3 AND cb.[BinIndex] = src.vel_idx;
```

This avoids hard-coding `ValueBin_ID` values and works correctly regardless of the
order in which bins were inserted.

### Retrieve a joint distribution

```sql
SELECT
    rb.[BinIndex]                                AS size_bin,
    (rb.[LowerBound] + rb.[UpperBound]) / 2.0    AS size_center_um,
    cb.[BinIndex]                                AS vel_bin,
    (cb.[LowerBound] + cb.[UpperBound]) / 2.0    AS vel_center_m_s,
    vm.[Value]                                   AS concentration_uL_per_L
FROM   [dbo].[ValueMatrix] vm
JOIN   [dbo].[ValueBin]    rb ON vm.[RowValueBin_ID] = rb.[ValueBin_ID]
JOIN   [dbo].[ValueBin]    cb ON vm.[ColValueBin_ID] = cb.[ValueBin_ID]
WHERE  vm.[Metadata_ID] = 10
  AND  vm.[Timestamp]   = '2025-09-10T10:00:00.0000000'
ORDER BY rb.[BinIndex], cb.[BinIndex];
```

---

## Summary

| Value type | MetaDataAxis rows | Storage table | Rows per timestamp |
|---|---|---|---|
| Scalar | 0 | `dbo.Value` | 1 |
| Vector | 1 (`AxisRole = 0`) | `dbo.ValueVector` | n_bins |
| Matrix | 2 (`AxisRole = 0` and `1`) | `dbo.ValueMatrix` | n_row_bins × n_col_bins |
| Image  | 0 | `dbo.ValueImage` | 1 (one frame) |

`MetaData.ValueType_ID` is the single discriminator that drives which table to query.
To list all Vector series at a sampling point:

```sql
SELECT m.[Metadata_ID], p.[Parameter]
FROM   [dbo].[MetaData]       m
JOIN   [dbo].[ValueType]      vt ON m.[ValueType_ID]      = vt.[ValueType_ID]
JOIN   [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN   [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE  vt.[ValueType_Name] = 'Vector'
  AND  sp.[Sampling_point] = 'WWTP-IN-01';
```
