-- Rollback: v1.10.0 -> v1.9.0
-- Platform: mssql
-- Generated: 2026-02-23
-- Forward migration: v1.9.0_to_v1.10.0_mssql.sql
--
-- Restores Project table, junction tables, and Campaign.Project_ID from the
-- backup table created during the forward migration.
--
-- PREREQUISITE: Forward migration must have been run (backup table must exist).

SET NOCOUNT ON;
GO

-- ============================================================
-- 1.  Verify backup table exists before proceeding
-- ============================================================

IF NOT EXISTS (
    SELECT 1 FROM sys.tables
    WHERE name = 'Campaign_v1_9_project_backup'
      AND schema_id = SCHEMA_ID('dbo')
)
BEGIN
    RAISERROR('Campaign_v1_9_project_backup does not exist. Cannot roll back.', 16, 1);
    RETURN;
END
GO

-- ============================================================
-- 2.  Recreate Project table
-- ============================================================

CREATE TABLE [dbo].[Project] (
    [Project_ID]  INT IDENTITY(1,1) NOT NULL,
    [name]        NVARCHAR(100)     NULL,
    [Description] NVARCHAR(MAX)     NULL,
    CONSTRAINT [PK_Project] PRIMARY KEY ([Project_ID])
);
GO

-- ============================================================
-- 3.  Recreate junction tables
-- ============================================================

CREATE TABLE [dbo].[ProjectHasContact] (
    [Contact_ID] INT NOT NULL,
    [Project_ID] INT NOT NULL,
    CONSTRAINT [PK_ProjectHasContact] PRIMARY KEY ([Contact_ID], [Project_ID])
);

CREATE TABLE [dbo].[ProjectHasEquipment] (
    [Equipment_ID] INT NOT NULL,
    [Project_ID]   INT NOT NULL,
    CONSTRAINT [PK_ProjectHasEquipment] PRIMARY KEY ([Equipment_ID], [Project_ID])
);

CREATE TABLE [dbo].[ProjectHasSamplingPoints] (
    [Project_ID]       INT NOT NULL,
    [Sampling_point_ID] INT NOT NULL,
    CONSTRAINT [PK_ProjectHasSamplingPoints] PRIMARY KEY ([Project_ID], [Sampling_point_ID])
);
GO

-- ============================================================
-- 4.  Restore Campaign.Project_ID column
-- ============================================================

ALTER TABLE [dbo].[Campaign]
    ADD [Project_ID] INT NULL;
GO

UPDATE c
SET c.[Project_ID] = b.[Project_ID]
FROM [dbo].[Campaign] c
JOIN [dbo].[Campaign_v1_9_project_backup] b ON b.[Campaign_ID] = c.[Campaign_ID];
GO

-- ============================================================
-- 5.  Restore FK constraint
-- ============================================================

ALTER TABLE [dbo].[Campaign]
    ADD CONSTRAINT [FK_Campaign_Project]
    FOREIGN KEY ([Project_ID]) REFERENCES [dbo].[Project] ([Project_ID]);
GO

-- ============================================================
-- 6.  Drop backup table
-- ============================================================

DROP TABLE [dbo].[Campaign_v1_9_project_backup];
GO

-- ============================================================
-- 7.  Update SchemaVersion
-- ============================================================

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.10.0';

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.9.0',
    SYSUTCDATETIME(),
    'ROLLBACK from 1.10.0: restored Project table, ProjectHas* junction tables, Campaign.Project_ID column',
    'v1.9.0_to_v1.10.0_mssql_rollback.sql'
);
GO
