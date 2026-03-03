# Plan: Fix Migration SQL and Seed Data to Match Current Schema

## Context

The YAML schema dictionary was updated this session (new tables, column renames, removed tables).
The migration SQL and seed SQL still reflect the old state. This plan lists every delta.

The render.py generator emits **no INSERT statements** — the migration SQL is
solely responsible for seeding all lookup tables.

---

## File 1: `migrations/v1.0.0_to_v2.1.0_mssql.sql`

### A. Step 2 — Add new lookup table CREATEs + seeds

Add after existing lookup tables (ValueType, CampaignType, DataProvenance, etc.):

```sql
-- ProcessingDegree (6 rows: Raw=1 … Predicted=6)
CREATE TABLE [dbo].[ProcessingDegree] (...)
INSERT ... (1, Raw), (2, Cleaned), (3, Calibrated), (4, Validated), (5, Filtered), (6, Predicted)

-- QualityCode (6 rows: Accepted=1 … Outlier=6) with IsUsable BIT
CREATE TABLE [dbo].[QualityCode] (...)
INSERT ... (1, Accepted, true), (2, Suspect, true), (3, Rejected, false),
           (4, BelowLoD, false), (5, AboveLoQ, false), (6, Outlier, true)

-- SampleType (5 rows: Field=1 … Blank=5)
CREATE TABLE [dbo].[SampleType] (...)
INSERT ... (1, Field), (2, Synthetic), (3, Master Standard), (4, Derived Standard), (5, Blank)

-- SampleMethod (5 rows: Grab=1 … Other=5)
CREATE TABLE [dbo].[SampleMethod] (...)
INSERT ... (1, Grab), (2, Composite24h), (3, Composite8h), (4, Passive), (5, Other)
```

### B. Step 9 — Fix Channel column additions

Current (wrong):
```sql
ALTER TABLE [dbo].[Channel] ADD [ProcessingDegree] NVARCHAR(50) NOT NULL DEFAULT 'Raw';
```
Remove the FK_Channel_Unit line from Step 15 too (Unit_ID was removed from Channel).

Replace with:
```sql
ALTER TABLE [dbo].[Channel] ADD [ProcessingDegree_ID] INT NOT NULL DEFAULT 1;
-- (no Unit_ID addition)
```

### C. Step 12 — Fix Campaign CREATE TABLE

Current column names are wrong:
```sql
[StartDate] DATETIME2(7),
[EndDate]   DATETIME2(7),
```
Fix to match YAML:
```sql
[CampaignStartDateTime] DATETIME2(7),
[CampaignEndDateTime]   DATETIME2(7),
```

### D. Step 12 — Fix Sample CREATE TABLE

Current (wrong):
```sql
[SampleCategory] NVARCHAR(50),
[SampleType]     NVARCHAR(50),
```
Replace with:
```sql
[SampleType_ID]   INT,
[SampleMethod_ID] INT,
```

### E. Step 12 — Fix LabValue CREATE TABLE

Current (wrong):
```sql
[Unit_ID]    INT NOT NULL,
[Value]      FLOAT NOT NULL,
[QualityCode] INT,
[Comment_ID] INT,
```
Replace with:
```sql
[LabResult]     FLOAT NOT NULL,
[QualityCode_ID] INT,
[Comment]       NVARCHAR(MAX),
```

### F. Step 12 — Fix ProcessingStep CREATE TABLE

Current (wrong):
```sql
[ExecutedAt] DATETIME2(7),
```
Replace with:
```sql
[ExecutedDateTime] DATETIME2(7),
[Dataset_ID]       INT,
```

### G. Step 13 — Replace DataLineage with ProcessingLineage; remove EquipmentEventChannel

Remove the `DataLineage` CREATE TABLE block entirely.
Remove the `EquipmentEventChannel` CREATE TABLE block entirely.

Add instead:
```sql
CREATE TABLE [dbo].[ProcessingLineage] (
    [ProcessingLineage_ID] INT IDENTITY(1,1) NOT NULL,
    [ProcessingStep_ID]    INT NOT NULL,
    [Channel_ID]           INT NOT NULL,
    [RoleInProcessingStep] NVARCHAR(10) NOT NULL,  -- CHECK IN ('Input','Output')
    [StartTime]            DATETIME2(7),
    [EndTime]              DATETIME2(7),
    CONSTRAINT [PK_ProcessingLineage] PRIMARY KEY ([ProcessingLineage_ID])
);
```

### H. Step 14 — Remove CampaignParameter CREATE TABLE + its FK adds

Remove the `CampaignParameter` CREATE TABLE block entirely.
Remove `FK_CampaignParameter_*` FK additions from Step 15.

### I. Step 12 — Add Dataset and DatasetChannel

```sql
CREATE TABLE [dbo].[Dataset] (
    [Dataset_ID]           INT IDENTITY(1,1) NOT NULL,
    [Name]                 NVARCHAR(200) NOT NULL,
    [Description]          NVARCHAR(2000),
    [Purpose]              NVARCHAR(500),
    [CreatedOn]            DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    [CreatedByPerson_ID]   INT,
    CONSTRAINT [PK_Dataset] PRIMARY KEY ([Dataset_ID])
);

CREATE TABLE [dbo].[DatasetChannel] (
    [Dataset_ID]  INT NOT NULL,
    [Channel_ID]  INT NOT NULL,
    CONSTRAINT [PK_DatasetChannel] PRIMARY KEY ([Dataset_ID], [Channel_ID])
);
```

### J. Step 15 — FK constraint changes

**Remove** these FK additions (tables/columns no longer exist):
- `FK_Channel_Unit` (Unit_ID removed from Channel)
- `FK_LabValue_Unit` (Unit_ID removed from LabValue)
- `FK_LabValue_Comments` (Comment_ID removed; Comments table remains in v1 only)
- `FK_CampaignParameter_*` (table removed)
- `FK_EquipmentEventChannel_*` (table removed)

**Add** these new FK additions:
```sql
ALTER TABLE [dbo].[Channel]         ADD CONSTRAINT [FK_Channel_ProcessingDegree]
    FOREIGN KEY ([ProcessingDegree_ID]) REFERENCES [dbo].[ProcessingDegree] ([ProcessingDegree_ID]);

ALTER TABLE [dbo].[LabValue]        ADD CONSTRAINT [FK_LabValue_QualityCode]
    FOREIGN KEY ([QualityCode_ID]) REFERENCES [dbo].[QualityCode] ([QualityCode_ID]);

ALTER TABLE [dbo].[Sample]          ADD CONSTRAINT [FK_Sample_SampleType]
    FOREIGN KEY ([SampleType_ID]) REFERENCES [dbo].[SampleType] ([SampleType_ID]);

ALTER TABLE [dbo].[Sample]          ADD CONSTRAINT [FK_Sample_SampleMethod]
    FOREIGN KEY ([SampleMethod_ID]) REFERENCES [dbo].[SampleMethod] ([SampleMethod_ID]);

ALTER TABLE [dbo].[ProcessingStep]  ADD CONSTRAINT [FK_ProcessingStep_Dataset]
    FOREIGN KEY ([Dataset_ID]) REFERENCES [dbo].[Dataset] ([Dataset_ID]);

ALTER TABLE [dbo].[Dataset]         ADD CONSTRAINT [FK_Dataset_Person]
    FOREIGN KEY ([CreatedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);

ALTER TABLE [dbo].[DatasetChannel]  ADD CONSTRAINT [FK_DatasetChannel_Dataset]
    FOREIGN KEY ([Dataset_ID]) REFERENCES [dbo].[Dataset] ([Dataset_ID]);

ALTER TABLE [dbo].[DatasetChannel]  ADD CONSTRAINT [FK_DatasetChannel_Channel]
    FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_ProcessingStep]
    FOREIGN KEY ([ProcessingStep_ID]) REFERENCES [dbo].[ProcessingStep] ([ProcessingStep_ID]);

ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_Channel]
    FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
```

### K. Step 16 — Index fixes

Replace:
```sql
CREATE UNIQUE INDEX [UQ_Channel_SensorStream]
    ON [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree]);
CREATE INDEX [IX_DataLineage_Channel]   ON [dbo].[DataLineage] ([Channel_ID]);
CREATE INDEX [IX_DataLineage_Step_Role] ON [dbo].[DataLineage] ([ProcessingStep_ID], [Role]);
```
With:
```sql
CREATE UNIQUE INDEX [UQ_Channel_SensorStream]
    ON [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID]);
CREATE INDEX [IX_ProcessingLineage_Channel] ON [dbo].[ProcessingLineage] ([Channel_ID]);
CREATE INDEX [IX_Lineage_Step_Role]         ON [dbo].[ProcessingLineage] ([ProcessingStep_ID], [RoleInProcessingStep]);
```

---

## File 2: `sql/seed_v2.1.0.sql`

### Remove these blocks entirely (tables no longer exist in v2.1.0 schema)

- All `INSERT INTO [dbo].[Comments]` rows (4 inserts)
- All `INSERT INTO [dbo].[ParameterHasProcedures]` rows (4 inserts)
- All `INSERT INTO [dbo].[CampaignParameter]` rows (4 inserts)
- The `INSERT INTO [dbo].[EquipmentEventChannel]` row

### Fix Campaign inserts

```sql
-- Wrong:
INSERT INTO [dbo].[Campaign] (..., [StartDate]) VALUES (..., '2024-01-01T00:00:00');
INSERT INTO [dbo].[Campaign] (..., [StartDate], [EndDate]) VALUES (...);
-- Right:
INSERT INTO [dbo].[Campaign] (..., [CampaignStartDateTime]) VALUES (...);
INSERT INTO [dbo].[Campaign] (..., [CampaignStartDateTime], [CampaignEndDateTime]) VALUES (...);
```

### Fix Channel inserts

```sql
-- Wrong (includes Unit_ID and ProcessingDegree string):
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [Unit_ID], [DataProvenance_ID], [ProcessingDegree], [ValueType_ID])
VALUES (1, 1, 1, 1, N'Raw', 1);
-- Right:
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (1, 1, 1, 1, 1);
```
Apply to all 11 Channel inserts. ProcessingDegree_ID=1 (Raw) for all existing channels.

### Fix Value inserts

```sql
-- Wrong (includes Comment_ID and Number_of_experiment):
INSERT INTO [dbo].[Value] ([Comment_ID], [Channel_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (1, 1, 185.0, 1, '2024-01-15T13:00:00');
-- Right:
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp])
VALUES (1, 185.0, '2024-01-15T13:00:00');
```
Apply to all 21 Value inserts. Drop Comment_ID and Number_of_experiment columns from every row.

### Fix LabValue inserts

```sql
-- Wrong:
INSERT INTO [dbo].[LabValue] ([LabAnalysis_ID], [Parameter_ID], [Unit_ID], [Value], [Replicate], [QualityCode])
VALUES (1, 1, 1, 178.4, 1, NULL);
-- Right:
INSERT INTO [dbo].[LabValue] ([LabAnalysis_ID], [Parameter_ID], [LabResult], [Replicate], [QualityCode_ID])
VALUES (1, 1, 178.4, 1, NULL);
```

### Fix Sample inserts

```sql
-- Wrong:
INSERT INTO [dbo].[Sample] (..., [SampleType], ...)
VALUES (..., N'Grab', ...);
-- Right: SampleType_ID=1 (Field), SampleMethod_ID=1 (Grab)
INSERT INTO [dbo].[Sample] (..., [SampleType_ID], [SampleMethod_ID], ...)
VALUES (..., 1, 1, ...);
```

---

## Verification

After applying all changes:
1. Run `docker compose --profile init up` to validate the full init sequence against a live DB.
2. Run `uv run pytest tests/unit/ tests/schema/ -q` — all 58 should still pass.
3. Run `uv run pytest tests/integration/ -m db -q` (if Docker is up).
