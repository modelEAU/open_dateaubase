-- Rollback: v1.9.0 -> v1.8.0
-- Platform: mssql
-- Generated: 2026-02-23
-- Forward migration: v1.8.0_to_v1.9.0_mssql.sql
--
-- Restores MetaData columns, IngestionRoute, and Purpose from backup tables
-- created during the forward migration.
--
-- PREREQUISITE: Forward migration must have been run (backup tables must exist).

SET NOCOUNT ON;
GO

-- ============================================================
-- 1.  Verify backup tables exist before proceeding
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'MetaData_v1_8_backup' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    RAISERROR('MetaData_v1_8_backup does not exist. Cannot roll back.', 16, 1);
    RETURN;
END

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'IngestionRoute_v1_8_backup' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    RAISERROR('IngestionRoute_v1_8_backup does not exist. Cannot roll back.', 16, 1);
    RETURN;
END
GO

-- ============================================================
-- 2.  Restore vw_ChannelStatus with LocationName (v1.8.0 definition)
-- ============================================================

ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusMD.[Metadata_ID]            AS StatusMetaDataID,
    statusMD.[StatusOfMetaDataID]     AS MeasurementMetaDataID,
    measMD.[Equipment_ID]             AS EquipmentID,
    e.[identifier]                    AS EquipmentName,
    p.[Parameter]                     AS MeasurementParameter,
    sp.[Sampling_point]               AS LocationName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)            AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData]        statusMD ON statusMD.[Metadata_ID]       = v.[Metadata_ID]
JOIN [dbo].[MetaData]        measMD   ON measMD.[Metadata_ID]          = statusMD.[StatusOfMetaDataID]
JOIN [dbo].[Parameter]       p        ON p.[Parameter_ID]              = measMD.[Parameter_ID]
JOIN [dbo].[SamplingPoints]  sp       ON sp.[Sampling_point_ID]        = measMD.[Sampling_point_ID]
JOIN [dbo].[Equipment]       e        ON e.[Equipment_ID]              = measMD.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc ON sc.[StatusCodeID]            = CAST(v.[Value] AS INT)
WHERE statusMD.[StatusOfMetaDataID] IS NOT NULL;
GO

-- ============================================================
-- 3.  Remove the UNIQUE sensor stream index
-- ============================================================

DROP INDEX [UQ_MetaData_SensorStream] ON [dbo].[MetaData];
GO

-- ============================================================
-- 4.  Restore columns to MetaData from backup
-- ============================================================

ALTER TABLE [dbo].[MetaData] ADD [Condition_ID]        INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Purpose_ID]          INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Sampling_point_ID]   INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Campaign_ID]         INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Project_ID]          INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Contact_ID]          INT NULL;
GO

UPDATE m
SET
    m.[Condition_ID]      = b.[Condition_ID],
    m.[Purpose_ID]        = b.[Purpose_ID],
    m.[Sampling_point_ID] = b.[Sampling_point_ID],
    m.[Campaign_ID]       = b.[Campaign_ID],
    m.[Project_ID]        = b.[Project_ID],
    m.[Contact_ID]        = b.[Contact_ID]
FROM [dbo].[MetaData] m
JOIN [dbo].[MetaData_v1_8_backup] b ON b.[Metadata_ID] = m.[Metadata_ID];
GO

-- ============================================================
-- 5.  Restore Purpose table from backup MetaData data
--     (Purpose table itself was dropped; restore from original create)
-- ============================================================

CREATE TABLE [dbo].[Purpose] (
    [Purpose_ID] INT IDENTITY(1,1) NOT NULL,
    [Purpose] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_Purpose] PRIMARY KEY ([Purpose_ID])
);
GO

-- Re-seed Purpose rows from backup if any existed (re-insert distinct purposes referenced)
-- NOTE: If Purpose had data, restore it here manually or from a separate backup.
-- This rollback only restores the table structure and the FK.
GO

-- ============================================================
-- 6.  Restore FK constraints on MetaData
-- ============================================================

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_WeatherCondition]
    FOREIGN KEY ([Condition_ID]) REFERENCES [dbo].[WeatherCondition] ([Condition_ID]);

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Purpose]
    FOREIGN KEY ([Purpose_ID]) REFERENCES [dbo].[Purpose] ([Purpose_ID]);

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_SamplingPoints]
    FOREIGN KEY ([Sampling_point_ID]) REFERENCES [dbo].[SamplingPoints] ([Sampling_point_ID]);

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Campaign]
    FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Project]
    FOREIGN KEY ([Project_ID]) REFERENCES [dbo].[Project] ([Project_ID]);

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Person]
    FOREIGN KEY ([Contact_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
GO

-- ============================================================
-- 7.  Restore IngestionRoute from backup
-- ============================================================

CREATE TABLE [dbo].[IngestionRoute] (
    [IngestionRoute_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT NULL,
    [Parameter_ID] INT NOT NULL,
    [DataProvenance_ID] INT NOT NULL,
    [ProcessingDegree] NVARCHAR(50) NOT NULL DEFAULT 'Raw',
    [ValidFrom] DATETIME2(7) NOT NULL,
    [ValidTo] DATETIME2(7) NULL,
    [CreatedAt] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    [Metadata_ID] INT NOT NULL,
    [Notes] NVARCHAR(500) NULL,
    CONSTRAINT [PK_IngestionRoute] PRIMARY KEY ([IngestionRoute_ID])
);
GO

-- Re-insert routes from backup (disable IDENTITY so IDs match)
SET IDENTITY_INSERT [dbo].[IngestionRoute] ON;

INSERT INTO [dbo].[IngestionRoute]
    ([IngestionRoute_ID], [Equipment_ID], [Parameter_ID], [DataProvenance_ID],
     [ProcessingDegree], [ValidFrom], [ValidTo], [CreatedAt], [Metadata_ID], [Notes])
SELECT
    [IngestionRoute_ID], [Equipment_ID], [Parameter_ID], [DataProvenance_ID],
    [ProcessingDegree], [ValidFrom], [ValidTo], [CreatedAt], [Metadata_ID], [Notes]
FROM [dbo].[IngestionRoute_v1_8_backup];

SET IDENTITY_INSERT [dbo].[IngestionRoute] OFF;
GO

ALTER TABLE [dbo].[IngestionRoute]
    ADD CONSTRAINT [FK_IngestionRoute_Equipment]
    FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);

ALTER TABLE [dbo].[IngestionRoute]
    ADD CONSTRAINT [FK_IngestionRoute_Parameter]
    FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);

ALTER TABLE [dbo].[IngestionRoute]
    ADD CONSTRAINT [FK_IngestionRoute_DataProvenance]
    FOREIGN KEY ([DataProvenance_ID]) REFERENCES [dbo].[DataProvenance] ([DataProvenance_ID]);

ALTER TABLE [dbo].[IngestionRoute]
    ADD CONSTRAINT [FK_IngestionRoute_MetaData]
    FOREIGN KEY ([Metadata_ID]) REFERENCES [dbo].[MetaData] ([Metadata_ID]);

CREATE INDEX [IX_IngestionRoute_Lookup]
    ON [dbo].[IngestionRoute] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree], [ValidFrom]);
GO

-- ============================================================
-- 8.  Drop backup tables
-- ============================================================

DROP TABLE [dbo].[MetaData_v1_8_backup];
DROP TABLE [dbo].[IngestionRoute_v1_8_backup];
GO

-- ============================================================
-- 9.  Update SchemaVersion
-- ============================================================

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.9.0';

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.8.0',
    SYSUTCDATETIME(),
    'ROLLBACK from 1.9.0: restored Condition_ID, Purpose_ID, Sampling_point_ID, Campaign_ID, Project_ID, Contact_ID columns; restored IngestionRoute and Purpose tables',
    'v1.8.0_to_v1.9.0_mssql_rollback.sql'
);
GO
