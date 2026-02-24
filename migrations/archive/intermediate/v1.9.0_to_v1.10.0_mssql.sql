-- Migration: v1.9.0 -> v1.10.0
-- Platform: mssql
-- Generated: 2026-02-23
--
-- Phase 7: Drop Project tables
--   7.1  Backup Campaign.Project_ID values (for rollback)
--   7.2  Drop FK constraint FK_Campaign_Project
--   7.3  Drop Campaign.Project_ID column
--   7.4  Drop junction tables (ProjectHasSamplingPoints, ProjectHasEquipment, ProjectHasContact)
--   7.5  Drop Project table
--   7.6  Update SchemaVersion
--
-- Rationale: Project is fully superseded by Campaign, which provides the same
--   organisational grouping with richer context (site, type, dates, equipment).
--   Campaign.Project_ID was already marked as a "backward-compatibility link".
--   MetaData.Project_ID was dropped in v1.9.0 — Project is now an orphan.
--
-- BREAKING CHANGES:
--   - Project table dropped
--   - ProjectHasContact, ProjectHasEquipment, ProjectHasSamplingPoints dropped
--   - Campaign.Project_ID column dropped

SET NOCOUNT ON;
GO

-- ============================================================
-- 7.1  Backup Campaign.Project_ID values
--       (needed by rollback to restore the column data)
-- ============================================================

SELECT [Campaign_ID], [Project_ID]
INTO [dbo].[Campaign_v1_9_project_backup]
FROM [dbo].[Campaign]
WHERE [Project_ID] IS NOT NULL;
GO

-- ============================================================
-- 7.2  Drop FK constraint on Campaign.Project_ID
-- ============================================================

ALTER TABLE [dbo].[Campaign]
    DROP CONSTRAINT [FK_Campaign_Project];
GO

-- ============================================================
-- 7.3  Drop Campaign.Project_ID column
-- ============================================================

ALTER TABLE [dbo].[Campaign]
    DROP COLUMN [Project_ID];
GO

-- ============================================================
-- 7.4  Drop junction tables
--       (no FK constraints referencing Project to drop first on these —
--        the inbound FK on Project itself is handled by step 7.5)
-- ============================================================

DROP TABLE [dbo].[ProjectHasSamplingPoints];
DROP TABLE [dbo].[ProjectHasEquipment];
DROP TABLE [dbo].[ProjectHasContact];
GO

-- ============================================================
-- 7.5  Drop Project table
-- ============================================================

DROP TABLE [dbo].[Project];
GO

-- ============================================================
-- 7.6  Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.10.0',
    SYSUTCDATETIME(),
    'Phase 7: Drop Project tables (Project, ProjectHasContact, ProjectHasEquipment, ProjectHasSamplingPoints) and Campaign.Project_ID column',
    'v1.9.0_to_v1.10.0_mssql.sql'
);
GO
