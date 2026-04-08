-- Migration script to add SiteType table and replace Site.Type
CREATE TABLE [dbo].[SiteType] (
    [SiteType_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_SiteType] PRIMARY KEY ([SiteType_ID]),
    CONSTRAINT [UQ_SiteType_Name] UNIQUE ([Name])
);

GO

-- Seed SiteType lookup table
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Wastewater Treatment Plant');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Combined Sewer Overflow');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'River / Stream');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Lake / Reservoir');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Groundwater / Well');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Drinking water distribution network access point');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Canal');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Wastewater pumping station');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Combined drainage network access point');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Rainwater drainage network acces point');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Wastewater drainage network acces point');
INSERT INTO [dbo].[SiteType] ([Name]) VALUES (N'Other');

GO

-- Add SiteType_ID column to Site
ALTER TABLE [dbo].[Site] ADD [SiteType_ID] INT NULL;

GO

-- Map existing data
UPDATE [dbo].[Site] 
SET [SiteType_ID] = (SELECT [SiteType_ID] FROM [dbo].[SiteType] WHERE [Name] = N'Wastewater Treatment Plant') 
WHERE [Type] LIKE N'%Wastewater treatment plant%' OR [Type] LIKE N'WWTP%';

UPDATE [dbo].[Site] 
SET [SiteType_ID] = (SELECT [SiteType_ID] FROM [dbo].[SiteType] WHERE [Name] = N'Combined Sewer Overflow') 
WHERE [Type] LIKE N'%Combined sewer overflow%' OR [Type] LIKE N'CSO%';

-- All other unmapped values will remain NULL as per feedback.

GO

-- Add Foreign Key
ALTER TABLE [dbo].[Site] ADD CONSTRAINT [FK_Site_SiteType] FOREIGN KEY ([SiteType_ID]) REFERENCES [dbo].[SiteType] ([SiteType_ID]);

GO

-- Drop old Type column
ALTER TABLE [dbo].[Site] DROP COLUMN [Type];

GO
