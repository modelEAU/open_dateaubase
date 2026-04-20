-- Rollback: Remove QualityCode column from dbo.Value.

USE open_dateaubase;
GO

ALTER TABLE [dbo].[Value] DROP COLUMN [QualityCode];
GO

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'3.0.1';
GO
