-- Migration: v1.7.0 -> v1.8.0 (ROLLBACK)
-- Platform: mssql
-- Generated: 2026-02-18
-- Rollback from: v1.8.0 to v1.7.0

-- Drop CHECK constraint
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [CK_MetaData_StatusTarget];

-- Drop FK constraints
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_StatusOfEquipmentID];
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_StatusOfMetaDataID];

-- Drop columns
ALTER TABLE [dbo].[MetaData] DROP COLUMN [StatusOfEquipmentID];
ALTER TABLE [dbo].[MetaData] DROP COLUMN [StatusOfMetaDataID];

-- Drop views (must come before table drop since they reference SensorStatusCode)
DROP VIEW IF EXISTS [dbo].[vw_DeviceStatus];
GO

DROP VIEW IF EXISTS [dbo].[vw_ChannelStatus];
GO

-- Drop SensorStatusCode table
DROP TABLE [dbo].[SensorStatusCode];
GO

-- Remove SchemaVersion row
DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.8.0';
GO