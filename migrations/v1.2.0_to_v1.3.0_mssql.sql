-- Migration: v1.2.0 -> v1.3.0
-- Platform: mssql
-- Generated: 2026-02-17
-- Rollback: v1.2.0_to_v1.3.0_mssql_rollback.sql
-- Breaking changes: NONE
--
-- Phase 2b: Lab Data Support
--   Task 2b.1 — Create Laboratory and Sample tables
--   Task 2b.2 — Add Sample_ID, Laboratory_ID, AnalystPerson_ID to MetaData
--   Task 2b.3 — Create CampaignSamplingLocation, CampaignEquipment, CampaignParameter junction tables

-- ============================================================
-- Task 2b.1: Laboratory table
-- ============================================================

CREATE TABLE [dbo].[Laboratory] (
    [Laboratory_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Site_ID] INT NULL,
    [Description] NVARCHAR(500) NULL,
    CONSTRAINT [PK_Laboratory] PRIMARY KEY ([Laboratory_ID]),
    CONSTRAINT [FK_Laboratory_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID])
);
GO

-- ============================================================
-- Task 2b.1: Sample table
-- ============================================================

CREATE TABLE [dbo].[Sample] (
    [Sample_ID] INT IDENTITY(1,1) NOT NULL,
    [ParentSample_ID] INT NULL,                -- self-FK added after table creation (see below)
    [SampleCategory] NVARCHAR(50) NULL,        -- Field | Synthetic | Master Standard | Derived Standard | Blank
    [Sampling_point_ID] INT NOT NULL,
    [SampledByPerson_ID] INT NULL,
    [Campaign_ID] INT NULL,
    [SampleDateTimeStart] DATETIME2(7) NOT NULL,
    [SampleDateTimeEnd] DATETIME2(7) NULL,
    [SampleType] NVARCHAR(50) NULL,
    [SampleEquipment_ID] INT NULL,
    [Description] NVARCHAR(500) NULL,
    CONSTRAINT [PK_Sample] PRIMARY KEY ([Sample_ID]),
    CONSTRAINT [FK_Sample_SamplingPoints] FOREIGN KEY ([Sampling_point_ID]) REFERENCES [dbo].[SamplingPoints] ([Sampling_point_ID]),
    CONSTRAINT [FK_Sample_Person] FOREIGN KEY ([SampledByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]),
    CONSTRAINT [FK_Sample_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]),
    CONSTRAINT [FK_Sample_Equipment] FOREIGN KEY ([SampleEquipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID])
);
GO

-- Self-referential FK must be added after table creation
ALTER TABLE [dbo].[Sample]
    ADD CONSTRAINT [FK_Sample_ParentSample]
    FOREIGN KEY ([ParentSample_ID]) REFERENCES [dbo].[Sample] ([Sample_ID]);
GO

-- ============================================================
-- Task 2b.2: Lab context columns on MetaData
-- ============================================================

ALTER TABLE [dbo].[MetaData]
    ADD [Sample_ID] INT NULL;
GO
ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Sample]
    FOREIGN KEY ([Sample_ID]) REFERENCES [dbo].[Sample] ([Sample_ID]);
GO

ALTER TABLE [dbo].[MetaData]
    ADD [Laboratory_ID] INT NULL;
GO
ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Laboratory]
    FOREIGN KEY ([Laboratory_ID]) REFERENCES [dbo].[Laboratory] ([Laboratory_ID]);
GO

ALTER TABLE [dbo].[MetaData]
    ADD [AnalystPerson_ID] INT NULL;
GO
ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_AnalystPerson]
    FOREIGN KEY ([AnalystPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
GO

-- ============================================================
-- Task 2b.3: Campaign junction tables
-- ============================================================

CREATE TABLE [dbo].[CampaignSamplingLocation] (
    [Campaign_ID] INT NOT NULL,
    [Sampling_point_ID] INT NOT NULL,
    [Role] NVARCHAR(100) NULL,
    CONSTRAINT [PK_CampaignSamplingLocation] PRIMARY KEY ([Campaign_ID], [Sampling_point_ID]),
    CONSTRAINT [FK_CampaignSamplingLocation_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]),
    CONSTRAINT [FK_CampaignSamplingLocation_SamplingPoints] FOREIGN KEY ([Sampling_point_ID]) REFERENCES [dbo].[SamplingPoints] ([Sampling_point_ID])
);
GO

CREATE TABLE [dbo].[CampaignEquipment] (
    [Campaign_ID] INT NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [Role] NVARCHAR(100) NULL,
    CONSTRAINT [PK_CampaignEquipment] PRIMARY KEY ([Campaign_ID], [Equipment_ID]),
    CONSTRAINT [FK_CampaignEquipment_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]),
    CONSTRAINT [FK_CampaignEquipment_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID])
);
GO

CREATE TABLE [dbo].[CampaignParameter] (
    [Campaign_ID] INT NOT NULL,
    [Parameter_ID] INT NOT NULL,
    CONSTRAINT [PK_CampaignParameter] PRIMARY KEY ([Campaign_ID], [Parameter_ID]),
    CONSTRAINT [FK_CampaignParameter_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]),
    CONSTRAINT [FK_CampaignParameter_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID])
);
GO

-- ============================================================
-- Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.3.0',
    GETUTCDATE(),
    'Phase 2b: Lab Data Support — Laboratory, Sample tables; lab context on MetaData; Campaign junction tables',
    'v1.2.0_to_v1.3.0_mssql.sql'
);
GO
