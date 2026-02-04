-- Create database if not exists
IF DB_ID('proposed_2025_11') IS NULL
BEGIN
    CREATE DATABASE proposed_2025_11;
END
GO

USE proposed_2025_11;
GO

-- Import the real schema + data
:r /sql_generation_scripts/2025-11-27_proposed_.sql
GO
