IF DB_ID(N'open_dateaubase') IS NULL
BEGIN
    CREATE DATABASE open_dateaubase;
END
GO

USE open_dateaubase;
GO

-- v1.0.0: Create baseline schema and seed data
:r /migrations/v1.0.0_create_mssql.sql
GO
:r /sql/seed_v1.0.0.sql
GO

-- v1.0.1: Add SchemaVersion tracking table
:r /migrations/v1.0.0_to_v1.0.1_mssql.sql
GO
:r /sql/seed_v1.0.1.sql
GO

-- v1.0.2: UTC timestamp storage convention
:r /migrations/v1.0.1_to_v1.0.2_mssql.sql
GO
:r /sql/seed_v1.0.2.sql
GO

PRINT 'Database initialized at v1.0.2 with sample data.';
SELECT 'metadata' AS t, COUNT(*) AS n FROM dbo.metadata;
SELECT 'value' AS t, COUNT(*) AS n FROM dbo.[value];
SELECT 'schema_version' AS t, COUNT(*) AS n FROM dbo.SchemaVersion;
GO
