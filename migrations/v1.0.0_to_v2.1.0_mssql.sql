-- ============================================================
-- Migration: v1.0.0 --> v2.1.0
-- Platform:  mssql
-- Generated: 2026-02-24
--
-- Applies to: a database initialized from migrations/v1.0.0_create_mssql.sql.
-- Produces:   the v2.1.0 schema (see sql_generation_scripts/v2.1.0_create_mssql.sql).
-- Rollback:   migrations/v2.1.0_to_v1.0.0_rollback_mssql.sql
--
-- NOTES
--   • This is a clean, single-step migration — NOT a concatenation of
--     intermediate scripts. Intermediate design iterations were never
--     deployed and are archived in migrations/archive/intermediate/.
--   • Value.Timestamp is migrated from INT (Unix epoch seconds) to
--     DATETIME2(7). Sub-second precision that was never stored is not lost.
--   • SamplingPoints.Pictures and Site.Picture are VARBINARY(MAX);
--     the v2.1.0 baseline generator emits "UNMAPPED TYPE" for these columns
--     but the type from v1.0.0 is correct.
-- ============================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

-- Guard: ensure we are starting from v1.0.0 baseline.
IF OBJECT_ID('dbo.MetaData') IS NULL
    RAISERROR('MetaData table not found — this migration expects a v1.0.0 baseline.', 16, 1);
IF OBJECT_ID('dbo.Channel') IS NOT NULL
    RAISERROR('Channel table already exists — migration may have already been applied.', 16, 1);
GO

BEGIN TRANSACTION;
GO

-- ============================================================
-- STEP 1: Create SchemaVersion table
-- ============================================================

CREATE TABLE [dbo].[SchemaVersion] (
    [VersionID]       INT IDENTITY(1,1) NOT NULL,
    [Version]         NVARCHAR(20)  NOT NULL,
    [AppliedDateTime]       DATETIME2(7)  NOT NULL DEFAULT SYSUTCDATETIME(),
    [Description]     NVARCHAR(500),
    [MigrationScript] NVARCHAR(200),
    CONSTRAINT [PK_SchemaVersion] PRIMARY KEY ([VersionID])
);
GO

-- ============================================================
-- STEP 2: Create lookup tables with reference data
-- ============================================================

CREATE TABLE [dbo].[ValueType] (
    [ValueType_ID]   INT IDENTITY(1,1) NOT NULL,
    [ValueType_Name] NVARCHAR(50)  NOT NULL,
    CONSTRAINT [PK_ValueType] PRIMARY KEY ([ValueType_ID])
);
GO
SET IDENTITY_INSERT [dbo].[ValueType] ON;
INSERT INTO [dbo].[ValueType] ([ValueType_ID], [ValueType_Name]) VALUES (1, N'Scalar');
INSERT INTO [dbo].[ValueType] ([ValueType_ID], [ValueType_Name]) VALUES (2, N'Vector');
INSERT INTO [dbo].[ValueType] ([ValueType_ID], [ValueType_Name]) VALUES (3, N'Matrix');
INSERT INTO [dbo].[ValueType] ([ValueType_ID], [ValueType_Name]) VALUES (4, N'Image');
SET IDENTITY_INSERT [dbo].[ValueType] OFF;
GO

CREATE TABLE [dbo].[CampaignType] (
    [CampaignType_ID]   INT IDENTITY(1,1) NOT NULL,
    [CampaignType_Name] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_CampaignType] PRIMARY KEY ([CampaignType_ID])
);
GO
SET IDENTITY_INSERT [dbo].[CampaignType] ON;
INSERT INTO [dbo].[CampaignType] ([CampaignType_ID], [CampaignType_Name]) VALUES (1, N'Experiment');
INSERT INTO [dbo].[CampaignType] ([CampaignType_ID], [CampaignType_Name]) VALUES (2, N'Operations');
INSERT INTO [dbo].[CampaignType] ([CampaignType_ID], [CampaignType_Name]) VALUES (3, N'Commissioning');
SET IDENTITY_INSERT [dbo].[CampaignType] OFF;
GO

CREATE TABLE [dbo].[DataProvenance] (
    [DataProvenance_ID]   INT IDENTITY(1,1) NOT NULL,
    [DataProvenance_Name] NVARCHAR(50)  NOT NULL,
    CONSTRAINT [PK_DataProvenance] PRIMARY KEY ([DataProvenance_ID])
);
GO
SET IDENTITY_INSERT [dbo].[DataProvenance] ON;
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (1, N'Sensor');
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (2, N'Laboratory');
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (3, N'Manual Entry');
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (4, N'Model Output');
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (5, N'External Source');
SET IDENTITY_INSERT [dbo].[DataProvenance] OFF;
GO

CREATE TABLE [dbo].[EquipmentEventType] (
    [EquipmentEventType_ID]   INT IDENTITY(1,1) NOT NULL,
    [EquipmentEventType_Name] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_EquipmentEventType] PRIMARY KEY ([EquipmentEventType_ID])
);
GO
INSERT INTO [dbo].[EquipmentEventType] ([EquipmentEventType_Name])
VALUES
    (N'Calibration'),
    (N'Validation'),
    (N'Maintenance'),
    (N'Installation'),
    (N'Removal'),
    (N'Firmware Update'),
    (N'Failure'),
    (N'Repair');
GO

CREATE TABLE [dbo].[AnnotationType] (
    [AnnotationType_ID]   INT          NOT NULL,
    [AnnotationTypeName]  NVARCHAR(100) NOT NULL,
    [Description]         NVARCHAR(500),
    [Color]               NVARCHAR(7),
    CONSTRAINT [PK_AnnotationType] PRIMARY KEY ([AnnotationType_ID])
);
GO
INSERT INTO [dbo].[AnnotationType] ([AnnotationType_ID], [AnnotationTypeName], [Description], [Color])
VALUES
    (1,  N'Fault',              N'Sensor or process fault',                      N'#FF4444'),
    (2,  N'Maintenance',        N'Sensor under maintenance',                     N'#FFA500'),
    (3,  N'Calibration Period', N'Data during calibration — may be invalid',     N'#FFD700'),
    (4,  N'Anomaly',            N'Unexpected behavior, needs investigation',     N'#FF69B4'),
    (5,  N'Experiment',         N'Data collected during a specific experiment',  N'#4488FF'),
    (6,  N'Process Event',      N'Known process event (storm, dosing, etc.)',    N'#44BB44'),
    (7,  N'Data Quality',       N'Suspect data quality (drift, fouling)',        N'#AA44FF'),
    (8,  N'Note',               N'General commentary',                           N'#888888'),
    (9,  N'Exclusion',          N'Data should be excluded from analysis',        N'#CC0000'),
    (10, N'Validated',          N'Data has been reviewed and accepted',          N'#00AA00');
GO

CREATE TABLE [dbo].[SensorStatusCode] (
    [StatusCodeID]   INT          NOT NULL,
    [StatusName]     NVARCHAR(50)  NOT NULL,
    [Description]    NVARCHAR(200),
    [IsOperational]  BIT          NOT NULL DEFAULT 1,
    [Severity]       INT          NOT NULL DEFAULT 0,
    CONSTRAINT [PK_SensorStatusCode] PRIMARY KEY ([StatusCodeID])
);
GO
INSERT INTO [dbo].[SensorStatusCode] ([StatusCodeID], [StatusName], [Description], [IsOperational], [Severity])
VALUES
    (0,  N'Unknown',      N'Status not reported or not available',                     0, 1),
    (1,  N'Operational',  N'Sensor channel is functioning normally',                   1, 0),
    (2,  N'Warning',      N'Sensor is operational but a warning condition exists',     1, 1),
    (3,  N'Fault',        N'Sensor channel has faulted, data is unreliable',           0, 2),
    (4,  N'Maintenance',  N'Sensor is undergoing maintenance',                         0, 1),
    (5,  N'Calibrating',  N'Sensor channel is being calibrated',                       0, 1),
    (6,  N'Starting Up',  N'Sensor is in startup/warmup phase',                        0, 1),
    (7,  N'Shutting Down',N'Sensor is shutting down',                                  0, 1),
    (8,  N'Offline',      N'Sensor is powered off or disconnected',                    0, 0),
    (9,  N'Degraded',     N'Sensor is operational but accuracy may be reduced',        1, 1),
    (10, N'Fouled',       N'Sensor probe is fouled, readings likely biased',           1, 2);
GO

CREATE TABLE [dbo].[ProcessingDegree] (
    [ProcessingDegree_ID]   INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(50)  NOT NULL,
    CONSTRAINT [PK_ProcessingDegree] PRIMARY KEY ([ProcessingDegree_ID])
);
GO
SET IDENTITY_INSERT [dbo].[ProcessingDegree] ON;
INSERT INTO [dbo].[ProcessingDegree] ([ProcessingDegree_ID], [Name]) VALUES (1, N'Raw');
INSERT INTO [dbo].[ProcessingDegree] ([ProcessingDegree_ID], [Name]) VALUES (2, N'Cleaned');
INSERT INTO [dbo].[ProcessingDegree] ([ProcessingDegree_ID], [Name]) VALUES (3, N'Calibrated');
INSERT INTO [dbo].[ProcessingDegree] ([ProcessingDegree_ID], [Name]) VALUES (4, N'Validated');
INSERT INTO [dbo].[ProcessingDegree] ([ProcessingDegree_ID], [Name]) VALUES (5, N'Filtered');
INSERT INTO [dbo].[ProcessingDegree] ([ProcessingDegree_ID], [Name]) VALUES (6, N'Predicted');
SET IDENTITY_INSERT [dbo].[ProcessingDegree] OFF;
GO

CREATE TABLE [dbo].[QualityCode] (
    [QualityCode_ID]   INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(50)  NOT NULL,
    [IsUsable]         BIT          NOT NULL DEFAULT 1,
    CONSTRAINT [PK_QualityCode] PRIMARY KEY ([QualityCode_ID])
);
GO
SET IDENTITY_INSERT [dbo].[QualityCode] ON;
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [IsUsable]) VALUES (1, N'Accepted',    1);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [IsUsable]) VALUES (2, N'Suspect',     1);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [IsUsable]) VALUES (3, N'Rejected',    0);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [IsUsable]) VALUES (4, N'BelowLoD',    0);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [IsUsable]) VALUES (5, N'AboveLoQ',    0);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [IsUsable]) VALUES (6, N'Outlier',     1);
SET IDENTITY_INSERT [dbo].[QualityCode] OFF;
GO

CREATE TABLE [dbo].[SampleType] (
    [SampleType_ID]   INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_SampleType] PRIMARY KEY ([SampleType_ID])
);
GO
SET IDENTITY_INSERT [dbo].[SampleType] ON;
INSERT INTO [dbo].[SampleType] ([SampleType_ID], [Name]) VALUES (1, N'Field');
INSERT INTO [dbo].[SampleType] ([SampleType_ID], [Name]) VALUES (2, N'Synthetic');
INSERT INTO [dbo].[SampleType] ([SampleType_ID], [Name]) VALUES (3, N'Master Standard');
INSERT INTO [dbo].[SampleType] ([SampleType_ID], [Name]) VALUES (4, N'Derived Standard');
INSERT INTO [dbo].[SampleType] ([SampleType_ID], [Name]) VALUES (5, N'Blank');
SET IDENTITY_INSERT [dbo].[SampleType] OFF;
GO

CREATE TABLE [dbo].[SampleMethod] (
    [SampleMethod_ID]   INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_SampleMethod] PRIMARY KEY ([SampleMethod_ID])
);
GO
SET IDENTITY_INSERT [dbo].[SampleMethod] ON;
INSERT INTO [dbo].[SampleMethod] ([SampleMethod_ID], [Name]) VALUES (1, N'Grab');
INSERT INTO [dbo].[SampleMethod] ([SampleMethod_ID], [Name]) VALUES (2, N'Composite24h');
INSERT INTO [dbo].[SampleMethod] ([SampleMethod_ID], [Name]) VALUES (3, N'Composite8h');
INSERT INTO [dbo].[SampleMethod] ([SampleMethod_ID], [Name]) VALUES (4, N'Passive');
INSERT INTO [dbo].[SampleMethod] ([SampleMethod_ID], [Name]) VALUES (5, N'Other');
SET IDENTITY_INSERT [dbo].[SampleMethod] OFF;
GO

-- ============================================================
-- STEP 3: Rename Contact → Person
-- ============================================================

-- Drop FKs that reference Contact.Contact_ID before renaming
ALTER TABLE [dbo].[MetaData]        DROP CONSTRAINT [FK_MetaData_Contact];
ALTER TABLE [dbo].[ProjectHasContact] DROP CONSTRAINT [FK_ProjectHasContact_Contact];
GO

ALTER TABLE [dbo].[Contact] DROP CONSTRAINT [PK_Contact];
GO

EXEC sp_rename 'dbo.Contact.Contact_ID', 'Person_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.Contact.Status', 'Role', 'COLUMN';
GO

ALTER TABLE [dbo].[Contact] DROP COLUMN [Skype_name];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Street_number];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Street_name];
ALTER TABLE [dbo].[Contact] DROP COLUMN [City];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Zip_code];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Country];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Office_number];
GO

EXEC sp_rename 'dbo.Contact', 'Person';
GO

ALTER TABLE [dbo].[Person] ADD CONSTRAINT [PK_Person] PRIMARY KEY ([Person_ID]);
GO

-- ============================================================
-- STEP 4: Convert Value.Timestamp from INT to DATETIME2(7)
-- NOTE: values are assumed to be Unix epoch seconds (UTC).
-- ============================================================

ALTER TABLE [dbo].[Value] ADD [Timestamp_new] DATETIME2(7) NULL;
GO

UPDATE [dbo].[Value]
SET [Timestamp_new] = DATEADD(SECOND, [Timestamp], CAST('1970-01-01T00:00:00' AS DATETIME2(7)))
WHERE [Timestamp] IS NOT NULL;
GO

ALTER TABLE [dbo].[Value] DROP CONSTRAINT [FK_Value_MetaData];
ALTER TABLE [dbo].[Value] DROP CONSTRAINT [FK_Value_Comments];
GO

ALTER TABLE [dbo].[Value] DROP COLUMN [Timestamp];
GO

EXEC sp_rename 'dbo.Value.Timestamp_new', 'Timestamp', 'COLUMN';
GO

-- Drop obsolete Value columns and the Comments table (FK already dropped above)
ALTER TABLE [dbo].[Value] DROP COLUMN [Comment_ID];
ALTER TABLE [dbo].[Value] DROP COLUMN [Number_of_experiment];
GO

DROP TABLE [dbo].[Comments];
GO

-- ============================================================
-- STEP 5: Drop all FKs that will be invalid after renames/drops
-- ============================================================

-- FKs on MetaData pointing at tables being dropped
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Project];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Purpose];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_SamplingPoints];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_WeatherCondition];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Equipment];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Parameter];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Procedures];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Unit];
GO

-- FKs on ParameterHasProcedures junction table
ALTER TABLE [dbo].[ParameterHasProcedures] DROP CONSTRAINT [FK_ParameterHasProcedures_Parameter];
ALTER TABLE [dbo].[ParameterHasProcedures] DROP CONSTRAINT [FK_ParameterHasProcedures_Procedures];
GO

-- FKs on Project junction tables
ALTER TABLE [dbo].[ProjectHasContact]      DROP CONSTRAINT [FK_ProjectHasContact_Project];
ALTER TABLE [dbo].[ProjectHasEquipment]    DROP CONSTRAINT [FK_ProjectHasEquipment_Equipment];
ALTER TABLE [dbo].[ProjectHasEquipment]    DROP CONSTRAINT [FK_ProjectHasEquipment_Project];
ALTER TABLE [dbo].[ProjectHasSamplingPoints] DROP CONSTRAINT [FK_ProjectHasSamplingPoints_Project];
ALTER TABLE [dbo].[ProjectHasSamplingPoints] DROP CONSTRAINT [FK_ProjectHasSamplingPoints_SamplingPoints];
GO

-- ============================================================
-- STEP 6: Drop obsolete tables (junctions first, then parents)
-- ============================================================

DROP TABLE [dbo].[ParameterHasProcedures];
DROP TABLE [dbo].[ProjectHasContact];
DROP TABLE [dbo].[ProjectHasEquipment];
DROP TABLE [dbo].[ProjectHasSamplingPoints];
DROP TABLE [dbo].[Project];
DROP TABLE [dbo].[Purpose];
GO

-- ============================================================
-- STEP 7: Drop v1.0.0-only columns from MetaData
-- ============================================================

ALTER TABLE [dbo].[MetaData] DROP COLUMN [Project_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Contact_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Purpose_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Sampling_point_ID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Condition_ID];
GO

-- ============================================================
-- STEP 8: Rename MetaData → Channel (column, then table)
-- ============================================================

ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [PK_MetaData];
GO

EXEC sp_rename 'dbo.MetaData.Metadata_ID', 'Channel_ID', 'COLUMN';
GO

EXEC sp_rename 'dbo.MetaData', 'Channel';
GO

ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [PK_Channel] PRIMARY KEY ([Channel_ID]);
GO

-- ============================================================
-- STEP 9: Add new columns to Channel
-- ============================================================

ALTER TABLE [dbo].[Channel] ADD [DataProvenance_ID]  INT NULL;
ALTER TABLE [dbo].[Channel] ADD [ProcessingDegree_ID] INT NOT NULL DEFAULT 1;
ALTER TABLE [dbo].[Channel] ADD [ValueType_ID]        INT NOT NULL DEFAULT 1;
ALTER TABLE [dbo].[Channel] ADD [StatusChannel_ID]    INT NULL;
GO

-- ============================================================
-- STEP 10: Rename Value.Metadata_ID → Channel_ID
-- ============================================================

EXEC sp_rename 'dbo.Value.Metadata_ID', 'Channel_ID', 'COLUMN';
GO

-- Re-add Value FK with new column name
ALTER TABLE [dbo].[Value] ADD CONSTRAINT [FK_Value_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
GO

-- ============================================================
-- STEP 11: Rename SamplingPoints table and columns; add new columns
-- ============================================================

-- Rename primary key column and other columns to PascalCase
EXEC sp_rename 'dbo.SamplingPoints.Sampling_point_ID', 'SamplingPoint_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.SamplingPoints.Sampling_point', 'SamplingPoint', 'COLUMN';
GO
EXEC sp_rename 'dbo.SamplingPoints.Sampling_location', 'SamplingLocation', 'COLUMN';
GO
EXEC sp_rename 'dbo.SamplingPoints.Latitude_GPS', 'LatitudeGPS', 'COLUMN';
GO
EXEC sp_rename 'dbo.SamplingPoints.Longitude_GPS', 'LongitudeGPS', 'COLUMN';
GO

-- Rename the table itself
EXEC sp_rename 'dbo.SamplingPoints', 'SamplingPoint';
GO

-- Add new columns
ALTER TABLE [dbo].[SamplingPoint] ADD [ValidFrom]            DATETIME2(7) NULL;
ALTER TABLE [dbo].[SamplingPoint] ADD [ValidTo]              DATETIME2(7) NULL;
ALTER TABLE [dbo].[SamplingPoint] ADD [CreatedByCampaign_ID] INT NULL;
GO

-- ============================================================
-- STEP 12: Create new tables — Tier A (no dependency on Channel)
-- ============================================================

CREATE TABLE [dbo].[ValueBinningAxis] (
    [ValueBinningAxis_ID] INT IDENTITY(1,1) NOT NULL,
    [Name]                NVARCHAR(200) NOT NULL,
    [Description]         NVARCHAR(500),
    [NumberOfBins]        INT NOT NULL,
    [Unit_ID]             INT NOT NULL,
    CONSTRAINT [PK_ValueBinningAxis] PRIMARY KEY ([ValueBinningAxis_ID])
);
GO

CREATE TABLE [dbo].[ValueBin] (
    [ValueBin_ID]         INT IDENTITY(1,1) NOT NULL,
    [ValueBinningAxis_ID] INT NOT NULL,
    [BinIndex]            INT NOT NULL,
    [LowerBound]          FLOAT NOT NULL,
    [UpperBound]          FLOAT NOT NULL,
    CONSTRAINT [PK_ValueBin] PRIMARY KEY ([ValueBin_ID]),
    CONSTRAINT [UQ_ValueBin_AxisIndex] UNIQUE ([ValueBinningAxis_ID], [BinIndex]),
    CONSTRAINT [CK_ValueBin_Bounds]    CHECK  ([UpperBound] > [LowerBound])
);
GO

CREATE TABLE [dbo].[Campaign] (
    [Campaign_ID]     INT IDENTITY(1,1) NOT NULL,
    [CampaignType_ID] INT NOT NULL,
    [Site_ID]         INT NOT NULL,
    [Name]                  NVARCHAR(200) NOT NULL,
    [Description]           NVARCHAR(2000),
    [CampaignStartDateTime] DATETIME2(7),
    [CampaignEndDateTime]   DATETIME2(7),
    CONSTRAINT [PK_Campaign] PRIMARY KEY ([Campaign_ID])
);
GO

CREATE TABLE [dbo].[Laboratory] (
    [Laboratory_ID] INT IDENTITY(1,1) NOT NULL,
    [Name]          NVARCHAR(200) NOT NULL,
    [Site_ID]       INT,
    [Description]   NVARCHAR(500),
    CONSTRAINT [PK_Laboratory] PRIMARY KEY ([Laboratory_ID])
);
GO

CREATE TABLE [dbo].[ProcessingStep] (
    [ProcessingStep_ID]  INT IDENTITY(1,1) NOT NULL,
    [Name]               NVARCHAR(200) NOT NULL,
    [Description]        NVARCHAR(2000),
    [MethodName]         NVARCHAR(200),
    [MethodVersion]      NVARCHAR(100),
    [ProcessingType]     NVARCHAR(100),
    [Parameters]          NVARCHAR(MAX),
    [ExecutedDateTime]    DATETIME2(7),
    [Dataset_ID]          INT,
    [ExecutedByPerson_ID] INT,
    CONSTRAINT [PK_ProcessingStep] PRIMARY KEY ([ProcessingStep_ID])
);
GO

CREATE TABLE [dbo].[Sample] (
    [Sample_ID]            INT IDENTITY(1,1) NOT NULL,
    [ParentSample_ID]      INT,
    [SampleType_ID]        INT,
    [SamplingPoint_ID]     INT NOT NULL,
    [SampledByPerson_ID]   INT,
    [Campaign_ID]          INT,
    [SampleDateTimeStart]  DATETIME2(7) NOT NULL,
    [SampleDateTimeEnd]    DATETIME2(7),
    [SampleMethod_ID]      INT,
    [SampleEquipment_ID]   INT,
    [Description]          NVARCHAR(500),
    CONSTRAINT [PK_Sample] PRIMARY KEY ([Sample_ID])
);
GO

CREATE TABLE [dbo].[LabAnalysis] (
    [LabAnalysis_ID]   INT IDENTITY(1,1) NOT NULL,
    [Sample_ID]        INT NOT NULL,
    [Laboratory_ID]    INT,
    [AnalystPerson_ID] INT,
    [Procedure_ID]     INT,
    [AnalysisDateTime] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    [Campaign_ID]      INT,
    [Notes]            NVARCHAR(500),
    CONSTRAINT [PK_LabAnalysis] PRIMARY KEY ([LabAnalysis_ID])
);
GO

CREATE TABLE [dbo].[LabValue] (
    [LabValue_ID]    INT IDENTITY(1,1) NOT NULL,
    [LabAnalysis_ID] INT NOT NULL,
    [Parameter_ID]   INT NOT NULL,
    [LabResult]      FLOAT NOT NULL,
    [Replicate]      INT NOT NULL DEFAULT 1,
    [QualityCode_ID] INT,
    [Comment]        NVARCHAR(MAX),
    CONSTRAINT [PK_LabValue] PRIMARY KEY ([LabValue_ID])
);
GO

CREATE TABLE [dbo].[EquipmentEvent] (
    [EquipmentEvent_ID]    INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID]         INT NOT NULL,
    [EquipmentEventType_ID] INT NOT NULL,
    [EventDateTimeStart]   DATETIME2(7) NOT NULL,
    [EventDateTimeEnd]     DATETIME2(7),
    [PerformedByPerson_ID] INT,
    [Campaign_ID]          INT,
    [Notes]                NVARCHAR(1000),
    CONSTRAINT [PK_EquipmentEvent] PRIMARY KEY ([EquipmentEvent_ID])
);
GO

CREATE TABLE [dbo].[EquipmentInstallation] (
    [Installation_ID]   INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID]      INT NOT NULL,
    [SamplingPoint_ID]  INT NOT NULL,
    [InstalledDate]     DATETIME2(7) NOT NULL,
    [RemovedDate]       DATETIME2(7),
    [Campaign_ID]       INT,
    [Notes]             NVARCHAR(500),
    CONSTRAINT [PK_EquipmentInstallation] PRIMARY KEY ([Installation_ID])
);
GO

CREATE TABLE [dbo].[Dataset] (
    [Dataset_ID]           INT IDENTITY(1,1) NOT NULL,
    [Name]                 NVARCHAR(200) NOT NULL,
    [Description]          NVARCHAR(2000),
    [Purpose]              NVARCHAR(500),
    [CreatedOn]            DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    [CreatedByPerson_ID]   INT,
    CONSTRAINT [PK_Dataset] PRIMARY KEY ([Dataset_ID])
);
GO

CREATE TABLE [dbo].[DatasetChannel] (
    [Dataset_ID]  INT NOT NULL,
    [Channel_ID]  INT NOT NULL,
    CONSTRAINT [PK_DatasetChannel] PRIMARY KEY ([Dataset_ID], [Channel_ID])
);
GO

-- ============================================================
-- STEP 13: Create new tables — Tier B (depend on Channel)
-- ============================================================

CREATE TABLE [dbo].[ChannelAxis] (
    [Channel_ID]          INT NOT NULL,
    [AxisRole]            INT NOT NULL,
    [ValueBinningAxis_ID] INT NOT NULL,
    CONSTRAINT [PK_ChannelAxis]         PRIMARY KEY ([Channel_ID], [AxisRole]),
    CONSTRAINT [CK_MetaDataAxis_AxisRole] CHECK ([AxisRole] IN (0, 1))
);
GO

CREATE TABLE [dbo].[ProcessingLineage] (
    [ProcessingLineage_ID] INT IDENTITY(1,1) NOT NULL,
    [ProcessingStep_ID]    INT NOT NULL,
    [Channel_ID]           INT NOT NULL,
    [RoleInProcessingStep] NVARCHAR(10) NOT NULL,
    [StartTime]            DATETIME2(7),
    [EndTime]              DATETIME2(7),
    CONSTRAINT [PK_ProcessingLineage] PRIMARY KEY ([ProcessingLineage_ID]),
    CONSTRAINT [CK_ProcessingLineage_Role] CHECK ([RoleInProcessingStep] IN (N'Input', N'Output'))
);
GO

CREATE TABLE [dbo].[Annotation] (
    [Annotation_ID]    INT IDENTITY(1,1) NOT NULL,
    [Channel_ID]       INT NOT NULL,
    [AnnotationType_ID] INT NOT NULL,
    [StartTime]        DATETIME2(7) NOT NULL,
    [EndTime]          DATETIME2(7),
    [AuthorPerson_ID]  INT,
    [Campaign_ID]      INT,
    [EquipmentEvent_ID] INT,
    [Title]            NVARCHAR(200),
    [Comment]          NVARCHAR(MAX),
    [CreatedDateTime]  DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    [ModifiedDateTime] DATETIME2(7),
    CONSTRAINT [PK_Annotation] PRIMARY KEY ([Annotation_ID])
);
GO

CREATE TABLE [dbo].[EquipmentStatusChannel] (
    [Equipment_ID]    INT NOT NULL,
    [StatusChannel_ID] INT NOT NULL,
    CONSTRAINT [PK_EquipmentStatusChannel] PRIMARY KEY ([Equipment_ID])
);
GO

CREATE TABLE [dbo].[ValueVector] (
    [Channel_ID]   INT NOT NULL,
    [Timestamp]    DATETIME2(7) NOT NULL,
    [ValueBin_ID]  INT NOT NULL,
    [Value]        FLOAT,
    [QualityCode]  INT,
    CONSTRAINT [PK_ValueVector] PRIMARY KEY ([Channel_ID], [Timestamp], [ValueBin_ID])
);
GO

CREATE TABLE [dbo].[ValueMatrix] (
    [Channel_ID]       INT NOT NULL,
    [Timestamp]        DATETIME2(7) NOT NULL,
    [RowValueBin_ID]   INT NOT NULL,
    [ColValueBin_ID]   INT NOT NULL,
    [Value]            FLOAT,
    [QualityCode]      INT,
    CONSTRAINT [PK_ValueMatrix] PRIMARY KEY ([Channel_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID])
);
GO

CREATE TABLE [dbo].[ValueImage] (
    [ValueImage_ID]   BIGINT IDENTITY(1,1) NOT NULL,
    [Channel_ID]      INT NOT NULL,
    [Timestamp]       DATETIME2(7) NOT NULL,
    [ImageWidth]      INT NOT NULL,
    [ImageHeight]     INT NOT NULL,
    [NumberOfChannels] INT NOT NULL DEFAULT 3,
    [ImageFormat]     NVARCHAR(20) NOT NULL,
    [FileSizeBytes]   BIGINT,
    [StorageBackend]  NVARCHAR(50) NOT NULL DEFAULT 'FileSystem',
    [StoragePath]     NVARCHAR(1000) NOT NULL,
    [Thumbnail]       VARBINARY(MAX),
    [QualityCode]     INT,
    CONSTRAINT [PK_ValueImage] PRIMARY KEY ([ValueImage_ID]),
    CONSTRAINT [UQ_ValueImage_ChannelTimestamp] UNIQUE ([Channel_ID], [Timestamp])
);
GO

-- ============================================================
-- STEP 14: Create new tables — Tier C (depend on Campaign)
-- ============================================================

CREATE TABLE [dbo].[CampaignEquipment] (
    [Campaign_ID]  INT NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [Role]         NVARCHAR(100),
    CONSTRAINT [PK_CampaignEquipment] PRIMARY KEY ([Campaign_ID], [Equipment_ID])
);
GO

CREATE TABLE [dbo].[CampaignSamplingLocation] (
    [Campaign_ID]      INT NOT NULL,
    [SamplingPoint_ID] INT NOT NULL,
    [Role]             NVARCHAR(100),
    CONSTRAINT [PK_CampaignSamplingLocation] PRIMARY KEY ([Campaign_ID], [SamplingPoint_ID])
);
GO

-- ============================================================
-- STEP 15: Add all FK constraints
-- ============================================================

-- Channel (formerly MetaData) — new FKs
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Equipment]         FOREIGN KEY ([Equipment_ID])       REFERENCES [dbo].[Equipment]       ([Equipment_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Parameter]         FOREIGN KEY ([Parameter_ID])       REFERENCES [dbo].[Parameter]       ([Parameter_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_DataProvenance]    FOREIGN KEY ([DataProvenance_ID])  REFERENCES [dbo].[DataProvenance]  ([DataProvenance_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ProcessingDegree]  FOREIGN KEY ([ProcessingDegree_ID]) REFERENCES [dbo].[ProcessingDegree] ([ProcessingDegree_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ValueType]         FOREIGN KEY ([ValueType_ID])       REFERENCES [dbo].[ValueType]       ([ValueType_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Channel]           FOREIGN KEY ([StatusChannel_ID])   REFERENCES [dbo].[Channel]         ([Channel_ID]);
GO

-- ChannelAxis
ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_Channel]          FOREIGN KEY ([Channel_ID])          REFERENCES [dbo].[Channel]          ([Channel_ID]);
ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_ValueBinningAxis] FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);
GO

-- ValueBinningAxis / ValueBin
ALTER TABLE [dbo].[ValueBinningAxis] ADD CONSTRAINT [FK_ValueBinningAxis_Unit] FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
ALTER TABLE [dbo].[ValueBin]         ADD CONSTRAINT [FK_ValueBin_ValueBinningAxis] FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);
GO

-- Campaign
ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_CampaignType] FOREIGN KEY ([CampaignType_ID]) REFERENCES [dbo].[CampaignType] ([CampaignType_ID]);
ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_Site]         FOREIGN KEY ([Site_ID])         REFERENCES [dbo].[Site]         ([Site_ID]);
GO

-- CampaignEquipment / CampaignSamplingLocation
ALTER TABLE [dbo].[CampaignEquipment]        ADD CONSTRAINT [FK_CampaignEquipment_Campaign]              FOREIGN KEY ([Campaign_ID])       REFERENCES [dbo].[Campaign]       ([Campaign_ID]);
ALTER TABLE [dbo].[CampaignEquipment]        ADD CONSTRAINT [FK_CampaignEquipment_Equipment]             FOREIGN KEY ([Equipment_ID])      REFERENCES [dbo].[Equipment]      ([Equipment_ID]);
ALTER TABLE [dbo].[CampaignSamplingLocation] ADD CONSTRAINT [FK_CampaignSamplingLocation_Campaign]      FOREIGN KEY ([Campaign_ID])      REFERENCES [dbo].[Campaign]      ([Campaign_ID]);
ALTER TABLE [dbo].[CampaignSamplingLocation] ADD CONSTRAINT [FK_CampaignSamplingLocation_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
GO

-- ProcessingLineage
ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_ProcessingStep] FOREIGN KEY ([ProcessingStep_ID]) REFERENCES [dbo].[ProcessingStep] ([ProcessingStep_ID]);
ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_Channel]        FOREIGN KEY ([Channel_ID])        REFERENCES [dbo].[Channel]        ([Channel_ID]);
GO

-- EquipmentEvent / EquipmentInstallation / EquipmentStatusChannel
ALTER TABLE [dbo].[EquipmentEvent]         ADD CONSTRAINT [FK_EquipmentEvent_Equipment]           FOREIGN KEY ([Equipment_ID])          REFERENCES [dbo].[Equipment]        ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentEvent]         ADD CONSTRAINT [FK_EquipmentEvent_EquipmentEventType]  FOREIGN KEY ([EquipmentEventType_ID]) REFERENCES [dbo].[EquipmentEventType] ([EquipmentEventType_ID]);
ALTER TABLE [dbo].[EquipmentEvent]         ADD CONSTRAINT [FK_EquipmentEvent_Person]              FOREIGN KEY ([PerformedByPerson_ID])  REFERENCES [dbo].[Person]           ([Person_ID]);
ALTER TABLE [dbo].[EquipmentEvent]         ADD CONSTRAINT [FK_EquipmentEvent_Campaign]            FOREIGN KEY ([Campaign_ID])           REFERENCES [dbo].[Campaign]         ([Campaign_ID]);
ALTER TABLE [dbo].[EquipmentInstallation]  ADD CONSTRAINT [FK_EquipmentInstallation_Equipment]     FOREIGN KEY ([Equipment_ID])    REFERENCES [dbo].[Equipment]     ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentInstallation]  ADD CONSTRAINT [FK_EquipmentInstallation_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[EquipmentInstallation]  ADD CONSTRAINT [FK_EquipmentInstallation_Campaign]      FOREIGN KEY ([Campaign_ID])     REFERENCES [dbo].[Campaign]      ([Campaign_ID]);
ALTER TABLE [dbo].[EquipmentStatusChannel] ADD CONSTRAINT [FK_EquipmentStatusChannel_Equipment]   FOREIGN KEY ([Equipment_ID])          REFERENCES [dbo].[Equipment]        ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentStatusChannel] ADD CONSTRAINT [FK_EquipmentStatusChannel_Channel]     FOREIGN KEY ([StatusChannel_ID])      REFERENCES [dbo].[Channel]          ([Channel_ID]);
GO

-- Lab tables
ALTER TABLE [dbo].[Laboratory]  ADD CONSTRAINT [FK_Laboratory_Site]          FOREIGN KEY ([Site_ID])          REFERENCES [dbo].[Site]       ([Site_ID]);
ALTER TABLE [dbo].[Sample]      ADD CONSTRAINT [FK_Sample_Sample]          FOREIGN KEY ([ParentSample_ID])    REFERENCES [dbo].[Sample]         ([Sample_ID]);
ALTER TABLE [dbo].[Sample]      ADD CONSTRAINT [FK_Sample_SampleType]      FOREIGN KEY ([SampleType_ID])      REFERENCES [dbo].[SampleType]     ([SampleType_ID]);
ALTER TABLE [dbo].[Sample]      ADD CONSTRAINT [FK_Sample_SamplingPoint]  FOREIGN KEY ([SamplingPoint_ID])  REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[Sample]      ADD CONSTRAINT [FK_Sample_Person]          FOREIGN KEY ([SampledByPerson_ID]) REFERENCES [dbo].[Person]         ([Person_ID]);
ALTER TABLE [dbo].[Sample]      ADD CONSTRAINT [FK_Sample_Campaign]        FOREIGN KEY ([Campaign_ID])        REFERENCES [dbo].[Campaign]       ([Campaign_ID]);
ALTER TABLE [dbo].[Sample]      ADD CONSTRAINT [FK_Sample_SampleMethod]    FOREIGN KEY ([SampleMethod_ID])    REFERENCES [dbo].[SampleMethod]   ([SampleMethod_ID]);
ALTER TABLE [dbo].[Sample]      ADD CONSTRAINT [FK_Sample_Equipment]       FOREIGN KEY ([SampleEquipment_ID]) REFERENCES [dbo].[Equipment]      ([Equipment_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Sample]       FOREIGN KEY ([Sample_ID])        REFERENCES [dbo].[Sample]     ([Sample_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Laboratory]   FOREIGN KEY ([Laboratory_ID])    REFERENCES [dbo].[Laboratory] ([Laboratory_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Person]       FOREIGN KEY ([AnalystPerson_ID]) REFERENCES [dbo].[Person]     ([Person_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Procedures]   FOREIGN KEY ([Procedure_ID])     REFERENCES [dbo].[Procedures] ([Procedure_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Campaign]     FOREIGN KEY ([Campaign_ID])      REFERENCES [dbo].[Campaign]   ([Campaign_ID]);
ALTER TABLE [dbo].[LabValue]    ADD CONSTRAINT [FK_LabValue_LabAnalysis]  FOREIGN KEY ([LabAnalysis_ID]) REFERENCES [dbo].[LabAnalysis]  ([LabAnalysis_ID]);
ALTER TABLE [dbo].[LabValue]    ADD CONSTRAINT [FK_LabValue_Parameter]    FOREIGN KEY ([Parameter_ID])   REFERENCES [dbo].[Parameter]    ([Parameter_ID]);
ALTER TABLE [dbo].[LabValue]    ADD CONSTRAINT [FK_LabValue_QualityCode]  FOREIGN KEY ([QualityCode_ID]) REFERENCES [dbo].[QualityCode]  ([QualityCode_ID]);
GO

-- Annotation
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Channel]        FOREIGN KEY ([Channel_ID])       REFERENCES [dbo].[Channel]       ([Channel_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_AnnotationType] FOREIGN KEY ([AnnotationType_ID]) REFERENCES [dbo].[AnnotationType] ([AnnotationType_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Person]         FOREIGN KEY ([AuthorPerson_ID])  REFERENCES [dbo].[Person]         ([Person_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Campaign]       FOREIGN KEY ([Campaign_ID])      REFERENCES [dbo].[Campaign]       ([Campaign_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_EquipmentEvent] FOREIGN KEY ([EquipmentEvent_ID]) REFERENCES [dbo].[EquipmentEvent] ([EquipmentEvent_ID]);
GO

-- ProcessingStep / Dataset / DatasetChannel
ALTER TABLE [dbo].[ProcessingStep]  ADD CONSTRAINT [FK_ProcessingStep_Person]        FOREIGN KEY ([ExecutedByPerson_ID]) REFERENCES [dbo].[Person]   ([Person_ID]);
ALTER TABLE [dbo].[ProcessingStep]  ADD CONSTRAINT [FK_ProcessingStep_Dataset]       FOREIGN KEY ([Dataset_ID])          REFERENCES [dbo].[Dataset]  ([Dataset_ID]);
ALTER TABLE [dbo].[Dataset]         ADD CONSTRAINT [FK_Dataset_Person]               FOREIGN KEY ([CreatedByPerson_ID])  REFERENCES [dbo].[Person]   ([Person_ID]);
ALTER TABLE [dbo].[DatasetChannel]  ADD CONSTRAINT [FK_DatasetChannel_Dataset]       FOREIGN KEY ([Dataset_ID])          REFERENCES [dbo].[Dataset]  ([Dataset_ID]);
ALTER TABLE [dbo].[DatasetChannel]  ADD CONSTRAINT [FK_DatasetChannel_Channel]       FOREIGN KEY ([Channel_ID])          REFERENCES [dbo].[Channel]  ([Channel_ID]);
GO

-- SamplingPoint new FK (Campaign)
ALTER TABLE [dbo].[SamplingPoint] ADD CONSTRAINT [FK_SamplingPoint_Campaign] FOREIGN KEY ([CreatedByCampaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
GO

-- ValueVector / ValueMatrix / ValueImage
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_Channel]  FOREIGN KEY ([Channel_ID])  REFERENCES [dbo].[Channel]  ([Channel_ID]);
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_ValueBin] FOREIGN KEY ([ValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_Channel]      FOREIGN KEY ([Channel_ID])       REFERENCES [dbo].[Channel]  ([Channel_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_RowValueBin]  FOREIGN KEY ([RowValueBin_ID])   REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_ColValueBin]  FOREIGN KEY ([ColValueBin_ID])   REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);
ALTER TABLE [dbo].[ValueImage]  ADD CONSTRAINT [FK_ValueImage_Channel]       FOREIGN KEY ([Channel_ID])       REFERENCES [dbo].[Channel]  ([Channel_ID]);
GO

-- ============================================================
-- STEP 16: Indexes
-- ============================================================

CREATE UNIQUE INDEX [UQ_Channel_SensorStream]
    ON [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID])
    WHERE [Equipment_ID] IS NOT NULL AND [Parameter_ID] IS NOT NULL;
GO

CREATE INDEX [IX_Annotation_Channel_Time]       ON [dbo].[Annotation]       ([Channel_ID], [StartTime], [EndTime]);
CREATE INDEX [IX_Annotation_Author]             ON [dbo].[Annotation]       ([AuthorPerson_ID], [CreatedDateTime]);
CREATE INDEX [IX_ProcessingLineage_Channel]     ON [dbo].[ProcessingLineage] ([Channel_ID]);
CREATE INDEX [IX_Lineage_Step_Role]             ON [dbo].[ProcessingLineage] ([ProcessingStep_ID], [RoleInProcessingStep]);
CREATE INDEX [IX_EquipmentEvent_Equipment_Start]         ON [dbo].[EquipmentEvent] ([Equipment_ID], [EventDateTimeStart]);
CREATE INDEX [IX_EquipmentInstallation_Equipment]        ON [dbo].[EquipmentInstallation] ([Equipment_ID], [InstalledDate]);
CREATE INDEX [IX_EquipmentInstallation_SamplingPoint]   ON [dbo].[EquipmentInstallation] ([SamplingPoint_ID], [InstalledDate]);
CREATE INDEX [IX_ValueImage_ChannelTimestamp]            ON [dbo].[ValueImage] ([Channel_ID], [Timestamp]);
GO

-- ============================================================
-- STEP 17: Create views
-- ============================================================

CREATE OR ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]          AS StatusChannelID,
    statusC.[StatusChannel_ID]    AS MeasurementChannelID,
    measC.[Equipment_ID]          AS EquipmentID,
    e.[Identifier]                AS EquipmentName,
    p.[Parameter]                 AS MeasurementParameter,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]               statusC ON statusC.[Channel_ID]      = v.[Channel_ID]
JOIN [dbo].[Channel]               measC   ON measC.[Channel_ID]        = statusC.[StatusChannel_ID]
JOIN [dbo].[Parameter]             p       ON p.[Parameter_ID]          = measC.[Parameter_ID]
JOIN [dbo].[Equipment]             e       ON e.[Equipment_ID]          = measC.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc      ON sc.[StatusCodeID]         = CAST(v.[Value] AS INT)
WHERE statusC.[StatusChannel_ID] IS NOT NULL;
GO

CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]          AS StatusChannelID,
    esc.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]                AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]                 statusC ON statusC.[Channel_ID]   = v.[Channel_ID]
JOIN [dbo].[EquipmentStatusChannel]  esc     ON esc.[StatusChannel_ID] = statusC.[Channel_ID]
JOIN [dbo].[Equipment]               e       ON e.[Equipment_ID]       = esc.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode]   sc      ON sc.[StatusCodeID]      = CAST(v.[Value] AS INT);
GO

-- ============================================================
-- STEP 18: Record schema version and commit
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedDateTime], [Description], [MigrationScript])
VALUES (
    '2.1.0',
    SYSUTCDATETIME(),
    'Consolidated migration from v1.0.0 baseline to v2.1.0 Channel schema',
    'v1.0.0_to_v2.1.0_mssql.sql'
);
GO

COMMIT TRANSACTION;
GO

PRINT 'Migration to v2.1.0 completed successfully.';
