-- Create database if not exists
IF DB_ID('proposed_2025_11') IS NULL
BEGIN
    CREATE DATABASE proposed_2025_11;
END
GO

USE proposed_2025_11;
GO

-- Import schema
:r /sql_generation_scripts/2025-11-27_proposed_.sql
GO

:r /sql_generation_scripts/2025-11-27_seed_test_data.sql
GO

-- Sanity checks
PRINT 'DB init OK - tables check';
SELECT 'metadata' AS t, COUNT(*) AS n FROM dbo.metadata;
SELECT 'value' AS t, COUNT(*) AS n FROM dbo.[value];
GO
