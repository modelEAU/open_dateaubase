-- Migration: v1.0.0 -> v1.0.1
-- Platform: mssql
-- Generated: 2026-02-14 03:43:22 UTC
-- Rollback: v1.0.0_to_v1.0.1_mssql_rollback.sql


CREATE TABLE [dbo].[SchemaVersion] (
    [VersionID] INT IDENTITY(1,1) NOT NULL,
    [Version] NVARCHAR(20) NOT NULL,
    [AppliedAt] DATETIME2(7) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    [Description] NVARCHAR(500),
    [MigrationScript] NVARCHAR(200),
    CONSTRAINT [PK_SchemaVersion] PRIMARY KEY ([VersionID])
);
