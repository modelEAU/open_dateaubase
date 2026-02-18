-- Migration: v1.5.0 -> v1.6.0
-- Platform: mssql
-- Generated: 2026-02-18
-- Rollback: v1.5.0_to_v1.6.0_mssql_rollback.sql
-- Breaking changes: NONE
--
-- Phase 3: Processing Lineage
--   Task 3.1 — Create ProcessingStep table
--   Task 3.2 — Create DataLineage table
--   Task 3.3 — Add ProcessingDegree column to MetaData

-- ============================================================
-- Task 3.1: ProcessingStep table
-- ============================================================

CREATE TABLE [dbo].[ProcessingStep] (
    [ProcessingStep_ID]     INT            IDENTITY(1,1) NOT NULL,
    [Name]                  NVARCHAR(200)  NOT NULL,
    [Description]           NVARCHAR(2000) NULL,
    [MethodName]            NVARCHAR(200)  NULL,
    [MethodVersion]         NVARCHAR(100)  NULL,
    [ProcessingType]        NVARCHAR(100)  NULL,
    [Parameters]            NVARCHAR(MAX)  NULL,
    [ExecutedAt]            DATETIME2(7)   NULL,
    [ExecutedByPerson_ID]   INT            NULL,

    CONSTRAINT [PK_ProcessingStep] PRIMARY KEY ([ProcessingStep_ID]),
    CONSTRAINT [FK_ProcessingStep_Person]
        FOREIGN KEY ([ExecutedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID])
);
GO

-- ============================================================
-- Task 3.2: DataLineage table
-- ============================================================

CREATE TABLE [dbo].[DataLineage] (
    [DataLineage_ID]        INT            IDENTITY(1,1) NOT NULL,
    [ProcessingStep_ID]     INT            NOT NULL,
    [Metadata_ID]           INT            NOT NULL,
    [Role]                  NVARCHAR(10)   NOT NULL,

    CONSTRAINT [PK_DataLineage] PRIMARY KEY ([DataLineage_ID]),
    CONSTRAINT [FK_DataLineage_ProcessingStep]
        FOREIGN KEY ([ProcessingStep_ID]) REFERENCES [dbo].[ProcessingStep] ([ProcessingStep_ID]),
    CONSTRAINT [FK_DataLineage_MetaData]
        FOREIGN KEY ([Metadata_ID]) REFERENCES [dbo].[MetaData] ([Metadata_ID]),
    CONSTRAINT [CK_DataLineage_Role]
        CHECK ([Role] IN ('Input', 'Output'))
);
GO

CREATE INDEX [IX_DataLineage_Metadata]
    ON [dbo].[DataLineage] ([Metadata_ID]);
GO

CREATE INDEX [IX_DataLineage_Step_Role]
    ON [dbo].[DataLineage] ([ProcessingStep_ID], [Role]);
GO

-- ============================================================
-- Task 3.3: Add ProcessingDegree to MetaData
-- ============================================================

ALTER TABLE [dbo].[MetaData]
    ADD [ProcessingDegree] NVARCHAR(50) NULL
        CONSTRAINT [DF_MetaData_ProcessingDegree] DEFAULT ('Raw');
GO

-- Backfill existing rows
UPDATE [dbo].[MetaData]
SET [ProcessingDegree] = 'Raw'
WHERE [ProcessingDegree] IS NULL;
GO

-- ============================================================
-- Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.6.0',
    GETUTCDATE(),
    'Phase 3: Processing Lineage — ProcessingStep + DataLineage tables record data transformation history',
    'v1.5.0_to_v1.6.0_mssql.sql'
);
GO
