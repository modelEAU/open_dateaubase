-- Migration: v2.4.0 -> v2.5.0
-- Platform: mssql
-- Generated: 2026-08-04 UTC
-- Rollback: v2.4.0_to_v2.5.0_mssql_rollback.sql
--
-- EquipmentKind: a controlled vocabulary classifying equipment models as
-- Online sensor, Offline analyzer, Sampler or Other. Seed-only in this step —
-- nothing references it yet.
--
-- Every step is guarded, so re-running on an already-migrated database is a
-- no-op.

-- ---------------------------------------------------------------------------
-- 1. EquipmentKind
-- ---------------------------------------------------------------------------

IF OBJECT_ID('dbo.EquipmentKind', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[EquipmentKind] (
        [EquipmentKind_ID] INT IDENTITY(1,1) NOT NULL,
        [Name] NVARCHAR(100) NOT NULL,
        [Description] NVARCHAR(500),
        CONSTRAINT [PK_EquipmentKind] PRIMARY KEY ([EquipmentKind_ID])
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM [dbo].[EquipmentKind])
BEGIN
    SET IDENTITY_INSERT [dbo].[EquipmentKind] ON;
    INSERT INTO [dbo].[EquipmentKind] ([EquipmentKind_ID], [Name], [Description]) VALUES
        (1, N'Online sensor',    N'Device measuring in place and emitting a continuous signal.'),
        (2, N'Offline analyzer', N'Instrument analyzing samples brought to it, in the field or in a laboratory.'),
        (3, N'Sampler',          N'Device collecting physical samples for later analysis.'),
        (4, N'Other',            N'Equipment type not covered by the other categories.');
    SET IDENTITY_INSERT [dbo].[EquipmentKind] OFF;
END
GO

IF NOT EXISTS (SELECT 1 FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.5.0')
BEGIN
    INSERT INTO [dbo].[SchemaVersion] ([Version], [Description])
    VALUES (N'2.5.0', N'EquipmentKind, a controlled vocabulary classifying equipment models as Online sensor, Offline analyzer, Sampler or Other.');
END
GO
