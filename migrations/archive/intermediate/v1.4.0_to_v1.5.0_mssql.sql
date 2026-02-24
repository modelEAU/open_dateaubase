-- Migration: v1.4.0 -> v1.5.0
-- Platform: mssql
-- Generated: 2026-02-18
-- Rollback: v1.4.0_to_v1.5.0_mssql_rollback.sql
-- Breaking changes: NONE
--
-- Phase 2d: Ingestion Routing
--   Task 2d.1 — Create IngestionRoute table

-- ============================================================
-- Task 2d.1: IngestionRoute table
-- ============================================================

CREATE TABLE [dbo].[IngestionRoute] (
    [IngestionRoute_ID]   INT          IDENTITY(1,1) NOT NULL,
    [Equipment_ID]        INT          NULL,
    [Parameter_ID]        INT          NOT NULL,
    [DataProvenance_ID]   INT          NOT NULL,
    [ProcessingDegree]    NVARCHAR(50) NOT NULL CONSTRAINT [DF_IngestionRoute_ProcessingDegree] DEFAULT ('Raw'),
    [ValidFrom]           DATETIME2(7) NOT NULL,
    [ValidTo]             DATETIME2(7) NULL,
    [CreatedAt]           DATETIME2(7) NOT NULL CONSTRAINT [DF_IngestionRoute_CreatedAt] DEFAULT (GETUTCDATE()),
    [Metadata_ID]         INT          NOT NULL,
    [Notes]               NVARCHAR(500) NULL,

    CONSTRAINT [PK_IngestionRoute] PRIMARY KEY ([IngestionRoute_ID]),
    CONSTRAINT [FK_IngestionRoute_Equipment]     FOREIGN KEY ([Equipment_ID])      REFERENCES [dbo].[Equipment]      ([Equipment_ID]),
    CONSTRAINT [FK_IngestionRoute_Parameter]     FOREIGN KEY ([Parameter_ID])      REFERENCES [dbo].[Parameter]      ([Parameter_ID]),
    CONSTRAINT [FK_IngestionRoute_DataProvenance] FOREIGN KEY ([DataProvenance_ID]) REFERENCES [dbo].[DataProvenance] ([DataProvenance_ID]),
    CONSTRAINT [FK_IngestionRoute_MetaData]      FOREIGN KEY ([Metadata_ID])       REFERENCES [dbo].[MetaData]       ([Metadata_ID])
);
GO

CREATE INDEX [IX_IngestionRoute_Lookup]
    ON [dbo].[IngestionRoute]
    ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree], [ValidFrom]);
GO

-- ============================================================
-- Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.5.0',
    GETUTCDATE(),
    'Phase 2d: Ingestion Routing — IngestionRoute table decouples ingestion scripts from hardcoded MetaDataIDs',
    'v1.4.0_to_v1.5.0_mssql.sql'
);
GO
