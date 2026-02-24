# Phase B — MetaData → Channel Rename (v1.10.0 → v2.0.0)

## Context

The ERD still shows `MetaData` because Phase A (v1.9.0) only cleaned up columns — it didn't rename the table. Phase B completes the semantic rename: `MetaData` → `Channel`. This makes the domain model legible (a Channel is an invariant data stream descriptor, not a bundle of context) and enables self-configuring ingestion.

Lab data gets its own tables (`LabAnalysis` + `LabValue`) because discrete sample results tied to a physical sample don't fit the continuous-stream Channel abstraction. Existing lab rows in MetaData stay as-is (they become legacy Channel rows); new lab writes go to the dedicated tables.

Two pre-existing broken queries from v1.9.0 are fixed here since we're rewriting those files anyway.

---

## Migration Strategy: sp_rename (in-place)

Use MSSQL `sp_rename` for all table and column renames — no data movement, FKs remain valid (engine uses object IDs, not names). Constraint names (e.g. `PK_MetaData`) will cosmetically mismatch after rename; accepted as-is.

---

## Forward Migration (v1.10.0 → v2.0.0)

File: `migrations/v1.10.0_to_v2.0.0_mssql.sql`

### Step 1: Create LabAnalysis and LabValue tables
```sql
CREATE TABLE [dbo].[LabAnalysis] (
    [LabAnalysis_ID]   INT IDENTITY(1,1) NOT NULL,
    [Sample_ID]        INT NOT NULL REFERENCES [dbo].[Sample]([Sample_ID]),
    [Laboratory_ID]    INT NULL REFERENCES [dbo].[Laboratory]([Laboratory_ID]),
    [AnalystPerson_ID] INT NULL REFERENCES [dbo].[Person]([Person_ID]),
    [Procedure_ID]     INT NULL REFERENCES [dbo].[Procedures]([Procedure_ID]),
    [AnalyzedAt]       DATETIME2(7) NOT NULL CONSTRAINT [DF_LabAnalysis_AnalyzedAt] DEFAULT SYSUTCDATETIME(),
    [Campaign_ID]      INT NULL REFERENCES [dbo].[Campaign]([Campaign_ID]),
    [Notes]            NVARCHAR(500) NULL,
    CONSTRAINT [PK_LabAnalysis] PRIMARY KEY ([LabAnalysis_ID])
);

CREATE TABLE [dbo].[LabValue] (
    [LabValue_ID]      INT IDENTITY(1,1) NOT NULL,
    [LabAnalysis_ID]   INT NOT NULL REFERENCES [dbo].[LabAnalysis]([LabAnalysis_ID]),
    [Parameter_ID]     INT NOT NULL REFERENCES [dbo].[Parameter]([Parameter_ID]),
    [Unit_ID]          INT NOT NULL REFERENCES [dbo].[Unit]([Unit_ID]),
    [Value]            FLOAT NOT NULL,
    [Replicate]        INT NOT NULL CONSTRAINT [DF_LabValue_Replicate] DEFAULT 1,
    [QualityCode]      INT NULL,
    [Comment_ID]       INT NULL REFERENCES [dbo].[Comments]([Comment_ID]),
    CONSTRAINT [PK_LabValue] PRIMARY KEY ([LabValue_ID])
);
```

### Step 2: Drop lab FK constraints from MetaData
```sql
-- Names must be verified against actual DB; adjust if constraint names differ
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT IF EXISTS [FK_MetaData_Sample];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT IF EXISTS [FK_MetaData_Laboratory];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT IF EXISTS [FK_MetaData_AnalystPerson];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT IF EXISTS [FK_MetaData_Procedures];
```

### Step 3: Drop lab columns from MetaData
```sql
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Sample_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Laboratory_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [AnalystPerson_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Procedure_ID];
```

### Step 4: Rename Metadata_ID → Channel_ID in all child tables
```sql
EXEC sp_rename 'dbo.Value.Metadata_ID',               'Channel_ID', 'COLUMN';
EXEC sp_rename 'dbo.ValueVector.Metadata_ID',          'Channel_ID', 'COLUMN';
EXEC sp_rename 'dbo.ValueMatrix.Metadata_ID',          'Channel_ID', 'COLUMN';
EXEC sp_rename 'dbo.ValueImage.Metadata_ID',           'Channel_ID', 'COLUMN';
EXEC sp_rename 'dbo.DataLineage.Metadata_ID',          'Channel_ID', 'COLUMN';
EXEC sp_rename 'dbo.DataLineage.SourceMetadata_ID',    'SourceChannel_ID', 'COLUMN';
EXEC sp_rename 'dbo.Annotation.Metadata_ID',           'Channel_ID', 'COLUMN';
EXEC sp_rename 'dbo.MetaDataAxis.Metadata_ID',         'Channel_ID', 'COLUMN';
EXEC sp_rename 'dbo.EquipmentEventMetaData.Metadata_ID','Channel_ID', 'COLUMN';
```

### Step 5: Rename MetaData PK column
```sql
EXEC sp_rename 'dbo.MetaData.Metadata_ID', 'Channel_ID', 'COLUMN';
```

### Step 6: Rename tables
```sql
EXEC sp_rename 'dbo.MetaData',              'Channel';
EXEC sp_rename 'dbo.MetaDataAxis',          'ChannelAxis';
EXEC sp_rename 'dbo.EquipmentEventMetaData','EquipmentEventChannel';
```

### Step 7: Rename unique index
```sql
EXEC sp_rename 'dbo.Channel.UQ_MetaData_SensorStream', 'UQ_Channel_SensorStream', 'INDEX';
```

### Step 8: ALTER views to reference Channel + Channel_ID
Rebuild `vw_ChannelStatus` and `vw_DeviceStatus` with updated table/column names.

### Step 9: Update SchemaVersion
```sql
INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [AppliedAt])
VALUES ('2.0.0', 'Phase B — MetaData → Channel rename, LabAnalysis/LabValue tables', SYSUTCDATETIME());
```

---

## Rollback Migration (v2.0.0 → v1.10.0)

File: `migrations/v1.10.0_to_v2.0.0_mssql_rollback.sql`

Reverse all sp_rename operations + restore lab columns + drop LabAnalysis/LabValue + restore views.
Order: rebuild views → rename tables back → rename columns back → add lab columns → add lab FK constraints → DROP LabValue → DROP LabAnalysis → update SchemaVersion.

---

## Files to Change

### Schema Dictionary (YAML)

| File | Change |
|------|--------|
| `schema_dictionary/tables/Channel.yaml` | New — replaces MetaData.yaml; all columns, no lab columns, Channel_ID as PK |
| `schema_dictionary/tables/ChannelAxis.yaml` | New — replaces MetaDataAxis.yaml; Channel_ID FK |
| `schema_dictionary/tables/EquipmentEventChannel.yaml` | New — replaces EquipmentEventMetaData.yaml; Channel_ID FK |
| `schema_dictionary/tables/LabAnalysis.yaml` | New — 7 columns |
| `schema_dictionary/tables/LabValue.yaml` | New — 8 columns |
| `schema_dictionary/tables/Value.yaml` | FK column: `Metadata_ID` → `Channel_ID` |
| `schema_dictionary/tables/ValueVector.yaml` | FK column: `Metadata_ID` → `Channel_ID` |
| `schema_dictionary/tables/ValueMatrix.yaml` | FK column: `Metadata_ID` → `Channel_ID` |
| `schema_dictionary/tables/ValueImage.yaml` | FK column: `Metadata_ID` → `Channel_ID` |
| `schema_dictionary/tables/DataLineage.yaml` | FK columns: `Metadata_ID` → `Channel_ID`, `SourceMetadata_ID` → `SourceChannel_ID` |
| `schema_dictionary/tables/Annotation.yaml` | FK column: `Metadata_ID` → `Channel_ID` |
| `schema_dictionary/views/vw_ChannelStatus.yaml` | Update Channel/Channel_ID references |
| `schema_dictionary/views/vw_DeviceStatus.yaml` | Update Channel/Channel_ID references |
| `schema_dictionary/deprecated/MetaData.yaml` | Move from `tables/` |
| `schema_dictionary/deprecated/MetaDataAxis.yaml` | Move from `tables/` |
| `schema_dictionary/deprecated/EquipmentEventMetaData.yaml` | Move from `tables/` |
| `schema_dictionary/version.yaml` | `1.10.0` → `2.0.0` |

### Migrations & SQL Baseline

| File | Change |
|------|--------|
| `migrations/v1.10.0_to_v2.0.0_mssql.sql` | New forward migration |
| `migrations/v1.10.0_to_v2.0.0_mssql_rollback.sql` | New rollback |
| `sql_generation_scripts/v2.0.0_create_mssql.sql` | New full baseline (auto-gen from YAML via `mkdocs build`) |

### API — Repositories

| File | Change |
|------|--------|
| `api/v1/repositories/metadata_repository.py` → `channel_repository.py` | Rename file; `MetaData` → `Channel`, `metadata_id` → `channel_id`, `MetadataOut` → `ChannelOut` in SQL + function names |
| `api/v1/repositories/ingestion_repository.py` | `MetaData` → `Channel`, `Metadata_ID` → `Channel_ID` throughout; add `insert_lab_analysis()` + `insert_lab_value()`; remove `find_or_create_metadata_for_lab()` |
| `api/v1/repositories/value_repository.py` | `Metadata_ID` → `Channel_ID` in all 4 value table queries |
| `api/v1/repositories/annotation_repository.py` | `[dbo].[MetaData]` → `[dbo].[Channel]`, `Metadata_ID` → `Channel_ID` |
| `api/v1/repositories/sensor_status_repository.py` | `[dbo].[MetaData]` → `[dbo].[Channel]`, `Metadata_ID` → `Channel_ID`; rename `check_metadata_exists` → `check_channel_exists`, `get_equipment_for_metadata` → `get_equipment_for_channel` |
| `api/v1/repositories/campaign_repository.py` | Update `get_campaign_context()` — replace `m.[Metadata_ID]` references with `m.[Channel_ID]` |

### API — Schemas

| File | Change |
|------|--------|
| `api/v1/schemas/metadata.py` → `channel.py` | Rename file; `MetadataOut` → `ChannelOut`; `metadata_id` → `channel_id`; remove `laboratory_id`, `laboratory_name`, `analyst_id`, `analyst_name` fields |
| `api/v1/schemas/ingestion.py` | `IngestResponse.metadata_id` → `channel_id`; add `LabIngestResponse` with `lab_analysis_id` |
| `api/v1/schemas/timeseries.py` | `TimeseriesOut.metadata_id` → `channel_id` |
| `api/v1/schemas/lineage.py` | `metadata_id` → `channel_id` throughout |
| `api/v1/schemas/sensor_status.py` | `measurement_metadata_id` → `measurement_channel_id`, `metadata_id` → `channel_id` |
| `api/v1/schemas/annotations.py` | `AnnotationResponse.metadata_id` → `channel_id` |

### API — Endpoints

| File | Change |
|------|--------|
| `api/v1/endpoints/metadata.py` → `channels.py` | Rename file; `GET /metadata` → `GET /channels`; `GET /metadata/{metadata_id}` → `GET /channels/{channel_id}`; import `ChannelOut` from `channel.py` |
| `api/v1/endpoints/ingest.py` | Add lab ingest endpoint (`POST /ingest/lab`) that calls `insert_lab_analysis()` + `insert_lab_value()`; update sensor/processed paths to return `channel_id` |
| `api/v1/endpoints/timeseries.py` | Update `metadata_id` path param → `channel_id` |
| `api/v1/endpoints/annotations.py` | Update `metadata_id` references → `channel_id` |
| `api/v1/endpoints/sensor_status.py` | Update `metadata_id` → `channel_id` |
| `api/v1/endpoints/lineage.py` | Update `metadata_id` → `channel_id` |
| `api/v1/router.py` | `include_router(metadata_router, prefix="/metadata")` → `include_router(channel_router, prefix="/channels")` |

### API — Services

| File | Change |
|------|--------|
| `api/v1/services/timeseries_service.py` | Fix `get_timeseries_by_context()`: replace `m.[Sampling_point_ID]` with `m.[Equipment_ID]`; update `metadata_id` → `channel_id` |
| `api/v1/services/annotation_service.py` | `metadata_repository.get_metadata_by_id()` → `channel_repository.get_channel_by_id()`; `metadata_id` → `channel_id` |
| `api/v1/services/sensor_status_service.py` | `metadata_id` → `channel_id` throughout |
| `api/v1/services/lineage_service.py` | `source_metadata_ids` → `source_channel_ids`, `output_metadata_id` → `output_channel_id` |

### Source Code

| File | Change |
|------|--------|
| `src/open_dateaubase/lineage.py` | All SQL: `[dbo].[MetaData]` → `[dbo].[Channel]`, `[Metadata_ID]` → `[Channel_ID]`, `[SourceMetadata_ID]` → `[SourceChannel_ID]`; rename Python params `metadata_id` → `channel_id` |
| `src/open_dateaubase/meteaudata_bridge.py` | Rewrite `load_signal_context()`: drop references to dropped columns; derive location from `EquipmentInstallation`, campaign from `CampaignEquipment`; use `[dbo].[Channel]` + `[Channel_ID]` |

### Tests

| File | Change |
|------|--------|
| `tests/api/contract/test_schema_contracts.py` | `REQUIRED_METADATA_FIELDS` → `REQUIRED_CHANNEL_FIELDS` (remove `laboratory_id`, `laboratory_name`, `analyst_id`, `analyst_name`; rename `metadata_id` → `channel_id`); rename `TestMetadataContract` → `TestChannelContract`; update `_mock_metadata()` → `_mock_channel()`; update ingestion test to check `channel_id` not `metadata_id` |

---

## Implementation Order

1. Write migration SQL (forward + rollback)
2. Update schema dictionary YAMLs (new files + FK column updates + archive)
3. Update `schema_dictionary/version.yaml`
4. Rename `metadata_repository.py` → `channel_repository.py` and update content
5. Update `ingestion_repository.py` (Channel rename + lab functions)
6. Update `value_repository.py`, `annotation_repository.py`, `sensor_status_repository.py`
7. Rename `schemas/metadata.py` → `channel.py` and update content; update 5 other schema files
8. Rename `endpoints/metadata.py` → `channels.py` and update; update 5 other endpoint files
9. Update `router.py`
10. Update 4 service files (fix broken timeseries query)
11. Rewrite `lineage.py` and `meteaudata_bridge.py`
12. Update contract tests
13. Run `uv run pytest tests/api/contract/ tests/unit/`

---

## Rewrite: `load_signal_context()` in `meteaudata_bridge.py`

Current function references 5 columns dropped in v1.9.0: `Sampling_point_ID`, `Campaign_ID`, `Project_ID`, `Contact_ID`, `Purpose_ID`. Replacement query:

```sql
SELECT
    c.[Channel_ID],
    c.[Equipment_ID],
    c.[Parameter_ID],
    c.[Unit_ID],
    c.[DataProvenance_ID],
    c.[ProcessingDegree],
    c.[ValueType_ID],
    -- Derive location from most recent EquipmentInstallation at time T
    ei.[Sampling_point_ID],
    sp.[Name] AS SamplingPointName,
    -- Derive campaign from CampaignEquipment active at time T
    ce.[Campaign_ID],
    camp.[Name] AS CampaignName
FROM [dbo].[Channel] c
LEFT JOIN [dbo].[EquipmentInstallation] ei
    ON ei.[Equipment_ID] = c.[Equipment_ID]
    AND ei.[InstalledDate] <= @Timestamp
    AND (ei.[RemovedDate] IS NULL OR ei.[RemovedDate] > @Timestamp)
LEFT JOIN [dbo].[SamplingPoints] sp ON sp.[Sampling_point_ID] = ei.[Sampling_point_ID]
LEFT JOIN [dbo].[CampaignEquipment] ce
    ON ce.[Equipment_ID] = c.[Equipment_ID]
    AND ce.[Campaign_ID] IN (
        SELECT [Campaign_ID] FROM [dbo].[Campaign]
        WHERE [StartDate] <= @Timestamp AND ([EndDate] IS NULL OR [EndDate] > @Timestamp)
    )
LEFT JOIN [dbo].[Campaign] camp ON camp.[Campaign_ID] = ce.[Campaign_ID]
WHERE c.[Channel_ID] = @Channel_ID
```

## Fix: `get_timeseries_by_context()` in `timeseries_service.py`

Replace broken `WHERE m.[Sampling_point_ID] = ?` (column dropped in v1.9.0) with `WHERE m.[Equipment_ID] = ?`.

---

## Verification

1. `uv run pytest tests/api/contract/` — all tests pass (metadata → channel field renames)
2. `uv run pytest tests/unit/` — schema YAML tests: MetaData.yaml now in `deprecated/`, Channel.yaml in `tables/`, version.yaml = `2.0.0`
3. `uv run pytest tests/unit/` — migration test: `v1.10.0_to_v2.0.0_mssql.sql` + rollback pair both exist
4. Docker MSSQL: run forward migration; verify:
   - `SELECT OBJECT_ID('dbo.Channel')` → non-null
   - `SELECT OBJECT_ID('dbo.MetaData')` → NULL
   - `SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='Channel' AND COLUMN_NAME='Sample_ID'` → 0 rows
   - `SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='Value' AND COLUMN_NAME='Channel_ID'` → 1 row
   - `SELECT OBJECT_ID('dbo.LabAnalysis')` → non-null
5. POST `/api/v1/ingest/sensor` → response contains `channel_id` not `metadata_id`
6. POST `/api/v1/ingest/lab` → `LabAnalysis` + `LabValue` rows created
7. GET `/api/v1/channels/{id}` → 200; response contains `channel_id`
8. GET `/api/v1/channels/{id}/timeseries` → 200
9. Run rollback; verify `MetaData` table restored, `Channel` gone; re-apply forward migration
10. `uv run pytest tests/integration/ -m db`

---

# Project Drop — v1.9.0 → v1.10.0

## Context

Phase A (v1.9.0) already dropped `Project_ID` from the `MetaData` table. The `Project` table is now orphaned — its only remaining coupling is a `Campaign.Project_ID` FK (described in the YAML as "backward-compatibility link"). The user confirmed: **Project is fully superseded by Campaign. Drop everything.**

Scope confirmed by user: **Full drop**
- Drop tables: `Project`, `ProjectHasContact`, `ProjectHasEquipment`, `ProjectHasSamplingPoints`
- Drop `Campaign.Project_ID` column (FK to Project)
- Remove `project_id` / `project_name` from Campaign API response
- Fix pre-existing broken query in `get_campaign_context()` (Campaign_ID dropped from MetaData in v1.9.0)

---

## Files to Change

| File | Change |
|------|--------|
| `migrations/v1.9.0_to_v1.10.0_mssql.sql` | New forward migration |
| `migrations/v1.9.0_to_v1.10.0_mssql_rollback.sql` | New rollback |
| `schema_dictionary/version.yaml` | `1.9.0` → `1.10.0` |
| `schema_dictionary/tables/Campaign.yaml` | Remove `Project_ID` column entry |
| `schema_dictionary/deprecated/Project.yaml` | Move from `tables/` |
| `schema_dictionary/deprecated/ProjectHasContact.yaml` | Move from `tables/` |
| `schema_dictionary/deprecated/ProjectHasEquipment.yaml` | Move from `tables/` |
| `schema_dictionary/deprecated/ProjectHasSamplingPoints.yaml` | Move from `tables/` |
| `api/v1/repositories/campaign_repository.py` | Remove Project JOIN + row fields; fix broken metadata count |
| `api/v1/schemas/campaigns.py` | Remove `project_id`, `project_name` from `CampaignOut` |
| `tests/api/contract/test_schema_contracts.py` | Remove project fields from `REQUIRED_CAMPAIGN_FIELDS` |
| `sql_generation_scripts/v1.10.0_create_mssql.sql` | New full baseline |

---

## Migration Plan

### Forward (v1.9.0 → v1.10.0)

1. **Backup** `Campaign.Project_ID` values into a temporary table
   ```sql
   SELECT [Campaign_ID], [Project_ID]
   INTO [dbo].[Campaign_v1_9_project_backup]
   FROM [dbo].[Campaign] WHERE [Project_ID] IS NOT NULL;
   ```

2. **Drop FK** on `Campaign.Project_ID`
   ```sql
   ALTER TABLE [dbo].[Campaign] DROP CONSTRAINT [FK_Campaign_Project];
   ```

3. **Drop column** `Campaign.Project_ID`
   ```sql
   ALTER TABLE [dbo].[Campaign] DROP COLUMN [Project_ID];
   ```

4. **Drop junction tables** (no FKs to drop first — they have no outbound FKs other than to Project/Equipment/Person/SamplingPoints):
   ```sql
   DROP TABLE [dbo].[ProjectHasSamplingPoints];
   DROP TABLE [dbo].[ProjectHasEquipment];
   DROP TABLE [dbo].[ProjectHasContact];
   ```

5. **Drop Project table**
   ```sql
   DROP TABLE [dbo].[Project];
   ```

6. **Update SchemaVersion**

### Rollback (v1.10.0 → v1.9.0)

1. Verify backup table exists
2. Recreate `Project` table (IDENTITY, PK)
3. Recreate junction tables (`ProjectHasContact`, `ProjectHasEquipment`, `ProjectHasSamplingPoints`)
4. Add `Campaign.Project_ID` column back (nullable INT)
5. Restore data from backup: `UPDATE Campaign SET Project_ID = b.Project_ID FROM backup b`
6. Add FK constraint `FK_Campaign_Project`
7. Drop backup table
8. Update SchemaVersion

---

## API Changes

### `campaign_repository.py`

**Remove from `_CAMPAIGN_SELECT`:**
- `c.[Project_ID]`
- `proj.[name] AS ProjectName`
- `LEFT JOIN [dbo].[Project] proj ON proj.[Project_ID] = c.[Project_ID]`

**Update `_row_to_dict`:** Remove `"project_id": row[9]` and `"project_name": row[10]` (column count drops from 11 to 9).

**Fix broken `get_campaign_context()` metadata count** (pre-existing v1.9.0 bug — `m.[Campaign_ID]` no longer exists on MetaData):
```sql
-- Replace:
FROM [dbo].[MetaData] m
LEFT JOIN [dbo].[Value] v ON v.[Metadata_ID] = m.[Metadata_ID]
WHERE m.[Campaign_ID] = ?

-- With (derive via CampaignEquipment):
FROM [dbo].[MetaData] m
JOIN [dbo].[CampaignEquipment] ce ON ce.[Equipment_ID] = m.[Equipment_ID]
LEFT JOIN [dbo].[Value] v ON v.[Metadata_ID] = m.[Metadata_ID]
WHERE ce.[Campaign_ID] = ?
```

### `schemas/campaigns.py`

Remove from `CampaignOut`:
```python
project_id: int | None
project_name: str | None
```

### `tests/api/contract/test_schema_contracts.py`

```python
# Before:
REQUIRED_CAMPAIGN_FIELDS = {
    "campaign_id", "campaign_type_id", "campaign_type_name",
    "site_id", "site_name", "name", "description",
    "start_date", "end_date", "project_id", "project_name",
}

# After:
REQUIRED_CAMPAIGN_FIELDS = {
    "campaign_id", "campaign_type_id", "campaign_type_name",
    "site_id", "site_name", "name", "description",
    "start_date", "end_date",
}
```
Update `_mock_campaign()` to not include `project_id`/`project_name`.

---

## Out of Scope (Pre-existing Issue)

`src/open_dateaubase/meteaudata_bridge.py:load_signal_context()` references multiple MetaData columns dropped in v1.9.0 (`Sampling_point_ID`, `Campaign_ID`, `Contact_ID`, `Purpose_ID`, `Project_ID`). This function is broken and needs a full rewrite aligned with the v1.9.0 channel model — but that is a separate task.

---

## Verification

1. `uv run pytest tests/api/contract/` — all 136 tests pass (project fields removed from contracts)
2. `uv run pytest tests/unit/` — passes (schema YAML tests: Project YAMLs now in `deprecated/`, Campaign.yaml has no Project_ID)
3. Docker MSSQL: run forward migration; verify:
   - `SELECT * FROM sys.tables WHERE name IN ('Project','ProjectHasContact','ProjectHasEquipment','ProjectHasSamplingPoints')` → 0 rows
   - `SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='Campaign' AND COLUMN_NAME='Project_ID'` → 0 rows
4. POST/GET `/api/v1/campaigns` — response has no `project_id`/`project_name`
5. `uv run pytest tests/integration/ -m db`
6. Run rollback script; verify Campaign and Project tables restored; re-apply forward migration.

---

# Schema Analysis & Design Discussion: open_dateaubase

## What Prompted This

ISSUES.md + user observation: the current ingestion flow forces you to:
1. Query tables to find context
2. Provide that context + external knowledge to resolve a MetaData ID
3. Only then write data

This is backwards. The *source* of data (equipment + parameter) is known at write time. The *context* (location, campaign) is derived later from other tables. The schema has this inverted.

---

## Where Does the Schema Stand?

### What's Clean and Well-Designed
- `EquipmentInstallation` — tracks where equipment was deployed, with time ranges and campaign link. This is exactly right.
- `Value`, `ValueVector`, `ValueMatrix`, `ValueImage` — core time-series storage is clean.
- `DataLineage` + `ProcessingStep` — lineage DAG is conceptually sound.
- `Annotation`, `AnnotationType` — clean interval annotation system.
- `EquipmentEvent`, `EquipmentEventType` — sensor lifecycle events are solid.
- API architecture (repositories / services / Pydantic schemas) — pattern is fine.

### What's Janky

**MetaData (the god table)** — currently holds:
- Invariant things: `Equipment_ID`, `Parameter_ID`, `Unit_ID`, `DataProvenance_ID`, `ProcessingDegree`, `ValueType_ID`
- Context things (change over time): `Sampling_point_ID`, `Campaign_ID`, `Project_ID`, `Contact_ID`
- Lab context (different data provenance): `Laboratory_ID`, `AnalystPerson_ID`, `Sample_ID`, `Procedure_ID`
- Wrong abstractions (per ISSUES.md): `Purpose_ID`, `Condition_ID`
- v1.8.0 hack: `StatusOfMetaDataID` (self-referential FK — a status stream linked to a measurement stream via the same table)

**IngestionRoute** — exists only to compensate. It pre-maps `(Equipment, Parameter, Provenance, Degree) → Metadata_ID` because the Metadata_ID couldn't be looked up directly without knowing all the context. It must be manually pre-configured before any data can flow. RouteNotFound errors are administrative, not data errors — a sign the design is fighting itself.

**`find_or_create_metadata_for_lab()`** — builds a dynamic WHERE clause with optional fields to find a MetaData row or create one. This is what happens when the table model doesn't match the lookup semantics.

---

## Is the "Channel" Metaphor Good?

Yes — and it's standard. The concept of a "channel" or "tag" or "point" as the *invariant data stream descriptor* is how every mature time-series system thinks:
- OSIsoft PI (now AVEVA) calls them **PI Points**
- InfluxDB uses **measurement + tag set** as the identity key
- SCADA systems use **tag names** tied to sensors
- OPC-UA uses **NodeId** per data point

The invariant identity of a data stream is: *what equipment, measuring what parameter, at what processing degree*. Everything else (location, campaign, project) is context that varies over the equipment's lifetime and is correctly stored in time-indexed join tables — which you already have (`EquipmentInstallation` is perfect for this).

The metaphor is apt because equipment literally has channels (a DO probe has a DO channel and a temperature channel), and because channels produce continuous streams that outlive any single campaign or location.

---

## Is Relying on an Ingestion Service OK?

Yes — an ingestion service/broker is universal in sensor data systems. Telegraf, PI Interface, AWS IoT Core, Telegraf — they all exist. The concept is fine.

The current service is janky for a specific reason: it requires *pre-configuration* (`IngestionRoute`) before any data can be written. A good ingestion service should be **self-configuring** — on first write, find or create the channel descriptor, then write the data. No prior administrative setup should be required.

The fix isn't to remove the API layer. It's to make the API layer not need the `IngestionRoute` crutch.

---

## The Core Problem, Stated Precisely

`MetaData` was designed as a *context bundle*, not as a *data source identity*.

Because it bundles identity + context, a new MetaData row is needed every time context changes — but the physical data source didn't change. This means:
- Same sensor, new campaign → new MetaData_ID
- Same sensor, new location → new MetaData_ID
- This makes it impossible to simply ask "what did sensor X measure?" without knowing which MetaData_ID to look at

`IngestionRoute` and `find_or_create_metadata_for_lab()` are band-aids on this wound.

---

## The Proposed Fix: Channel Replaces MetaData

**Channel** = the invariant data source descriptor.

```
Channel:
  Channel_ID      (PK, identity)
  Equipment_ID    → Equipment (NOT NULL for sensors)
  Parameter_ID    → Parameter
  Unit_ID         → Unit
  DataProvenance_ID → DataProvenance (Sensor/Lab/Manual/Model/External)
  ProcessingDegree  (Raw / Cleaned / Validated / ...)
  ValueType_ID    → ValueType (Scalar/Vector/Matrix/Image)
  Notes           (optional free text)

  UNIQUE (Equipment_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree)
```

**What this enables:**
```sql
-- Ingesting a sensor reading:
-- 1. MERGE Channel on UNIQUE key → get Channel_ID (create if first time)
-- 2. INSERT Value (Channel_ID, Timestamp, Value)
-- Done. No IngestionRoute. No pre-configuration.
```

**Context is derived at query time from tables you already have:**
```sql
-- Where was channel 42 at time T?
JOIN EquipmentInstallation ON Equipment_ID AND InstalledDate <= T AND (RemovedDate IS NULL OR RemovedDate > T)
JOIN SamplingPoints ON Sampling_point_ID

-- What campaign was active for channel 42 at time T?
JOIN CampaignEquipment ON Equipment_ID
JOIN Campaign ON Campaign_ID WHERE StartDate <= T AND (EndDate IS NULL OR EndDate > T)
```

**Tables to retire:**
- `IngestionRoute` → no longer needed
- `Purpose` table + `Purpose_ID` column → redundant (per ISSUES.md)
- `Condition_ID` / `WeatherCondition` usage on measurements → wrong abstraction (per ISSUES.md); WeatherEvent table can be added later as a site-level annotation

**Tables to update FKs (Metadata_ID → Channel_ID):**
- `Value`, `ValueVector`, `ValueMatrix`, `ValueImage`
- `DataLineage`
- `Annotation`
- `EquipmentEventMetaData` (→ rename `EquipmentEventChannel`)
- `MetaDataAxis` (→ rename `ChannelAxis`)

**Sensor status (v1.8.0 self-referential hack):**
Replace `StatusOfMetaDataID` self-ref with `StatusChannel_ID` nullable FK on Channel:
- A measurement channel optionally points to the Channel that carries its status codes
- Device-level status: new `EquipmentStatusChannel` table (Equipment → StatusChannel)
- `vw_ChannelStatus` and `vw_DeviceStatus` views updated to use these

---

## Lab Data Decision: Separate Tables (Option B)

Lab measurements are discrete results tied to a physical sample, not a continuous stream. The Channel abstraction doesn't fit.

**New tables:**
```
LabAnalysis:
  LabAnalysis_ID (PK, identity)
  Sample_ID          → Sample
  Laboratory_ID      → Laboratory (nullable)
  AnalystPerson_ID   → Person (nullable)
  Procedure_ID       → Procedures (nullable)
  AnalyzedAt         DATETIME2
  Campaign_ID        → Campaign (nullable)
  Notes              NVARCHAR(500)

LabValue:
  LabValue_ID (PK, identity)
  LabAnalysis_ID     → LabAnalysis
  Parameter_ID       → Parameter
  Unit_ID            → Unit
  Value              FLOAT
  Replicate          INT DEFAULT 1
  QualityCode        INT
  Comment_ID         → Comments (nullable)
```

**Migration:** Existing MetaData rows where `DataProvenance_ID = 2` (Laboratory) and `Sample_ID IS NOT NULL` are migrated to `LabAnalysis` + `LabValue`. Their corresponding `Value` rows become `LabValue` rows.

**Implication:** Lab data no longer participates in `DataLineage` or `Annotation` through the Channel path. If lineage or annotations are needed for lab data in the future, bridge tables (`LabLineage`, `LabAnnotation`) can be added. For now: YAGNI.

---

## Phased Migration Plan

Real data exists → careful phased approach. Each phase is its own migration + rollback script.

---

### Phase A — v1.9.0: Clean up MetaData, drop junk

**Goal:** Remove the columns that don't belong on a measurement descriptor. Add the UNIQUE constraint that makes ingestion self-configuring. Drop `IngestionRoute`.

**Schema changes:**
1. Drop `Condition_ID` from `MetaData` (not known at recording time per ISSUES.md)
2. Drop `Purpose_ID` from `MetaData`; drop `Purpose` table
3. Drop context FKs from `MetaData`: `Sampling_point_ID`, `Campaign_ID`, `Project_ID`, `Contact_ID`

   ⚠️ **Pre-migration check required:** Before dropping `Sampling_point_ID` and `Campaign_ID`, verify that `EquipmentInstallation` rows cover all time periods where MetaData rows had those values. Any gap means context would be permanently lost. If gaps exist, they must be backfilled in `EquipmentInstallation` first.

4. Add UNIQUE constraint:
   ```sql
   ALTER TABLE [dbo].[MetaData]
     ADD CONSTRAINT [UQ_MetaData_SensorStream]
     UNIQUE ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree]);
   ```
   (This requires that duplicate sensor MetaData rows — same equipment+parameter+provenance+degree — have already been collapsed. Requires a deduplication pass first.)

5. Drop `IngestionRoute` table (find-or-create on UNIQUE key replaces it)

**API changes:**
- `ingest_sensor` endpoint: drop `routing_service.resolve_route()` call; replace with `MERGE MetaData ON (Equipment_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree)` → returns `Metadata_ID` directly
- Delete `routing_service.py`
- Delete `ingestion_repository.resolve_ingestion_route()`
- `RouteNotFound`, `RouteAmbiguous` exceptions deleted

**Files touched (Phase A):**
| File | Change |
|---|---|
| `migrations/v1.9.0_cleanup.sql` | New migration |
| `migrations/v1.9.0_rollback.sql` | Backup MetaData pre-drop, restore on rollback |
| `schema_dictionary/tables/MetaData.yaml` | Remove dropped columns |
| `schema_dictionary/tables/IngestionRoute.yaml` | Archive |
| `schema_dictionary/tables/Purpose.yaml` | Archive |
| `api/v1/services/routing_service.py` | Delete |
| `api/v1/repositories/ingestion_repository.py` | Drop route resolution; add MERGE-based sensor channel lookup |
| `api/v1/endpoints/ingest.py` | Remove routing logic |
| `api/v1/schemas/` | Remove Purpose, Condition, context fields from MetaData schema |
| `tests/api/contract/` | Update contract tests to remove routing test cases |

---

### Phase B — v2.0.0: Lab data model + MetaData → Channel rename

**Goal:** Move lab data to dedicated tables; rename MetaData → Channel and update all FK references.

**Schema changes:**
1. Create `LabAnalysis` + `LabValue` tables
2. Migrate existing lab MetaData rows:
   ```sql
   -- For each MetaData row with DataProvenance_ID = 2:
   -- Create LabAnalysis from (Sample_ID, Laboratory_ID, AnalystPerson_ID, Procedure_ID, Campaign_ID)
   -- Create LabValue from each corresponding Value row
   ```
3. Drop lab columns from MetaData: `Laboratory_ID`, `AnalystPerson_ID`, `Sample_ID`, `Procedure_ID`
4. Create `Channel` table (same structure as cleaned MetaData), copy data, update all FKs:
   - `Value.Metadata_ID` → `Value.Channel_ID`
   - `DataLineage.Metadata_ID` → `DataLineage.Channel_ID`
   - `Annotation.Metadata_ID` → `Annotation.Channel_ID`
   - `MetaDataAxis` → `ChannelAxis` (rename table + FK column)
   - `EquipmentEventMetaData` → `EquipmentEventChannel` (rename + FK column)
5. Drop `MetaData` table

**API changes:**
- All `metadata_repository.py` → `channel_repository.py`
- All `MetaData` Pydantic schemas → `Channel` schemas
- `GET /metadata/{id}` → `GET /channels/{id}`
- Lab ingest endpoint: POST to `LabAnalysis` + `LabValue` instead of MetaData+Value
- Processed ingest: output channel is a new Channel row (no longer clones context from source)

**Files touched (Phase B):**
| File | Change |
|---|---|
| `migrations/v2.0.0_channel.sql` | New migration (lab tables, Channel rename, FK updates) |
| `migrations/v2.0.0_rollback.sql` | Restore from backup tables |
| `schema_dictionary/tables/Channel.yaml` | New (replaces MetaData.yaml) |
| `schema_dictionary/tables/LabAnalysis.yaml` | New |
| `schema_dictionary/tables/LabValue.yaml` | New |
| `schema_dictionary/tables/ChannelAxis.yaml` | Replaces MetaDataAxis.yaml |
| `schema_dictionary/tables/EquipmentEventChannel.yaml` | Replaces EquipmentEventMetaData.yaml |
| `schema_dictionary/tables/Value.yaml` | FK update |
| `schema_dictionary/tables/DataLineage.yaml` | FK update |
| `schema_dictionary/tables/Annotation.yaml` | FK update |
| `api/v1/repositories/metadata_repository.py` | → rename to `channel_repository.py` |
| `api/v1/repositories/ingestion_repository.py` | Lab path replaces find_or_create; processed path simplified |
| `api/v1/repositories/value_repository.py` | Metadata_ID → Channel_ID throughout |
| `api/v1/schemas/` | Channel, LabAnalysis, LabValue schemas |
| `api/v1/endpoints/ingest.py` | Lab endpoint posts to LabAnalysis/LabValue |
| `api/v1/router.py` | Rename metadata route to channels |
| `src/open_dateaubase/lineage.py` | Metadata_ID → Channel_ID in all SQL |
| `src/open_dateaubase/meteaudata_bridge.py` | Rewrite `load_signal_context()` to derive context from EquipmentInstallation+Campaign |
| `sql_generation_scripts/v2.0.0_create_mssql.sql` | Full create script for new schema |

---

### Phase C — v2.1.0: Status system cleanup

**Goal:** Replace the v1.8.0 `StatusOfMetaDataID` self-referential hack with clean FKs on Channel.

**Schema changes:**
1. Add `StatusChannel_ID` (nullable FK → Channel) to `Channel` table
2. Create `EquipmentStatusChannel` table: (Equipment_ID PK → Equipment, StatusChannel_ID → Channel)
3. Migrate `StatusOfMetaDataID` → `StatusChannel_ID` on the corresponding Channel rows
4. Migrate `StatusOfEquipmentID` → `EquipmentStatusChannel` rows
5. Drop `StatusOfMetaDataID` and `StatusOfEquipmentID` columns from `Channel`
6. Rebuild `vw_ChannelStatus` and `vw_DeviceStatus` using new structure

**Files touched (Phase C):**
| File | Change |
|---|---|
| `migrations/v2.1.0_status_cleanup.sql` | New migration |
| `migrations/v2.1.0_rollback.sql` | Restore columns |
| `schema_dictionary/tables/Channel.yaml` | Add StatusChannel_ID, remove old status columns |
| `schema_dictionary/tables/EquipmentStatusChannel.yaml` | New |
| `schema_dictionary/views/vw_ChannelStatus.yaml` | Updated |
| `schema_dictionary/views/vw_DeviceStatus.yaml` | Updated |
| `api/v1/repositories/sensor_status_repository.py` | Rewrite all status queries |
| `api/v1/services/sensor_status_service.py` | Update calls |

---

## Future: Control Loops (Phase D)

Control loop support is **additive** — it requires no changes to the Channel model, just new tables layered on top.

**Key design decision:** Setpoint, MV, and similar concepts are **roles** a channel plays in a control loop, not `ProcessingDegree` values. The same channel can play different roles in different loops simultaneously.

**Clarified ProcessingDegree vocabulary** (valid uses):
- `Raw`, `Cleaned`, `Calibrated`, `Validated`, `Filtered`, `Predicted` — transformations of a data stream
- **Not** `Setpoint`, `MV`, `CV` — those are loop roles, not degrees of processing

**Proposed tables (future phase):**

```sql
CREATE TABLE [dbo].[ControlLoopChannelRole] (
    [Role_ID]   INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    [RoleName]  NVARCHAR(50) NOT NULL UNIQUE
    -- Seeds: CV, SP, MV, Disturbance, MeasuredDisturbance,
    --        ControllerOutput, ModelPrediction, StateEstimate
);

CREATE TABLE [dbo].[ControlLoop] (
    [ControlLoop_ID]   INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    [Name]             NVARCHAR(200) NOT NULL,
    [Description]      NVARCHAR(2000) NULL,
    [AlgorithmType]    NVARCHAR(100) NULL,  -- PID, MPC, Cascade, Feedforward, ...
    [Site_ID]          INT NULL REFERENCES [dbo].[Site]([Site_ID]),
    [Controller_ID]    INT NULL REFERENCES [dbo].[Equipment]([Equipment_ID]),
    [ValidFrom]        DATETIME2(7) NOT NULL,
    [ValidTo]          DATETIME2(7) NULL,
    [Notes]            NVARCHAR(500) NULL
);

CREATE TABLE [dbo].[ControlLoopChannel] (
    [ControlLoop_ID]   INT NOT NULL REFERENCES [dbo].[ControlLoop]([ControlLoop_ID]),
    [Channel_ID]       INT NOT NULL REFERENCES [dbo].[Channel]([Channel_ID]),
    [Role_ID]          INT NOT NULL REFERENCES [dbo].[ControlLoopChannelRole]([Role_ID]),
    [ValidFrom]        DATETIME2(7) NOT NULL,
    [ValidTo]          DATETIME2(7) NULL,
    [Notes]            NVARCHAR(500) NULL,
    PRIMARY KEY ([ControlLoop_ID], [Channel_ID], [Role_ID], [ValidFrom])
);
```

**Example:** DO control via aeration at a WWTP:
- CV channel: (DO_Sensor, DO_parameter, DataProvenance=Sensor, Degree=Raw) → Role=CV
- SP channel: (MPC_Controller, DO_parameter, DataProvenance=ModelOutput, Degree=Raw) → Role=SP
- MV channel: (Blower_Actuator, AerationRate_parameter, DataProvenance=Sensor, Degree=Raw) → Role=MV
- Disturbance channel: (InfluentFlowMeter, Flow_parameter, DataProvenance=Sensor, Degree=Raw) → Role=Disturbance

All four are already valid Channel rows. `ControlLoopChannel` is the only addition needed.

**Equipment-vs-Model gap:** The `Controller_ID` on `ControlLoop` references `Equipment`, which is designed for physical instruments. A software MPC controller is a different kind of entity. Options:
1. Use `Equipment` table with a new `EquipmentModel` entry for the controller software — workable short-term
2. Add a `ComputationalAgent` table as a future parallel to `Equipment` — cleaner long-term

Defer this decision to when control loops are actually implemented.

---

## WeatherCondition

`Condition_ID` drops from measurements in Phase A (not known at recording time, per ISSUES.md).
`WeatherCondition` table can be retained as a reference table for future `WeatherEvent` table (site-level event tagging with dry/wet weather periods). No immediate action needed.

---

## Verification Plan

**After Phase A (v1.9.0):**
1. `uv run pytest tests/unit/` passes
2. `uv run pytest tests/api/contract/` passes (routing tests removed/updated)
3. Docker MSSQL: run migration, verify `IngestionRoute` dropped, `Purpose` dropped, context columns gone
4. `SELECT COUNT(*) FROM MetaData WHERE Condition_ID IS NOT NULL` = 0 (pre-migration check)
5. POST `/ingest/sensor` with equipment+parameter → succeeds without IngestionRoute pre-configuration
6. `uv run pytest tests/integration/ -m db`

**After Phase B (v2.0.0):**
1. All tests pass
2. `SELECT COUNT(*) FROM Channel` = number of distinct sensor streams
3. `SELECT COUNT(*) FROM Value WHERE Channel_ID IS NULL` = 0
4. `SELECT COUNT(*) FROM LabValue` = number of former lab Value rows
5. Lab ingest POST → LabAnalysis + LabValue rows created
6. Processed ingest → DataLineage references Channel_IDs
7. Lineage forward/backward traversal works

**After Phase C (v2.1.0):**
1. All tests pass
2. `SELECT * FROM Channel WHERE StatusChannel_ID IS NOT NULL` returns expected rows
3. `vw_ChannelStatus` and `vw_DeviceStatus` return correct data
