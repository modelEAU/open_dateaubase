-- Migration: add ENVO_IRI to Parameter and QUDT_IRI + UnitVector to Unit
-- Schema version: v3.0.0 patch
-- Enables semantic linking to ENVO and QUDT ontologies, and SI unit vector for unit conversion.

ALTER TABLE [dbo].[Parameter] ADD [ENVO_IRI] NVARCHAR(256) NULL;
ALTER TABLE [dbo].[Unit] ADD [QUDT_IRI] NVARCHAR(256) NULL;
ALTER TABLE [dbo].[Unit] ADD [UnitVector] NVARCHAR(64) NULL;

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedDateTime], [Description], [MigrationScript])
VALUES ('3.0.0', SYSUTCDATETIME(), 'Add ENVO_IRI to Parameter, QUDT_IRI and UnitVector to Unit', 'v3.0.0_add_ontology_iris.sql');
GO
