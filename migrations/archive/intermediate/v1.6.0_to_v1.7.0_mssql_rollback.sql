-- Rollback: v1.7.0 -> v1.6.0
-- Platform: mssql
-- Generated: 2026-02-18
-- Forward:   v1.6.0_to_v1.7.0_mssql.sql

-- Drop Annotation first (depends on AnnotationType)
DROP TABLE IF EXISTS [dbo].[Annotation];
GO

DROP TABLE IF EXISTS [dbo].[AnnotationType];
GO

-- Remove SchemaVersion row
DELETE FROM [dbo].[SchemaVersion]
WHERE [Version] = '1.7.0';
GO
