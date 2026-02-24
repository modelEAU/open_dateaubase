-- Rollback: v1.4.0 -> v1.3.0
-- Platform: mssql
-- Generated: 2026-02-18
-- Forward migration: v1.3.0_to_v1.4.0_mssql.sql

-- ============================================================
-- Remove SamplingPoints temporal columns
-- ============================================================

ALTER TABLE [dbo].[SamplingPoints]
    DROP CONSTRAINT [FK_SamplingPoints_Campaign];
GO
ALTER TABLE [dbo].[SamplingPoints]
    DROP COLUMN [CreatedByCampaign_ID];
GO
ALTER TABLE [dbo].[SamplingPoints]
    DROP COLUMN [ValidTo];
GO
ALTER TABLE [dbo].[SamplingPoints]
    DROP COLUMN [ValidFrom];
GO

-- ============================================================
-- Drop EquipmentInstallation
-- ============================================================

DROP TABLE [dbo].[EquipmentInstallation];
GO

-- ============================================================
-- Drop EquipmentEventMetaData
-- ============================================================

DROP TABLE [dbo].[EquipmentEventMetaData];
GO

-- ============================================================
-- Drop EquipmentEvent
-- ============================================================

DROP TABLE [dbo].[EquipmentEvent];
GO

-- ============================================================
-- Drop EquipmentEventType
-- ============================================================

DROP TABLE [dbo].[EquipmentEventType];
GO

-- ============================================================
-- Remove SchemaVersion entry
-- ============================================================

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.4.0';
GO
