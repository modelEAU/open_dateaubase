-- Rollback: remove ENVO_IRI from Parameter and QUDT_IRI + UnitVector from Unit
-- Reverses: v3.0.0_add_ontology_iris.sql

ALTER TABLE [dbo].[Parameter] DROP COLUMN [ENVO_IRI];
ALTER TABLE [dbo].[Unit] DROP COLUMN [QUDT_IRI];
ALTER TABLE [dbo].[Unit] DROP COLUMN [UnitVector];
