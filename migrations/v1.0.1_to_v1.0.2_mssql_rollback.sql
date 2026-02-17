-- Migration: v1.0.2 -> v1.0.1 (ROLLBACK)
-- Platform: mssql
-- Description: Revert UTC datetime back to integer epoch
-- Rollback: v1.0.1_to_v1.0.2_mssql.sql

-- Step 1: Value.Timestamp — convert DATETIME2(7) back to INT (Unix epoch)
-- Each DDL step must be in its own batch so SQL Server can resolve the new column name.
ALTER TABLE [dbo].[Value] ADD [Timestamp_old] INT NULL;
GO

UPDATE [dbo].[Value]
SET [Timestamp_old] = CASE
    WHEN [Timestamp] IS NOT NULL
    THEN DATEDIFF(SECOND, CAST('1970-01-01T00:00:00' AS DATETIME2), [Timestamp])
    ELSE NULL
END;
GO

ALTER TABLE [dbo].[Value] DROP COLUMN [Timestamp];
GO

EXEC sp_rename 'dbo.Value.Timestamp_old', 'Timestamp', 'COLUMN';
GO

-- Step 2: SchemaVersion.AppliedAt — revert default to CURRENT_TIMESTAMP
-- The column type is already DATETIME2(7); only the default constraint changes.
DECLARE @DF_Name NVARCHAR(200);
SELECT @DF_Name = d.name
FROM sys.default_constraints d
JOIN sys.columns c ON d.parent_column_id = c.column_id AND d.parent_object_id = c.object_id
WHERE c.name = 'AppliedAt'
  AND d.parent_object_id = OBJECT_ID('dbo.SchemaVersion');

IF @DF_Name IS NOT NULL
    EXEC('ALTER TABLE [dbo].[SchemaVersion] DROP CONSTRAINT [' + @DF_Name + ']');

ALTER TABLE [dbo].[SchemaVersion] ADD DEFAULT CURRENT_TIMESTAMP FOR [AppliedAt];

-- Step 3: Remove version record
DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.0.2';
