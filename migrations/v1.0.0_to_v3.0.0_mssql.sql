-- ============================================================
-- Migration: v1.0.0 --> v3.0.0
-- Platform:  mssql
-- Generated: 2026-03-30
--
-- Applies to: a database initialized from migrations/v1.0.0_create_mssql.sql.
-- Produces:   the v3.0.0 schema (see sql_generation_scripts/v3.0.0_create_mssql.sql).
-- Rollback:   migrations/v1.0.0_to_v3.0.0_mssql_rollback.sql
--
-- NOTES
--   • Supersedes v1.0.0_to_v2.1.0_mssql.sql + v2.1.0_to_v2.2.0_mssql.sql
--     (both archived in migrations/archive/intermediate/).
--   • Sections A-C: v1.0.0 → v2.1.0 (MetaData→Channel rename chain, Observation hub excluded)
--   • Section D:   v2.1.0 → v2.2.0 (Observation hub: Value/ValueVector/ValueMatrix/ValueImage)
--   • Section E:   v2.2.0 → v3.0.0 (SignalPort abstraction, ControlLoop tables)
-- ============================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;

-- Guard: ensure v1.0.0 baseline (MetaData exists, SignalPort does not).
IF OBJECT_ID('dbo.MetaData') IS NULL
    RAISERROR('MetaData table not found — this migration expects a v1.0.0 baseline.', 16, 1);
IF OBJECT_ID('dbo.SignalPort') IS NOT NULL
    RAISERROR('SignalPort already exists — migration may have already been applied.', 16, 1);
GO

BEGIN TRANSACTION;
GO

-- ============================================================
-- SECTIONS A-C: v1.0.0 → v2.1.0
-- ============================================================

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
    (N'Repair'),
    (N'Commissioning'),
    (N'Decommissioning');
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
    (10, N'Validated',          N'Data has been reviewed and accepted',          N'#00AA00'),
    (11, N'Equipment Relocation', N'Sensor was physically moved to a different sampling point', N'#FF8C00');
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
DROP TABLE [dbo].[WeatherCondition];
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
EXEC sp_rename 'dbo.SamplingPoints.Latitude_GPS', 'LatitudeWGS84', 'COLUMN';
GO
EXEC sp_rename 'dbo.SamplingPoints.Longitude_GPS', 'LongitudeWGS84', 'COLUMN';
GO
-- Change GPS columns from NVARCHAR(100) to FLOAT (note: table still named SamplingPoints at this point)
ALTER TABLE [dbo].[SamplingPoints] ALTER COLUMN [LatitudeWGS84] FLOAT;
GO
ALTER TABLE [dbo].[SamplingPoints] ALTER COLUMN [LongitudeWGS84] FLOAT;
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
-- STEP 11b: Add LatitudeWGS84 and LongitudeWGS84 columns to Site table
-- ============================================================

ALTER TABLE [dbo].[Site] ADD [LatitudeWGS84] FLOAT NULL;
ALTER TABLE [dbo].[Site] ADD [LongitudeWGS84] FLOAT NULL;
GO

-- ============================================================
-- STEP 11c: Rename columns to PascalCase to match v2.1.0 schema
-- ============================================================

-- Site table
EXEC sp_rename 'dbo.Site.Zip_code', 'PostCode', 'COLUMN';
EXEC sp_rename 'dbo.Site.Street_number', 'StreetNumber', 'COLUMN';
EXEC sp_rename 'dbo.Site.Street_name', 'StreetName', 'COLUMN';
GO

-- Person table (formerly Contact)
EXEC sp_rename 'dbo.Person.Last_name', 'LastName', 'COLUMN';
EXEC sp_rename 'dbo.Person.First_name', 'FirstName', 'COLUMN';
GO

-- Equipment table
EXEC sp_rename 'dbo.Equipment.model_ID', 'EquipmentModel_ID', 'COLUMN';
EXEC sp_rename 'dbo.Equipment.identifier', 'Identifier', 'COLUMN';
EXEC sp_rename 'dbo.Equipment.Serial_number', 'SerialNumber', 'COLUMN';
EXEC sp_rename 'dbo.Equipment.Storage_location', 'StorageLocation', 'COLUMN';
EXEC sp_rename 'dbo.Equipment.Purchase_date', 'PurchaseDate', 'COLUMN';
GO

-- EquipmentModel table
EXEC sp_rename 'dbo.EquipmentModel.Equipment_model_ID', 'EquipmentModel_ID', 'COLUMN';
EXEC sp_rename 'dbo.EquipmentModel.Equipment_model', 'EquipmentModel', 'COLUMN';
EXEC sp_rename 'dbo.EquipmentModel.Manual_location', 'ManualLocation', 'COLUMN';
GO

-- Watershed table
EXEC sp_rename 'dbo.Watershed.name', 'Name', 'COLUMN';
EXEC sp_rename 'dbo.Watershed.Surface_area', 'SurfaceArea', 'COLUMN';
EXEC sp_rename 'dbo.Watershed.Concentration_time', 'ConcentrationTime', 'COLUMN';
EXEC sp_rename 'dbo.Watershed.Impervious_surface', 'ImperviousSurface', 'COLUMN';
GO

-- UrbanCharacteristics table
EXEC sp_rename 'dbo.UrbanCharacteristics.Green_spaces', 'GreenSpaces', 'COLUMN';
GO

-- HydrologicalCharacteristics table
EXEC sp_rename 'dbo.HydrologicalCharacteristics.Urban_area', 'UrbanArea', 'COLUMN';
GO

-- Procedures table
EXEC sp_rename 'dbo.Procedures.Procedure_name', 'ProcedureName', 'COLUMN';
EXEC sp_rename 'dbo.Procedures.Procedure_type', 'ProcedureType', 'COLUMN';
EXEC sp_rename 'dbo.Procedures.Procedure_location', 'ProcedureLocation', 'COLUMN';
GO

-- Junction tables (EquipmentModel column was renamed, so junction columns must match)
EXEC sp_rename 'dbo.EquipmentModelHasParameter.Equipment_model_ID', 'EquipmentModel_ID', 'COLUMN';
EXEC sp_rename 'dbo.EquipmentModelHasProcedures.Equipment_model_ID', 'EquipmentModel_ID', 'COLUMN';
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

SET QUOTED_IDENTIFIER ON;
GO

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
    CAST(v.[Value] AS INT)        AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Channel]               statusC ON statusC.[Channel_ID]      = v.[Channel_ID]
JOIN [dbo].[Channel]               measC   ON measC.[Channel_ID]        = statusC.[StatusChannel_ID]
JOIN [dbo].[Parameter]             p       ON p.[Parameter_ID]          = measC.[Parameter_ID]
JOIN [dbo].[Equipment]             e       ON e.[Equipment_ID]          = measC.[Equipment_ID]
WHERE statusC.[StatusChannel_ID] IS NOT NULL;
GO

CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]          AS StatusChannelID,
    esc.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]                AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Channel]                 statusC ON statusC.[Channel_ID]   = v.[Channel_ID]
JOIN [dbo].[EquipmentStatusChannel]  esc     ON esc.[StatusChannel_ID] = statusC.[Channel_ID]
JOIN [dbo].[Equipment]               e       ON e.[Equipment_ID]       = esc.[Equipment_ID];
GO

-- ============================================================
-- SECTION D: v2.1.0 → v2.2.0 (Observation hub)
-- ============================================================

-- ============================================================
-- STEP 1: Create Observation hub table
-- ============================================================

CREATE TABLE [dbo].[Observation] (
    [Observation_ID] BIGINT        IDENTITY(1,1) NOT NULL,
    [Channel_ID]     INT           NOT NULL,
    [Timestamp]      DATETIME2(7)  NOT NULL,
    [DataType]       VARCHAR(10)   NOT NULL,
    CONSTRAINT [PK_Observation] PRIMARY KEY ([Observation_ID]),
    CONSTRAINT [UQ_Observation_ChannelTimestampType]
        UNIQUE ([Channel_ID], [Timestamp], [DataType]),
    CONSTRAINT [FK_Observation_Channel]
        FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]),
    CONSTRAINT [CK_Observation_DataType]
        CHECK ([DataType] IN ('Scalar','Vector','Matrix','Image'))
);
GO

CREATE INDEX [IX_Observation_Channel_Timestamp]
    ON [dbo].[Observation] ([Channel_ID], [Timestamp]);
GO

-- ============================================================
-- STEP 2: Data integrity check + backfill Observation from Value;
--         restructure Value as lean scalar payload
-- ============================================================

-- Pre-migration duplicate check — fail if any (Channel_ID, Timestamp) pair
-- appears more than once in Value (would violate UQ_Observation_ChannelTimestampType).
IF EXISTS (
    SELECT [Channel_ID], [Timestamp]
    FROM [dbo].[Value]
    WHERE [Channel_ID] IS NOT NULL AND [Timestamp] IS NOT NULL
    GROUP BY [Channel_ID], [Timestamp]
    HAVING COUNT(*) > 1
)
    RAISERROR('Duplicate (Channel_ID, Timestamp) pairs in dbo.Value — deduplicate before migrating.', 16, 1);
GO

-- Backfill Observation rows from Value (one per scalar row).
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
SELECT [Channel_ID], [Timestamp], 'Scalar'
FROM [dbo].[Value]
WHERE [Channel_ID] IS NOT NULL AND [Timestamp] IS NOT NULL;
GO

-- Add Observation_ID column to Value (nullable until populated).
ALTER TABLE [dbo].[Value] ADD [Observation_ID] BIGINT NULL;
GO

-- Populate Observation_ID by joining back to Observation.
UPDATE v
SET v.[Observation_ID] = o.[Observation_ID]
FROM [dbo].[Value] v
JOIN [dbo].[Observation] o
    ON o.[Channel_ID] = v.[Channel_ID]
   AND o.[Timestamp]  = v.[Timestamp]
   AND o.[DataType]   = 'Scalar';
GO

-- Make Observation_ID NOT NULL now that all rows are populated.
ALTER TABLE [dbo].[Value] ALTER COLUMN [Observation_ID] BIGINT NOT NULL;
GO

-- Drop FK_Value_Channel (blocks column drop).
ALTER TABLE [dbo].[Value] DROP CONSTRAINT [FK_Value_Channel];
GO

-- Drop PK on Value_ID (use dynamic name lookup for safety).
DECLARE @pk NVARCHAR(200) = (
    SELECT name FROM sys.key_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.Value') AND type = 'PK'
);
IF @pk IS NOT NULL
    EXEC('ALTER TABLE [dbo].[Value] DROP CONSTRAINT [' + @pk + ']');
GO

-- Drop Value_ID (IDENTITY — no other table FKs into Value.Value_ID).
ALTER TABLE [dbo].[Value] DROP COLUMN [Value_ID];
GO

-- Drop Channel_ID and Timestamp (now redundant, encoded in Observation).
ALTER TABLE [dbo].[Value] DROP COLUMN [Channel_ID];
ALTER TABLE [dbo].[Value] DROP COLUMN [Timestamp];
GO

-- Add new PK on Observation_ID.
ALTER TABLE [dbo].[Value]
    ADD CONSTRAINT [PK_Value] PRIMARY KEY ([Observation_ID]);
GO

-- Add FK Observation_ID → Observation.
ALTER TABLE [dbo].[Value]
    ADD CONSTRAINT [FK_Value_Observation]
    FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
GO

-- ==============================================================
-- STEP 3: Backfill Observation from ValueVector; restructure as
--         lean payload keyed by (Observation_ID, ValueBin_ID)
-- ==============================================================

-- Backfill Observation rows from ValueVector (one per unique Channel_ID/Timestamp pair).
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
SELECT DISTINCT [Channel_ID], [Timestamp], 'Vector'
FROM [dbo].[ValueVector];
GO

-- Add Observation_ID column to ValueVector (nullable until populated).
ALTER TABLE [dbo].[ValueVector] ADD [Observation_ID] BIGINT NULL;
GO

-- Populate Observation_ID by joining back to Observation.
UPDATE vv
SET vv.[Observation_ID] = o.[Observation_ID]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[Observation] o
    ON o.[Channel_ID] = vv.[Channel_ID]
   AND o.[Timestamp]  = vv.[Timestamp]
   AND o.[DataType]   = 'Vector';
GO

-- Make Observation_ID NOT NULL now that all rows are populated.
ALTER TABLE [dbo].[ValueVector] ALTER COLUMN [Observation_ID] BIGINT NOT NULL;
GO

-- Drop old composite PK (blocks column drops).
ALTER TABLE [dbo].[ValueVector] DROP CONSTRAINT [PK_ValueVector];
GO

-- Drop FK on Channel_ID (blocks Channel_ID column drop).
ALTER TABLE [dbo].[ValueVector] DROP CONSTRAINT [FK_ValueVector_Channel];
GO

-- Drop Channel_ID and Timestamp (now redundant, encoded in Observation).
ALTER TABLE [dbo].[ValueVector] DROP COLUMN [Channel_ID];
ALTER TABLE [dbo].[ValueVector] DROP COLUMN [Timestamp];
GO

-- Add new composite PK on (Observation_ID, ValueBin_ID).
ALTER TABLE [dbo].[ValueVector]
    ADD CONSTRAINT [PK_ValueVector] PRIMARY KEY ([Observation_ID], [ValueBin_ID]);
GO

-- Add FK Observation_ID → Observation.
ALTER TABLE [dbo].[ValueVector]
    ADD CONSTRAINT [FK_ValueVector_Observation]
    FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
GO

-- Note: FK_ValueVector_ValueBin is NOT dropped — ValueBin_ID column is unchanged.

-- ==============================================================
-- STEP 4: Backfill Observation from ValueMatrix; restructure as
--         lean payload keyed by (Observation_ID, RowValueBin_ID, ColValueBin_ID)
-- ==============================================================

-- Backfill Observation rows from ValueMatrix (one per unique Channel_ID/Timestamp pair).
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
SELECT DISTINCT [Channel_ID], [Timestamp], 'Matrix'
FROM [dbo].[ValueMatrix];
GO

-- Add Observation_ID column to ValueMatrix (nullable until populated).
ALTER TABLE [dbo].[ValueMatrix] ADD [Observation_ID] BIGINT NULL;
GO

-- Populate Observation_ID by joining back to Observation.
UPDATE vm
SET vm.[Observation_ID] = o.[Observation_ID]
FROM [dbo].[ValueMatrix] vm
JOIN [dbo].[Observation] o
    ON o.[Channel_ID] = vm.[Channel_ID]
   AND o.[Timestamp]  = vm.[Timestamp]
   AND o.[DataType]   = 'Matrix';
GO

-- Make Observation_ID NOT NULL now that all rows are populated.
ALTER TABLE [dbo].[ValueMatrix] ALTER COLUMN [Observation_ID] BIGINT NOT NULL;
GO

-- Drop old composite PK (blocks column drops).
ALTER TABLE [dbo].[ValueMatrix] DROP CONSTRAINT [PK_ValueMatrix];
GO

-- Drop FK on Channel_ID (blocks Channel_ID column drop).
ALTER TABLE [dbo].[ValueMatrix] DROP CONSTRAINT [FK_ValueMatrix_Channel];
GO

-- Drop Channel_ID and Timestamp (now redundant, encoded in Observation).
ALTER TABLE [dbo].[ValueMatrix] DROP COLUMN [Channel_ID];
ALTER TABLE [dbo].[ValueMatrix] DROP COLUMN [Timestamp];
GO

-- Add new composite PK on (Observation_ID, RowValueBin_ID, ColValueBin_ID).
ALTER TABLE [dbo].[ValueMatrix]
    ADD CONSTRAINT [PK_ValueMatrix]
    PRIMARY KEY ([Observation_ID], [RowValueBin_ID], [ColValueBin_ID]);
GO

-- Add FK Observation_ID → Observation.
ALTER TABLE [dbo].[ValueMatrix]
    ADD CONSTRAINT [FK_ValueMatrix_Observation]
    FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
GO

-- Note: FK_ValueMatrix_RowValueBin and FK_ValueMatrix_ColValueBin are NOT dropped.

-- ==============================================================
-- STEP 5: Backfill Observation from ValueImage; restructure —
--         swap ValueImage_ID IDENTITY PK for Observation_ID PK
-- ==============================================================

-- Backfill Observation rows from ValueImage.
-- No DISTINCT needed: UQ_ValueImage_ChannelTimestamp already enforces uniqueness.
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
SELECT [Channel_ID], [Timestamp], 'Image'
FROM [dbo].[ValueImage];
GO

-- Add Observation_ID column to ValueImage (nullable until populated).
ALTER TABLE [dbo].[ValueImage] ADD [Observation_ID] BIGINT NULL;
GO

-- Populate Observation_ID by joining back to Observation.
UPDATE vi
SET vi.[Observation_ID] = o.[Observation_ID]
FROM [dbo].[ValueImage] vi
JOIN [dbo].[Observation] o
    ON o.[Channel_ID] = vi.[Channel_ID]
   AND o.[Timestamp]  = vi.[Timestamp]
   AND o.[DataType]   = 'Image';
GO

-- Make Observation_ID NOT NULL now that all rows are populated.
ALTER TABLE [dbo].[ValueImage] ALTER COLUMN [Observation_ID] BIGINT NOT NULL;
GO

-- Drop UNIQUE constraint on (Channel_ID, Timestamp) — blocks Timestamp column drop later.
ALTER TABLE [dbo].[ValueImage] DROP CONSTRAINT [UQ_ValueImage_ChannelTimestamp];
GO

-- Drop FK on Channel_ID (blocks Channel_ID column drop).
ALTER TABLE [dbo].[ValueImage] DROP CONSTRAINT [FK_ValueImage_Channel];
GO

-- Drop old PK on ValueImage_ID (required before dropping the IDENTITY column it covers).
ALTER TABLE [dbo].[ValueImage] DROP CONSTRAINT [PK_ValueImage];
GO

-- Drop ValueImage_ID (IDENTITY column — no external FK references).
ALTER TABLE [dbo].[ValueImage] DROP COLUMN [ValueImage_ID];
GO

-- Drop Channel_ID and Timestamp (now redundant, encoded in Observation).
ALTER TABLE [dbo].[ValueImage] DROP COLUMN [Channel_ID];
ALTER TABLE [dbo].[ValueImage] DROP COLUMN [Timestamp];
GO

-- Add new PK on Observation_ID.
ALTER TABLE [dbo].[ValueImage]
    ADD CONSTRAINT [PK_ValueImage] PRIMARY KEY ([Observation_ID]);
GO

-- Add FK Observation_ID → Observation.
ALTER TABLE [dbo].[ValueImage]
    ADD CONSTRAINT [FK_ValueImage_Observation]
    FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
GO

-- ==============================================================
-- STEP 6: Add nullable Observation_ID FK to Annotation
--         (supports point-level annotations alongside time-range)
-- ==============================================================

ALTER TABLE [dbo].[Annotation]
    ADD [Observation_ID] BIGINT NULL;
GO

ALTER TABLE [dbo].[Annotation]
    ADD CONSTRAINT [FK_Annotation_Observation]
    FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
GO

-- ProcessingLineage: unchanged (channel-level lineage semantics are correct).

-- ==============================================================
-- STEP 7: Recreate views to join through Observation
-- ==============================================================

CREATE OR ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    statusC.[StatusChannel_ID]  AS MeasurementChannelID,
    measC.[Equipment_ID]        AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    p.[Parameter]               AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]   o       ON o.[Observation_ID]    = v.[Observation_ID]
JOIN [dbo].[Channel]       statusC ON statusC.[Channel_ID]  = o.[Channel_ID]
JOIN [dbo].[Channel]       measC   ON measC.[Channel_ID]    = statusC.[StatusChannel_ID]
JOIN [dbo].[Parameter]     p       ON p.[Parameter_ID]      = measC.[Parameter_ID]
JOIN [dbo].[Equipment]     e       ON e.[Equipment_ID]      = measC.[Equipment_ID]
WHERE statusC.[StatusChannel_ID] IS NOT NULL;
GO

CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    esc.[Equipment_ID]          AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]            o       ON o.[Observation_ID]    = v.[Observation_ID]
JOIN [dbo].[Channel]                statusC ON statusC.[Channel_ID]  = o.[Channel_ID]
JOIN [dbo].[EquipmentStatusChannel] esc     ON esc.[StatusChannel_ID] = statusC.[Channel_ID]
JOIN [dbo].[Equipment]              e       ON e.[Equipment_ID]      = esc.[Equipment_ID];
GO

-- ============================================================
-- SECTION E: v2.2.0 → v3.0.0 — SignalPort abstraction
-- ============================================================

-- ============================================================
-- E1: Drop obsolete tables
-- ============================================================

ALTER TABLE [dbo].[EquipmentInstallation] DROP CONSTRAINT [FK_EquipmentInstallation_Equipment];
ALTER TABLE [dbo].[EquipmentInstallation] DROP CONSTRAINT [FK_EquipmentInstallation_SamplingPoint];
ALTER TABLE [dbo].[EquipmentInstallation] DROP CONSTRAINT [FK_EquipmentInstallation_Campaign];
GO

DROP TABLE [dbo].[EquipmentInstallation];
GO

ALTER TABLE [dbo].[EquipmentStatusChannel] DROP CONSTRAINT [FK_EquipmentStatusChannel_Equipment];
ALTER TABLE [dbo].[EquipmentStatusChannel] DROP CONSTRAINT [FK_EquipmentStatusChannel_Channel];
GO

DROP TABLE [dbo].[EquipmentStatusChannel];
GO

-- ============================================================
-- E2: Add IsActive to Equipment
-- ============================================================

ALTER TABLE [dbo].[Equipment]
    ADD [IsActive] BIT NOT NULL CONSTRAINT [DF_Equipment_IsActive] DEFAULT 1;
GO

-- ============================================================
-- E3: Create lookup tables with seed data
-- ============================================================

CREATE TABLE [dbo].[SignalPortType] (
    [SignalPortType_ID] INT          NOT NULL,
    [Name]              NVARCHAR(50) NOT NULL,
    [Description]       NVARCHAR(200) NULL,
    CONSTRAINT [PK_SignalPortType] PRIMARY KEY ([SignalPortType_ID])
);
GO

INSERT INTO [dbo].[SignalPortType] ([SignalPortType_ID], [Name], [Description]) VALUES
(1, N'Value',       N'Primary measurement or output value'),
(2, N'Status',      N'Device or measurement status flag'),
(3, N'Alarm',       N'Alarm or alert indicator'),
(4, N'Uncertainty', N'Measurement uncertainty estimate');
GO


CREATE TABLE [dbo].[ControlLoopPortRole] (
    [ControlLoopPortRole_ID] INT          NOT NULL,
    [Name]                   NVARCHAR(50) NOT NULL,
    [Description]            NVARCHAR(200) NULL,
    CONSTRAINT [PK_ControlLoopPortRole] PRIMARY KEY ([ControlLoopPortRole_ID])
);
GO

INSERT INTO [dbo].[ControlLoopPortRole] ([ControlLoopPortRole_ID], [Name], [Description]) VALUES
(1, N'MeasuredVariable',    N'The controlled or observed process variable'),
(2, N'ManipulatedVariable', N'The actuator or output adjusted by the controller'),
(3, N'SetPoint',            N'Target value supplied to the controller'),
(4, N'Disturbance',         N'Measured input that affects the process; not manipulated'),
(5, N'PredictedOutput',     N'Model-predicted value of the controlled variable'),
(6, N'Other',               N'Escape hatch for novel roles; describe in ControlLoop.Description');
GO

-- ============================================================
-- E4: Create DataAcquisitionSystem
-- ============================================================

CREATE TABLE [dbo].[DataAcquisitionSystem] (
    [DataAcquisitionSystem_ID] INT IDENTITY(1,1) NOT NULL,
    [ParentSystem_ID]          INT NULL,
    [Name]                     NVARCHAR(200) NOT NULL,
    [SystemType]               NVARCHAR(50)  NULL,
    [Manufacturer]             NVARCHAR(100) NULL,
    [Model]                    NVARCHAR(100) NULL,
    [Description]              NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_DataAcquisitionSystem] PRIMARY KEY ([DataAcquisitionSystem_ID]),
    CONSTRAINT [FK_DAS_ParentSystem]
        FOREIGN KEY ([ParentSystem_ID])
        REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID])
);
GO

-- ============================================================
-- E5: Create SignalPort
-- ============================================================

CREATE TABLE [dbo].[SignalPort] (
    [SignalPort_ID]            INT IDENTITY(1,1) NOT NULL,
    [DataAcquisitionSystem_ID] INT           NOT NULL,
    [Tag]                      NVARCHAR(200) NOT NULL,
    [SignalPortType_ID]        INT           NOT NULL,
    [ParentPort_ID]            INT           NULL,
    [IsActive]                 BIT           NOT NULL CONSTRAINT [DF_SignalPort_IsActive] DEFAULT 1,
    [Description]              NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_SignalPort] PRIMARY KEY ([SignalPort_ID]),
    CONSTRAINT [UQ_SignalPort_DAS_Tag]
        UNIQUE ([DataAcquisitionSystem_ID], [Tag]),
    CONSTRAINT [FK_SignalPort_DAS]
        FOREIGN KEY ([DataAcquisitionSystem_ID])
        REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID]),
    CONSTRAINT [FK_SignalPort_Type]
        FOREIGN KEY ([SignalPortType_ID])
        REFERENCES [dbo].[SignalPortType] ([SignalPortType_ID]),
    CONSTRAINT [FK_SignalPort_ParentPort]
        FOREIGN KEY ([ParentPort_ID])
        REFERENCES [dbo].[SignalPort] ([SignalPort_ID])
);
GO

-- ============================================================
-- E6: Create temporal history tables
-- ============================================================

CREATE TABLE [dbo].[SignalPortLocationHistory] (
    [SignalPortLocationHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [SignalPort_ID]                INT          NOT NULL,
    [SamplingPoint_ID]             INT          NOT NULL,
    [StartTime]                    DATETIME2(7) NOT NULL,
    [EndTime]                      DATETIME2(7) NULL,
    [Notes]                        NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_SignalPortLocationHistory] PRIMARY KEY ([SignalPortLocationHistory_ID]),
    CONSTRAINT [FK_SignalPortLocationHistory_Port]
        FOREIGN KEY ([SignalPort_ID])
        REFERENCES [dbo].[SignalPort] ([SignalPort_ID]),
    CONSTRAINT [FK_SignalPortLocationHistory_SamplingPoint]
        FOREIGN KEY ([SamplingPoint_ID])
        REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID])
);
GO

-- At most one active row (EndTime IS NULL) per SignalPort_ID.
CREATE UNIQUE INDEX [UQ_SignalPortLocationHistory_ActiveRow]
    ON [dbo].[SignalPortLocationHistory] ([SignalPort_ID])
    WHERE [EndTime] IS NULL;
GO

CREATE TABLE [dbo].[SignalPortEquipmentHistory] (
    [SignalPortEquipmentHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [SignalPort_ID]                 INT          NOT NULL,
    [Equipment_ID]                  INT          NULL,
    [StartTime]                     DATETIME2(7) NOT NULL,
    [EndTime]                       DATETIME2(7) NULL,
    [Notes]                         NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_SignalPortEquipmentHistory] PRIMARY KEY ([SignalPortEquipmentHistory_ID]),
    CONSTRAINT [FK_SignalPortEquipmentHistory_Port]
        FOREIGN KEY ([SignalPort_ID])
        REFERENCES [dbo].[SignalPort] ([SignalPort_ID]),
    CONSTRAINT [FK_SignalPortEquipmentHistory_Equipment]
        FOREIGN KEY ([Equipment_ID])
        REFERENCES [dbo].[Equipment] ([Equipment_ID])
);
GO

-- At most one active row (EndTime IS NULL) per SignalPort_ID.
CREATE UNIQUE INDEX [UQ_SignalPortEquipmentHistory_ActiveRow]
    ON [dbo].[SignalPortEquipmentHistory] ([SignalPort_ID])
    WHERE [EndTime] IS NULL;
GO

-- ============================================================
-- E7: Modify Channel — replace Equipment_ID with SignalPort_ID,
--     drop StatusChannel_ID
-- ============================================================

-- E7a: Drop UQ index on Channel
DROP INDEX IF EXISTS [UQ_Channel_SensorStream] ON [dbo].[Channel];
GO

-- E7b: Drop FKs on Equipment_ID and StatusChannel_ID (dynamic lookup)
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql = @sql + N'ALTER TABLE [dbo].[Channel] DROP CONSTRAINT ['
              + fk.[name] + N'];' + CHAR(10)
FROM   sys.foreign_keys        fk
JOIN   sys.foreign_key_columns fkc
    ON fk.[object_id] = fkc.[constraint_object_id]
WHERE  fk.[parent_object_id] = OBJECT_ID('dbo.Channel')
  AND  COL_NAME(fkc.[parent_object_id], fkc.[parent_column_id])
       IN (N'Equipment_ID', N'StatusChannel_ID');
IF LEN(@sql) > 0
    EXEC sp_executesql @sql;
GO

-- E7c: Drop the old columns
ALTER TABLE [dbo].[Channel] DROP COLUMN [Equipment_ID];
ALTER TABLE [dbo].[Channel] DROP COLUMN [StatusChannel_ID];
GO

-- E7d: Add SignalPort_ID NOT NULL.
-- Temp DEFAULT 0 satisfies the NOT NULL requirement; dropped immediately after.
-- Safe because no Channel rows exist in a fresh v1.0.0 test environment.
ALTER TABLE [dbo].[Channel]
    ADD [SignalPort_ID] INT NOT NULL
    CONSTRAINT [DF_Channel_SignalPort_Temp] DEFAULT 0;
GO

ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [DF_Channel_SignalPort_Temp];
GO

-- E7e: Add FK to SignalPort
ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [FK_Channel_SignalPort]
    FOREIGN KEY ([SignalPort_ID]) REFERENCES [dbo].[SignalPort] ([SignalPort_ID]);
GO

-- E7f: Recreate unique stream index (channel = unique signal stream per port)
CREATE UNIQUE INDEX [UQ_Channel_SignalStream]
    ON [dbo].[Channel] ([SignalPort_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID])
    WHERE [Parameter_ID] IS NOT NULL;
GO

-- ============================================================
-- E8: Create ControlLoop tables
-- ============================================================

CREATE TABLE [dbo].[ControlLoop] (
    [ControlLoop_ID]         INT IDENTITY(1,1) NOT NULL,
    [Name]                   NVARCHAR(200) NOT NULL,
    [ControllerType]         NVARCHAR(50)  NOT NULL,
    [FallbackControlLoop_ID] INT           NULL,
    [AlgorithmReference]     NVARCHAR(500) NULL,
    [Description]            NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_ControlLoop] PRIMARY KEY ([ControlLoop_ID]),
    CONSTRAINT [FK_ControlLoop_Fallback]
        FOREIGN KEY ([FallbackControlLoop_ID])
        REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID])
);
GO

CREATE TABLE [dbo].[ControlLoopPort] (
    [ControlLoopPort_ID]     INT IDENTITY(1,1) NOT NULL,
    [ControlLoop_ID]         INT NOT NULL,
    [SignalPort_ID]          INT NOT NULL,
    [ControlLoopPortRole_ID] INT NOT NULL,
    CONSTRAINT [PK_ControlLoopPort] PRIMARY KEY ([ControlLoopPort_ID]),
    CONSTRAINT [UQ_ControlLoopPort_LoopPort] UNIQUE ([ControlLoop_ID], [SignalPort_ID]),
    CONSTRAINT [FK_ControlLoopPort_Loop]
        FOREIGN KEY ([ControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]),
    CONSTRAINT [FK_ControlLoopPort_Port]
        FOREIGN KEY ([SignalPort_ID]) REFERENCES [dbo].[SignalPort] ([SignalPort_ID]),
    CONSTRAINT [FK_ControlLoopPort_Role]
        FOREIGN KEY ([ControlLoopPortRole_ID]) REFERENCES [dbo].[ControlLoopPortRole] ([ControlLoopPortRole_ID])
);
GO

CREATE TABLE [dbo].[ControlLoopApplication] (
    [ControlLoopApplication_ID] INT IDENTITY(1,1) NOT NULL,
    [ControlLoop_ID]            INT           NOT NULL,
    [StartTime]                 DATETIME2(7)  NOT NULL,
    [EndTime]                   DATETIME2(7)  NULL,
    [Parameters]                NVARCHAR(MAX) NULL,
    [AppliedByPerson_ID]        INT           NULL,
    [Notes]                     NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_ControlLoopApplication] PRIMARY KEY ([ControlLoopApplication_ID]),
    CONSTRAINT [FK_ControlLoopApplication_Loop]
        FOREIGN KEY ([ControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]),
    CONSTRAINT [FK_ControlLoopApplication_Person]
        FOREIGN KEY ([AppliedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID])
);
GO

-- At most one active application (EndTime IS NULL) per ControlLoop_ID.
CREATE UNIQUE INDEX [UQ_ControlLoopApplication_ActiveRow]
    ON [dbo].[ControlLoopApplication] ([ControlLoop_ID])
    WHERE [EndTime] IS NULL;
GO

-- ============================================================
-- E9: Add DataProvenance row 6 = Forecast
-- ============================================================

SET IDENTITY_INSERT [dbo].[DataProvenance] ON;
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name])
VALUES (6, N'Forecast');
SET IDENTITY_INSERT [dbo].[DataProvenance] OFF;
GO

-- ============================================================
-- E10: Recreate views with SignalPort-based navigation
-- ============================================================

-- vw_ChannelStatus: status channel ↔ parent measurement channel, current equipment.
-- A "status channel" is a Channel whose SignalPort has SignalPortType=Status
-- and a non-null ParentPort_ID pointing to the measured value port.
CREATE OR ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    valueC.[Channel_ID]         AS MeasurementChannelID,
    e.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    p.[Parameter]               AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]               o        ON o.[Observation_ID]      = v.[Observation_ID]
JOIN [dbo].[Channel]                   statusC  ON statusC.[Channel_ID]    = o.[Channel_ID]
JOIN [dbo].[SignalPort]                statusP  ON statusP.[SignalPort_ID] = statusC.[SignalPort_ID]
JOIN [dbo].[SignalPortType]            spt      ON spt.[SignalPortType_ID] = statusP.[SignalPortType_ID]
JOIN [dbo].[SignalPort]                valueP   ON valueP.[SignalPort_ID]  = statusP.[ParentPort_ID]
JOIN [dbo].[Channel]                   valueC   ON valueC.[SignalPort_ID]  = valueP.[SignalPort_ID]
JOIN [dbo].[Parameter]                 p        ON p.[Parameter_ID]        = valueC.[Parameter_ID]
LEFT JOIN [dbo].[SignalPortEquipmentHistory] peh  ON peh.[SignalPort_ID]     = valueP.[SignalPort_ID]
                                                  AND peh.[EndTime]          IS NULL
LEFT JOIN [dbo].[Equipment]            e        ON e.[Equipment_ID]        = peh.[Equipment_ID]
WHERE spt.[Name] = N'Status'
  AND statusP.[ParentPort_ID] IS NOT NULL;
GO

-- vw_DeviceStatus: status channels grouped by currently-linked equipment.
-- Replaces the EquipmentStatusChannel junction from v2.x.
CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    e.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]               o        ON o.[Observation_ID]      = v.[Observation_ID]
JOIN [dbo].[Channel]                   statusC  ON statusC.[Channel_ID]    = o.[Channel_ID]
JOIN [dbo].[SignalPort]                statusP  ON statusP.[SignalPort_ID] = statusC.[SignalPort_ID]
JOIN [dbo].[SignalPortType]            spt      ON spt.[SignalPortType_ID] = statusP.[SignalPortType_ID]
JOIN [dbo].[SignalPortEquipmentHistory]  peh      ON peh.[SignalPort_ID]     = statusP.[SignalPort_ID]
                                                 AND peh.[EndTime]          IS NULL
JOIN [dbo].[Equipment]                 e        ON e.[Equipment_ID]        = peh.[Equipment_ID]
WHERE spt.[Name] = N'Status';
GO

-- ============================================================
-- FINAL: Record schema version and commit
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedDateTime], [Description], [MigrationScript])
VALUES (
    '3.0.0',
    SYSUTCDATETIME(),
    'v3.0.0 — SignalPort abstraction: replaces Equipment_ID on Channel, adds DAS/SignalPort/ControlLoop tables, DataProvenance=Forecast',
    'v1.0.0_to_v3.0.0_mssql.sql'
);
GO

COMMIT TRANSACTION;
GO

PRINT 'Migration to v3.0.0 completed successfully.';
