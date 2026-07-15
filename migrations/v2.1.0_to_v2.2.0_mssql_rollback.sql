-- Migration: v2.2.0 -> v2.1.0 (ROLLBACK)
-- Platform: mssql
-- Generated: 2026-07-07 20:02:52 UTC
-- Rollback: v2.2.0_to_v2.1.0_mssql_rollback.sql


DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.2.0';

ALTER TABLE [dbo].[LabPanel] DROP CONSTRAINT [FK_LabPanel_DefaultSampleKind_ID];

ALTER TABLE [dbo].[LabPanel] DROP CONSTRAINT [FK_LabPanel_DefaultSampleMaterialKind_ID];

ALTER TABLE [dbo].[Sample] DROP CONSTRAINT [FK_Sample_SampleMaterialKind_ID];

-- Revert SampleCollectionKind_ID / SampleKind_ID from IDENTITY back to a plain
-- manually-assigned INT PK (rebuild via #temp, mirroring the forward migration).
SELECT [SampleCollectionKind_ID], [Name], [Description]
    INTO #SampleCollectionKind_bak FROM [dbo].[SampleCollectionKind];
GO
ALTER TABLE [dbo].[Sample] DROP CONSTRAINT [FK_Sample_SampleCollectionKind_ID];
ALTER TABLE [dbo].[LabPanel] DROP CONSTRAINT [FK_LabPanel_DefaultSampleCollectionKind_ID];
DROP TABLE [dbo].[SampleCollectionKind];
GO
CREATE TABLE [dbo].[SampleCollectionKind] (
    [SampleCollectionKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SampleCollectionKind] PRIMARY KEY ([SampleCollectionKind_ID])
);
GO
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description])
    SELECT [SampleCollectionKind_ID], [Name], [Description] FROM #SampleCollectionKind_bak;
DROP TABLE #SampleCollectionKind_bak;
GO
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SampleCollectionKind_ID] FOREIGN KEY ([SampleCollectionKind_ID]) REFERENCES [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID]);
ALTER TABLE [dbo].[LabPanel] ADD CONSTRAINT [FK_LabPanel_DefaultSampleCollectionKind_ID] FOREIGN KEY ([DefaultSampleCollectionKind_ID]) REFERENCES [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID]);
GO

SELECT [SampleKind_ID], [Name], [Description]
    INTO #SampleKind_bak FROM [dbo].[SampleKind];
GO
ALTER TABLE [dbo].[Sample] DROP CONSTRAINT [FK_Sample_SampleKind_ID];
DROP TABLE [dbo].[SampleKind];
GO
CREATE TABLE [dbo].[SampleKind] (
    [SampleKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SampleKind] PRIMARY KEY ([SampleKind_ID])
);
GO
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description])
    SELECT [SampleKind_ID], [Name], [Description] FROM #SampleKind_bak;
DROP TABLE #SampleKind_bak;
GO
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SampleKind_ID] FOREIGN KEY ([SampleKind_ID]) REFERENCES [dbo].[SampleKind] ([SampleKind_ID]);

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.LabPanel') AND c.name = 'DefaultSampleKind_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[LabPanel] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[LabPanel] DROP COLUMN [DefaultSampleKind_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.LabPanel') AND c.name = 'DefaultSampleMaterialKind_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[LabPanel] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[LabPanel] DROP COLUMN [DefaultSampleMaterialKind_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Sample') AND c.name = 'SampleMaterialKind_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Sample] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[Sample] DROP COLUMN [SampleMaterialKind_ID];

DROP TABLE [dbo].[SampleMaterialKind];
