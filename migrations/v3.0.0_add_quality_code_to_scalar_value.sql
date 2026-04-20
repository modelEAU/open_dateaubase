-- Migration: Add QualityCode column to dbo.Value (scalar payload table).
-- Brings dbo.Value in line with ValueVector / ValueMatrix / ValueImage,
-- which already carry a QualityCode INT NULL column, so that quality flags
-- can be stored and bulk-updated for all four value types uniformly.

USE open_dateaubase;
GO

ALTER TABLE [dbo].[Value] ADD [QualityCode] INT NULL;
GO

INSERT INTO [dbo].[SchemaVersion] ([Version], [Description])
VALUES (N'3.0.1', N'Add QualityCode column to dbo.Value');
GO
