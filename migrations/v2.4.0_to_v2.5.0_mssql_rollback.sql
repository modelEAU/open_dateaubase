-- Migration: v2.5.0 -> v2.4.0 (ROLLBACK)
-- Platform: mssql
-- Generated: 2026-08-04 UTC
--
-- Drops the EquipmentKind vocabulary table and its seed rows.
--
-- Every step is guarded, so re-running is a no-op.

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.5.0';
GO

IF OBJECT_ID('dbo.EquipmentKind', 'U') IS NOT NULL
BEGIN
    DROP TABLE [dbo].[EquipmentKind];
END
GO
