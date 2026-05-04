IF DB_ID(N'open_dateaubase') IS NULL
BEGIN
    CREATE DATABASE open_dateaubase;
END
GO

USE open_dateaubase;
GO

-- Full schema — generated from schema_dictionary/tables/*.yaml via `uv run mkdocs build`
:r /sql_generation_scripts/v4.1.0_create_mssql.sql
GO

-- Vocabulary seed (auto-generated from YAML seed_data fields):
-- ValueKind, ChannelKind, DataProvenanceKind, ProcessingKind,
-- SignalInterfaceKind, SignalInterfacePortKind, QualityCode, AnnotationKind,
-- BinKind, CampaignKind, EquipmentEventKind, ControlLoopPortKind,
-- ProcessUnitKind, SampleKind, SampleCollectionKind, Unit, Parameter, ParameterHasUnit.
:r /sql_generation_scripts/v4.1.0_seed_mssql.sql
GO

-- Fixture seed: units, parameters, procedures, one TEST_ watershed, one TEST_ lab.
-- No equipment, sites, campaigns, or channels — those are created by the importer.
:r /sql/seed_fixtures.sql
GO

PRINT 'Database initialized with sample data (schema + generated vocabulary seed + fixtures).';
SELECT [Version], [AppliedDateTime], [Description] FROM dbo.SchemaVersion ORDER BY [AppliedDateTime];
SELECT 'channel'     AS t, COUNT(*) AS n FROM dbo.Channel;
SELECT 'value'       AS t, COUNT(*) AS n FROM dbo.[Value];
SELECT 'valuevector' AS t, COUNT(*) AS n FROM dbo.ValueVector;
SELECT 'valuematrix' AS t, COUNT(*) AS n FROM dbo.ValueMatrix;
SELECT 'valueimage'  AS t, COUNT(*) AS n FROM dbo.ValueImage;
GO
