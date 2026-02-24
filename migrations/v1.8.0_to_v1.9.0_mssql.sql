-- Migration: v1.8.0 -> v1.9.0
-- Platform: mssql
-- Generated: 2026-02-23
-- Rollback: v1.8.0_to_v1.9.0_mssql_rollback.sql
--
-- Phase 6: Schema cleanup — establish Channel model foundation
--
--   6.1  Pre-migration checks — verify EquipmentInstallation coverage
--   6.2  Drop IngestionRoute (replaced by UNIQUE constraint on MetaData)
--   6.3  Drop junk columns from MetaData:
--          Condition_ID  (not known at recording time per ISSUES.md)
--          Purpose_ID    (redundant with DataProvenance per ISSUES.md)
--          Sampling_point_ID (context derived from EquipmentInstallation at query time)
--          Campaign_ID       (context derived from EquipmentInstallation.Campaign_ID)
--          Project_ID        (context derived from Campaign.Project_ID)
--          Contact_ID        (context belongs on Campaign / Project)
--   6.4  Drop Purpose table
--   6.5  Add UNIQUE index on MetaData for sensor streams
--          UNIQUE(Equipment_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree)
--          WHERE Equipment_ID IS NOT NULL AND Sample_ID IS NULL
--
-- BREAKING CHANGES:
--   - MetaData.Sampling_point_ID, Campaign_ID, Project_ID, Contact_ID,
--     Condition_ID, Purpose_ID dropped
--   - IngestionRoute table dropped
--   - Purpose table dropped
--   - Sensor MetaData rows now have a UNIQUE constraint — duplicate rows
--     (same equipment+parameter+provenance+degree) must be resolved BEFORE
--     running this migration.
--
-- PRE-MIGRATION CHECKS: See Section 6.1 — review output before proceeding.

SET NOCOUNT ON;
GO

-- ============================================================
-- 6.1  Pre-migration checks (informational — review before committing)
-- ============================================================

-- a) How many MetaData rows have Condition_ID set? These will lose it.
SELECT
    'Rows with Condition_ID' AS check_name,
    COUNT(*) AS row_count
FROM [dbo].[MetaData]
WHERE [Condition_ID] IS NOT NULL;

-- b) How many MetaData rows have Purpose_ID set?
SELECT
    'Rows with Purpose_ID' AS check_name,
    COUNT(*) AS row_count
FROM [dbo].[MetaData]
WHERE [Purpose_ID] IS NOT NULL;

-- c) Sensor MetaData rows whose location is NOT covered by EquipmentInstallation.
--    These rows will lose their Sampling_point_ID with no way to recover context.
--    RESOLVE THESE BEFORE RUNNING THE FULL MIGRATION.
SELECT
    m.[Metadata_ID],
    m.[Equipment_ID],
    m.[Sampling_point_ID],
    'No EquipmentInstallation record covers this MetaData location' AS warning
FROM [dbo].[MetaData] m
WHERE m.[Equipment_ID] IS NOT NULL
  AND m.[Sampling_point_ID] IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM [dbo].[EquipmentInstallation] ei
      WHERE ei.[Equipment_ID] = m.[Equipment_ID]
        AND ei.[Sampling_point_ID] = m.[Sampling_point_ID]
  );

-- d) Sensor MetaData rows that would violate the new UNIQUE constraint.
--    These indicate duplicate channel descriptors that must be deduplicated.
SELECT
    [Equipment_ID], [Parameter_ID],
    COALESCE(CAST([DataProvenance_ID] AS NVARCHAR), 'NULL') AS DataProvenance_ID,
    COALESCE([ProcessingDegree], 'NULL') AS ProcessingDegree,
    COUNT(*) AS duplicate_count
FROM [dbo].[MetaData]
WHERE [Equipment_ID] IS NOT NULL
  AND [Sample_ID] IS NULL
GROUP BY [Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree]
HAVING COUNT(*) > 1;

GO

-- ============================================================
-- 6.2  Back up tables before destructive changes
-- ============================================================

-- Backup MetaData (preserves dropped column values for rollback)
SELECT * INTO [dbo].[MetaData_v1_8_backup] FROM [dbo].[MetaData];
GO

-- Backup IngestionRoute
SELECT * INTO [dbo].[IngestionRoute_v1_8_backup] FROM [dbo].[IngestionRoute];
GO

-- ============================================================
-- 6.3  Drop IngestionRoute (FK constraints first, then table)
-- ============================================================

ALTER TABLE [dbo].[IngestionRoute] DROP CONSTRAINT [FK_IngestionRoute_Equipment];
ALTER TABLE [dbo].[IngestionRoute] DROP CONSTRAINT [FK_IngestionRoute_Parameter];
ALTER TABLE [dbo].[IngestionRoute] DROP CONSTRAINT [FK_IngestionRoute_DataProvenance];
ALTER TABLE [dbo].[IngestionRoute] DROP CONSTRAINT [FK_IngestionRoute_MetaData];
GO

DROP INDEX [IX_IngestionRoute_Lookup] ON [dbo].[IngestionRoute];
GO

DROP TABLE [dbo].[IngestionRoute];
GO

-- ============================================================
-- 6.4  Drop FK constraints on MetaData columns being removed
-- ============================================================

ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_WeatherCondition];   -- Condition_ID
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Purpose];             -- Purpose_ID
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_SamplingPoints];      -- Sampling_point_ID
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Campaign];            -- Campaign_ID
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Project];             -- Project_ID
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Person];              -- Contact_ID
GO

-- ============================================================
-- 6.5  Drop columns from MetaData
-- ============================================================

ALTER TABLE [dbo].[MetaData] DROP COLUMN [Condition_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Purpose_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Sampling_point_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Campaign_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Project_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Contact_ID];
GO

-- ============================================================
-- 6.6  Update vw_ChannelStatus (remove LocationName — Sampling_point_ID gone)
-- ============================================================

-- vw_ChannelStatus previously joined MetaData.Sampling_point_ID -> SamplingPoints.
-- Location context is now derived at query time via EquipmentInstallation.
ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusMD.[Metadata_ID]            AS StatusMetaDataID,
    statusMD.[StatusOfMetaDataID]     AS MeasurementMetaDataID,
    measMD.[Equipment_ID]             AS EquipmentID,
    e.[identifier]                    AS EquipmentName,
    p.[Parameter]                     AS MeasurementParameter,
    v.[Timestamp],
    CAST(v.[Value] AS INT)            AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]        statusMD ON statusMD.[Metadata_ID]      = v.[Metadata_ID]
JOIN [dbo].[MetaData]        measMD   ON measMD.[Metadata_ID]         = statusMD.[StatusOfMetaDataID]
JOIN [dbo].[Parameter]       p        ON p.[Parameter_ID]             = measMD.[Parameter_ID]
JOIN [dbo].[Equipment]       e        ON e.[Equipment_ID]             = measMD.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc ON sc.[StatusCodeID]           = CAST(v.[Value] AS INT)
WHERE statusMD.[StatusOfMetaDataID] IS NOT NULL;
GO

-- ============================================================
-- 6.7  Drop Purpose table (no longer referenced)
-- ============================================================

DROP TABLE [dbo].[Purpose];
GO

-- ============================================================
-- 6.8  Add UNIQUE constraint for sensor stream identity
-- ============================================================

-- Sensor streams: unique on (Equipment, Parameter, DataProvenance, ProcessingDegree)
-- Filtered index excludes lab MetaData rows (where Equipment_ID IS NULL or Sample_ID IS NOT NULL).
CREATE UNIQUE INDEX [UQ_MetaData_SensorStream]
    ON [dbo].[MetaData] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree])
    WHERE [Equipment_ID] IS NOT NULL AND [Sample_ID] IS NULL;
GO

-- ============================================================
-- 6.9  Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.9.0',
    SYSUTCDATETIME(),
    'Phase 6: Schema cleanup — drop junk columns (Condition_ID, Purpose_ID, Sampling_point_ID, Campaign_ID, Project_ID, Contact_ID), drop IngestionRoute, drop Purpose, add UNIQUE sensor stream constraint',
    'v1.8.0_to_v1.9.0_mssql.sql'
);
GO
