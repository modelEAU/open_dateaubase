# Sample Data & Business Query Catalogue

This page documents the **sample dataset** shipped with the database and defines a catalogue of **business queries** the schema is designed to answer.
Result tables in §2 and §3 are **generated live** from the database at documentation-build time — every release reflects the actual state of the data.

---

## 1. Sample Case

### 1.1 Scenario

The sample data represents a realistic **wastewater and stormwater monitoring programme** at a treatment plant and a combined sewer overflow outfall in Quebec City.
The dataset covers: baseline monitoring data (sites, equipment, parameters, scalar measurements), UV-Vis spectrometer spectra, camera images, particle size distribution arrays, lab analyses, and sensor status tracking.

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
| ISCO-001 | ISCO 6712 autosampler | TSS, COD |
| YSI-001 | YSI ProDSS multi-parameter probe | pH, Temperature, Conductivity |
| HACH-001 | Hach 2100Q turbidimeter | No parameter capabilities recorded in this dataset |

### 1.4 Parameters and units

| Parameter | Unit | Channel rows | Total Value rows |
| --- | --- | --- | --- |
| TSS | mg/L | 3 (WWTP-IN, WWTP-OUT, CSO) | 11 |
| COD | mg/L | 1 (WWTP-IN) | 3 |
| pH | pH units | 1 (WWTP-IN) | 5 |
| Temperature | °C | 1 (WWTP-IN) | 3 |
| Conductivity | mS/cm | 0 | 0 |

### 1.5 Campaigns

Equipment is associated to a campaign via `CampaignEquipment`, and sampling points via `CampaignSamplingLocation`.

| Campaign | Equipment | Sampling points |
| --- | --- | --- |
| WWTP Inlet Monitoring 2024 | ISCO-001, YSI-001, HACH-001 | WWTP-IN-01, WWTP-OUT-01 |
| CSO Event Study 2024 | ISCO-001 | CSO-12-OUT |

### 1.6 Scalar measurements (dbo.Value)

22 rows total. Key subsets:

| Value_ID | Parameter | Equipment | Value | Timestamp (UTC) | QA comment |
| --- | --- | --- | --- | --- | --- |
| 1 | TSS | ISCO-001 | 185.0 mg/L | 2024-01-15 13:00 | Normal |
| 2 | TSS | ISCO-001 | 210.5 mg/L | 2024-01-15 19:00 | — |
| 3 | TSS | ISCO-001 | 192.3 mg/L | 2024-01-16 13:00 | Normal |
| 9 | pH | YSI-001 | 7.8 pH units | 2024-01-15 17:00 | **Possible equipment drift** |
| 10 | TSS | ISCO-001 | 350.0 mg/L | 2024-03-20 12:00 | — |
| 11 | TSS | ISCO-001 | 580.2 mg/L | 2024-03-20 14:00 | — |
| 12 | TSS | ISCO-001 | 345.0 mg/L | 2024-03-20 14:00 | **Duplicate (QA/QC)** |
| 13 | TSS | ISCO-001 | 12.5 mg/L | 2024-01-15 13:00 | — |
| 14 | TSS | ISCO-001 | 15.0 mg/L | 2024-01-16 13:00 | — |
| 18 | TSS | ISCO-001 | 200.0 mg/L | **NULL** | Edge case: no timestamp |
| 19 | TSS | ISCO-001 | 145.2 mg/L | 2025-06-15 12:00 EDT | — |
| 20 | TSS | ISCO-001 | 160.8 mg/L | 2025-06-15 18:30 EDT | — |

### 1.7 Polymorphic value types

| Type | Channel_ID | Description | Rows |
| --- | --- | --- | --- |
| Vector (UV-Vis) | 7 | S::CAN spectro::lyser, 200–750 nm, 7 sample bins across 2 timestamps | 10 rows in ValueVector |
| Image | 8 | Camera at CSO-12-OUT during rain, 1920×1080 JPEG | 2 rows in ValueImage |
| Vector (particle size) | 9 | 4-fraction PSD at WWTP-IN-01, 2 timestamps | 8 rows in ValueVector |
| Matrix (size × velocity) | 10 | Joint distribution at WWTP-IN-01, 3×2 bins | 6 rows in ValueMatrix |

The scalar Channel rows (IDs 1–6) all have `ValueType_ID = 1` (Scalar).

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

### 2.7 Channel series — `dbo.Channel`

Each row in `Channel` defines one measurement stream (a parameter measured by an instrument
at a given processing degree).

```python exec="true" session="bq"
print(run_bq("""
SELECT c.[Channel_ID],
       vt.[ValueType_Name]  AS [ValueType],
       p.[Parameter],
       e.[identifier]       AS [Equipment],
       u.[Unit],
       c.[ProcessingDegree]
FROM [dbo].[Channel]        c
LEFT JOIN [dbo].[ValueType]  vt ON c.[ValueType_ID]  = vt.[ValueType_ID]
LEFT JOIN [dbo].[Parameter]  p  ON c.[Parameter_ID]  = p.[Parameter_ID]
LEFT JOIN [dbo].[Equipment]  e  ON c.[Equipment_ID]  = e.[Equipment_ID]
LEFT JOIN [dbo].[Unit]       u  ON c.[Unit_ID]       = u.[Unit_ID]
ORDER BY c.[Channel_ID]
"""))
```

### 2.8 Scalar measurements — `dbo.Value`

```python exec="true" session="bq"
print(run_bq("""
SELECT v.[Value_ID],
       p.[Parameter],
       e.[identifier]  AS [Equipment],
       v.[Value],
       v.[Timestamp]
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
ORDER BY v.[Value_ID]
"""))
```

### 2.9 UV-Vis spectra — `dbo.ValueVector`

```python exec="true" session="bq"
print(run_bq("""
SELECT vv.[Channel_ID],
       vv.[Timestamp],
       vb.[BinIndex],
       (vb.[LowerBound] + vb.[UpperBound]) / 2.0 AS [Wavelength_nm],
       vv.[Value]        AS [Absorbance]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[ValueBin] vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
JOIN [dbo].[ChannelAxis] ca ON vv.[Channel_ID] = ca.[Channel_ID]
JOIN [dbo].[ValueBinningAxis] vba ON ca.[ValueBinningAxis_ID] = vba.[ValueBinningAxis_ID]
WHERE vba.[Name] = 'S::CAN spectro::lyser UV-Vis'
ORDER BY vv.[Timestamp], vb.[BinIndex]
"""))
```

### 2.10 Camera images — `dbo.ValueImage`

```python exec="true" session="bq"
print(run_bq("""
SELECT [ValueImage_ID],
       [Channel_ID],
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

### 2.11 Particle size distribution vectors — `dbo.ValueVector`

```python exec="true" session="bq"
print(run_bq("""
SELECT vv.[Channel_ID],
       vv.[Timestamp],
       vb.[BinIndex],
       vv.[Value]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[ValueBin] vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
JOIN [dbo].[ChannelAxis] ca ON vv.[Channel_ID] = ca.[Channel_ID]
JOIN [dbo].[ValueBinningAxis] vba ON ca.[ValueBinningAxis_ID] = vba.[ValueBinningAxis_ID]
WHERE vba.[Name] = 'LISST-200X particle size'
ORDER BY vv.[Timestamp], vb.[BinIndex]
"""))
```

---

## 3. Business Queries

This section documents queries that the schema is designed to answer.
The test suite `tests/integration/test_business_queries.py` runs every query and asserts that results meet the expected criteria.

| ID | Category | Business question | Test |
| --- | --- | --- | --- |
| BQ-01 | Measurement retrieval | What are all TSS measurements from ISCO-001, sorted by timestamp? | `test_bq01` |
| BQ-02 | Measurement retrieval | What are the TSS measurements from ISCO-001 in January 2024? | `test_bq02` |
| BQ-03 | Measurement retrieval | What is the average TSS concentration per equipment unit? | `test_bq03` |
| BQ-04 | Equipment | Which equipment models are capable of measuring TSS? | `test_bq04` |
| BQ-05 | Equipment | What parameters can each equipment model measure? | `test_bq05` |
| BQ-06 | Equipment | Where has ISCO-001 been deployed (installation history)? | `test_bq06` |
| BQ-07 | Site | What equipment is currently installed at WWTP-IN-01? | `test_bq07` |
| BQ-08 | Watershed | How many measurements of each parameter are available per sampling point in the Saint-Charles watershed? | `test_bq08` |
| BQ-09 | Campaigns | Which campaigns have data from the CSO outfall? | `test_bq09` |
| BQ-10 | Data quality | Which measurements carry a QA/QC comment? | `test_bq10` |
| BQ-11 | Data quality | Are there duplicate measurements at the same Channel and timestamp? | `test_bq11` |
| BQ-12 | Data quality | Which Channel rows have no EquipmentInstallation record covering their data window? | `test_bq12` |
| BQ-13 | Polymorphic types | What value types are recorded per equipment unit? | `test_bq13` |
| BQ-14 | Polymorphic types | What is the UV-Vis absorbance spectrum at 10:00 on 2025-09-10? | `test_bq14` |
| BQ-15 | Polymorphic types | What is the total particle concentration (sum of PSD fractions) at each timestamp? | `test_bq15` |

### 3.1 Detailed queries

---

#### BQ-01 — All TSS measurements from ISCO-001

**Business question:** What are all TSS values measured by ISCO-001, in chronological order?

**SQL:**

```sql
SELECT
    v.[Value_ID],
    v.[Value],
    v.[Timestamp]
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE p.[Parameter]    = 'TSS'
  AND e.[identifier]   = 'ISCO-001'
ORDER BY v.[Timestamp];
```

**Live result** — 6 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT v.[Value_ID], v.[Value], v.[Timestamp]
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE p.[Parameter] = 'TSS' AND e.[identifier] = 'ISCO-001'
  AND c.[Channel_ID] = (
      SELECT TOP 1 c2.[Channel_ID] FROM [dbo].[Channel] c2
      JOIN [dbo].[Parameter] p2 ON c2.[Parameter_ID] = p2.[Parameter_ID]
      JOIN [dbo].[Equipment] e2 ON c2.[Equipment_ID] = e2.[Equipment_ID]
      WHERE p2.[Parameter] = 'TSS' AND e2.[identifier] = 'ISCO-001'
        AND c2.[ProcessingDegree] = 'Raw'
  )
ORDER BY v.[Timestamp]
"""))
```

---

#### BQ-02 — TSS from ISCO-001 in January 2024

**Business question:** Filter measurements to a specific date range (the standard "give me data between dates" query).

**SQL:**

```sql
SELECT v.[Value], v.[Timestamp]
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE p.[Parameter]  = 'TSS'
  AND e.[identifier] = 'ISCO-001'
  AND v.[Timestamp] >= '2024-01-15T00:00:00.0000000+00:00'
  AND v.[Timestamp] <  '2024-01-17T00:00:00.0000000+00:00'
ORDER BY v.[Timestamp];
```

**Live result** — 3 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT v.[Value], v.[Timestamp]
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE p.[Parameter] = 'TSS' AND e.[identifier] = 'ISCO-001'
  AND v.[Timestamp] >= '2024-01-15T00:00:00.0000000+00:00'
  AND v.[Timestamp] <  '2024-01-17T00:00:00.0000000+00:00'
ORDER BY v.[Timestamp]
"""))
```

---

#### BQ-03 — Average TSS per equipment unit

**Business question:** Aggregate statistics per instrument — "what is the typical concentration seen by sensor X?".

**SQL:**

```sql
SELECT
    e.[identifier]      AS equipment,
    AVG(v.[Value])      AS avg_tss_mg_L,
    COUNT(v.[Value_ID]) AS n_measurements
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE p.[Parameter] = 'TSS'
GROUP BY e.[identifier]
ORDER BY e.[identifier];
```

**Live result** — 1 row expected (ISCO-001):

```python exec="true" session="bq"
print(run_bq("""
SELECT e.[identifier] AS equipment, AVG(v.[Value]) AS avg_tss_mg_L, COUNT(v.[Value_ID]) AS n_measurements
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE p.[Parameter] = 'TSS'
GROUP BY e.[identifier]
ORDER BY e.[identifier]
"""))
```

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

**Business question:** "Where has sensor ISCO-001 been deployed over its lifespan?"

**SQL:**

```sql
SELECT e.[identifier],
       sp.[Sampling_point],
       s.[name]          AS site,
       ei.[InstalledDate],
       ei.[RemovedDate]
FROM [dbo].[Equipment]             e
JOIN [dbo].[EquipmentInstallation] ei ON e.[Equipment_ID]        = ei.[Equipment_ID]
JOIN [dbo].[SamplingPoints]        sp ON ei.[Sampling_point_ID]  = sp.[Sampling_point_ID]
JOIN [dbo].[Site]                  s  ON sp.[Site_ID]            = s.[Site_ID]
WHERE e.[identifier] = 'ISCO-001'
ORDER BY ei.[InstalledDate];
```

**Live result** — rows expected per installation record:

```python exec="true" session="bq"
print(run_bq("""
SELECT e.[identifier], sp.[Sampling_point], s.[name] AS site,
       ei.[InstalledDate], ei.[RemovedDate]
FROM [dbo].[Equipment]             e
JOIN [dbo].[EquipmentInstallation] ei ON e.[Equipment_ID]       = ei.[Equipment_ID]
JOIN [dbo].[SamplingPoints]        sp ON ei.[Sampling_point_ID] = sp.[Sampling_point_ID]
JOIN [dbo].[Site]                  s  ON sp.[Site_ID]           = s.[Site_ID]
WHERE e.[identifier] = 'ISCO-001'
ORDER BY ei.[InstalledDate]
"""))
```

---

#### BQ-07 — Equipment currently installed at a location

**Business question:** "What sensors are currently active at WWTP-IN-01?"

**SQL:**

```sql
SELECT e.[identifier], em.[Equipment_model], ei.[InstalledDate]
FROM [dbo].[EquipmentInstallation] ei
JOIN [dbo].[Equipment]             e  ON ei.[Equipment_ID]       = e.[Equipment_ID]
JOIN [dbo].[EquipmentModel]        em ON e.[model_ID]            = em.[Equipment_model_ID]
JOIN [dbo].[SamplingPoints]        sp ON ei.[Sampling_point_ID]  = sp.[Sampling_point_ID]
WHERE sp.[Sampling_point] = 'WWTP-IN-01'
  AND ei.[RemovedDate]    IS NULL
ORDER BY e.[identifier];
```

**Live result** — rows expected per currently installed sensor:

```python exec="true" session="bq"
print(run_bq("""
SELECT e.[identifier], em.[Equipment_model], ei.[InstalledDate]
FROM [dbo].[EquipmentInstallation] ei
JOIN [dbo].[Equipment]             e  ON ei.[Equipment_ID]       = e.[Equipment_ID]
JOIN [dbo].[EquipmentModel]        em ON e.[model_ID]            = em.[Equipment_model_ID]
JOIN [dbo].[SamplingPoints]        sp ON ei.[Sampling_point_ID]  = sp.[Sampling_point_ID]
WHERE sp.[Sampling_point] = 'WWTP-IN-01'
  AND ei.[RemovedDate] IS NULL
ORDER BY e.[identifier]
"""))
```

---

#### BQ-08 — Measurement counts per parameter and sampling point in a watershed

**Business question:** "How much data do we have for each parameter at each location in the Saint-Charles watershed?"

Location context is derived at query time via `EquipmentInstallation`.

**SQL:**

```sql
SELECT
    p.[Parameter],
    sp.[Sampling_point],
    COUNT(v.[Value_ID]) AS n_measurements
FROM [dbo].[Value]             v
JOIN [dbo].[Channel]           c   ON v.[Channel_ID]          = c.[Channel_ID]
JOIN [dbo].[Parameter]         p   ON c.[Parameter_ID]         = p.[Parameter_ID]
JOIN [dbo].[Equipment]         e   ON c.[Equipment_ID]         = e.[Equipment_ID]
JOIN [dbo].[EquipmentInstallation] ei ON e.[Equipment_ID]      = ei.[Equipment_ID]
JOIN [dbo].[SamplingPoints]    sp  ON ei.[Sampling_point_ID]   = sp.[Sampling_point_ID]
JOIN [dbo].[Site]              s   ON sp.[Site_ID]             = s.[Site_ID]
JOIN [dbo].[Watershed]         w   ON s.[Watershed_ID]         = w.[Watershed_ID]
WHERE w.[name] = 'Riviere Saint-Charles'
GROUP BY p.[Parameter], sp.[Sampling_point]
ORDER BY p.[Parameter], sp.[Sampling_point];
```

**Live result** — rows per (parameter, sampling-point) combination in the catchment:

```python exec="true" session="bq"
print(run_bq("""
SELECT p.[Parameter], sp.[Sampling_point], COUNT(v.[Value_ID]) AS n_measurements
FROM [dbo].[Value]             v
JOIN [dbo].[Channel]           c   ON v.[Channel_ID]         = c.[Channel_ID]
JOIN [dbo].[Parameter]         p   ON c.[Parameter_ID]        = p.[Parameter_ID]
JOIN [dbo].[Equipment]         e   ON c.[Equipment_ID]        = e.[Equipment_ID]
JOIN [dbo].[EquipmentInstallation] ei ON e.[Equipment_ID]     = ei.[Equipment_ID]
JOIN [dbo].[SamplingPoints]    sp  ON ei.[Sampling_point_ID]  = sp.[Sampling_point_ID]
JOIN [dbo].[Site]              s   ON sp.[Site_ID]            = s.[Site_ID]
JOIN [dbo].[Watershed]         w   ON s.[Watershed_ID]        = w.[Watershed_ID]
WHERE w.[name] = 'Riviere Saint-Charles'
GROUP BY p.[Parameter], sp.[Sampling_point]
ORDER BY p.[Parameter], sp.[Sampling_point]
"""))
```

---

#### BQ-09 — Campaigns at a sampling point

**Business question:** "Which campaigns have data collected at the CSO outfall?"

**SQL:**

```sql
SELECT DISTINCT cam.[Campaign_name], cam.[Start_date], cam.[End_date]
FROM [dbo].[Campaign]              cam
JOIN [dbo].[CampaignSamplingPoints] csp ON cam.[Campaign_ID]     = csp.[Campaign_ID]
JOIN [dbo].[SamplingPoints]         sp  ON csp.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE sp.[Sampling_point] = 'CSO-12-OUT'
ORDER BY cam.[Start_date];
```

**Live result** — rows expected per campaign covering the CSO outfall:

```python exec="true" session="bq"
print(run_bq("""
SELECT DISTINCT cam.[Campaign_name], cam.[Start_date], cam.[End_date]
FROM [dbo].[Campaign]              cam
JOIN [dbo].[CampaignSamplingPoints] csp ON cam.[Campaign_ID]      = csp.[Campaign_ID]
JOIN [dbo].[SamplingPoints]         sp  ON csp.[Sampling_point_ID] = sp.[Sampling_point_ID]
WHERE sp.[Sampling_point] = 'CSO-12-OUT'
ORDER BY cam.[Start_date]
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
    e.[identifier]  AS equipment,
    v.[Value],
    v.[Timestamp],
    c.[Comment]
FROM [dbo].[Value]     v
JOIN [dbo].[Comments]  c  ON v.[Comment_ID]   = c.[Comment_ID]
JOIN [dbo].[Channel]   ch ON v.[Channel_ID]   = ch.[Channel_ID]
JOIN [dbo].[Parameter] p  ON ch.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON ch.[Equipment_ID] = e.[Equipment_ID]
WHERE c.[Comment] IS NOT NULL
ORDER BY v.[Value_ID];
```

**Live result** — 4 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT v.[Value_ID], p.[Parameter], e.[identifier] AS equipment,
       v.[Value], v.[Timestamp], c.[Comment]
FROM [dbo].[Value]     v
JOIN [dbo].[Comments]  c  ON v.[Comment_ID]    = c.[Comment_ID]
JOIN [dbo].[Channel]   ch ON v.[Channel_ID]    = ch.[Channel_ID]
JOIN [dbo].[Parameter] p  ON ch.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON ch.[Equipment_ID] = e.[Equipment_ID]
WHERE c.[Comment] IS NOT NULL
ORDER BY v.[Value_ID]
"""))
```

---

#### BQ-11 — Duplicate measurements at the same timestamp

**Business question:** "Are there cases where the same Channel has two readings at the exact same timestamp? (Indicates a QA/QC duplicate or a data ingestion error.)"

**SQL:**

```sql
SELECT
    v.[Channel_ID],
    p.[Parameter],
    e.[identifier]  AS equipment,
    v.[Timestamp],
    COUNT(*)        AS duplicate_count
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE v.[Timestamp] IS NOT NULL
GROUP BY v.[Channel_ID], p.[Parameter], e.[identifier], v.[Timestamp]
HAVING COUNT(*) > 1;
```

**Live result** — 1 row expected (the intentional QA/QC duplicate at the CSO outfall):

```python exec="true" session="bq"
print(run_bq("""
SELECT v.[Channel_ID], p.[Parameter], e.[identifier] AS equipment,
       v.[Timestamp], COUNT(*) AS duplicate_count
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE v.[Timestamp] IS NOT NULL
GROUP BY v.[Channel_ID], p.[Parameter], e.[identifier], v.[Timestamp]
HAVING COUNT(*) > 1
"""))
```

---

#### BQ-12 — Channel rows without any EquipmentInstallation record

**Business question:** "Which measurement channels have no deployment record linking them to a physical location?"

**SQL:**

```sql
SELECT c.[Channel_ID], p.[Parameter], e.[identifier] AS equipment
FROM [dbo].[Channel]   c
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE NOT EXISTS (
    SELECT 1 FROM [dbo].[EquipmentInstallation] ei
    WHERE ei.[Equipment_ID] = c.[Equipment_ID]
)
ORDER BY c.[Channel_ID];
```

**Live result** — 0 rows expected (all equipment in the sample data has installation records):

```python exec="true" session="bq"
print(run_bq("""
SELECT c.[Channel_ID], p.[Parameter], e.[identifier] AS equipment
FROM [dbo].[Channel]   c
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
WHERE NOT EXISTS (
    SELECT 1 FROM [dbo].[EquipmentInstallation] ei
    WHERE ei.[Equipment_ID] = c.[Equipment_ID]
)
ORDER BY c.[Channel_ID]
"""))
```

---

#### BQ-13 — Value types per equipment unit

**Business question:** "What kinds of data (scalar, spectral, image, array) are collected by each instrument?"

**SQL:**

```sql
SELECT
    e.[identifier]      AS equipment,
    vt.[ValueType_Name],
    COUNT(*)            AS n_channels
FROM [dbo].[Channel]   c
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
GROUP BY e.[identifier], vt.[ValueType_Name]
ORDER BY e.[identifier], vt.[ValueType_Name];
```

**Live result** — 6 rows expected:

```python exec="true" session="bq"
print(run_bq("""
SELECT e.[identifier] AS equipment, vt.[ValueType_Name], COUNT(*) AS n_channels
FROM [dbo].[Channel]   c
JOIN [dbo].[Equipment] e  ON c.[Equipment_ID] = e.[Equipment_ID]
JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
GROUP BY e.[identifier], vt.[ValueType_Name]
ORDER BY e.[identifier], vt.[ValueType_Name]
"""))
```

---

#### BQ-14 — UV-Vis absorption spectrum at a specific timestamp

**Business question:** "Give me the full absorbance spectrum recorded at 14:00 on 2025-09-10."

**SQL:**

```sql
SELECT
    vb.[BinIndex],
    (vb.[LowerBound] + vb.[UpperBound]) / 2.0 AS wavelength_nm,
    vv.[Value]       AS absorbance,
    vv.[QualityCode]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[ValueBin]    vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
WHERE vv.[Channel_ID] = 7
  AND vv.[Timestamp]  = '2025-09-10T14:00:00.0000000'
ORDER BY vb.[BinIndex];
```

**Live result** — 7 rows expected (all bins at this timestamp):

```python exec="true" session="bq"
print(run_bq("""
SELECT vb.[BinIndex], (vb.[LowerBound] + vb.[UpperBound]) / 2.0 AS wavelength_nm,
       vv.[Value] AS absorbance, vv.[QualityCode]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[ValueBin]    vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
WHERE vv.[Channel_ID] = 7
  AND vv.[Timestamp]  = '2025-09-10T14:00:00.0000000'
ORDER BY vb.[BinIndex]
"""))
```

---

#### BQ-15 — Total particle mass per timestamp from PSD vector

**Business question:** "What is the total suspended particle concentration (sum of all size fractions) at each measurement time?"

**SQL:**

```sql
SELECT
    vv.[Timestamp],
    SUM(vv.[Value]) AS total_concentration_mg_L,
    COUNT(*)         AS n_fractions
FROM [dbo].[ValueVector] vv
WHERE vv.[Channel_ID] = 9
GROUP BY vv.[Timestamp]
ORDER BY vv.[Timestamp];
```

**Live result** — 2 rows expected (T1 = 91.6, T2 = 107.7 mg/L):

```python exec="true" session="bq"
print(run_bq("""
SELECT vv.[Timestamp], SUM(vv.[Value]) AS total_concentration_mg_L, COUNT(*) AS n_fractions
FROM [dbo].[ValueVector] vv
WHERE vv.[Channel_ID] = 9
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
| IC-04 | Unit consistency | The unit recorded in `Channel` matches the default unit of the `Parameter` | 0 rows |
| IC-05 | Referential | Every `Channel` row references an existing `Equipment` and `Parameter` | 0 rows |
| IC-06 | Polymorphic | Every `Channel` row with `ValueType = Vector` has at least one `ChannelAxis` row | 0 rows |
| IC-07 | Polymorphic | Every `Channel` row with `ValueType = Scalar` has no rows in `ValueVector`, `ValueMatrix`, or `ValueImage` | 0 rows |
| IC-08 | Cardinality | No `Value` row references a `Channel_ID` that does not exist | 0 rows |

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
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
WHERE p.[Parameter] = 'pH'
  AND (v.[Value] < 0 OR v.[Value] > 14);
```

```python exec="true" session="bq"
print(run_ic("""
SELECT v.[Value_ID], v.[Value]
FROM [dbo].[Value]     v
JOIN [dbo].[Channel]   c  ON v.[Channel_ID]   = c.[Channel_ID]
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
WHERE p.[Parameter] = 'pH' AND (v.[Value] < 0 OR v.[Value] > 14)
"""))
```

---

#### IC-04 — Unit mismatch between Channel and Parameter default unit

```sql
SELECT c.[Channel_ID], p.[Parameter], pu.[Unit] AS parameter_unit, cu.[Unit] AS channel_unit
FROM [dbo].[Channel]   c
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Unit]      pu ON p.[Unit_ID]       = pu.[Unit_ID]
JOIN [dbo].[Unit]      cu ON c.[Unit_ID]       = cu.[Unit_ID]
WHERE c.[Parameter_ID] IS NOT NULL
  AND c.[Unit_ID]      IS NOT NULL
  AND p.[Unit_ID]      != c.[Unit_ID];
```

```python exec="true" session="bq"
print(run_ic("""
SELECT c.[Channel_ID], p.[Parameter], pu.[Unit] AS parameter_unit, cu.[Unit] AS channel_unit
FROM [dbo].[Channel]   c
JOIN [dbo].[Parameter] p  ON c.[Parameter_ID] = p.[Parameter_ID]
JOIN [dbo].[Unit]      pu ON p.[Unit_ID]       = pu.[Unit_ID]
JOIN [dbo].[Unit]      cu ON c.[Unit_ID]       = cu.[Unit_ID]
WHERE c.[Parameter_ID] IS NOT NULL AND c.[Unit_ID] IS NOT NULL AND p.[Unit_ID] != c.[Unit_ID]
"""))
```

---

#### IC-05 — Channel rows with missing Equipment or Parameter

```sql
SELECT c.[Channel_ID]
FROM [dbo].[Channel] c
WHERE c.[Equipment_ID]  IS NULL
   OR c.[Parameter_ID]  IS NULL;
```

```python exec="true" session="bq"
print(run_ic("""
SELECT c.[Channel_ID]
FROM [dbo].[Channel] c
WHERE c.[Equipment_ID] IS NULL OR c.[Parameter_ID] IS NULL
"""))
```

---

#### IC-06 — Vector Channel without a ChannelAxis

```sql
SELECT c.[Channel_ID]
FROM [dbo].[Channel]   c
JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Vector'
  AND NOT EXISTS (
      SELECT 1 FROM [dbo].[ChannelAxis] ca
      WHERE ca.[Channel_ID] = c.[Channel_ID]
  );
```

```python exec="true" session="bq"
print(run_ic("""
SELECT c.[Channel_ID]
FROM [dbo].[Channel]   c
JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Vector'
  AND NOT EXISTS (
      SELECT 1 FROM [dbo].[ChannelAxis] ca
      WHERE ca.[Channel_ID] = c.[Channel_ID]
  )
"""))
```

---

#### IC-07 — Scalar Channel with data in polymorphic tables

```sql
SELECT c.[Channel_ID], 'ValueVector' AS violation_table
FROM [dbo].[Channel] c
JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueVector] vv WHERE vv.[Channel_ID] = c.[Channel_ID])
UNION ALL
SELECT c.[Channel_ID], 'ValueMatrix'
FROM [dbo].[Channel] c
JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueMatrix] vm WHERE vm.[Channel_ID] = c.[Channel_ID])
UNION ALL
SELECT c.[Channel_ID], 'ValueImage'
FROM [dbo].[Channel] c
JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueImage] vi WHERE vi.[Channel_ID] = c.[Channel_ID]);
```

```python exec="true" session="bq"
print(run_ic("""
SELECT c.[Channel_ID], 'ValueVector' AS violation_table
FROM [dbo].[Channel] c JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueVector] vv WHERE vv.[Channel_ID] = c.[Channel_ID])
UNION ALL
SELECT c.[Channel_ID], 'ValueMatrix'
FROM [dbo].[Channel] c JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueMatrix] vm WHERE vm.[Channel_ID] = c.[Channel_ID])
UNION ALL
SELECT c.[Channel_ID], 'ValueImage'
FROM [dbo].[Channel] c JOIN [dbo].[ValueType] vt ON c.[ValueType_ID] = vt.[ValueType_ID]
WHERE vt.[ValueType_Name] = 'Scalar'
  AND EXISTS (SELECT 1 FROM [dbo].[ValueImage] vi WHERE vi.[Channel_ID] = c.[Channel_ID])
"""))
```

---

#### IC-08 — Orphaned Value rows

```sql
SELECT v.[Value_ID]
FROM [dbo].[Value]   v
LEFT JOIN [dbo].[Channel] c ON v.[Channel_ID] = c.[Channel_ID]
WHERE v.[Channel_ID] IS NOT NULL
  AND c.[Channel_ID] IS NULL;
```

```python exec="true" session="bq"
print(run_ic("""
SELECT v.[Value_ID]
FROM [dbo].[Value]   v
LEFT JOIN [dbo].[Channel] c ON v.[Channel_ID] = c.[Channel_ID]
WHERE v.[Channel_ID] IS NOT NULL AND c.[Channel_ID] IS NULL
"""))
```
