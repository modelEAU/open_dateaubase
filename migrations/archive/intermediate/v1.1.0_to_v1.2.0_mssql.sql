-- Migration: v1.1.0 -> v1.2.0
-- Platform: mssql
-- Generated: 2026-02-17
-- Rollback: v1.2.0_to_v1.1.0_mssql_rollback.sql
-- Breaking changes: NONE
--
-- Phase 2a: Core Context — Campaign and Provenance
--   Task 2a.1 — Rename Contact → Person, drop obsolete fields, rename Status → Role
--   Task 2a.2 — Create CampaignType and Campaign tables
--   Task 2a.3 — Create DataProvenance lookup; add DataProvenance_ID and Campaign_ID to MetaData

-- ============================================================
-- Task 2a.1: Rename Contact → Person
-- ============================================================

-- 1a. Drop FK constraints that reference Contact.Contact_ID
ALTER TABLE [dbo].[MetaData]
    DROP CONSTRAINT [FK_MetaData_Contact];
GO

ALTER TABLE [dbo].[ProjectHasContact]
    DROP CONSTRAINT [FK_ProjectHasContact_Contact];
GO

-- 1b. Drop the existing PK on Contact so we can rename the column
ALTER TABLE [dbo].[Contact]
    DROP CONSTRAINT [PK_Contact];
GO

-- 1c. Rename the PK column: Contact_ID → Person_ID
EXEC sp_rename 'dbo.Contact.Contact_ID', 'Person_ID', 'COLUMN';
GO

-- 1d. Rename the Status column → Role
EXEC sp_rename 'dbo.Contact.Status', 'Role', 'COLUMN';
GO

-- 1e. Drop obsolete contact columns
ALTER TABLE [dbo].[Contact] DROP COLUMN [Skype_name];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Street_number];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Street_name];
ALTER TABLE [dbo].[Contact] DROP COLUMN [City];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Zip_code];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Country];
ALTER TABLE [dbo].[Contact] DROP COLUMN [Office_number];
GO

-- 1f. Rename the table itself
EXEC sp_rename 'dbo.Contact', 'Person';
GO

-- 1g. Re-add PK with new name
ALTER TABLE [dbo].[Person]
    ADD CONSTRAINT [PK_Person] PRIMARY KEY ([Person_ID]);
GO

-- 1h. Re-add FK constraints pointing to Person.Person_ID
--     Note: MetaData.Contact_ID column name is preserved (per plan)
ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Person]
    FOREIGN KEY ([Contact_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
GO

ALTER TABLE [dbo].[ProjectHasContact]
    ADD CONSTRAINT [FK_ProjectHasContact_Person]
    FOREIGN KEY ([Contact_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
GO

-- ============================================================
-- Task 2a.2: CampaignType and Campaign tables
-- ============================================================

CREATE TABLE [dbo].[CampaignType] (
    [CampaignType_ID] INT IDENTITY(1,1) NOT NULL,
    [CampaignType_Name] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_CampaignType] PRIMARY KEY ([CampaignType_ID])
);
GO

-- Seed CampaignType lookup data
SET IDENTITY_INSERT [dbo].[CampaignType] ON;
INSERT INTO [dbo].[CampaignType] ([CampaignType_ID], [CampaignType_Name]) VALUES (1, 'Experiment');
INSERT INTO [dbo].[CampaignType] ([CampaignType_ID], [CampaignType_Name]) VALUES (2, 'Operations');
INSERT INTO [dbo].[CampaignType] ([CampaignType_ID], [CampaignType_Name]) VALUES (3, 'Commissioning');
SET IDENTITY_INSERT [dbo].[CampaignType] OFF;
GO

CREATE TABLE [dbo].[Campaign] (
    [Campaign_ID] INT IDENTITY(1,1) NOT NULL,
    [CampaignType_ID] INT NOT NULL,
    [Site_ID] INT NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Description] NVARCHAR(2000) NULL,
    [StartDate] DATETIME2(7) NULL,
    [EndDate] DATETIME2(7) NULL,
    [Project_ID] INT NULL,
    CONSTRAINT [PK_Campaign] PRIMARY KEY ([Campaign_ID]),
    CONSTRAINT [FK_Campaign_CampaignType] FOREIGN KEY ([CampaignType_ID]) REFERENCES [dbo].[CampaignType] ([CampaignType_ID]),
    CONSTRAINT [FK_Campaign_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]),
    CONSTRAINT [FK_Campaign_Project] FOREIGN KEY ([Project_ID]) REFERENCES [dbo].[Project] ([Project_ID])
);
GO

-- ============================================================
-- Task 2a.3: DataProvenance lookup + new MetaData columns
-- ============================================================

CREATE TABLE [dbo].[DataProvenance] (
    [DataProvenance_ID] INT IDENTITY(1,1) NOT NULL,
    [DataProvenance_Name] NVARCHAR(50) NOT NULL,
    CONSTRAINT [PK_DataProvenance] PRIMARY KEY ([DataProvenance_ID])
);
GO

-- Seed DataProvenance lookup data
SET IDENTITY_INSERT [dbo].[DataProvenance] ON;
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (1, 'Sensor');
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (2, 'Laboratory');
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (3, 'Manual Entry');
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (4, 'Model Output');
INSERT INTO [dbo].[DataProvenance] ([DataProvenance_ID], [DataProvenance_Name]) VALUES (5, 'External Source');
SET IDENTITY_INSERT [dbo].[DataProvenance] OFF;
GO

-- Add nullable DataProvenance_ID to MetaData (no default — backfilled separately)
ALTER TABLE [dbo].[MetaData]
    ADD [DataProvenance_ID] INT NULL;
GO

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_DataProvenance]
    FOREIGN KEY ([DataProvenance_ID]) REFERENCES [dbo].[DataProvenance] ([DataProvenance_ID]);
GO

-- Add nullable Campaign_ID to MetaData
ALTER TABLE [dbo].[MetaData]
    ADD [Campaign_ID] INT NULL;
GO

ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Campaign]
    FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
GO

-- ============================================================
-- Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.2.0',
    GETUTCDATE(),
    'Phase 2a: Rename Contact→Person; add CampaignType, Campaign, DataProvenance; add DataProvenance_ID and Campaign_ID to MetaData',
    'v1.1.0_to_v1.2.0_mssql.sql'
);
GO
