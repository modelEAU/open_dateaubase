-- Rollback script for SiteType addition

-- Add Type column back to Site
ALTER TABLE [dbo].[Site] ADD [Type] NVARCHAR(255) NULL;

GO

-- Map data back from SiteType
UPDATE s
SET s.[Type] = st.[Name]
FROM [dbo].[Site] s
JOIN [dbo].[SiteType] st ON s.[SiteType_ID] = st.[SiteType_ID];

GO

-- Drop Foreign Key and new column
ALTER TABLE [dbo].[Site] DROP CONSTRAINT [FK_Site_SiteType];
ALTER TABLE [dbo].[Site] DROP COLUMN [SiteType_ID];

GO

-- Drop SiteType table
DROP TABLE [dbo].[SiteType];

GO
