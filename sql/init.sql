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

-- Step 4: Load Explore page demonstration data (Feb 2026, all four value types)
:r /sql/seed_explore.sql
GO

PRINT 'Database initialized at v2.1.0 with sample data.';
SELECT [Version], [AppliedDateTime], [Description] FROM dbo.SchemaVersion ORDER BY [AppliedDateTime];
SELECT 'channel'     AS t, COUNT(*) AS n FROM dbo.Channel;
SELECT 'value'       AS t, COUNT(*) AS n FROM dbo.[Value];
SELECT 'valuevector' AS t, COUNT(*) AS n FROM dbo.ValueVector;
SELECT 'valuematrix' AS t, COUNT(*) AS n FROM dbo.ValueMatrix;
SELECT 'valueimage'  AS t, COUNT(*) AS n FROM dbo.ValueImage;
GO
