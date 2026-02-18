-- Migration: v1.3.0 -> v1.2.0 (ROLLBACK)
-- Platform: mssql
-- Reverses: v1.2.0_to_v1.3.0_mssql.sql

-- ============================================================
-- Reverse Task 2b.3: Drop junction tables
-- ============================================================

DROP TABLE [dbo].[CampaignParameter];
GO
DROP TABLE [dbo].[CampaignEquipment];
GO
DROP TABLE [dbo].[CampaignSamplingLocation];
GO

-- ============================================================
-- Reverse Task 2b.2: Remove lab context columns from MetaData
-- ============================================================

ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_AnalystPerson];
GO
ALTER TABLE [dbo].[MetaData] DROP COLUMN [AnalystPerson_ID];
GO

ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Laboratory];
GO
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Laboratory_ID];
GO

ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Sample];
GO
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Sample_ID];
GO

-- ============================================================
-- Reverse Task 2b.1: Drop Sample and Laboratory tables
-- ============================================================

DROP TABLE [dbo].[Sample];
GO
DROP TABLE [dbo].[Laboratory];
GO

-- ============================================================
-- Update SchemaVersion
-- ============================================================

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.3.0';
GO
