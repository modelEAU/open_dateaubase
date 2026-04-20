-- Rollback: Restore Pictures VARBINARY(MAX) and remove PicturePath.

USE open_dateaubase;
GO

ALTER TABLE [dbo].[SamplingPoint] DROP COLUMN [PicturePath];
GO

ALTER TABLE [dbo].[SamplingPoint] ADD [Pictures] VARBINARY(MAX) NULL;
GO

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'3.0.3';
GO
