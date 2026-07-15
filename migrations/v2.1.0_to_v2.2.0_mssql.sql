-- Migration: v2.1.0 -> v2.2.0
-- Platform: mssql
-- Generated: 2026-07-07 20:02:52 UTC
-- Rollback: v2.1.0_to_v2.2.0_mssql_rollback.sql


CREATE TABLE [dbo].[SampleMaterialKind] (
    [SampleMaterialKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SampleMaterialKind] PRIMARY KEY ([SampleMaterialKind_ID])
);

ALTER TABLE [dbo].[LabPanel] ADD [DefaultSampleKind_ID] INT;

ALTER TABLE [dbo].[LabPanel] ADD [DefaultSampleMaterialKind_ID] INT;

ALTER TABLE [dbo].[Sample] ADD [SampleMaterialKind_ID] INT;

-- Convert SampleCollectionKind_ID / SampleKind_ID to IDENTITY. MSSQL has no
-- in-place ALTER for this, so each table is rebuilt: stash rows in a #temp,
-- drop inbound FKs + the table, recreate with IDENTITY, re-insert preserving
-- the seeded IDs (IDENTITY_INSERT reseeds the counter to MAX), re-add FKs.
-- Hand-written: the generator renders an identity change as a no-op ALTER.
SELECT [SampleCollectionKind_ID], [Name], [Description]
    INTO #SampleCollectionKind_bak FROM [dbo].[SampleCollectionKind];
GO
ALTER TABLE [dbo].[Sample] DROP CONSTRAINT [FK_Sample_SampleCollectionKind_ID];
ALTER TABLE [dbo].[LabPanel] DROP CONSTRAINT [FK_LabPanel_DefaultSampleCollectionKind_ID];
DROP TABLE [dbo].[SampleCollectionKind];
GO
CREATE TABLE [dbo].[SampleCollectionKind] (
    [SampleCollectionKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SampleCollectionKind] PRIMARY KEY ([SampleCollectionKind_ID])
);
GO
SET IDENTITY_INSERT [dbo].[SampleCollectionKind] ON;
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description])
    SELECT [SampleCollectionKind_ID], [Name], [Description] FROM #SampleCollectionKind_bak;
SET IDENTITY_INSERT [dbo].[SampleCollectionKind] OFF;
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
    [SampleKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SampleKind] PRIMARY KEY ([SampleKind_ID])
);
GO
SET IDENTITY_INSERT [dbo].[SampleKind] ON;
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description])
    SELECT [SampleKind_ID], [Name], [Description] FROM #SampleKind_bak;
SET IDENTITY_INSERT [dbo].[SampleKind] OFF;
DROP TABLE #SampleKind_bak;
GO
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SampleKind_ID] FOREIGN KEY ([SampleKind_ID]) REFERENCES [dbo].[SampleKind] ([SampleKind_ID]);
GO

ALTER TABLE [dbo].[LabPanel] ADD CONSTRAINT [FK_LabPanel_DefaultSampleKind_ID] FOREIGN KEY ([DefaultSampleKind_ID]) REFERENCES [dbo].[SampleKind] ([SampleKind_ID]);

ALTER TABLE [dbo].[LabPanel] ADD CONSTRAINT [FK_LabPanel_DefaultSampleMaterialKind_ID] FOREIGN KEY ([DefaultSampleMaterialKind_ID]) REFERENCES [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID]);

ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SampleMaterialKind_ID] FOREIGN KEY ([SampleMaterialKind_ID]) REFERENCES [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID]);

-- SampleMaterialKind
SET IDENTITY_INSERT [dbo].[SampleMaterialKind] ON;
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (1, N'grit', N'Sand, gravel, and heavy inert solids removed at the headworks');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (2, N'domestic wastewater', N'Sanitary sewage of primarily domestic origin');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (3, N'combined wastewater', N'Mixed sanitary and stormwater flow from a combined sewer');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (4, N'stormwater', N'Runoff collected from rainfall or snowmelt');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (5, N'preliminary effluent', N'Flow after preliminary treatment (screening, grit removal)');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (6, N'primary effluent', N'Clarified flow leaving primary settling');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (7, N'secondary effluent', N'Clarified flow leaving secondary (biological) treatment');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (8, N'tertiary effluent', N'Flow leaving tertiary/advanced treatment or final polishing');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (9, N'mixed liquor', N'Aerated mixture of wastewater and activated sludge in the bioreactor');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (10, N'settled activated sludge', N'Settled biomass returned or wasted from clarifiers (RAS/WAS)');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (11, N'floating activated sludge', N'Poorly-settling (bulking) flocs floating at the surface of basins or clarifiers');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (12, N'sludge blanket', N'Settled sludge layer at the bottom of a clarifier or thickener');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (13, N'scum/foam', N'Floating scum or biological foam skimmed from tank surfaces');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (14, N'digester sludge', N'Sludge inside an anaerobic or aerobic digester');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (15, N'digestate', N'Combined liquid/solid output of a digestion process');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (16, N'digested sludge', N'Stabilised sludge withdrawn after digestion');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (17, N'dewatered sludge', N'Sludge cake after mechanical dewatering');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (18, N'dried sludge', N'Thermally or air-dried sludge solids');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (19, N'concentrate', N'Reject/retentate stream from a membrane process');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (20, N'permeate', N'Filtered stream passing through a membrane');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (21, N'tap water', N'Potable water from the distribution network');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (22, N'demineralized water', N'Water with dissolved minerals removed');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (23, N'deionized water', N'Water with ions removed by ion exchange');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (24, N'nanofiltered water', N'Water treated by nanofiltration');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (25, N'ultrafiltered water', N'Water treated by ultrafiltration');
SET IDENTITY_INSERT [dbo].[SampleMaterialKind] OFF;

INSERT INTO [dbo].[SchemaVersion] ([Version], [Description]) VALUES (N'2.2.0', N'Adds SampleMaterialKind controlled vocabulary describing a sample''s physical matrix (grit, wastewater, mixed liquor, sludges, membrane and reference waters), orthogonal to SampleKind''s analytical role. Sample gains a nullable SampleMaterialKind_ID FK; LabPanel gains DefaultSampleKind_ID and DefaultSampleMaterialKind_ID so panels can pre-fill both role and matrix. See migrations/v2.1.0_to_v2.2.0_mssql.sql.');
