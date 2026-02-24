IF DB_ID(N'open_dateaubase') IS NULL
BEGIN
    CREATE DATABASE open_dateaubase;
END
GO

USE open_dateaubase;
GO

-- Step 1: Create the v1.0.0 baseline schema
:r /migrations/v1.0.0_create_mssql.sql
GO

-- Step 2: Apply the consolidated migration to v2.1.0
:r /migrations/v1.0.0_to_v2.1.0_mssql.sql
GO

-- Step 3: Load test seed data for the Quebec City monitoring scenario
:r /sql/seed_v2.1.0.sql
GO

PRINT 'Database initialized at v2.1.0 with sample data.';
SELECT [Version], [AppliedAt], [Description] FROM dbo.SchemaVersion ORDER BY [AppliedAt];
SELECT 'channel' AS t, COUNT(*) AS n FROM dbo.Channel;
SELECT 'value'   AS t, COUNT(*) AS n FROM dbo.[Value];
GO
