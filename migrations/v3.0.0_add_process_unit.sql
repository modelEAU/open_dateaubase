-- Forward migration: add ProcessUnitType lookup and ProcessUnit hierarchy
-- Also adds nullable ProcessUnit_ID FK to SamplingPoint

-- 1. ProcessUnitType lookup table
CREATE TABLE [dbo].[ProcessUnitType] (
    [ProcessUnitType_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_ProcessUnitType] PRIMARY KEY ([ProcessUnitType_ID]),
    CONSTRAINT [UQ_ProcessUnitType_Name] UNIQUE ([Name])
);

GO

INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Area');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Zone');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Tank');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Reactor');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Pipe');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Pump');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Valve');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Clarifier');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Basin');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Blower');
INSERT INTO [dbo].[ProcessUnitType] ([Name]) VALUES (N'Other');

GO

-- 2. ProcessUnit: self-referential, site-scoped hierarchy
CREATE TABLE [dbo].[ProcessUnit] (
    [ProcessUnit_ID] INT IDENTITY(1,1) NOT NULL,
    [Site_ID] INT NOT NULL,
    [Tag] NVARCHAR(100) NOT NULL,
    [Name] NVARCHAR(255) NOT NULL,
    [Description] NVARCHAR(MAX),
    [ProcessUnitType_ID] INT,
    [Parent_ID] INT,
    CONSTRAINT [PK_ProcessUnit] PRIMARY KEY ([ProcessUnit_ID]),
    CONSTRAINT [UQ_ProcessUnit_SiteTag] UNIQUE ([Site_ID], [Tag]),
    CONSTRAINT [FK_ProcessUnit_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site]([Site_ID]),
    CONSTRAINT [FK_ProcessUnit_Type] FOREIGN KEY ([ProcessUnitType_ID]) REFERENCES [dbo].[ProcessUnitType]([ProcessUnitType_ID]),
    CONSTRAINT [FK_ProcessUnit_Parent] FOREIGN KEY ([Parent_ID]) REFERENCES [dbo].[ProcessUnit]([ProcessUnit_ID])
);

GO

-- 3. Add nullable ProcessUnit_ID FK to SamplingPoint
ALTER TABLE [dbo].[SamplingPoint] ADD [ProcessUnit_ID] INT NULL;

GO

ALTER TABLE [dbo].[SamplingPoint] ADD CONSTRAINT [FK_SamplingPoint_ProcessUnit]
    FOREIGN KEY ([ProcessUnit_ID]) REFERENCES [dbo].[ProcessUnit]([ProcessUnit_ID]);

GO
