-- Migration: v1.0.1 -> v1.0.2
-- Platform: mssql
-- Description: Migrate datetime storage to UTC timestamps (stored by convention)
-- Rollback: v1.0.1_to_v1.0.2_mssql_rollback.sql

-- Step 1: Value.Timestamp — convert INT (Unix epoch) to DATETIME2(7), UTC by convention
ALTER TABLE [dbo].[Value] ADD [Timestamp_new] DATETIME2(7) NULL;
GO

UPDATE [dbo].[Value]
SET [Timestamp_new] = CASE
    WHEN [Timestamp] IS NOT NULL
    THEN DATEADD(SECOND, [Timestamp], CAST('1970-01-01T00:00:00' AS DATETIME2))
    ELSE NULL
END;
GO

ALTER TABLE [dbo].[Value] DROP COLUMN [Timestamp];
GO

EXEC sp_rename 'dbo.Value.Timestamp_new', 'Timestamp', 'COLUMN';
GO

-- Step 2: SchemaVersion.AppliedAt — update default to SYSUTCDATETIME() (UTC by convention)
-- The column type stays DATETIME2(7); only the default constraint is replaced.
DECLARE @DF_Name NVARCHAR(200);
SELECT @DF_Name = d.name
FROM sys.default_constraints d
JOIN sys.columns c ON d.parent_column_id = c.column_id AND d.parent_object_id = c.object_id
WHERE c.name = 'AppliedAt'
  AND d.parent_object_id = OBJECT_ID('dbo.SchemaVersion');

IF @DF_Name IS NOT NULL
    EXEC('ALTER TABLE [dbo].[SchemaVersion] DROP CONSTRAINT [' + @DF_Name + ']');

ALTER TABLE [dbo].[SchemaVersion] ADD DEFAULT SYSUTCDATETIME() FOR [AppliedAt];

-- Step 3: Record this migration
INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [MigrationScript])
VALUES ('1.0.2', 'Migrate datetime storage to UTC timestamps (stored by convention)', 'v1.0.1_to_v1.0.2_mssql.sql');
