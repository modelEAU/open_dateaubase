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

PRINT 'Database initialized at v1.0.0 with sample data.';
SELECT 'metadata' AS t, COUNT(*) AS n FROM dbo.metadata;
SELECT 'value' AS t, COUNT(*) AS n FROM dbo.[value];
GO
