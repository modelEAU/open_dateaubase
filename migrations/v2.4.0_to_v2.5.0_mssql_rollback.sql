-- Migration: v2.5.0 -> v2.4.0 (ROLLBACK)
-- Platform: mssql
-- Generated: 2026-08-04 UTC
--
-- Drops vw_UnclassifiedEquipment, EquipmentModel.EquipmentKind_ID and the
-- EquipmentKind vocabulary table with its seed rows.
--
-- Every step is guarded, so re-running is a no-op.

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.5.0';
GO

IF OBJECT_ID('dbo.vw_UnclassifiedEquipment', 'V') IS NOT NULL
BEGIN
    DROP VIEW [dbo].[vw_UnclassifiedEquipment];
END
GO

IF OBJECT_ID('dbo.FK_EquipmentModel_EquipmentKind_ID', 'F') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[EquipmentModel] DROP CONSTRAINT [FK_EquipmentModel_EquipmentKind_ID];
END
GO

IF COL_LENGTH('dbo.EquipmentModel', 'EquipmentKind_ID') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[EquipmentModel] DROP COLUMN [EquipmentKind_ID];
END
GO

IF OBJECT_ID('dbo.EquipmentKind', 'U') IS NOT NULL
BEGIN
    DROP TABLE [dbo].[EquipmentKind];
END
GO
