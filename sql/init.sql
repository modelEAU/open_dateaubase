IF DB_ID(N'open_dateaubase') IS NULL
BEGIN
    CREATE DATABASE open_dateaubase;
END
GO

USE open_dateaubase;
GO

-- Full schema — generated from schema_dictionary/tables/*.yaml via `uv run mkdocs build`
:r /sql_generation_scripts/v4.0.0_create_mssql.sql
GO

-- Vocabulary seed: units, parameters, procedures, one TEST_ watershed, one TEST_ lab.
-- No equipment, sites, campaigns, or channels — those are created by the importer.
:r /sql/seed_vocabulary.sql
GO

PRINT 'Database initialized with sample data.';
SELECT [Version], [AppliedDateTime], [Description] FROM dbo.SchemaVersion ORDER BY [AppliedDateTime];
SELECT 'channel'     AS t, COUNT(*) AS n FROM dbo.Channel;
SELECT 'value'       AS t, COUNT(*) AS n FROM dbo.[Value];
SELECT 'valuevector' AS t, COUNT(*) AS n FROM dbo.ValueVector;
SELECT 'valuematrix' AS t, COUNT(*) AS n FROM dbo.ValueMatrix;
SELECT 'valueimage'  AS t, COUNT(*) AS n FROM dbo.ValueImage;
GO
