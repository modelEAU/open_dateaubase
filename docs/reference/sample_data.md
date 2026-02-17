# Sample Data & Business Query Catalogue

This page documents the **sample dataset** shipped with the database and defines a catalogue of **business queries** the schema is designed to answer.
Result tables in §2 and §3 are **generated live** from the database at documentation-build time — every release reflects the actual state of the data.

---

## 1. Sample Case

### 1.1 Scenario

The sample data represents a realistic **wastewater and stormwater monitoring programme** at a treatment plant and a combined sewer overflow outfall in Quebec City.
Data is built up in layers — one layer per schema version — so the dataset grows naturally as the schema evolves.

| Schema version | What was added |
| --- | --- |
| v1.0.0 | Baseline monitoring data: sites, equipment, parameters, projects, contacts, scalar measurements with Unix-epoch timestamps |
| v1.0.1 | Schema version history records |
| v1.0.2 | New scalar measurements inserted with timezone-aware `DATETIMEOFFSET` timestamps |
| v1.1.0 | UV-Vis spectrometer data (spectra), camera images, particle size distribution arrays |

### 1.2 Spatial context

Two watersheds are defined. Both sites and all sampling points belong to the urban catchment.

| Watershed | Surface area | Impervious surface | Type |
| --- | --- | --- | --- |
| Rivière Saint-Charles | 550 ha | 35.5 % | Urban catchment |
| Rivière Montmorency | 1 150 ha | 8.2 % | Rural reference |

Each watershed has one row in `HydrologicalCharacteristics` and one row in `UrbanCharacteristics`.

Two sites, three sampling points:

| Sampling point | Site | Location |
| --- | --- | --- |
| WWTP-IN-01 | WWTP Est Inlet | 46.8310 N, 71.2080 W |
| WWTP-OUT-01 | WWTP Est Inlet | 46.8315 N, 71.2075 W |
| CSO-12-OUT | CSO Outfall 12 | 46.8200 N, 71.2250 W |

### 1.3 Instrumentation

| Equipment | Model | Capabilities |
| --- | --- | --- |
| ISCO-001 | ISCO 6712 autosampler | TSS, COD (via 24 h composite and grab sampling) |
| YSI-001 | YSI ProDSS multi-parameter probe | pH, Temperature, Conductivity (online continuous) |
| HACH-001 | Hach 2100Q turbidimeter | No parameter capabilities recorded in this dataset |

### 1.4 Parameters and units

| Parameter | Unit | Metadata rows | Total Value rows |
| --- | --- | --- | --- |
| TSS | mg/L | 3 (WWTP-IN, WWTP-OUT, CSO) | 11 |
| COD | mg/L | 1 (WWTP-IN) | 3 |
| pH | pH units | 1 (WWTP-IN) | 5 |
| Temperature | °C | 1 (WWTP-IN) | 3 |
| Conductivity | mS/cm | 0 | 0 |

### 1.5 Projects and contacts

| Project | Contact(s) | Equipment | Sampling points |
| --- | --- | --- | --- |
| WWTP Inlet Monitoring 2024 | M. Tremblay, P. Gagnon | ISCO-001, YSI-001, HACH-001 | WWTP-IN-01, WWTP-OUT-01 |
| CSO Event Study 2024 | P. Gagnon | ISCO-001 | CSO-12-OUT |

### 1.6 Scalar measurements (dbo.Value)

22 rows total after v1.0.2 seed data. Key subsets:

| Value_ID | Parameter | Sampling point | Value | Timestamp (UTC) | QA comment |
| --- | --- | --- | --- | --- | --- |
| 1 | TSS | WWTP-IN-01 | 185.0 mg/L | 2024-01-15 13:00 | Normal |
| 2 | TSS | WWTP-IN-01 | 210.5 mg/L | 2024-01-15 19:00 | — |
| 3 | TSS | WWTP-IN-01 | 192.3 mg/L | 2024-01-16 13:00 | Normal |
| 9 | pH | WWTP-IN-01 | 7.8 pH units | 2024-01-15 17:00 | **Possible equipment drift** |
| 10 | TSS | CSO-12-OUT | 350.0 mg/L | 2024-03-20 12:00 | — |
| 11 | TSS | CSO-12-OUT | 580.2 mg/L | 2024-03-20 14:00 | — |
| 12 | TSS | CSO-12-OUT | 345.0 mg/L | 2024-03-20 14:00 | **Duplicate (QA/QC)** |
| 13 | TSS | WWTP-OUT-01 | 12.5 mg/L | 2024-01-15 13:00 | — |
| 14 | TSS | WWTP-OUT-01 | 15.0 mg/L | 2024-01-16 13:00 | — |
| 18 | TSS | WWTP-IN-01 | 200.0 mg/L | **NULL** | Edge case: no timestamp |
| 19 | TSS | WWTP-IN-01 | 145.2 mg/L | 2025-06-15 12:00 EDT | v1.0.2 seed |
| 20 | TSS | WWTP-IN-01 | 160.8 mg/L | 2025-06-15 18:30 EDT | v1.0.2 seed |

### 1.7 Polymorphic value types (v1.1.0)

| Type | Metadata_ID | Description | Rows |
| --- | --- | --- | --- |
| Vector (UV-Vis) | 7 | S::CAN spectro::lyser, 200–750 nm, 7 sample bins across 2 timestamps | 10 rows in ValueVector |
| Image | 8 | Camera at CSO-12-OUT during rain, 1920×1080 JPEG | 2 rows in ValueImage |
| Vector (particle size) | 9 | 4-fraction PSD at WWTP-IN-01, 2 timestamps | 8 rows in ValueVector |
| Matrix (size × velocity) | 10 | Joint distribution at WWTP-IN-01, 3×2 bins | 6 rows in ValueMatrix |

All 6 pre-existing `Metadata` rows (IDs 1–6) have `ValueType_ID = 1` (Scalar) after the v1.1.0 migration.

---

## 2. Table Contents

The tables below are **generated live from the database** at documentation-build time and show the full contents of the key sample-data tables.

```python exec="true" session="bq"
import sys
sys.path.insert(0, "docs/hooks")
from bq_runner import make_runner
run_bq, run_ic = make_runner()
```

### 2.1 Schema version history — `dbo.SchemaVersion`

```python exec="true" session="bq"
print(run_bq("""
SELECT [Version], [Description],
       CONVERT(NVARCHAR(23), [AppliedAt], 126) AS [AppliedAt]
FROM [dbo].[SchemaVersion]
ORDER BY [AppliedAt]
"""))
```

### 2.2 Watersheds — `dbo.Watershed`

```python exec="true" session="bq"
print(run_bq("""
SELECT [name],
       CAST([Surface_area]      AS INT)              AS [Surface_area_ha],
       CAST(ROUND([Impervious_surface], 1) AS DECIMAL(5,1)) AS [Impervious_pct],
       [Description]
FROM [dbo].[Watershed]
ORDER BY [name]
"""))
```

### 2.3 Sites and sampling points — `dbo.Site` / `dbo.SamplingPoints`

```python exec="true" session="bq"
print(run_bq("""
SELECT s.[name]           AS [Site],
       sp.[Sampling_point],
       sp.[Sampling_location]
FROM [dbo].[SamplingPoints] sp
JOIN [dbo].[Site]           s  ON sp.[Site_ID] = s.[Site_ID]
ORDER BY s.[name], sp.[Sampling_point]
"""))
```

### 2.4 Equipment models and parameter capabilities — `dbo.EquipmentModel`

```python exec="true" session="bq"
print(run_bq("""
SELECT em.[Equipment_model],
       STRING_AGG(p.[Parameter], ', ') AS [Can_measure]
FROM [dbo].[EquipmentModel]             em
LEFT JOIN [dbo].[EquipmentModelHasParameter] ehp
       ON em.[Equipment_model_ID] = ehp.[Equipment_model_ID]
LEFT JOIN [dbo].[Parameter] p
       ON ehp.[Parameter_ID] = p.[Parameter_ID]
GROUP BY em.[Equipment_model_ID], em.[Equipment_model]
ORDER BY em.[Equipment_model]
"""))
```

### 2.5 Equipment instances — `dbo.Equipment`

```python exec="true" session="bq"
print(run_bq("""
SELECT e.[identifier],
       em.[Equipment_model],
       e.[Serial_number]
FROM [dbo].[Equipment]   e
JOIN [dbo].[EquipmentModel] em ON e.[model_ID] = em.[Equipment_model_ID]
ORDER BY e.[identifier]
"""))
```

### 2.6 Parameters and units — `dbo.Parameter`

```python exec="true" session="bq"
print(run_bq("""
SELECT p.[Parameter], u.[Unit]
FROM [dbo].[Parameter] p
JOIN [dbo].[Unit]      u ON p.[Unit_ID] = u.[Unit_ID]
ORDER BY p.[Parameter]
"""))
```

### 2.7 Contacts — `dbo.Contact`

```python exec="true" session="bq"
print(run_bq("""
SELECT [First_name], [Last_name], [Email], [Function]
FROM [dbo].[Contact]
ORDER BY [Last_name], [First_name]
"""))
```

### 2.8 Projects — `dbo.Project`

```python exec="true" session="bq"
print(run_bq("""
SELECT [name], [Description]
FROM [dbo].[Project]
ORDER BY [name]
"""))
```

### 2.9 MetaData series — `dbo.MetaData`

Each row in `MetaData` defines one measurement series (a parameter measured at a location with a given instrument).

```python exec="true" session="bq"
print(run_bq("""
SELECT m.[Metadata_ID],
       vt.[ValueType_Name]  AS [ValueType],
       p.[Parameter],
       sp.[Sampling_point],
       e.[identifier]       AS [Equipment],
       u.[Unit]
FROM [dbo].[MetaData]       m
LEFT JOIN [dbo].[ValueType]      vt ON m.[ValueType_ID]       = vt.[ValueType_ID]
LEFT JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]       = p.[Parameter_ID]
LEFT JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID]  = sp.[Sampling_point_ID]
LEFT JOIN [dbo].[Equipment]      e  ON m.[Equipment_ID]       = e.[Equipment_ID]
LEFT JOIN [dbo].[Unit]           u  ON m.[Unit_ID]            = u.[Unit_ID]
ORDER BY m.[Metadata_ID]
"""))
```

### 2.10 Scalar measurements — `dbo.Value`

```python exec="true" session="bq"
print(run_bq("""
SELECT v.[Value_ID],
       p.[Parameter],
       sp.[Sampling_point],
       v.[Value],
       v.[Timestamp]
FROM [dbo].[Value]          v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]     = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID]= sp.[Sampling_point_ID]
ORDER BY v.[Value_ID]
"""))
```

### 2.11 UV-Vis spectra — `dbo.ValueVector` (v1.1.0)

```python exec="true" session="bq"
print(run_bq("""
SELECT vv.[Metadata_ID],
       vv.[Timestamp],
       vb.[BinIndex],
       (vb.[LowerBound] + vb.[UpperBound]) / 2.0 AS [Wavelength_nm],
       vv.[Value]        AS [Absorbance]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[ValueBin] vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
JOIN [dbo].[MetaDataAxis] mda ON vv.[Metadata_ID] = mda.[Metadata_ID]
JOIN [dbo].[ValueBinningAxis] vba ON mda.[ValueBinningAxis_ID] = vba.[ValueBinningAxis_ID]
WHERE vba.[Name] = 'S::CAN spectro::lyser UV-Vis'
ORDER BY vv.[Timestamp], vb.[BinIndex]
"""))
```

### 2.12 Camera images — `dbo.ValueImage` (v1.1.0)

```python exec="true" session="bq"
print(run_bq("""
SELECT [ValueImage_ID],
       [Metadata_ID],
       [Timestamp],
       [ImageWidth],
       [ImageHeight],
       [ImageFormat],
       [StorageBackend],
       [StoragePath]
FROM [dbo].[ValueImage]
ORDER BY [Timestamp]
"""))
```

### 2.13 Particle size distribution vectors — `dbo.ValueVector` (v1.1.0)

```python exec="true" session="bq"
print(run_bq("""
SELECT vv.[Metadata_ID],
       vv.[Timestamp],
       vb.[BinIndex],
       vv.[Value]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[ValueBin] vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
JOIN [dbo].[MetaDataAxis] mda ON vv.[Metadata_ID] = mda.[Metadata_ID]
JOIN [dbo].[ValueBinningAxis] vba ON mda.[ValueBinningAxis_ID] = vba.[ValueBinningAxis_ID]
WHERE vba.[Name] = 'LISST-200X particle size'
ORDER BY vv.[Timestamp], vb.[BinIndex]
"""))
```

---

## 3. Business Queries

This section documents queries that the schema is designed to answer.
The test suite `tests/integration/test_business_queries.py` runs every query and asserts that results meet the expected criteria.

| ID | Category | Business question | Min. schema | Test |
| --- | --- | --- | --- | --- |
| BQ-01 | Measurement retrieval | What are all TSS measurements at WWTP-IN-01, sorted by timestamp? | v1.0.2 | `test_bq01` |
| BQ-02 | Measurement retrieval | What are the TSS measurements at WWTP-IN-01 in January 2024? | v1.0.2 | `test_bq02` |
| BQ-03 | Measurement retrieval | What is the average TSS concentration per sampling point? | v1.0.2 | `test_bq03` |
| BQ-04 | Equipment | Which equipment models are capable of measuring TSS? | v1.0.0 | `test_bq04` |
| BQ-05 | Equipment | What parameters can each equipment model measure? | v1.0.0 | `test_bq05` |
| BQ-06 | Equipment | Where has ISCO-001 been deployed (which projects)? | v1.0.0 | `test_bq06` |
| BQ-07 | Site & project | What sampling points exist in the WWTP Inlet Monitoring 2024 project? | v1.0.0 | `test_bq07` |
| BQ-08 | Site & project | How many measurements of each parameter are available per sampling point in the Saint-Charles watershed? | v1.0.2 | `test_bq08` |
| BQ-09 | Site & project | Which contacts are associated with the CSO Event Study? | v1.0.0 | `test_bq09` |
| BQ-10 | Data quality | Which measurements carry a QA/QC comment? | v1.0.2 | `test_bq10` |
| BQ-11 | Data quality | Are there duplicate measurements at the same location and timestamp? | v1.0.2 | `test_bq11` |
| BQ-12 | Data quality | Which MetaData entries are missing a contact, equipment, or weather condition? | v1.0.2 | `test_bq12` |
| BQ-13 | Polymorphic types | What value types are recorded at each sampling point? | v1.1.0 | `test_bq13` |
| BQ-14 | Polymorphic types | What is the UV-Vis absorbance spectrum at WWTP-IN-01 at 10:00 on 2025-09-10? | v1.1.0 | `test_bq14` |
| BQ-15 | Polymorphic types | What is the total particle concentration (sum of PSD fractions) at each timestamp? | v1.1.0 | `test_bq15` |

### 3.1 Detailed queries

---

#### BQ-01 — All TSS measurements at WWTP-IN-01

**Business question:** What are all TSS values measured at the WWTP inlet sampling point, in chronological order?

**SQL:**

```sql
SELECT
    v.[Value_ID],
    v.[Value],
    v.[Timestamp]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]       = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]       = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID]  = sp.[Sampling_point_ID]
WHERE p.[Parameter]       = 'TSS'
  AND sp.[Sampling_point] = 'WWTP-IN-01'
ORDER BY v.[Timestamp];
```

**Live result** — 6 rows expected (3 from v1.0.0 seed + 1 NULL-timestamp edge case + 2 from v1.0.2 seed):

```python exec="true" session="bq"
print(run_bq("""
SELECT v.[Value_ID], v.[Value], v.[Timestamp]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]       = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]       = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID]  = sp.[Sampling_point_ID]
WHERE p.[Parameter] = 'TSS' AND sp.[Sampling_point] = 'WWTP-IN-01'
ORDER BY v.[Timestamp]
"""))
```

---

#### BQ-02 — TSS at WWTP-IN-01 in January 2024

**Business question:** Filter measurements to a specific date range (the standard "give me data between dates" query).

**SQL:**

```sql
SELECT v.[Value], v.[Timestamp]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE p.[Parameter]       = 'TSS'
  AND sp.[Sampling_point] = 'WWTP-IN-01'
  AND v.[Timestamp] >= '2024-01-15T00:00:00.0000000+00:00'
  AND v.[Timestamp] <  '2024-01-17T00:00:00.0000000+00:00'
ORDER BY v.[Timestamp];
```

**Live result** — 3 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT v.[Value], v.[Timestamp]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE p.[Parameter] = 'TSS' AND sp.[Sampling_point] = 'WWTP-IN-01'
  AND v.[Timestamp] >= '2024-01-15T00:00:00.0000000+00:00'
  AND v.[Timestamp] <  '2024-01-17T00:00:00.0000000+00:00'
ORDER BY v.[Timestamp]
"""))
```

---

#### BQ-03 — Average TSS per sampling point

**Business question:** Aggregate statistics per location — the classic "what is the typical concentration at site X" question.

**SQL:**

```sql
SELECT
    sp.[Sampling_point],
    AVG(v.[Value])       AS avg_tss_mg_L,
    COUNT(v.[Value_ID])  AS n_measurements
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE p.[Parameter] = 'TSS'
GROUP BY sp.[Sampling_point]
ORDER BY sp.[Sampling_point];
```

**Live result** — 3 rows expected (CSO-12-OUT ≈ 425.1, WWTP-IN-01 ≈ 182.3, WWTP-OUT-01 = 13.75):

```python exec="true" session="bq"
print(run_bq("""
SELECT sp.[Sampling_point], AVG(v.[Value]) AS avg_tss_mg_L, COUNT(v.[Value_ID]) AS n_measurements
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE p.[Parameter] = 'TSS'
GROUP BY sp.[Sampling_point]
ORDER BY sp.[Sampling_point]
"""))
```

!!! note "Removal efficiency"
    Dividing the WWTP-OUT-01 average by the WWTP-IN-01 average gives an apparent TSS removal efficiency. This is the kind of derived calculation a user would perform after retrieving data from the schema.

---

#### BQ-04 — Equipment capable of measuring TSS

**Business question:** "I need to measure TSS — which instruments do we have that can do it?"

**SQL:**

```sql
SELECT DISTINCT e.[identifier], em.[Equipment_model]
FROM [dbo].[Equipment]                  e
JOIN [dbo].[EquipmentModel]             em  ON e.[model_ID]           = em.[Equipment_model_ID]
JOIN [dbo].[EquipmentModelHasParameter] ehp ON em.[Equipment_model_ID] = ehp.[Equipment_model_ID]
JOIN [dbo].[Parameter]                  p   ON ehp.[Parameter_ID]     = p.[Parameter_ID]
WHERE p.[Parameter] = 'TSS'
ORDER BY e.[identifier];
```

**Live result** — 1 row expected (ISCO-001):

```python exec="true" session="bq"
print(run_bq("""
SELECT DISTINCT e.[identifier], em.[Equipment_model]
FROM [dbo].[Equipment]                  e
JOIN [dbo].[EquipmentModel]             em  ON e.[model_ID]           = em.[Equipment_model_ID]
JOIN [dbo].[EquipmentModelHasParameter] ehp ON em.[Equipment_model_ID] = ehp.[Equipment_model_ID]
JOIN [dbo].[Parameter]                  p   ON ehp.[Parameter_ID]     = p.[Parameter_ID]
WHERE p.[Parameter] = 'TSS'
ORDER BY e.[identifier]
"""))
```

---

#### BQ-05 — All parameters per equipment model

**Business question:** "What can each instrument measure?" — useful for planning campaigns and checking instrument capability.

**SQL:**

```sql
SELECT em.[Equipment_model], p.[Parameter]
FROM [dbo].[EquipmentModel]             em
JOIN [dbo].[EquipmentModelHasParameter] ehp ON em.[Equipment_model_ID] = ehp.[Equipment_model_ID]
JOIN [dbo].[Parameter]                  p   ON ehp.[Parameter_ID]      = p.[Parameter_ID]
ORDER BY em.[Equipment_model], p.[Parameter];
```

**Live result** — 5 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT em.[Equipment_model], p.[Parameter]
FROM [dbo].[EquipmentModel]             em
JOIN [dbo].[EquipmentModelHasParameter] ehp ON em.[Equipment_model_ID] = ehp.[Equipment_model_ID]
JOIN [dbo].[Parameter]                  p   ON ehp.[Parameter_ID]      = p.[Parameter_ID]
ORDER BY em.[Equipment_model], p.[Parameter]
"""))
```

---

#### BQ-06 — Equipment deployment history

**Business question:** "Where has sensor ISCO-001 been deployed over its lifespan?" — at the project level.

**SQL:**

```sql
SELECT e.[identifier], p.[name] AS project, em.[Equipment_model]
FROM [dbo].[Equipment]           e
JOIN [dbo].[EquipmentModel]      em  ON e.[model_ID]     = em.[Equipment_model_ID]
JOIN [dbo].[ProjectHasEquipment] phe ON e.[Equipment_ID] = phe.[Equipment_ID]
JOIN [dbo].[Project]             p   ON phe.[Project_ID] = p.[Project_ID]
ORDER BY e.[identifier], p.[name];
```

**Live result** — 4 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT e.[identifier], p.[name] AS project, em.[Equipment_model]
FROM [dbo].[Equipment]           e
JOIN [dbo].[EquipmentModel]      em  ON e.[model_ID]     = em.[Equipment_model_ID]
JOIN [dbo].[ProjectHasEquipment] phe ON e.[Equipment_ID] = phe.[Equipment_ID]
JOIN [dbo].[Project]             p   ON phe.[Project_ID] = p.[Project_ID]
ORDER BY e.[identifier], p.[name]
"""))
```

---

#### BQ-07 — Sampling points in a project

**Business question:** "What sampling points exist in the WWTP Inlet Monitoring 2024 project?"

**SQL:**

```sql
SELECT sp.[Sampling_point], sp.[Sampling_location], s.[name] AS site
FROM [dbo].[SamplingPoints]           sp
JOIN [dbo].[ProjectHasSamplingPoints] phs ON sp.[Sampling_point_ID] = phs.[Sampling_point_ID]
JOIN [dbo].[Project]                  p   ON phs.[Project_ID]        = p.[Project_ID]
JOIN [dbo].[Site]                     s   ON sp.[Site_ID]            = s.[Site_ID]
WHERE p.[name] = 'WWTP Inlet Monitoring 2024'
ORDER BY sp.[Sampling_point];
```

**Live result** — 2 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT sp.[Sampling_point], sp.[Sampling_location], s.[name] AS site
FROM [dbo].[SamplingPoints]           sp
JOIN [dbo].[ProjectHasSamplingPoints] phs ON sp.[Sampling_point_ID] = phs.[Sampling_point_ID]
JOIN [dbo].[Project]                  p   ON phs.[Project_ID]        = p.[Project_ID]
JOIN [dbo].[Site]                     s   ON sp.[Site_ID]            = s.[Site_ID]
WHERE p.[name] = 'WWTP Inlet Monitoring 2024'
ORDER BY sp.[Sampling_point]
"""))
```

---

#### BQ-08 — Measurement counts per parameter and sampling point in a watershed

**Business question:** "How much data do we have for each parameter at each location in the Saint-Charles watershed?"

**SQL:**

```sql
SELECT
    p.[Parameter],
    sp.[Sampling_point],
    COUNT(v.[Value_ID]) AS n_measurements
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
JOIN [dbo].[Site]           s  ON sp.[Site_ID]          = s.[Site_ID]
JOIN [dbo].[Watershed]      w  ON s.[Watershed_ID]      = w.[Watershed_ID]
WHERE w.[name] = 'Riviere Saint-Charles'
GROUP BY p.[Parameter], sp.[Sampling_point]
ORDER BY p.[Parameter], sp.[Sampling_point];
```

**Live result** — 6 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT p.[Parameter], sp.[Sampling_point], COUNT(v.[Value_ID]) AS n_measurements
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
JOIN [dbo].[Site]           s  ON sp.[Site_ID]          = s.[Site_ID]
JOIN [dbo].[Watershed]      w  ON s.[Watershed_ID]      = w.[Watershed_ID]
WHERE w.[name] = 'Riviere Saint-Charles'
GROUP BY p.[Parameter], sp.[Sampling_point]
ORDER BY p.[Parameter], sp.[Sampling_point]
"""))
```

---

#### BQ-09 — Contacts associated with a project

**Business question:** "Who is responsible for data collection in the CSO Event Study?"

**SQL:**

```sql
SELECT c.[First_name], c.[Last_name], c.[Email], c.[Function]
FROM [dbo].[Contact]           c
JOIN [dbo].[ProjectHasContact] phc ON c.[Contact_ID]  = phc.[Contact_ID]
JOIN [dbo].[Project]           p   ON phc.[Project_ID] = p.[Project_ID]
WHERE p.[name] = 'CSO Event Study 2024'
ORDER BY c.[Last_name];
```

**Live result** — 1 row expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT c.[First_name], c.[Last_name], c.[Email], c.[Function]
FROM [dbo].[Contact]           c
JOIN [dbo].[ProjectHasContact] phc ON c.[Contact_ID]  = phc.[Contact_ID]
JOIN [dbo].[Project]           p   ON phc.[Project_ID] = p.[Project_ID]
WHERE p.[name] = 'CSO Event Study 2024'
ORDER BY c.[Last_name]
"""))
```

---

#### BQ-10 — Measurements with QA/QC comments

**Business question:** "Show me all measurements that carry an annotation — I want to review them before using the data."

**SQL:**

```sql
SELECT
    v.[Value_ID],
    p.[Parameter],
    sp.[Sampling_point],
    v.[Value],
    v.[Timestamp],
    c.[Comment]
FROM [dbo].[Value] v
JOIN [dbo].[Comments]       c  ON v.[Comment_ID]        = c.[Comment_ID]
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]       = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE c.[Comment] IS NOT NULL
ORDER BY v.[Value_ID];
```

**Live result** — 4 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT v.[Value_ID], p.[Parameter], sp.[Sampling_point], v.[Value], v.[Timestamp], c.[Comment]
FROM [dbo].[Value] v
JOIN [dbo].[Comments]       c  ON v.[Comment_ID]        = c.[Comment_ID]
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]       = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE c.[Comment] IS NOT NULL
ORDER BY v.[Value_ID]
"""))
```

---

#### BQ-11 — Duplicate measurements at the same timestamp

**Business question:** "Are there cases where the same sensor has two readings at the exact same timestamp? (Indicates a QA/QC duplicate or a data ingestion error.)"

**SQL:**

```sql
SELECT
    m.[Metadata_ID],
    p.[Parameter],
    sp.[Sampling_point],
    v.[Timestamp],
    COUNT(*) AS duplicate_count
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE v.[Timestamp] IS NOT NULL
GROUP BY m.[Metadata_ID], p.[Parameter], sp.[Sampling_point], v.[Timestamp]
HAVING COUNT(*) > 1;
```

**Live result** — 1 row expected (the intentional QA/QC duplicate at the CSO outfall):

```python exec="true" session="bq"
print(run_bq("""
SELECT m.[Metadata_ID], p.[Parameter], sp.[Sampling_point], v.[Timestamp], COUNT(*) AS duplicate_count
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]      = p.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE v.[Timestamp] IS NOT NULL
GROUP BY m.[Metadata_ID], p.[Parameter], sp.[Sampling_point], v.[Timestamp]
HAVING COUNT(*) > 1
"""))
```

---

#### BQ-12 — MetaData completeness audit

**Business question:** "Which data series are missing key contextual information? (Contact, equipment, or weather condition.)"

**SQL:**

```sql
SELECT
    m.[Metadata_ID],
    CASE WHEN m.[Contact_ID]   IS NULL THEN 'missing' ELSE 'ok' END AS contact,
    CASE WHEN m.[Equipment_ID] IS NULL THEN 'missing' ELSE 'ok' END AS equipment,
    CASE WHEN m.[Condition_ID] IS NULL THEN 'missing' ELSE 'ok' END AS weather_condition
FROM [dbo].[MetaData] m
WHERE m.[Contact_ID]   IS NULL
   OR m.[Equipment_ID] IS NULL
   OR m.[Condition_ID] IS NULL
ORDER BY m.[Metadata_ID];
```

**Live result** — 5 rows expected (MetaData IDs 3, 5, 7, 8, 9):

```python exec="true" session="bq"
print(run_bq("""
SELECT
    m.[Metadata_ID],
    CASE WHEN m.[Contact_ID]   IS NULL THEN 'missing' ELSE 'ok' END AS contact,
    CASE WHEN m.[Equipment_ID] IS NULL THEN 'missing' ELSE 'ok' END AS equipment,
    CASE WHEN m.[Condition_ID] IS NULL THEN 'missing' ELSE 'ok' END AS weather_condition
FROM [dbo].[MetaData] m
WHERE m.[Contact_ID] IS NULL OR m.[Equipment_ID] IS NULL OR m.[Condition_ID] IS NULL
ORDER BY m.[Metadata_ID]
"""))
```

---

#### BQ-13 — Value types per sampling point (v1.1.0)

**Business question:** "What kinds of data (scalar, spectral, image, array) are collected at each location?"

**SQL:**

```sql
SELECT
    sp.[Sampling_point],
    vt.[ValueType_Name],
    COUNT(*) AS n_metadata_entries
FROM [dbo].[MetaData]       m
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
JOIN [dbo].[ValueType]      vt ON m.[ValueType_ID]       = vt.[ValueType_ID]
WHERE m.[Sampling_point_ID] IS NOT NULL
GROUP BY sp.[Sampling_point], vt.[ValueType_Name]
ORDER BY sp.[Sampling_point], vt.[ValueType_Name];
```

**Live result** — 6 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT sp.[Sampling_point], vt.[ValueType_Name], COUNT(*) AS n_metadata_entries
FROM [dbo].[MetaData]       m
JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
JOIN [dbo].[ValueType]      vt ON m.[ValueType_ID]       = vt.[ValueType_ID]
WHERE m.[Sampling_point_ID] IS NOT NULL
GROUP BY sp.[Sampling_point], vt.[ValueType_Name]
ORDER BY sp.[Sampling_point], vt.[ValueType_Name]
"""))
```

---

#### BQ-14 — UV-Vis absorption spectrum at a specific timestamp (v1.1.0)

**Business question:** "Give me the full absorbance spectrum recorded at WWTP-IN-01 at 10:00 on 2025-09-10."

**SQL:**

```sql
SELECT
    vb.[BinIndex],
    (vb.[LowerBound] + vb.[UpperBound]) / 2.0 AS wavelength_nm,
    vv.[Value]       AS absorbance,
    vv.[QualityCode]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[ValueBin] vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
WHERE vv.[Metadata_ID] = 7
  AND vv.[Timestamp]   = '2025-09-10T14:00:00.0000000'
ORDER BY vb.[BinIndex];
```

**Live result** — 7 rows expected (all bins at this timestamp):

```python exec="true" session="bq"
print(run_bq("""
SELECT vb.[BinIndex], (vb.[LowerBound] + vb.[UpperBound]) / 2.0 AS wavelength_nm, vv.[Value] AS absorbance, vv.[QualityCode]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[ValueBin] vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
WHERE vv.[Metadata_ID] = 7
  AND vv.[Timestamp]   = '2025-09-10T14:00:00.0000000'
ORDER BY vb.[BinIndex]
"""))
```

---

#### BQ-15 — Total particle mass per timestamp from PSD vector (v1.1.0)

**Business question:** "What is the total suspended particle concentration (sum of all size fractions) at each measurement time?"

**SQL:**

```sql
SELECT
    vv.[Timestamp],
    SUM(vv.[Value]) AS total_concentration_mg_L,
    COUNT(*)         AS n_fractions
FROM [dbo].[ValueVector] vv
WHERE vv.[Metadata_ID] = 9
GROUP BY vv.[Timestamp]
ORDER BY vv.[Timestamp];
```

**Live result** — 2 rows expected (T1 = 91.6, T2 = 107.7 mg/L):

```python exec="true" session="bq"
print(run_bq("""
SELECT vv.[Timestamp], SUM(vv.[Value]) AS total_concentration_mg_L, COUNT(*) AS n_fractions
FROM [dbo].[ValueVector] vv
WHERE vv.[Metadata_ID] = 9
GROUP BY vv.[Timestamp]
ORDER BY vv.[Timestamp]
"""))
```

---

### 3.2 Data Integrity Checks

These checks assert structural and domain-logic invariants the schema is designed to maintain. A passing check returns 0 rows.

| ID | Type | Assertion | Expected |
| --- | --- | --- | --- |
| IC-01 | Referential | Every watershed has exactly one `HydrologicalCharacteristics` row | 0 rows |
| IC-02 | Referential | Every watershed has exactly one `UrbanCharacteristics` row | 0 rows |
| IC-03 | Domain logic | All pH values fall within the physical range 0–14 | 0 rows |
| IC-04 | Unit consistency | The unit recorded in `MetaData` matches the default unit of the `Parameter` | 0 rows |
| IC-05 | Cross-table | Equipment used in a `MetaData` row is registered to the same project in `ProjectHasEquipment` | 0 rows |
| IC-06 | Polymorphic (v1.1.0) | Every `MetaData` row with `ValueType = Vector` has at least one `MetaDataAxis` row | 0 rows |
| IC-07 | Polymorphic (v1.1.0) | Every `MetaData` row with `ValueType = Scalar` has no rows in `ValueVector`, `ValueMatrix`, or `ValueImage` | 0 rows |
| IC-08 | Cardinality | No `Value` row references a `Metadata_ID` that does not exist | 0 rows |

---

#### IC-01 — Watersheds without hydrological characteristics

```sql
SELECT w.[name]
FROM [dbo].[Watershed] w
LEFT JOIN [dbo].[HydrologicalCharacteristics] hc ON w.[Watershed_ID] = hc.[Watershed_ID]
WHERE hc.[Watershed_ID] IS NULL;
```

```python exec="true" session="bq"
print(run_ic("""
SELECT w.[name]
FROM [dbo].[Watershed] w
LEFT JOIN [dbo].[HydrologicalCharacteristics] hc ON w.[Watershed_ID] = hc.[Watershed_ID]
WHERE hc.[Watershed_ID] IS NULL
"""))
```

---

#### IC-02 — Watersheds without urban characteristics

```sql
SELECT w.[name]
FROM [dbo].[Watershed] w
LEFT JOIN [dbo].[UrbanCharacteristics] uc ON w.[Watershed_ID] = uc.[Watershed_ID]
WHERE uc.[Watershed_ID] IS NULL;
```

```python exec="true" session="bq"
print(run_ic("""
SELECT w.[name]
FROM [dbo].[Watershed] w
LEFT JOIN [dbo].[UrbanCharacteristics] uc ON w.[Watershed_ID] = uc.[Watershed_ID]
WHERE uc.[Watershed_ID] IS NULL
"""))
```

---

#### IC-03 — pH values outside 0–14

```sql
SELECT v.[Value_ID], v.[Value]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]  m ON v.[Metadata_ID] = m.[Metadata_ID]
JOIN [dbo].[Parameter] p ON m.[Parameter_ID] = p.[Parameter_ID]
WHERE p.[Parameter] = 'pH'
  AND (v.[Value] < 0 OR v.[Value] > 14);
```

```python exec="true" session="bq"
print(run_ic("""
SELECT v.[Value_ID], v.[Value]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]  m ON v.[Metadata_ID] = m.[Metadata_ID]
JOIN [dbo].[Parameter] p ON m.[Parameter_ID] = p.[Parameter_ID]
WHERE p.[Parameter] = 'pH' AND (v.[Value] < 0 OR v.[Value] > 14)
"""))
```

---

#### IC-04 — Unit mismatch between MetaData and Parameter default unit

```sql
SELECT v.[Value_ID], p.[Parameter], pu.[Unit] AS parameter_unit, mu.[Unit] AS metadata_unit
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]  m  ON v.[Metadata_ID]  = m.[Metadata_ID]
JOIN [dbo].[Parameter] p  ON m.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Unit]      pu ON p.[Unit_ID]       = pu.[Unit_ID]
JOIN [dbo].[Unit]      mu ON m.[Unit_ID]       = mu.[Unit_ID]
WHERE m.[Parameter_ID] IS NOT NULL
  AND m.[Unit_ID]      IS NOT NULL
  AND p.[Unit_ID]      != m.[Unit_ID];
```

```python exec="true" session="bq"
print(run_ic("""
SELECT v.[Value_ID], p.[Parameter], pu.[Unit] AS parameter_unit, mu.[Unit] AS metadata_unit
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]  m  ON v.[Metadata_ID]  = m.[Metadata_ID]
JOIN [dbo].[Parameter] p  ON m.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Unit]      pu ON p.[Unit_ID]       = pu.[Unit_ID]
JOIN [dbo].[Unit]      mu ON m.[Unit_ID]       = mu.[Unit_ID]
WHERE m.[Parameter_ID] IS NOT NULL AND m.[Unit_ID] IS NOT NULL AND p.[Unit_ID] != m.[Unit_ID]
"""))
```

---

#### IC-05 — Equipment in MetaData not registered to the project

```sql
SELECT m.[Metadata_ID], e.[identifier]
FROM [dbo].[MetaData]  m
JOIN [dbo].[Equipment] e ON m.[Equipment_ID] = e.[Equipment_ID]
LEFT JOIN [dbo].[ProjectHasEquipment] phe
    ON e.[Equipment_ID] = phe.[Equipment_ID]
   AND m.[Project_ID]   = phe.[Project_ID]
WHERE m.[Equipment_ID]   IS NOT NULL
  AND m.[Project_ID]     IS NOT NULL
  AND phe.[Equipment_ID] IS NULL;
```

```python exec="true" session="bq"
print(run_ic("""
SELECT m.[Metadata_ID], e.[identifier]
FROM [dbo].[MetaData]  m
JOIN [dbo].[Equipment] e ON m.[Equipment_ID] = e.[Equipment_ID]
LEFT JOIN [dbo].[ProjectHasEquipment] phe
    ON e.[Equipment_ID] = phe.[Equipment_ID] AND m.[Project_ID] = phe.[Project_ID]
WHERE m.[Equipment_ID] IS NOT NULL AND m.[Project_ID] IS NOT NULL AND phe.[Equipment_ID] IS NULL
"""))
```

---

#### IC-06 — Vector MetaData without a MetaDataAxis (v1.1.0)

```sql
SELECT m.[Metadata_ID]
FROM [dbo].[MetaData]  m
JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Vector'
  AND NOT EXISTS (
      SELECT 1 FROM [dbo].[MetaDataAxis] mda
      WHERE mda.[Metadata_ID] = m.[Metadata_ID]
  );
```

```python exec="true" session="bq"
print(run_ic("""
SELECT m.[Metadata_ID]
FROM [dbo].[MetaData]  m
JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Vector'
  AND NOT EXISTS (
      SELECT 1 FROM [dbo].[MetaDataAxis] mda
      WHERE mda.[Metadata_ID] = m.[Metadata_ID]
  )
"""))
```

---

#### IC-07 — Scalar MetaData with data in polymorphic tables (v1.1.0)

```sql
SELECT m.[Metadata_ID], 'ValueVector' AS violation_table
FROM [dbo].[MetaData] m
JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueVector] vv WHERE vv.[Metadata_ID] = m.[Metadata_ID])
UNION ALL
SELECT m.[Metadata_ID], 'ValueMatrix'
FROM [dbo].[MetaData] m
JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueMatrix] vm WHERE vm.[Metadata_ID] = m.[Metadata_ID])
UNION ALL
SELECT m.[Metadata_ID], 'ValueImage'
FROM [dbo].[MetaData] m
JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueImage] vi WHERE vi.[Metadata_ID] = m.[Metadata_ID]);
```

```python exec="true" session="bq"
print(run_ic("""
SELECT m.[Metadata_ID], 'ValueVector' AS violation_table
FROM [dbo].[MetaData] m JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueVector] vv WHERE vv.[Metadata_ID] = m.[Metadata_ID])
UNION ALL
SELECT m.[Metadata_ID], 'ValueMatrix'
FROM [dbo].[MetaData] m JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueMatrix] vm WHERE vm.[Metadata_ID] = m.[Metadata_ID])
UNION ALL
SELECT m.[Metadata_ID], 'ValueImage'
FROM [dbo].[MetaData] m JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueImage] vi WHERE vi.[Metadata_ID] = m.[Metadata_ID])
"""))
```

---

#### IC-08 — Orphaned Value rows

```sql
SELECT v.[Value_ID]
FROM [dbo].[Value] v
LEFT JOIN [dbo].[MetaData] m ON v.[Metadata_ID] = m.[Metadata_ID]
WHERE v.[Metadata_ID] IS NOT NULL
  AND m.[Metadata_ID] IS NULL;
```

```python exec="true" session="bq"
print(run_ic("""
SELECT v.[Value_ID]
FROM [dbo].[Value] v
LEFT JOIN [dbo].[MetaData] m ON v.[Metadata_ID] = m.[Metadata_ID]
WHERE v.[Metadata_ID] IS NOT NULL AND m.[Metadata_ID] IS NULL
"""))
```
