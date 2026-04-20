-- Migration: add Description column to QualityCode, SampleType, and SampleMethod
-- Version:   v3.0.0 patch
-- Rationale: Schema dictionary YAMLs define Description on these three tables
--            but the CREATE TABLE statements omitted it.
-- ============================================================

ALTER TABLE [dbo].[QualityCode]
    ADD [Description] NVARCHAR(200) NULL;
GO

ALTER TABLE [dbo].[SampleType]
    ADD [Description] NVARCHAR(200) NULL;
GO

ALTER TABLE [dbo].[SampleMethod]
    ADD [Description] NVARCHAR(200) NULL;
GO

INSERT INTO [dbo].[SchemaVersion] ([Version], [Description])
VALUES (N'3.0.2', N'Add Description column to QualityCode, SampleType, SampleMethod');
GO
