-- ============================================================
-- Rollback: v2.1.0 --> v1.0.0
-- Platform:  mssql
-- Generated: 2026-02-24
--
-- Applies to: a database at schema v2.1.0.
-- Produces:   the v1.0.0 schema (see migrations/v1.0.0_create_mssql.sql).
-- Forward:    migrations/v1.0.0_to_v2.1.0_mssql.sql
--
-- WARNING — DATA LOSS
--   This rollback is DESTRUCTIVE. Any data that exists only in v2.1.0
--   tables (LabAnalysis, LabValue, Campaign, EquipmentEvent, etc.) will
--   be permanently lost.
--
--   The following structural reversals are lossless only IF the
--   corresponding data never existed:
--     • Value.Timestamp DATETIME2(7) → INT  (sub-second precision lost;
--       values before 1970-01-01 or after 2038-01-19 may overflow INT)
--     • Person columns dropped in v1.2.0 (Skype_name, Street_number, etc.)
--       are recreated as NULL — original values cannot be recovered.
--     • Channel.ProcessingDegree is dropped — original values lost.
--
--   Only run this rollback on a TEST database or when you have
--   verified that all v2.1.0-only tables are empty.
-- ============================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

-- Guard: ensure we are starting from v2.1.0.
IF OBJECT_ID('dbo.Channel') IS NULL
    RAISERROR('Channel table not found — this rollback expects a v2.1.0 schema.', 16, 1);
IF OBJECT_ID('dbo.MetaData') IS NOT NULL
    RAISERROR('MetaData table already exists — rollback may have already been applied.', 16, 1);
GO

BEGIN TRANSACTION;
GO

-- ============================================================
-- STEP 1: Drop views
-- ============================================================

DROP VIEW IF EXISTS [dbo].[vw_DeviceStatus];
DROP VIEW IF EXISTS [dbo].[vw_ChannelStatus];
GO

-- ============================================================
-- STEP 2: Drop all v2.1.0-only tables (leaves first)
-- ============================================================

-- Tables that reference Channel
DROP TABLE IF EXISTS [dbo].[EquipmentStatusChannel];
DROP TABLE IF EXISTS [dbo].[ValueVector];
DROP TABLE IF EXISTS [dbo].[ValueMatrix];
DROP TABLE IF EXISTS [dbo].[ValueImage];
DROP TABLE IF EXISTS [dbo].[DataLineage];
DROP TABLE IF EXISTS [dbo].[Annotation];
DROP TABLE IF EXISTS [dbo].[ChannelAxis];
DROP TABLE IF EXISTS [dbo].[EquipmentEventChannel];
GO

-- ValueBin / ValueBinningAxis
DROP TABLE IF EXISTS [dbo].[ValueBin];
DROP TABLE IF EXISTS [dbo].[ValueBinningAxis];
GO

-- Lab tables
DROP TABLE IF EXISTS [dbo].[LabValue];
DROP TABLE IF EXISTS [dbo].[LabAnalysis];
DROP TABLE IF EXISTS [dbo].[Sample];
DROP TABLE IF EXISTS [dbo].[Laboratory];
GO

-- Equipment lifecycle
DROP TABLE IF EXISTS [dbo].[EquipmentInstallation];
DROP TABLE IF EXISTS [dbo].[EquipmentEvent];
DROP TABLE IF EXISTS [dbo].[EquipmentEventType];
GO

-- Campaign tables
DROP TABLE IF EXISTS [dbo].[CampaignSamplingLocation];
DROP TABLE IF EXISTS [dbo].[CampaignParameter];
DROP TABLE IF EXISTS [dbo].[CampaignEquipment];
DROP TABLE IF EXISTS [dbo].[Campaign];
DROP TABLE IF EXISTS [dbo].[CampaignType];
GO

-- Processing lineage
DROP TABLE IF EXISTS [dbo].[ProcessingStep];
GO

-- Lookup tables
DROP TABLE IF EXISTS [dbo].[AnnotationType];
DROP TABLE IF EXISTS [dbo].[ValueType];
DROP TABLE IF EXISTS [dbo].[DataProvenance];
GO

-- Schema tracking
DROP TABLE IF EXISTS [dbo].[SchemaVersion];
GO

-- ============================================================
-- STEP 3: Drop new FKs and indexes added to pre-existing tables
-- ============================================================

-- Channel (formerly MetaData) — drop new FKs and new columns
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT IF EXISTS [FK_Channel_Channel];
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT IF EXISTS [FK_Channel_DataProvenance];
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT IF EXISTS [FK_Channel_ValueType];
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT IF EXISTS [FK_Channel_Equipment];
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT IF EXISTS [FK_Channel_Parameter];
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT IF EXISTS [FK_Channel_Unit];
GO

DROP INDEX IF EXISTS [UQ_Channel_SensorStream] ON [dbo].[Channel];
GO

ALTER TABLE [dbo].[Channel] DROP COLUMN [DataProvenance_ID];
ALTER TABLE [dbo].[Channel] DROP COLUMN [ProcessingDegree];
ALTER TABLE [dbo].[Channel] DROP COLUMN [ValueType_ID];
ALTER TABLE [dbo].[Channel] DROP COLUMN [StatusChannel_ID];
GO

-- SamplingPoints — drop new FK and columns
ALTER TABLE [dbo].[SamplingPoints] DROP CONSTRAINT IF EXISTS [FK_SamplingPoints_Campaign];
GO
ALTER TABLE [dbo].[SamplingPoints] DROP COLUMN [ValidFrom];
ALTER TABLE [dbo].[SamplingPoints] DROP COLUMN [ValidTo];
ALTER TABLE [dbo].[SamplingPoints] DROP COLUMN [CreatedByCampaign_ID];
GO

-- Value — drop Channel FK before renaming column
ALTER TABLE [dbo].[Value] DROP CONSTRAINT IF EXISTS [FK_Value_Channel];
ALTER TABLE [dbo].[Value] DROP CONSTRAINT IF EXISTS [FK_Value_Comments];
GO

-- ============================================================
-- STEP 4: Rename Channel → MetaData
-- ============================================================

ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [PK_Channel];
GO

EXEC sp_rename 'dbo.Channel', 'MetaData';
GO

EXEC sp_rename 'dbo.MetaData.Channel_ID', 'Metadata_ID', 'COLUMN';
GO

ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [PK_MetaData] PRIMARY KEY ([Metadata_ID]);
GO

-- ============================================================
-- STEP 5: Rename Value.Channel_ID → Metadata_ID
-- ============================================================

EXEC sp_rename 'dbo.Value.Channel_ID', 'Metadata_ID', 'COLUMN';
GO

-- ============================================================
-- STEP 6: Revert Value.Timestamp: DATETIME2(7) → INT
-- WARNING: sub-second precision is lost; pre-1970 values will
-- produce negative integers; post-2038 values overflow INT.
-- ============================================================

ALTER TABLE [dbo].[Value] ADD [Timestamp_old] INT NULL;
GO

UPDATE [dbo].[Value]
SET [Timestamp_old] = DATEDIFF(SECOND, CAST('1970-01-01T00:00:00' AS DATETIME2(7)), [Timestamp])
WHERE [Timestamp] IS NOT NULL;
GO

ALTER TABLE [dbo].[Value] DROP COLUMN [Timestamp];
GO

EXEC sp_rename 'dbo.Value.Timestamp_old', 'Timestamp', 'COLUMN';
GO

-- ============================================================
-- STEP 7: Rename Person → Contact; restore dropped columns
-- ============================================================

ALTER TABLE [dbo].[Person] DROP CONSTRAINT [PK_Person];
GO

EXEC sp_rename 'dbo.Person.Person_ID', 'Contact_ID', 'COLUMN';
GO
EXEC sp_rename 'dbo.Person.Role', 'Status', 'COLUMN';
GO

-- Restore columns that were dropped in the forward migration.
-- These columns are recreated as NULLable; original data is unrecoverable.
ALTER TABLE [dbo].[Person] ADD [Skype_name]    NVARCHAR(100) NULL;
ALTER TABLE [dbo].[Person] ADD [Street_number] NVARCHAR(100) NULL;
ALTER TABLE [dbo].[Person] ADD [Street_name]   NVARCHAR(100) NULL;
ALTER TABLE [dbo].[Person] ADD [City]          NVARCHAR(255) NULL;
ALTER TABLE [dbo].[Person] ADD [Zip_code]      NVARCHAR(45)  NULL;
ALTER TABLE [dbo].[Person] ADD [Country]       NVARCHAR(255) NULL;
ALTER TABLE [dbo].[Person] ADD [Office_number] NVARCHAR(100) NULL;
GO

EXEC sp_rename 'dbo.Person', 'Contact';
GO

ALTER TABLE [dbo].[Contact] ADD CONSTRAINT [PK_Contact] PRIMARY KEY ([Contact_ID]);
GO

-- ============================================================
-- STEP 7b: Rename columns back to snake_case (reverse of forward migration)
-- ============================================================

-- Site table
EXEC sp_rename 'dbo.Site.PostCode', 'Zip_code', 'COLUMN';
EXEC sp_rename 'dbo.Site.StreetNumber', 'Street_number', 'COLUMN';
EXEC sp_rename 'dbo.Site.StreetName', 'Street_name', 'COLUMN';
GO

-- Contact table (formerly Person)
EXEC sp_rename 'dbo.Contact.LastName', 'Last_name', 'COLUMN';
EXEC sp_rename 'dbo.Contact.FirstName', 'First_name', 'COLUMN';
GO

-- Equipment table
EXEC sp_rename 'dbo.Equipment.EquipmentModel_ID', 'model_ID', 'COLUMN';
EXEC sp_rename 'dbo.Equipment.Identifier', 'identifier', 'COLUMN';
EXEC sp_rename 'dbo.Equipment.SerialNumber', 'Serial_number', 'COLUMN';
EXEC sp_rename 'dbo.Equipment.StorageLocation', 'Storage_location', 'COLUMN';
EXEC sp_rename 'dbo.Equipment.PurchaseDate', 'Purchase_date', 'COLUMN';
GO

-- EquipmentModel table
EXEC sp_rename 'dbo.EquipmentModel.EquipmentModel_ID', 'Equipment_model_ID', 'COLUMN';
EXEC sp_rename 'dbo.EquipmentModel.EquipmentModel', 'Equipment_model', 'COLUMN';
EXEC sp_rename 'dbo.EquipmentModel.ManualLocation', 'Manual_location', 'COLUMN';
GO

-- Watershed table
EXEC sp_rename 'dbo.Watershed.Name', 'name', 'COLUMN';
EXEC sp_rename 'dbo.Watershed.SurfaceArea', 'Surface_area', 'COLUMN';
EXEC sp_rename 'dbo.Watershed.ConcentrationTime', 'Concentration_time', 'COLUMN';
EXEC sp_rename 'dbo.Watershed.ImperviousSurface', 'Impervious_surface', 'COLUMN';
GO

-- UrbanCharacteristics table
EXEC sp_rename 'dbo.UrbanCharacteristics.GreenSpaces', 'Green_spaces', 'COLUMN';
GO

-- HydrologicalCharacteristics table
EXEC sp_rename 'dbo.HydrologicalCharacteristics.UrbanArea', 'Urban_area', 'COLUMN';
GO

-- Procedures table
EXEC sp_rename 'dbo.Procedures.ProcedureName', 'Procedure_name', 'COLUMN';
EXEC sp_rename 'dbo.Procedures.ProcedureType', 'Procedure_type', 'COLUMN';

-- Junction tables (reverse EquipmentModel column rename)
EXEC sp_rename 'dbo.EquipmentModelHasParameter.EquipmentModel_ID', 'Equipment_model_ID', 'COLUMN';
EXEC sp_rename 'dbo.EquipmentModelHasProcedures.EquipmentModel_ID', 'Equipment_model_ID', 'COLUMN';
EXEC sp_rename 'dbo.Procedures.ProcedureLocation', 'Procedure_location', 'COLUMN';
GO

-- ============================================================
-- STEP 8: Recreate dropped tables (empty — data unrecoverable)
-- ============================================================

CREATE TABLE [dbo].[Purpose] (
    [Purpose_ID]  INT IDENTITY(1,1),
    [Purpose]     NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_Purpose] PRIMARY KEY ([Purpose_ID])
);
GO

CREATE TABLE [dbo].[Project] (
    [Project_ID]  INT IDENTITY(1,1),
    [name]        NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_Project] PRIMARY KEY ([Project_ID])
);
GO

CREATE TABLE [dbo].[ProjectHasContact] (
    [Contact_ID] INT,
    [Project_ID] INT,
    CONSTRAINT [PK_ProjectHasContact] PRIMARY KEY ([Contact_ID], [Project_ID])
);
GO

CREATE TABLE [dbo].[ProjectHasEquipment] (
    [Equipment_ID] INT,
    [Project_ID]   INT,
    CONSTRAINT [PK_ProjectHasEquipment] PRIMARY KEY ([Equipment_ID], [Project_ID])
);
GO

CREATE TABLE [dbo].[ProjectHasSamplingPoints] (
    [Project_ID]        INT,
    [Sampling_point_ID] INT,
    CONSTRAINT [PK_ProjectHasSamplingPoints] PRIMARY KEY ([Project_ID], [Sampling_point_ID])
);
GO

-- ============================================================
-- STEP 9: Restore v1.0.0 columns on MetaData
-- ============================================================

ALTER TABLE [dbo].[MetaData] ADD [Project_ID]        INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Contact_ID]        INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Purpose_ID]        INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Sampling_point_ID] INT NULL;
ALTER TABLE [dbo].[MetaData] ADD [Condition_ID]      INT NULL;
GO

-- ============================================================
-- STEP 10: Restore all v1.0.0 FK constraints
-- ============================================================

ALTER TABLE [dbo].[Equipment]              ADD CONSTRAINT [FK_Equipment_EquipmentModel]              FOREIGN KEY ([model_ID])          REFERENCES [dbo].[EquipmentModel]   ([Equipment_model_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter]  ADD CONSTRAINT [FK_EquipmentModelHasParameter_EquipmentModel]  FOREIGN KEY ([Equipment_model_ID]) REFERENCES [dbo].[EquipmentModel] ([Equipment_model_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter]  ADD CONSTRAINT [FK_EquipmentModelHasParameter_Parameter]       FOREIGN KEY ([Parameter_ID])      REFERENCES [dbo].[Parameter]      ([Parameter_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_EquipmentModel] FOREIGN KEY ([Equipment_model_ID]) REFERENCES [dbo].[EquipmentModel] ([Equipment_model_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_Procedures]     FOREIGN KEY ([Procedure_ID])      REFERENCES [dbo].[Procedures]     ([Procedure_ID]);
ALTER TABLE [dbo].[MetaData]          ADD CONSTRAINT [FK_MetaData_Project]        FOREIGN KEY ([Project_ID])        REFERENCES [dbo].[Project]        ([Project_ID]);
ALTER TABLE [dbo].[MetaData]          ADD CONSTRAINT [FK_MetaData_Contact]        FOREIGN KEY ([Contact_ID])        REFERENCES [dbo].[Contact]        ([Contact_ID]);
ALTER TABLE [dbo].[MetaData]          ADD CONSTRAINT [FK_MetaData_Equipment]      FOREIGN KEY ([Equipment_ID])      REFERENCES [dbo].[Equipment]      ([Equipment_ID]);
ALTER TABLE [dbo].[MetaData]          ADD CONSTRAINT [FK_MetaData_Parameter]      FOREIGN KEY ([Parameter_ID])      REFERENCES [dbo].[Parameter]      ([Parameter_ID]);
ALTER TABLE [dbo].[MetaData]          ADD CONSTRAINT [FK_MetaData_Procedures]     FOREIGN KEY ([Procedure_ID])      REFERENCES [dbo].[Procedures]     ([Procedure_ID]);
ALTER TABLE [dbo].[MetaData]          ADD CONSTRAINT [FK_MetaData_Unit]           FOREIGN KEY ([Unit_ID])           REFERENCES [dbo].[Unit]           ([Unit_ID]);
ALTER TABLE [dbo].[MetaData]          ADD CONSTRAINT [FK_MetaData_Purpose]        FOREIGN KEY ([Purpose_ID])        REFERENCES [dbo].[Purpose]        ([Purpose_ID]);
ALTER TABLE [dbo].[MetaData]          ADD CONSTRAINT [FK_MetaData_SamplingPoints] FOREIGN KEY ([Sampling_point_ID]) REFERENCES [dbo].[SamplingPoints] ([Sampling_point_ID]);
ALTER TABLE [dbo].[MetaData]          ADD CONSTRAINT [FK_MetaData_WeatherCondition] FOREIGN KEY ([Condition_ID])    REFERENCES [dbo].[WeatherCondition] ([Condition_ID]);
ALTER TABLE [dbo].[Parameter]         ADD CONSTRAINT [FK_Parameter_Unit]          FOREIGN KEY ([Unit_ID])           REFERENCES [dbo].[Unit]           ([Unit_ID]);
ALTER TABLE [dbo].[ParameterHasProcedures] ADD CONSTRAINT [FK_ParameterHasProcedures_Procedures] FOREIGN KEY ([Procedure_ID])  REFERENCES [dbo].[Procedures] ([Procedure_ID]);
ALTER TABLE [dbo].[ParameterHasProcedures] ADD CONSTRAINT [FK_ParameterHasProcedures_Parameter]  FOREIGN KEY ([Parameter_ID])  REFERENCES [dbo].[Parameter]  ([Parameter_ID]);
ALTER TABLE [dbo].[ProjectHasContact]      ADD CONSTRAINT [FK_ProjectHasContact_Contact]   FOREIGN KEY ([Contact_ID])   REFERENCES [dbo].[Contact]  ([Contact_ID]);
ALTER TABLE [dbo].[ProjectHasContact]      ADD CONSTRAINT [FK_ProjectHasContact_Project]   FOREIGN KEY ([Project_ID])   REFERENCES [dbo].[Project]  ([Project_ID]);
ALTER TABLE [dbo].[ProjectHasEquipment]    ADD CONSTRAINT [FK_ProjectHasEquipment_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[ProjectHasEquipment]    ADD CONSTRAINT [FK_ProjectHasEquipment_Project]   FOREIGN KEY ([Project_ID])   REFERENCES [dbo].[Project]   ([Project_ID]);
ALTER TABLE [dbo].[ProjectHasSamplingPoints] ADD CONSTRAINT [FK_ProjectHasSamplingPoints_Project]        FOREIGN KEY ([Project_ID])        REFERENCES [dbo].[Project]        ([Project_ID]);
ALTER TABLE [dbo].[ProjectHasSamplingPoints] ADD CONSTRAINT [FK_ProjectHasSamplingPoints_SamplingPoints] FOREIGN KEY ([Sampling_point_ID]) REFERENCES [dbo].[SamplingPoints] ([Sampling_point_ID]);
ALTER TABLE [dbo].[SamplingPoints]    ADD CONSTRAINT [FK_SamplingPoints_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);
ALTER TABLE [dbo].[Site]              ADD CONSTRAINT [FK_Site_Watershed]      FOREIGN KEY ([Watershed_ID]) REFERENCES [dbo].[Watershed] ([Watershed_ID]);
ALTER TABLE [dbo].[Value]             ADD CONSTRAINT [FK_Value_Comments]      FOREIGN KEY ([Comment_ID])   REFERENCES [dbo].[Comments]  ([Comment_ID]);
ALTER TABLE [dbo].[Value]             ADD CONSTRAINT [FK_Value_MetaData]      FOREIGN KEY ([Metadata_ID])  REFERENCES [dbo].[MetaData]  ([Metadata_ID]);
GO

COMMIT TRANSACTION;
GO

PRINT 'Rollback to v1.0.0 completed. All v2.1.0-only data has been dropped.';
PRINT 'NOTE: Recreated tables (Purpose, Project, ProjectHas*) are empty.';
PRINT 'NOTE: Restored Contact columns (Skype_name etc.) contain NULL values.';
