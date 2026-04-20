-- Rollback: remove Description column from QualityCode, SampleType, and SampleMethod
-- Reverts: v3.0.0_add_description_to_lookup_tables.sql
-- ============================================================

ALTER TABLE [dbo].[QualityCode]  DROP COLUMN [Description];
GO

ALTER TABLE [dbo].[SampleType]   DROP COLUMN [Description];
GO

ALTER TABLE [dbo].[SampleMethod] DROP COLUMN [Description];
GO

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'3.0.2';
GO
