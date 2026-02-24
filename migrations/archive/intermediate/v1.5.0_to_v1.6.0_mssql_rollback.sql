-- Rollback: v1.6.0 -> v1.5.0
-- Platform: mssql
-- Generated: 2026-02-18
-- Rolls back: v1.5.0_to_v1.6.0_mssql.sql
-- Breaking changes: NONE
--
-- Phase 3 rollback: removes ProcessingStep, DataLineage tables
-- and the ProcessingDegree column from MetaData.

-- ============================================================
-- Drop DataLineage table (FKs dropped automatically with table)
-- ============================================================

IF OBJECT_ID('[dbo].[DataLineage]', 'U') IS NOT NULL
    DROP TABLE [dbo].[DataLineage];
GO

-- ============================================================
-- Drop ProcessingStep table
-- ============================================================

IF OBJECT_ID('[dbo].[ProcessingStep]', 'U') IS NOT NULL
    DROP TABLE [dbo].[ProcessingStep];
GO

-- ============================================================
-- Remove ProcessingDegree column from MetaData
-- ============================================================

IF EXISTS (
    SELECT 1 FROM sys.default_constraints
    WHERE name = 'DF_MetaData_ProcessingDegree'
)
BEGIN
    ALTER TABLE [dbo].[MetaData]
        DROP CONSTRAINT [DF_MetaData_ProcessingDegree];
END
GO

IF EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo'
      AND TABLE_NAME   = 'MetaData'
      AND COLUMN_NAME  = 'ProcessingDegree'
)
BEGIN
    ALTER TABLE [dbo].[MetaData] DROP COLUMN [ProcessingDegree];
END
GO

-- ============================================================
-- Remove SchemaVersion entry
-- ============================================================

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.6.0';
GO
