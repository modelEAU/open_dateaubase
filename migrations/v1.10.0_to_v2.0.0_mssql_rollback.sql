-- Rollback: v2.0.0 -> v1.10.0
-- Platform: mssql
-- Generated: 2026-02-23
--
-- Phase B rollback: restore Channel -> MetaData, drop LabAnalysis/LabValue
--   R.1  Drop views (they reference Channel/Channel_ID)
--   R.2  Drop UQ_Channel_SensorStream index (before renaming columns)
--   R.3  Rename tables back
--   R.4  Rename Channel_ID -> Metadata_ID in all tables
--   R.5  Add lab columns back to MetaData
--   R.6  Recreate filtered unique index with original name
--   R.7  Add lab FK constraints back
--   R.8  Drop LabValue and LabAnalysis tables
--   R.9  Rebuild views with original table/column names
--   R.10 Update SchemaVersion

SET NOCOUNT ON;
GO

-- ============================================================
-- R.1  Drop views (reference Channel which is about to be renamed)
-- ============================================================

DROP VIEW IF EXISTS [dbo].[vw_ChannelStatus];
DROP VIEW IF EXISTS [dbo].[vw_DeviceStatus];
GO

-- ============================================================
-- R.2  Drop unique index before column renames
-- ============================================================

DROP INDEX IF EXISTS [UQ_Channel_SensorStream] ON [dbo].[Channel];
GO

-- ============================================================
-- R.3  Rename tables back
-- ============================================================

EXEC sp_rename 'dbo.EquipmentEventChannel', 'EquipmentEventMetaData';
GO
EXEC sp_rename 'dbo.ChannelAxis',           'MetaDataAxis';
GO
EXEC sp_rename 'dbo.Channel',               'MetaData';
GO

-- ============================================================
-- R.4  Rename Channel_ID -> Metadata_ID in all tables
-- ============================================================

EXEC sp_rename 'dbo.MetaData.Channel_ID',                      'Metadata_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.EquipmentEventMetaData.Channel_ID',        'Metadata_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.MetaDataAxis.Channel_ID',                  'Metadata_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.Annotation.Channel_ID',                    'Metadata_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.DataLineage.Channel_ID',                   'Metadata_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.ValueImage.Channel_ID',                    'Metadata_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.ValueMatrix.Channel_ID',                   'Metadata_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.ValueVector.Channel_ID',                   'Metadata_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.Value.Channel_ID',                         'Metadata_ID', 'COLUMN';
GO

-- ============================================================
-- R.5  Add lab columns back to MetaData (all nullable)
-- ============================================================

ALTER TABLE [dbo].[MetaData] ADD [Sample_ID]        INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Laboratory_ID]    INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [AnalystPerson_ID] INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Procedure_ID]     INT NULL;
GO

-- ============================================================
-- R.6  Recreate filtered unique index (original name + Sample_ID filter)
-- ============================================================

CREATE UNIQUE INDEX [UQ_MetaData_SensorStream]
    ON [dbo].[MetaData] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree])
    WHERE [Equipment_ID] IS NOT NULL AND [Sample_ID] IS NULL;
GO

-- ============================================================
-- R.7  Add lab FK constraints back
-- ============================================================

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Sample]
    FOREIGN KEY ([Sample_ID]) REFERENCES [dbo].[Sample]([Sample_ID]);

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Laboratory]
    FOREIGN KEY ([Laboratory_ID]) REFERENCES [dbo].[Laboratory]([Laboratory_ID]);

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_AnalystPerson]
    FOREIGN KEY ([AnalystPerson_ID]) REFERENCES [dbo].[Person]([Person_ID]);

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Procedures]
    FOREIGN KEY ([Procedure_ID]) REFERENCES [dbo].[Procedures]([Procedure_ID]);
GO

-- ============================================================
-- R.8  Drop LabValue and LabAnalysis tables
-- ============================================================

DROP TABLE IF EXISTS [dbo].[LabValue];
DROP TABLE IF EXISTS [dbo].[LabAnalysis];
GO

-- ============================================================
-- R.9  Rebuild views with original table/column names
-- ============================================================

CREATE VIEW [dbo].[vw_ChannelStatus] AS
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
JOIN [dbo].[MetaData]          statusMD ON statusMD.[Metadata_ID]    = v.[Metadata_ID]
JOIN [dbo].[MetaData]          measMD   ON measMD.[Metadata_ID]      = statusMD.[StatusOfMetaDataID]
JOIN [dbo].[Parameter]         p        ON p.[Parameter_ID]          = measMD.[Parameter_ID]
JOIN [dbo].[Equipment]         e        ON e.[Equipment_ID]          = measMD.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc   ON sc.[StatusCodeID]         = CAST(v.[Value] AS INT)
WHERE statusMD.[StatusOfMetaDataID] IS NOT NULL;
GO

CREATE VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusMD.[Metadata_ID]            AS StatusMetaDataID,
    statusMD.[StatusOfEquipmentID]    AS EquipmentID,
    e.[identifier]                    AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)            AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]          statusMD ON statusMD.[Metadata_ID]    = v.[Metadata_ID]
JOIN [dbo].[Equipment]         e        ON e.[Equipment_ID]          = statusMD.[StatusOfEquipmentID]
LEFT JOIN [dbo].[SensorStatusCode] sc   ON sc.[StatusCodeID]         = CAST(v.[Value] AS INT)
WHERE statusMD.[StatusOfEquipmentID] IS NOT NULL;
GO

-- ============================================================
-- R.10 Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.10.0',
    SYSUTCDATETIME(),
    'Rollback of Phase B — Channel restored to MetaData, LabAnalysis/LabValue dropped',
    'v1.10.0_to_v2.0.0_mssql_rollback.sql'
);
GO
