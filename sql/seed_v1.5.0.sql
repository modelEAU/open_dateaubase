-- Seed data for schema v1.5.0
-- Phase 2d: Ingestion Routing
--
-- Prerequisites: seed_v1.4.0.sql must have been applied.
--
-- The IngestionRoute table is populated at runtime via the backfill
-- script (migrations/data/backfill_ingestion_routes.sql) or by
-- ingestion scripts that register their own routes.
--
-- For testing purposes we insert one route pointing the seed Equipment
-- (Equipment_ID=1) + Parameter (Parameter_ID=1) + DataProvenance=Sensor
-- to the seed MetaData entry (Metadata_ID=1), active from a known date.

INSERT INTO [dbo].[IngestionRoute]
    ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree],
     [ValidFrom], [ValidTo], [Metadata_ID], [Notes])
SELECT
    m.[Equipment_ID],
    m.[Parameter_ID],
    COALESCE(m.[DataProvenance_ID], 1),          -- default to Sensor if NULL
    'Raw',
    '2000-01-01T00:00:00',                       -- default ValidFrom (beginning of time)
    NULL,                                          -- NULL = still active
    m.[Metadata_ID],
    'Seed route created by seed_v1.5.0.sql'
FROM [dbo].[MetaData] m
WHERE m.[Equipment_ID] IS NOT NULL
  AND m.[Parameter_ID] IS NOT NULL
  AND m.[Metadata_ID] = (SELECT TOP 1 [Metadata_ID] FROM [dbo].[MetaData]
                          WHERE [Equipment_ID] IS NOT NULL AND [Parameter_ID] IS NOT NULL
                          ORDER BY [Metadata_ID]);
GO
