-- Migration: v1.10.0 -> v2.0.0
-- Platform: mssql
-- Generated: 2026-02-23
--
-- Phase B: MetaData -> Channel rename + LabAnalysis/LabValue tables
--   B.1  Create LabAnalysis and LabValue tables
--   B.2  Drop lab FK constraints from MetaData
--   B.3  Drop filtered unique index (references Sample_ID about to be dropped)
--   B.4  Drop lab columns from MetaData (Sample_ID, Laboratory_ID, AnalystPerson_ID, Procedure_ID)
--   B.5  Rename Metadata_ID -> Channel_ID in all child tables
--   B.6  Rename MetaData PK column (Metadata_ID -> Channel_ID)
--   B.7  Rename tables (MetaData -> Channel, MetaDataAxis -> ChannelAxis,
--         EquipmentEventMetaData -> EquipmentEventChannel)
--   B.8  Recreate unique index with new name (no Sample_ID filter needed)
--   B.9  Rebuild views to reference Channel + Channel_ID
--   B.10 Update SchemaVersion
--
-- BREAKING CHANGES:
--   - MetaData table renamed to Channel; Metadata_ID PK renamed to Channel_ID
--   - MetaDataAxis renamed to ChannelAxis; EquipmentEventMetaData renamed to EquipmentEventChannel
--   - Lab columns (Sample_ID, Laboratory_ID, AnalystPerson_ID, Procedure_ID) dropped from Channel
--   - All child FK columns (Value, ValueVector, ValueMatrix, ValueImage, DataLineage,
--     Annotation, ChannelAxis, EquipmentEventChannel) renamed Metadata_ID -> Channel_ID
--   - New tables: LabAnalysis, LabValue
--   - vw_ChannelStatus, vw_DeviceStatus rebuilt with new column/table names

SET NOCOUNT ON;
GO

-- ============================================================
-- B.1  Create LabAnalysis and LabValue tables
-- ============================================================

CREATE TABLE [dbo].[LabAnalysis] (
    [LabAnalysis_ID]   INT IDENTITY(1,1) NOT NULL,
    [Sample_ID]        INT NOT NULL
        REFERENCES [dbo].[Sample]([Sample_ID]),
    [Laboratory_ID]    INT NULL
        REFERENCES [dbo].[Laboratory]([Laboratory_ID]),
    [AnalystPerson_ID] INT NULL
        REFERENCES [dbo].[Person]([Person_ID]),
    [Procedure_ID]     INT NULL
        REFERENCES [dbo].[Procedures]([Procedure_ID]),
    [AnalyzedAt]       DATETIME2(7) NOT NULL
        CONSTRAINT [DF_LabAnalysis_AnalyzedAt] DEFAULT SYSUTCDATETIME(),
    [Campaign_ID]      INT NULL
        REFERENCES [dbo].[Campaign]([Campaign_ID]),
    [Notes]            NVARCHAR(500) NULL,
    CONSTRAINT [PK_LabAnalysis] PRIMARY KEY ([LabAnalysis_ID])
);
GO

CREATE TABLE [dbo].[LabValue] (
    [LabValue_ID]    INT IDENTITY(1,1) NOT NULL,
    [LabAnalysis_ID] INT NOT NULL
        REFERENCES [dbo].[LabAnalysis]([LabAnalysis_ID]),
    [Parameter_ID]   INT NOT NULL
        REFERENCES [dbo].[Parameter]([Parameter_ID]),
    [Unit_ID]        INT NOT NULL
        REFERENCES [dbo].[Unit]([Unit_ID]),
    [Value]          FLOAT NOT NULL,
    [Replicate]      INT NOT NULL
        CONSTRAINT [DF_LabValue_Replicate] DEFAULT 1,
    [QualityCode]    INT NULL,
    [Comment_ID]     INT NULL
        REFERENCES [dbo].[Comments]([Comment_ID]),
    CONSTRAINT [PK_LabValue] PRIMARY KEY ([LabValue_ID])
);
GO

-- ============================================================
-- B.2  Drop lab FK constraints from MetaData
--       (IF EXISTS: actual constraint names may differ across environments)
-- ============================================================

ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT IF EXISTS [FK_MetaData_Sample];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT IF EXISTS [FK_MetaData_Laboratory];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT IF EXISTS [FK_MetaData_AnalystPerson];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT IF EXISTS [FK_MetaData_Procedures];
GO

-- ============================================================
-- B.3  Drop filtered unique index before dropping Sample_ID
--       (filter references Sample_ID IS NULL — must go first)
-- ============================================================

DROP INDEX IF EXISTS [UQ_MetaData_SensorStream] ON [dbo].[MetaData];
GO

-- ============================================================
-- B.4  Drop lab columns from MetaData
-- ============================================================

ALTER TABLE [dbo].[MetaData] DROP COLUMN [Sample_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Laboratory_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [AnalystPerson_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Procedure_ID];
GO

-- ============================================================
-- B.5  Rename Metadata_ID -> Channel_ID in all child tables
-- ============================================================

EXEC sp_rename 'dbo.Value.Metadata_ID',                 'Channel_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.ValueVector.Metadata_ID',            'Channel_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.ValueMatrix.Metadata_ID',            'Channel_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.ValueImage.Metadata_ID',             'Channel_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.DataLineage.Metadata_ID',            'Channel_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.Annotation.Metadata_ID',             'Channel_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.MetaDataAxis.Metadata_ID',           'Channel_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.EquipmentEventMetaData.Metadata_ID', 'Channel_ID', 'COLUMN';
GO

-- ============================================================
-- B.6  Rename MetaData PK column
-- ============================================================

EXEC sp_rename 'dbo.MetaData.Metadata_ID', 'Channel_ID', 'COLUMN';
GO

-- ============================================================
-- B.7  Rename tables
-- ============================================================

EXEC sp_rename 'dbo.MetaData',              'Channel';
GO
EXEC sp_rename 'dbo.MetaDataAxis',          'ChannelAxis';
GO
EXEC sp_rename 'dbo.EquipmentEventMetaData','EquipmentEventChannel';
GO

-- ============================================================
-- B.8  Recreate unique sensor stream index on Channel
--       (no Sample_ID filter needed — lab data moved to LabAnalysis)
-- ============================================================

CREATE UNIQUE INDEX [UQ_Channel_SensorStream]
    ON [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree])
    WHERE [Equipment_ID] IS NOT NULL;
GO

-- ============================================================
-- B.9  Rebuild views
-- ============================================================

DROP VIEW IF EXISTS [dbo].[vw_ChannelStatus];
GO

CREATE VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]              AS StatusChannelID,
    statusC.[StatusOfMetaDataID]      AS MeasurementChannelID,
    measC.[Equipment_ID]              AS EquipmentID,
    e.[identifier]                    AS EquipmentName,
    p.[Parameter]                     AS MeasurementParameter,
    v.[Timestamp],
    CAST(v.[Value] AS INT)            AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]           statusC ON statusC.[Channel_ID]       = v.[Channel_ID]
JOIN [dbo].[Channel]           measC   ON measC.[Channel_ID]         = statusC.[StatusOfMetaDataID]
JOIN [dbo].[Parameter]         p       ON p.[Parameter_ID]           = measC.[Parameter_ID]
JOIN [dbo].[Equipment]         e       ON e.[Equipment_ID]           = measC.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc  ON sc.[StatusCodeID]          = CAST(v.[Value] AS INT)
WHERE statusC.[StatusOfMetaDataID] IS NOT NULL;
GO

DROP VIEW IF EXISTS [dbo].[vw_DeviceStatus];
GO

CREATE VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]              AS StatusChannelID,
    statusC.[StatusOfEquipmentID]     AS EquipmentID,
    e.[identifier]                    AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)            AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]           statusC ON statusC.[Channel_ID]       = v.[Channel_ID]
JOIN [dbo].[Equipment]         e       ON e.[Equipment_ID]           = statusC.[StatusOfEquipmentID]
LEFT JOIN [dbo].[SensorStatusCode] sc  ON sc.[StatusCodeID]          = CAST(v.[Value] AS INT)
WHERE statusC.[StatusOfEquipmentID] IS NOT NULL;
GO

-- ============================================================
-- B.10 Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '2.0.0',
    SYSUTCDATETIME(),
    'Phase B — MetaData -> Channel rename, LabAnalysis/LabValue tables',
    'v1.10.0_to_v2.0.0_mssql.sql'
);
GO
