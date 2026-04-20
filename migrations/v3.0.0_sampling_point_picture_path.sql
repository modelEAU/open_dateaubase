-- Migration: Replace Pictures (VARBINARY MAX) with PicturePath (NVARCHAR 500)
-- on dbo.SamplingPoint. Moves sampling point photos from BLOB storage to
-- filesystem-based storage consistent with ValueImage.StoragePath.

USE open_dateaubase;
GO

ALTER TABLE [dbo].[SamplingPoint] DROP COLUMN [Pictures];
GO

ALTER TABLE [dbo].[SamplingPoint] ADD [PicturePath] NVARCHAR(500) NULL;
GO

INSERT INTO [dbo].[SchemaVersion] ([Version], [Description])
VALUES (N'3.0.2', N'Replace SamplingPoint.Pictures BLOB with PicturePath NVARCHAR(500)');
GO
