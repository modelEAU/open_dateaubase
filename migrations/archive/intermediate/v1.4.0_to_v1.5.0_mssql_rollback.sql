-- Rollback: v1.5.0 -> v1.4.0
-- Platform: mssql
-- Generated: 2026-02-18
-- Rolls back: v1.4.0_to_v1.5.0_mssql.sql
-- Breaking changes: NONE
--
-- Phase 2d rollback: removes IngestionRoute table

-- ============================================================
-- Drop IngestionRoute table (cascades FKs automatically via DROP TABLE)
-- ============================================================

IF OBJECT_ID('[dbo].[IngestionRoute]', 'U') IS NOT NULL
    DROP TABLE [dbo].[IngestionRoute];
GO

-- ============================================================
-- Remove SchemaVersion entry
-- ============================================================

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.5.0';
GO
